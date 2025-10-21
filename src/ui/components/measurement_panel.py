"""
Measurement configuration panel for I-V sweep settings with integrated visualization.
"""

import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QFileDialog,
    QMessageBox, QProgressBar, QSplitter, QFrame, QToolBar,
    QComboBox, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

# Import for real-time plotting
import numpy as np
import numpy.linalg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Import theme and CustomNavigationToolbar
from ui.components.visualization_panel import CustomNavigationToolbar
from ..theme import AppTheme, PlotTheme

# Setup matplotlib
PlotTheme.setup_matplotlib()


class StatusIndicator(QLabel):
    """Custom label that shows status with color."""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(100)
        self.setStyleSheet("border-radius: 5px; padding: 5px;")
        self.set_status("idle")
        
    def set_status(self, status):
        """Set the status and update the appearance."""
        if status == "idle":
            self.setStyleSheet("background-color: #f0f0f0; color: #333; border-radius: 5px; padding: 5px;")
            self.setText("Ready")
        elif status == "running":
            self.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px;")
            self.setText("Running")
        elif status == "completed":
            self.setStyleSheet("background-color: #2196F3; color: white; border-radius: 5px; padding: 5px;")
            self.setText("Completed")
        elif status == "error":
            self.setStyleSheet("background-color: #f44336; color: white; border-radius: 5px; padding: 5px;")
            self.setText("Error")
        elif status == "stopped":
            self.setStyleSheet("background-color: #FF9800; color: white; border-radius: 5px; padding: 5px;")
            self.setText("Stopped")


class MeasurementPanel(QWidget):
    """Panel for configuring I-V sweep measurements with integrated visualization."""
    
    # Signals
    measurement_started = pyqtSignal(dict)  # Emits measurement parameters
    measurement_stopped = pyqtSignal()
    update_plot_signal = pyqtSignal(dict)  # For forwarding plot updates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get centralized theme colors and styles
        self.colors = AppTheme.get_colors()
        self.HEADER_STYLE = f"QLabel {{ font-size: 16px; font-weight: bold; color: {self.colors['text']}; }}"
        self.GROUP_STYLE = AppTheme.group_box_style()
        self.BUTTON_STYLE = AppTheme.button_style()
        self.START_BUTTON_STYLE = AppTheme.primary_button_style()
        self.STOP_BUTTON_STYLE = AppTheme.danger_button_style()
        self.SECTION_SEPARATOR_STYLE = AppTheme.section_separator_style()
        
        # Removed presets - keeping only manual configuration
        
        # Main layout with splitter
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        
        # Create toolbar with presets
        self.create_toolbar()
        
        # Create splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Left panel for settings
        self.settings_panel = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_panel)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # Right panel for real-time visualization
        self.visualization_panel = QWidget()
        self.visualization_layout = QVBoxLayout(self.visualization_panel)
        self.visualization_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add panels to splitter
        self.splitter.addWidget(self.settings_panel)
        self.splitter.addWidget(self.visualization_panel)
        self.splitter.setSizes([350, 650])  # Initial sizes
        
        # Setup settings panel
        self.create_settings_header()
        self.create_sweep_settings()
        self.create_dc_bias_settings()
        self.create_pm100d_settings()
        self.create_save_settings()
        self.create_control_buttons()
        self.create_progress_section()
        self.settings_layout.addStretch()
        
        # Setup visualization
        self.setup_visualization()
        
        # Set initial state
        self.instrument = None
        self.instrument2 = None
        self.pm100d_instrument = None
        self.dual_mode = False
        self.is_measuring = False
        self.current_data = {"voltage": [], "current": [], "power": [], "voltage_reverse": [], "current_reverse": [], "power_reverse": []}
        self.update_ui_state()
    
    def create_toolbar(self):
        """Create a toolbar with preset configurations."""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setStyleSheet(f"""
            QToolBar {{
                spacing: 6px;
                background-color: {self.colors['darker']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
            }}
            QToolButton {{
                background-color: transparent;
                border-radius: 3px;
                padding: 3px;
                color: {self.colors['text']};
            }}
            QToolButton:hover {{
                background-color: {self.colors['light']};
            }}
        """)
        
        # Removed preset functionality - keeping only mode selector
        
        # Measurement mode selector
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet(f"font-weight: bold; padding-right: 5px; color: {self.colors['text']};")
        toolbar.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["I-V Sweep", "Dual Keithley", "P-I-V Measurement"])
        self.mode_combo.setMinimumWidth(150)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                border: 2px solid {self.colors['primary']};
                border-radius: 6px;
                padding: 6px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                font-weight: bold;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 2px solid {self.colors['secondary']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {self.colors['border']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
            }}
        """)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        toolbar.addWidget(self.mode_combo)
        
        toolbar.addSeparator()
        
        self.main_layout.addWidget(toolbar)
    
    def create_settings_header(self):
        """Create a header for the settings panel."""
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Measurement Configuration")
        title.setStyleSheet(self.HEADER_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title)
        
        # Status indicator
        self.status_indicator = StatusIndicator()
        header_layout.addWidget(self.status_indicator)
        
        self.settings_layout.addLayout(header_layout)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(self.SECTION_SEPARATOR_STYLE)
        self.settings_layout.addWidget(separator)
    
    def create_sweep_settings(self):
        """Create sweep settings group."""
        group_box = QGroupBox("Sweep Settings")
        group_box.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Input field styling
        input_style = f"""
            QSpinBox, QDoubleSpinBox {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {self.colors['primary']};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                width: 16px;
                border-radius: 0px;
                background-color: {self.colors['button']};
            }}
        """
        
        # Start voltage
        self.start_voltage_spin = QDoubleSpinBox()
        self.start_voltage_spin.setRange(-10.0, 10.0)
        self.start_voltage_spin.setValue(0.0)
        self.start_voltage_spin.setSuffix(" V")
        self.start_voltage_spin.setDecimals(3)
        self.start_voltage_spin.setSingleStep(0.1)
        self.start_voltage_spin.setToolTip("Starting voltage for the sweep measurement")
        self.start_voltage_spin.setStyleSheet(input_style)
        form_layout.addRow("Start Voltage:", self.start_voltage_spin)
        
        # Stop voltage
        self.stop_voltage_spin = QDoubleSpinBox()
        self.stop_voltage_spin.setRange(-10.0, 10.0)
        self.stop_voltage_spin.setValue(0.8)
        self.stop_voltage_spin.setSuffix(" V")
        self.stop_voltage_spin.setDecimals(3)
        self.stop_voltage_spin.setSingleStep(0.1)
        self.stop_voltage_spin.setToolTip("Ending voltage for the sweep measurement")
        self.stop_voltage_spin.setStyleSheet(input_style)
        form_layout.addRow("Stop Voltage:", self.stop_voltage_spin)
        
        # Number of points
        self.num_points_spin = QSpinBox()
        self.num_points_spin.setRange(10, 500)
        self.num_points_spin.setValue(100)
        self.num_points_spin.setToolTip("Number of measurement points to take during the sweep")
        self.num_points_spin.setStyleSheet(input_style)
        form_layout.addRow("Number of Points:", self.num_points_spin)
        
        # Current compliance
        self.compliance_spin = QDoubleSpinBox()
        self.compliance_spin.setRange(0.001, 1.0)
        self.compliance_spin.setValue(0.01)
        self.compliance_spin.setSuffix(" A")
        self.compliance_spin.setDecimals(3)
        self.compliance_spin.setSingleStep(0.001)
        self.compliance_spin.setToolTip("Maximum current allowed during measurement (compliance)")
        self.compliance_spin.setStyleSheet(input_style)
        form_layout.addRow("Current Compliance:", self.compliance_spin)
        
        # Bidirectional sweep with improved checkbox styling
        checkbox_style = f"""
            QCheckBox {{
                spacing: 5px;
                color: {self.colors['text']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid {self.colors['border']};
                background-color: {self.colors['input']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 1px solid {self.colors['primary']};
            }}
        """
        
        self.bidirectional_check = QCheckBox("Enable")
        self.bidirectional_check.setChecked(True)
        self.bidirectional_check.setToolTip("Measure both up and down sweeps")
        self.bidirectional_check.setStyleSheet(checkbox_style)
        form_layout.addRow("Bidirectional Sweep:", self.bidirectional_check)
        
        group_box.setLayout(form_layout)
        self.settings_layout.addWidget(group_box)
        self.sweep_group = group_box  # Store reference for mode switching
    
    def create_dc_bias_settings(self):
        """Create DC bias settings group for dual mode."""
        self.dc_bias_group = QGroupBox("DC Bias Settings (Instrument 1)")
        self.dc_bias_group.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Input field styling
        input_style = f"""
            QDoubleSpinBox {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
            }}
            QDoubleSpinBox:focus {{
                border: 1px solid {self.colors['primary']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 16px;
                border-radius: 0px;
                background-color: {self.colors['button']};
            }}
        """
        
        # DC bias voltage
        self.dc_bias_voltage_spin = QDoubleSpinBox()
        self.dc_bias_voltage_spin.setRange(-10.0, 10.0)
        self.dc_bias_voltage_spin.setValue(0.0)
        self.dc_bias_voltage_spin.setSuffix(" V")
        self.dc_bias_voltage_spin.setDecimals(3)
        self.dc_bias_voltage_spin.setSingleStep(0.1)
        self.dc_bias_voltage_spin.setToolTip("DC bias voltage applied by Instrument 1")
        self.dc_bias_voltage_spin.setStyleSheet(input_style)
        form_layout.addRow("DC Bias Voltage:", self.dc_bias_voltage_spin)
        
        # DC bias compliance
        self.dc_bias_compliance_spin = QDoubleSpinBox()
        self.dc_bias_compliance_spin.setRange(0.001, 1.0)
        self.dc_bias_compliance_spin.setValue(0.01)
        self.dc_bias_compliance_spin.setSuffix(" A")
        self.dc_bias_compliance_spin.setDecimals(3)
        self.dc_bias_compliance_spin.setSingleStep(0.001)
        self.dc_bias_compliance_spin.setToolTip("Current compliance for DC bias source")
        self.dc_bias_compliance_spin.setStyleSheet(input_style)
        form_layout.addRow("DC Bias Compliance:", self.dc_bias_compliance_spin)
        
        self.dc_bias_group.setLayout(form_layout)
        self.settings_layout.addWidget(self.dc_bias_group)
        
        # Initially hide the DC bias group
        self.dc_bias_group.hide()
    
    def create_pm100d_settings(self):
        """Create PM100D settings group for P-I-V measurement."""
        self.pm100d_group = QGroupBox("PM100D Power Meter Settings")
        self.pm100d_group.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        
        # Input field styling
        input_style = f"""
            QSpinBox, QDoubleSpinBox, QComboBox {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
                min-height: 25px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
                border: 1px solid {self.colors['primary']};
            }}
        """
        
        # Wavelength setting
        self.pm100d_wavelength_spin = QSpinBox()
        self.pm100d_wavelength_spin.setRange(200, 2000)
        self.pm100d_wavelength_spin.setValue(800)  # Default wavelength
        self.pm100d_wavelength_spin.setSuffix(" nm")
        self.pm100d_wavelength_spin.setToolTip("Wavelength for power measurement")
        self.pm100d_wavelength_spin.setStyleSheet(input_style)
        form_layout.addRow("Wavelength:", self.pm100d_wavelength_spin)
        
        # Range mode selection
        self.pm100d_range_combo = QComboBox()
        self.pm100d_range_combo.addItems(["Auto", "Manual"])
        self.pm100d_range_combo.setToolTip("Power range mode")
        self.pm100d_range_combo.setStyleSheet(input_style)
        self.pm100d_range_combo.currentTextChanged.connect(self.on_pm100d_range_changed)
        form_layout.addRow("Range Mode:", self.pm100d_range_combo)
        
        # Manual range setting (initially hidden)
        self.pm100d_manual_range_spin = QDoubleSpinBox()
        self.pm100d_manual_range_spin.setRange(0.001, 10.0)
        self.pm100d_manual_range_spin.setValue(0.01)
        self.pm100d_manual_range_spin.setDecimals(3)
        self.pm100d_manual_range_spin.setSuffix(" W")
        self.pm100d_manual_range_spin.setToolTip("Manual power range in Watts")
        self.pm100d_manual_range_spin.setStyleSheet(input_style)
        form_layout.addRow("Manual Range:", self.pm100d_manual_range_spin)
        
        # Initially hide manual range
        self.pm100d_manual_range_spin.hide()
        form_layout.labelForField(self.pm100d_manual_range_spin).hide()
        
        self.pm100d_group.setLayout(form_layout)
        self.settings_layout.addWidget(self.pm100d_group)
        
        # Initially hide the PM100D group
        self.pm100d_group.hide()
    
    def on_pm100d_range_changed(self, range_mode):
        """Handle PM100D range mode change."""
        if range_mode == "Manual":
            self.pm100d_manual_range_spin.show()
            form_layout = self.pm100d_group.layout()
            for i in range(form_layout.rowCount()):
                if form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole) and form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget() == form_layout.labelForField(self.pm100d_manual_range_spin):
                    form_layout.labelForField(self.pm100d_manual_range_spin).show()
                    break
        else:
            self.pm100d_manual_range_spin.hide()
            form_layout = self.pm100d_group.layout()
            for i in range(form_layout.rowCount()):
                if form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole) and form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget() == form_layout.labelForField(self.pm100d_manual_range_spin):
                    form_layout.labelForField(self.pm100d_manual_range_spin).hide()
                    break
    
    def create_save_settings(self):
        """Create save settings group."""
        # Add separator before save settings
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(self.SECTION_SEPARATOR_STYLE)
        separator.setMaximumHeight(2)
        self.settings_layout.addWidget(separator)
        
        group_box = QGroupBox("Save Settings")
        group_box.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Device name
        device_layout = QHBoxLayout()
        device_layout.setSpacing(10)  # Increased spacing between elements
        
        self.device_name_edit = QLineEdit("Data/Glasgow/BlockA/5-7")
        self.device_name_edit.setMinimumWidth(250)  # Ensure minimum width
        self.device_name_edit.setToolTip("Directory/path where data will be saved")
        # Apply elided text in the middle of long paths
        self.device_name_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
        """)
        device_layout.addWidget(self.device_name_edit, 1)  # Give text field stretch priority
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFixedWidth(80)  # Fixed width instead of maximum
        self.browse_button.clicked.connect(self.on_browse_clicked)
        self.browse_button.setStyleSheet(self.BUTTON_STYLE)
        self.browse_button.setToolTip("Select a directory to save data")
        device_layout.addWidget(self.browse_button)
        
        device_container = QWidget()
        device_container.setLayout(device_layout)
        form_layout.addRow("Device Name:", device_container)
        
        # Save files checkbox
        save_files_layout = QHBoxLayout()
        self.save_files_check = QCheckBox("Enable")
        self.save_files_check.setChecked(True)
        self.save_files_check.setToolTip("Save measurement data to files")
        save_files_layout.addWidget(self.save_files_check)
        save_files_layout.addStretch()
        
        save_files_container = QWidget()
        save_files_container.setLayout(save_files_layout)
        form_layout.addRow("Save Files:", save_files_container)
        
        group_box.setLayout(form_layout)
        self.settings_layout.addWidget(group_box)
    
    
    def create_control_buttons(self):
        """Create measurement control buttons."""
        # Add separator before control buttons
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(self.SECTION_SEPARATOR_STYLE)
        separator.setMaximumHeight(2)
        self.settings_layout.addWidget(separator)
        
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Measurement")
        self.start_button.clicked.connect(self.on_start_clicked)
        self.start_button.setStyleSheet(self.START_BUTTON_STYLE)
        self.start_button.setMinimumHeight(40)
        self.start_button.setToolTip("Start a new measurement with the current settings")
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Measurement")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setStyleSheet(self.STOP_BUTTON_STYLE)
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setToolTip("Stop the current measurement")
        button_layout.addWidget(self.stop_button)
        
        self.settings_layout.addLayout(button_layout)
    
    def create_progress_section(self):
        """Create progress bar and status section."""
        # Add separator before progress section
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(self.SECTION_SEPARATOR_STYLE)
        separator.setMaximumHeight(2)
        self.settings_layout.addWidget(separator)
        
        # Status label (compact, without group box)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            background-color: {self.colors['input']};
            color: {self.colors['text_secondary']};
            font-weight: bold;
            font-size: 13px;
        """)
        self.settings_layout.addWidget(self.status_label)
        
        # Progress bar with modern styling - more prominent
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(30)  # Make it taller
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {self.colors['primary']};
                border-radius: 8px;
                text-align: center;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                height: 30px;
                font-size: 14px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.colors['primary']}, stop:1 #3498db);
                border-radius: 6px;
            }}
        """)
        self.settings_layout.addWidget(self.progress_bar)
        
        # Initially hide progress bar
        self.progress_bar.hide()
    
    def setup_visualization(self):
        """Set up real-time visualization panel."""
        # Add title
        title = QLabel("Live Measurement")
        title.setStyleSheet(self.HEADER_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visualization_layout.addWidget(title)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(self.SECTION_SEPARATOR_STYLE)
        self.visualization_layout.addWidget(separator)
        
        # Create plot container that will expand to fill available space
        plot_container = QWidget()
        plot_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create matplotlib figure and canvas with improved styling
        self.figure = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(300)
        
        # Add toolbar with custom styling
        self.toolbar = CustomNavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                spacing: 6px;
                background-color: {self.colors['darker']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
            }}
            QToolButton {{
                background-color: transparent;
                border-radius: 3px;
                padding: 3px;
                color: {self.colors['text']};
            }}
            QToolButton:hover {{
                background-color: {self.colors['light']};
            }}
        """)
        
        # Add clear plot functionality to toolbar
        self.toolbar.add_clear_button(self.clear_plot)
        
        # Create the plot with enhanced styling - use subplots for P-I-V mode
        self.ax = self.figure.add_subplot(111)
        self.ax_power = None  # Will be created for P-I-V mode
        self.customize_plot()
        
        # Add to plot container
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        # Add plot container to main visualization layout
        self.visualization_layout.addWidget(plot_container, 1)  # Stretch factor of 1
        
        # Create button bar (no buttons, export and clear moved to toolbar)
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Just a spacer to keep layout consistent
        self.visualization_layout.addLayout(button_layout)
        
        # Force figure to fill canvas
        self.canvas.draw()
    
    def customize_plot(self, is_piv_mode=False):
        """Apply custom styling to the plot."""
        if is_piv_mode:
            # Clear existing subplot and create two subplots for P-I-V mode with better spacing
            self.figure.clear()
            # Use constrained_layout for better spacing, or manually adjust
            self.figure.subplots_adjust(left=0.08, right=0.95, bottom=0.12, top=0.92, wspace=0.25)
            self.ax = self.figure.add_subplot(121)  # Left plot for I-V
            self.ax_power = self.figure.add_subplot(122)  # Right plot for P-V
        else:
            # Single plot mode
            if self.ax_power is not None:
                self.figure.clear()
                self.figure.subplots_adjust(left=0.1, right=0.94, bottom=0.12, top=0.92)
                self.ax = self.figure.add_subplot(111)
                self.ax_power = None
            else:
                # Just adjust margins for single plot
                self.figure.subplots_adjust(left=0.1, right=0.94, bottom=0.12, top=0.92)
        
        # Style the I-V plot
        self.ax.set_xlabel('Voltage (V)', fontsize=12, color=self.colors['plot_text'], fontweight='bold')
        self.ax.set_ylabel('Current (mA)', fontsize=12, color=self.colors['plot_text'], fontweight='bold')
        self.ax.set_title('I-V Curve', fontsize=14, color=self.colors['plot_text'], fontweight='bold')
        
        # Grid styling
        self.ax.grid(True, linestyle='--', alpha=0.7, color=self.colors['plot_grid'])
        
        # Customize axes
        for spine in self.ax.spines.values():
            spine.set_color('#000000')  # Black spines
            spine.set_linewidth(1.5)    # Slightly thicker
        
        # Tick styling - black and bold for better visibility
        self.ax.tick_params(colors='#000000', direction='out', width=1.5, labelsize=10)
        
        # Add forward and reverse line objects for I-V plot
        self.line_forward, = self.ax.plot(
            [], [], 
            color=self.colors['plot_forward'], 
            marker='o', 
            markersize=4,
            linestyle='-', 
            linewidth=2, 
            label='Upward'
        )
        
        self.line_reverse, = self.ax.plot(
            [], [], 
            color=self.colors['plot_reverse'], 
            marker='o', 
            markersize=4,
            linestyle='-', 
            linewidth=2, 
            label='Downward'
        )
        
        # Enhanced legend with black text for I-V plot
        legend = self.ax.legend(loc='upper right', frameon=True, fontsize=11)
        legend.get_frame().set_facecolor('#ffffff')
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor('#000000')
        
        # Make legend text black for better visibility
        for text in legend.get_texts():
            text.set_color('#000000')
        
        # Style the P-V plot if in P-I-V mode
        if is_piv_mode and self.ax_power is not None:
            self.ax_power.set_xlabel('Voltage (V)', fontsize=12, color=self.colors['plot_text'], fontweight='bold')
            self.ax_power.set_ylabel('Power (µW)', fontsize=12, color=self.colors['plot_text'], fontweight='bold')
            self.ax_power.set_title('P-V Curve', fontsize=14, color=self.colors['plot_text'], fontweight='bold')
            
            # Set white background for P-V plot to match I-V plot
            self.ax_power.set_facecolor(self.colors['plot_bg'])
            
            # Grid styling for P-V plot
            self.ax_power.grid(True, linestyle='--', alpha=0.7, color=self.colors['plot_grid'])
            
            # Customize axes for P-V plot
            for spine in self.ax_power.spines.values():
                spine.set_color('#000000')  # Black spines
                spine.set_linewidth(1.5)    # Slightly thicker
            
            # Tick styling for P-V plot
            self.ax_power.tick_params(colors='#000000', direction='out', width=1.5, labelsize=10)
            
            # Add forward and reverse line objects for P-V plot
            self.line_power_forward, = self.ax_power.plot(
                [], [], 
                color=self.colors['plot_forward'], 
                marker='o', 
                markersize=4,
                linestyle='-', 
                linewidth=2, 
                label='Upward'
            )
            
            self.line_power_reverse, = self.ax_power.plot(
                [], [], 
                color=self.colors['plot_reverse'], 
                marker='o', 
                markersize=4,
                linestyle='-', 
                linewidth=2, 
                label='Downward'
            )
            
            # Enhanced legend with black text for P-V plot (same as I-V plot)
            legend_power = self.ax_power.legend(loc='upper right', frameon=True, fontsize=11)
            legend_power.get_frame().set_facecolor('#ffffff')
            legend_power.get_frame().set_alpha(0.9)
            legend_power.get_frame().set_edgecolor('#000000')
            
            # Make legend text black for better visibility
            for text in legend_power.get_texts():
                text.set_color('#000000')
        
        # Set background colors - keep plot bg white but use dark figure bg
        self.figure.set_facecolor(self.colors['plot_fig_bg'])
        self.ax.set_facecolor(self.colors['plot_bg'])
        
        # Apply tight layout safely (suppress warnings)
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='The figure layout has changed to tight')
                self.figure.tight_layout()
        except (ValueError, numpy.linalg.LinAlgError):
            pass
        
        # Force redraw of the canvas after layout changes
        # Use a small delay to ensure layout changes are processed
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, self.canvas.draw)
    
    def resizeEvent(self, event):
        """Handle resize events to adjust the plot size."""
        super().resizeEvent(event)
        # Update figure size when window is resized
        if hasattr(self, 'figure') and hasattr(self, 'canvas'):
            try:
                self.figure.tight_layout()
                self.canvas.draw()
            except (ValueError, numpy.linalg.LinAlgError):
                # Skip tight_layout if it fails due to invalid figure dimensions
                pass
    
    # Removed preset methods - keeping only manual configuration
    
    def set_instrument(self, instrument):
        """Set the connected instrument."""
        self.instrument = instrument
        self.update_ui_state()
    
    def clear_instrument(self):
        """Clear the instrument reference."""
        self.instrument = None
        self.update_ui_state()
    
    def on_browse_clicked(self):
        """Handle browse button click to select save directory."""
        # Get the directory for saving files
        # Use non-native dialog to avoid macOS NSOpenPanel crashes
        options = QFileDialog.Option.DontUseNativeDialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.device_name_edit.text(),
            options=options
        )
        
        if directory:
            self.device_name_edit.setText(directory)
    
    def on_start_clicked(self):
        """Handle start measurement button click."""
        if not self.instrument:
            QMessageBox.warning(
                self,
                "No Instrument Connected",
                "Please connect to an instrument before starting a measurement."
            )
            return
        
        # Check if dual mode is selected but second instrument not connected
        if self.get_measurement_mode() == "DC Bias + Sweep" and not self.instrument2:
            QMessageBox.warning(
                self,
                "Second Instrument Required",
                "DC Bias + Sweep mode requires both instruments to be connected."
            )
            return
        
        # Check if P-I-V mode is selected but PM100D not connected
        if self.get_measurement_mode() == "P-I-V Measurement" and not self.pm100d_instrument:
            # Allow P-I-V mode to proceed without PM100D (power will be 0)
            pass
        
        # Validate parameters
        start_voltage = self.start_voltage_spin.value()
        stop_voltage = self.stop_voltage_spin.value()
        
        if start_voltage == stop_voltage:
            QMessageBox.warning(
                self,
                "Invalid Parameters",
                "Start and stop voltages cannot be the same."
            )
            return
        
        # Clear previous plot
        self.clear_plot()
        
        # Ensure P-I-V plot is properly initialized
        if self.get_measurement_mode() == "P-I-V Measurement":
            self.customize_plot(is_piv_mode=True)
            # Re-initialize data structure after plot customization
            self.current_data = {
                'voltage': [],
                'current': [],
                'voltage_reverse': [],
                'current_reverse': [],
                'power': [],
                'power_reverse': []
            }
            
        # Collect parameters
        params = {
            'start_voltage': start_voltage,
            'stop_voltage': stop_voltage,
            'num_points': self.num_points_spin.value(),
            'compliance': self.compliance_spin.value(),
            'bidirectional': self.bidirectional_check.isChecked(),
            'save_files': self.save_files_check.isChecked(),
            'device_name': self.device_name_edit.text(),
            'instrument': self.instrument,
            'measurement_mode': self.get_measurement_mode(),
            'instrument2': self.instrument2 if self.dual_mode else None,
            'dc_bias_params': self.get_dc_bias_params() if self.dual_mode else None,
            'pm100d_instrument': getattr(self, 'pm100d_instrument', None),
            'pm100d_params': self.get_pm100d_params() if self.get_measurement_mode() == "P-I-V Measurement" else None
        }
        
        # Update UI state
        self.is_measuring = True
        self.status_label.setText("Measurement in progress...")
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            background-color: {self.colors['success_bg']};
            color: #27ae60;
            font-weight: bold;
            font-size: 13px;
        """)
        self.progress_bar.setValue(0)
        self.progress_bar.show()  # Show progress bar during measurement
        self.update_ui_state()
        
        # Initialize real-time plot data
        self.current_data = {
            'voltage': [],
            'current': [],
            'voltage_reverse': [],
            'current_reverse': []
        }
        
        # Emit signal with parameters
        self.measurement_started.emit(params)
    
    def on_stop_clicked(self):
        """Handle stop measurement button click."""
        # Update UI state
        self.is_measuring = False
        self.status_label.setText("⏹ Measurement stopped")
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            background-color: {self.colors['warning_bg']};
            color: #f39c12;
            font-weight: bold;
            font-size: 13px;
        """)
        self.progress_bar.hide()  # Hide progress bar when stopped
        self.update_ui_state()
        
        # Emit signal
        self.measurement_stopped.emit()
    
    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
    
    def update_real_time_data(self, voltage, current, is_reverse=False):
        """Update the plot with real-time data during measurement."""
        if not is_reverse:
            self.current_data['voltage'].append(voltage)
            self.current_data['current'].append(current)
            self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
        else:
            self.current_data['voltage_reverse'].append(voltage)
            self.current_data['current_reverse'].append(current)
            self.line_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['current_reverse'])
        
        # Update axes limits with better padding
        all_voltages = self.current_data['voltage']
        all_currents = self.current_data['current']
        
        if len(self.current_data['voltage_reverse']) > 0:
            all_voltages = np.concatenate((all_voltages, self.current_data['voltage_reverse']))
            all_currents = np.concatenate((all_currents, self.current_data['current_reverse']))
        
        if len(all_voltages) > 0 and len(all_currents) > 0:
            # Calculate margins with at least 10% padding
            v_range = max(all_voltages) - min(all_voltages)
            c_range = max(all_currents) - min(all_currents)
            
            # Use at least 10% padding, but minimum of 0.005 for small ranges
            margin_x = max(0.15 * v_range if v_range > 0.01 else 0.005, 0.02)
            margin_y = max(0.15 * c_range if c_range > 0.01 else 0.005, 0.02)
            
            self.ax.set_xlim(min(all_voltages) - margin_x, max(all_voltages) + margin_x)
            self.ax.set_ylim(min(all_currents) - margin_y, max(all_currents) + margin_y)
        
        # Redraw the canvas
        self.canvas.draw()
    
    def update_real_time_data_piv(self, voltage, current, power, is_reverse=False):
        """Update the plot with real-time P-I-V data during measurement."""
        # Ensure current_data has all required keys for P-I-V mode
        if not hasattr(self, 'current_data'):
            self.current_data = {}
        
        required_keys = ['voltage', 'current', 'voltage_reverse', 'current_reverse', 'power', 'power_reverse']
        for key in required_keys:
            if key not in self.current_data:
                self.current_data[key] = []
        
        try:
            if not is_reverse:
                self.current_data['voltage'].append(voltage)
                self.current_data['current'].append(current)
                self.current_data['power'].append(power)
                self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
                # Update power plot if available
                if hasattr(self, 'line_power_forward'):
                    self.line_power_forward.set_data(self.current_data['voltage'], self.current_data['power'])
            else:
                self.current_data['voltage_reverse'].append(voltage)
                self.current_data['current_reverse'].append(current)
                self.current_data['power_reverse'].append(power)
                self.line_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['current_reverse'])
                # Update power plot if available
                if hasattr(self, 'line_power_reverse'):
                    self.line_power_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['power_reverse'])
        except Exception as e:
            # Continue without updating plots
            pass
        
        # Update axes limits with better padding for I-V plot
        all_voltages = self.current_data['voltage']
        all_currents = self.current_data['current']
        
        if len(self.current_data['voltage_reverse']) > 0:
            all_voltages = np.concatenate((all_voltages, self.current_data['voltage_reverse']))
            all_currents = np.concatenate((all_currents, self.current_data['current_reverse']))
        
        if len(all_voltages) > 0 and len(all_currents) > 0:
            # Calculate margins with at least 10% padding
            v_margin = max(0.1, (max(all_voltages) - min(all_voltages)) * 0.1)
            i_margin = max(0.1, (max(all_currents) - min(all_currents)) * 0.1)
            
            self.ax.set_xlim(min(all_voltages) - v_margin, max(all_voltages) + v_margin)
            self.ax.set_ylim(min(all_currents) - i_margin, max(all_currents) + i_margin)
        
        # Update axes limits for P-V plot if available
        if hasattr(self, 'ax_power') and self.ax_power is not None:
            all_powers = self.current_data['power']
            if len(self.current_data['power_reverse']) > 0:
                all_powers = np.concatenate((all_powers, self.current_data['power_reverse']))
            
            if len(all_voltages) > 0 and len(all_powers) > 0:
                p_margin = max(0.1, (max(all_powers) - min(all_powers)) * 0.1)
                self.ax_power.set_xlim(min(all_voltages) - v_margin, max(all_voltages) + v_margin)
                self.ax_power.set_ylim(min(all_powers) - p_margin, max(all_powers) + p_margin)
        
        # Redraw the canvas
        self.canvas.draw()
    
    def update_plot(self, data):
        """Update the plot with final data after measurement is completed."""
        bidirectional = 'voltage_reverse' in data and 'current_reverse' in data
        is_piv = 'power' in data or 'power_forward' in data
        
        # Store the data
        if bidirectional:
            self.current_data = {
                'voltage': data['voltage_forward'],
                'current': data['current_forward'],
                'voltage_reverse': data['voltage_reverse'],
                'current_reverse': data['current_reverse'],
                'power': data.get('power_forward', []),
                'power_reverse': data.get('power_reverse', [])
            }
            
            # Update line data
            self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
            self.line_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['current_reverse'])
            
            # Update P-V plot lines if they exist
            if is_piv and hasattr(self, 'line_power_forward'):
                self.line_power_forward.set_data(self.current_data['voltage'], self.current_data['power'])
            if is_piv and hasattr(self, 'line_power_reverse'):
                self.line_power_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['power_reverse'])
        else:
            self.current_data = {
                'voltage': data['voltage'],
                'current': data['current'],
                'voltage_reverse': [],
                'current_reverse': [],
                'power': data.get('power', []),
                'power_reverse': []
            }
            
            # Update line data
            self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
            self.line_reverse.set_data([], [])
            
            # Update P-V plot lines if they exist
            if is_piv and hasattr(self, 'line_power_forward'):
                self.line_power_forward.set_data(self.current_data['voltage'], self.current_data['power'])
            if is_piv and hasattr(self, 'line_power_reverse'):
                self.line_power_reverse.set_data([], [])
        
        # Adjust plot limits for I-V plot
        all_voltages = self.current_data['voltage']
        all_currents = self.current_data['current']
        
        if bidirectional:
            all_voltages = np.concatenate((all_voltages, self.current_data['voltage_reverse']))
            all_currents = np.concatenate((all_currents, self.current_data['current_reverse']))
        
        if len(all_voltages) > 0 and len(all_currents) > 0:
            margin_x = 0.1 * (max(all_voltages) - min(all_voltages)) if len(all_voltages) > 1 else 0.1
            margin_y = 0.1 * (max(all_currents) - min(all_currents)) if len(all_currents) > 1 else 0.1
            
            self.ax.set_xlim(min(all_voltages) - margin_x, max(all_voltages) + margin_x)
            self.ax.set_ylim(min(all_currents) - margin_y, max(all_currents) + margin_y)
        
        # Adjust plot limits for P-V plot if it exists
        if is_piv and hasattr(self, 'ax_power') and self.ax_power is not None:
            all_powers = self.current_data['power']
            if bidirectional and len(self.current_data['power_reverse']) > 0:
                all_powers = np.concatenate((all_powers, self.current_data['power_reverse']))
            
            if len(all_voltages) > 0 and len(all_powers) > 0:
                margin_x = 0.1 * (max(all_voltages) - min(all_voltages)) if len(all_voltages) > 1 else 0.1
                margin_y = 0.1 * (max(all_powers) - min(all_powers)) if len(all_powers) > 1 else 0.1
                
                self.ax_power.set_xlim(min(all_voltages) - margin_x, max(all_voltages) + margin_x)
                self.ax_power.set_ylim(min(all_powers) - margin_y, max(all_powers) + margin_y)
        
        # Redraw the canvas
        self.canvas.draw()
        
        # Forward update to external visualization
        self.update_plot_signal.emit(data)
    
    def clear_plot(self):
        """Clear the plot."""
        self.current_data = {
            'voltage': [],
            'current': [],
            'voltage_reverse': [],
            'current_reverse': [],
            'power': [],
            'power_reverse': []
        }
        
        self.line_forward.set_data([], [])
        self.line_reverse.set_data([], [])
        
        # Clear P-V plot lines if they exist
        if hasattr(self, 'line_power_forward'):
            self.line_power_forward.set_data([], [])
        if hasattr(self, 'line_power_reverse'):
            self.line_power_reverse.set_data([], [])
        
        self.ax.relim()
        self.ax.autoscale_view()
        
        # Reset P-V plot if it exists
        if hasattr(self, 'ax_power') and self.ax_power is not None:
            self.ax_power.relim()
            self.ax_power.autoscale_view()
        
        self.canvas.draw()
    
    def measurement_completed(self):
        """Handle measurement completion."""
        self.is_measuring = False
        self.status_label.setText("✅ Measurement completed successfully")
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            background-color: {self.colors['success_bg']};
            color: #2ecc71;
            font-weight: bold;
            font-size: 13px;
        """)
        self.progress_bar.setValue(100)
        # Hide progress bar after brief delay to show 100%
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self.progress_bar.hide)
        self.update_ui_state()
    
    def measurement_error(self, error_message):
        """Handle measurement error."""
        self.is_measuring = False
        self.status_label.setText(f"❌ Error: {error_message}")
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 5px;
            background-color: {self.colors['error_bg']};
            color: #e74c3c;
            font-weight: bold;
            font-size: 13px;
        """)
        self.progress_bar.hide()  # Hide progress bar on error
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI elements based on connection and measurement state."""
        has_instrument = self.instrument is not None
        is_measuring = self.is_measuring
        current_mode = self.get_measurement_mode()
        
        # Show/hide panels based on mode
        if current_mode == "I-V Sweep":
            if hasattr(self, 'sweep_group'):
                self.sweep_group.show()
            if hasattr(self, 'dc_bias_group'):
                self.dc_bias_group.show() if self.dual_mode else self.dc_bias_group.hide()
            if hasattr(self, 'pm100d_group'):
                self.pm100d_group.hide()
        elif current_mode == "Dual Keithley":
            if hasattr(self, 'sweep_group'):
                self.sweep_group.show()
            if hasattr(self, 'dc_bias_group'):
                self.dc_bias_group.show()
            if hasattr(self, 'pm100d_group'):
                self.pm100d_group.hide()
        elif current_mode == "P-I-V Measurement":
            if hasattr(self, 'sweep_group'):
                self.sweep_group.show()
            if hasattr(self, 'dc_bias_group'):
                self.dc_bias_group.hide()
            if hasattr(self, 'pm100d_group'):
                self.pm100d_group.show()
        
        # Enable/disable controls based on measurement state
        self.start_voltage_spin.setEnabled(has_instrument and not is_measuring)
        self.stop_voltage_spin.setEnabled(has_instrument and not is_measuring)
        self.num_points_spin.setEnabled(has_instrument and not is_measuring)
        self.compliance_spin.setEnabled(has_instrument and not is_measuring)
        self.bidirectional_check.setEnabled(has_instrument and not is_measuring)
        
        self.device_name_edit.setEnabled(has_instrument and not is_measuring)
        self.save_files_check.setEnabled(has_instrument and not is_measuring)
        self.browse_button.setEnabled(has_instrument and not is_measuring)
        
        self.start_button.setEnabled(has_instrument and not is_measuring)
        self.stop_button.setEnabled(has_instrument and is_measuring)
        
        # Update status label for idle state
        if not has_instrument and not is_measuring:
            self.status_label.setText("Ready - Connect instrument first")
            self.status_label.setStyleSheet(f"""
                padding: 8px;
                border-radius: 5px;
                background-color: {self.colors['input']};
                color: {self.colors['text_secondary']};
                font-weight: medium;
                font-size: 13px;
            """)
        elif has_instrument and not is_measuring and not self.current_data['voltage']:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet(f"""
                padding: 8px;
                border-radius: 5px;
                background-color: {self.colors['input']};
                color: {self.colors['text_secondary']};
                font-weight: medium;
                font-size: 13px;
            """)
    
    def set_instrument2(self, instrument2):
        """Set the second connected instrument."""
        self.instrument2 = instrument2
        self.update_ui_state()
    
    def set_pm100d_instrument(self, pm100d_instrument):
        """Set the PM100D instrument for P-I-V measurements."""
        self.pm100d_instrument = pm100d_instrument
        self.update_ui_state()
    
    def set_dual_mode(self, dual_mode):
        """Set dual instrument mode."""
        self.dual_mode = dual_mode
        self.update_ui_state()
        
        # Show/hide DC bias settings based on mode
        if dual_mode:
            self.dc_bias_group.show()
            self.mode_combo.setEnabled(True)
        else:
            self.dc_bias_group.hide()
            self.mode_combo.setEnabled(False)
            self.mode_combo.setCurrentText("Single Source")
    
    def on_mode_changed(self, mode_text):
        """Handle measurement mode change."""
        if mode_text == "Dual Keithley" and not self.dual_mode:
            # Can't use dual mode without two instruments
            self.mode_combo.setCurrentText("I-V Sweep")
            return
        
        # Update plot layout based on mode
        is_piv_mode = mode_text == "P-I-V Measurement"
        self.customize_plot(is_piv_mode)
        
        # Update UI based on mode
        self.update_ui_state()
    
    def get_measurement_mode(self):
        """Get the current measurement mode."""
        return self.mode_combo.currentText()
    
    def get_dc_bias_params(self):
        """Get DC bias parameters for dual mode."""
        return {
            'voltage': self.dc_bias_voltage_spin.value(),
            'compliance': self.dc_bias_compliance_spin.value()
        }
    
    def get_pm100d_params(self):
        """Get PM100D parameters for P-I-V measurement."""
        return {
            'wavelength': self.pm100d_wavelength_spin.value(),
            'auto_range': self.pm100d_range_combo.currentText() == "Auto",
            'manual_range': self.pm100d_manual_range_spin.value() if self.pm100d_range_combo.currentText() == "Manual" else None
        }
    
    def save_plot(self, data, device_name, bidirectional):
        """
        Save the current plot as a PNG file.
        
        Args:
            data: Measurement data dictionary
            device_name: Device name/path for saving
            bidirectional: Whether this was a bidirectional sweep
        """
        try:
            # Create folder if it doesn't exist
            os.makedirs(device_name, exist_ok=True)
            
            # Generate timestamp for filename
            timestamp = time.strftime('%Y-%m-%d_%H%M.%S')
            folder_name = os.path.basename(device_name)
            base_path = os.path.join(device_name, f'I-V Curve - {folder_name} - [{timestamp}]')
            
            # Create a new figure for saving with proper backend
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            # Apply dark theme styling (same as visualization panel)
            plt.style.use('dark_background')
            fig.patch.set_facecolor('#1e272e')
            ax.set_facecolor('#1e272e')
            
            # Apply enhanced styling to axes
            ax.tick_params(colors='#ecf0f1', labelsize=10, length=6, width=1)
            ax.spines['bottom'].set_color('#34495e')
            ax.spines['top'].set_color('#34495e')
            ax.spines['left'].set_color('#34495e')
            ax.spines['right'].set_color('#34495e')
            
            # Enhanced text styling
            ax.xaxis.label.set_color('#ecf0f1')
            ax.xaxis.label.set_fontsize(12)
            ax.xaxis.label.set_fontweight('bold')
            
            ax.yaxis.label.set_color('#ecf0f1')
            ax.yaxis.label.set_fontsize(12)
            ax.yaxis.label.set_fontweight('bold')
            
            ax.title.set_color('#ecf0f1')
            ax.title.set_fontsize(14)
            ax.title.set_fontweight('bold')
            
            # Check if this is P-I-V data
            is_piv = 'power' in data or 'power_forward' in data
            
            # Validate data before plotting
            if bidirectional:
                if not all(key in data for key in ['voltage_forward', 'current_forward', 'voltage_reverse', 'current_reverse']):
                    print("Error: Missing required data for bidirectional plot")
                    return
                if is_piv and not all(key in data for key in ['power_forward', 'power_reverse']):
                    print("Error: Missing power data for PIV plot")
                    return
            else:
                if not all(key in data for key in ['voltage', 'current']):
                    print("Error: Missing required data for single sweep plot")
                    return
                if is_piv and 'power' not in data:
                    print("Error: Missing power data for PIV plot")
                    return
            
            if is_piv:
                # Create subplots for P-I-V mode with better spacing
                fig.subplots_adjust(left=0.12, right=0.95, bottom=0.15, top=0.9, wspace=0.3)
                ax_iv = fig.add_subplot(121)
                ax_power = fig.add_subplot(122)
                
                
                # I-V plot
                ax_iv.set_xlabel('Voltage (V)')
                ax_iv.set_ylabel('Current (mA)')
                ax_iv.set_title('I-V Curve')
                ax_iv.grid(True, linestyle='--', alpha=0.3, color='#34495e')
                
                # P-V plot
                ax_power.set_xlabel('Voltage (V)')
                ax_power.set_ylabel('Power (µW)')
                ax_power.set_title('P-V Curve')
                ax_power.grid(True, linestyle='--', alpha=0.3, color='#34495e')
                
                # Plot I-V data
                if bidirectional:
                    # Plot forward sweep
                    ax_iv.plot(data['voltage_forward'], data['current_forward'], 
                              'b+-', label='Upward', linewidth=2, markersize=4)
                    # Plot reverse sweep
                    ax_iv.plot(data['voltage_reverse'], data['current_reverse'], 
                              'r+-', label='Downward', linewidth=2, markersize=4)
                    
                    # Plot P-V data (use same voltage data as I-V)
                    ax_power.plot(data['voltage_forward'], data['power_forward'], 
                                 'b+-', label='Upward', linewidth=2, markersize=4)
                    ax_power.plot(data['voltage_reverse'], data['power_reverse'], 
                                 'r+-', label='Downward', linewidth=2, markersize=4)
                else:
                    # Plot single sweep
                    ax_iv.plot(data['voltage'], data['current'], 
                              'b+-', label='Upward', linewidth=2, markersize=4)
                    ax_power.plot(data['voltage'], data['power'], 
                                 'b+-', label='Upward', linewidth=2, markersize=4)
                
                # Create legends for both plots
                legend_iv = ax_iv.legend(loc='upper right', fontsize=11, frameon=True, 
                                       fancybox=True, shadow=True, framealpha=0.95)
                legend_iv.get_frame().set_facecolor('#2c3e50')
                legend_iv.get_frame().set_edgecolor('#34495e')
                legend_iv.get_frame().set_linewidth(1.0)
                
                legend_power = ax_power.legend(loc='upper right', fontsize=11, frameon=True, 
                                             fancybox=True, shadow=True, framealpha=0.95)
                legend_power.get_frame().set_facecolor('#2c3e50')
                legend_power.get_frame().set_edgecolor('#34495e')
                legend_power.get_frame().set_linewidth(1.0)
                
                # Make legend text white and bold for both plots
                for text in legend_iv.get_texts():
                    text.set_color('#ecf0f1')
                    text.set_fontweight('bold')
                for text in legend_power.get_texts():
                    text.set_color('#ecf0f1')
                    text.set_fontweight('bold')
                
                # Apply styling to both plots
                for ax_plot in [ax_iv, ax_power]:
                    ax_plot.tick_params(colors='#ecf0f1', labelsize=9, length=4, width=1, pad=8)
                    ax_plot.spines['bottom'].set_color('#34495e')
                    ax_plot.spines['top'].set_color('#34495e')
                    ax_plot.spines['left'].set_color('#34495e')
                    ax_plot.spines['right'].set_color('#34495e')
                    ax_plot.xaxis.label.set_color('#ecf0f1')
                    ax_plot.xaxis.label.set_fontsize(11)
                    ax_plot.xaxis.label.set_fontweight('bold')
                    ax_plot.yaxis.label.set_color('#ecf0f1')
                    ax_plot.yaxis.label.set_fontsize(11)
                    ax_plot.yaxis.label.set_fontweight('bold')
                    ax_plot.title.set_color('#ecf0f1')
                    ax_plot.title.set_fontsize(13)
                    ax_plot.title.set_fontweight('bold')
                    ax_plot.set_facecolor('#1e272e')
                    
                    # Fix tick formatting to prevent overlap
                    ax_plot.ticklabel_format(style='plain', axis='both')
                    
                    # Set better tick spacing
                    from matplotlib.ticker import MaxNLocator
                    ax_plot.xaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
                    ax_plot.yaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
                
                # Ensure both plots have the same voltage range and proper scaling
                if bidirectional:
                    all_voltages = list(data['voltage_forward']) + list(data['voltage_reverse'])
                else:
                    all_voltages = list(data['voltage'])
                
                if all_voltages:
                    v_min, v_max = min(all_voltages), max(all_voltages)
                    v_margin = max(0.01, (v_max - v_min) * 0.05)  # At least 0.01V margin
                    
                    # Set identical voltage ranges for both plots
                    ax_iv.set_xlim(v_min - v_margin, v_max + v_margin)
                    ax_power.set_xlim(v_min - v_margin, v_max + v_margin)
                    
                    # Auto-scale y-axes appropriately
                    ax_iv.relim()
                    ax_iv.autoscale_view()
                    ax_power.relim()
                    ax_power.autoscale_view()
            else:
                # Regular I-V plot
                ax.set_xlabel('Voltage (V)')
                ax.set_ylabel('Current (mA)')
                ax.set_title('I-V Curve')
                
                # Grid styling
                ax.grid(True, linestyle='--', alpha=0.3, color='#34495e')
                
                # Plot the data
                if bidirectional:
                    # Plot forward sweep
                    ax.plot(data['voltage_forward'], data['current_forward'], 
                           'b+-', label='Upward', linewidth=2, markersize=4)
                    # Plot reverse sweep
                    ax.plot(data['voltage_reverse'], data['current_reverse'], 
                           'r+-', label='Downward', linewidth=2, markersize=4)
                else:
                    # Plot single sweep
                    ax.plot(data['voltage'], data['current'], 
                           'b+-', label='Upward', linewidth=2, markersize=4)
                
                # Create legend with enhanced styling for regular I-V plot
                legend = ax.legend(loc='upper right', fontsize=11, frameon=True, 
                                 fancybox=True, shadow=True, framealpha=0.95)
                legend.get_frame().set_facecolor('#2c3e50')
                legend.get_frame().set_edgecolor('#34495e')
                legend.get_frame().set_linewidth(1.0)
                
                # Make legend text white and bold
                for text in legend.get_texts():
                    text.set_color('#ecf0f1')
                    text.set_fontweight('bold')
                
                # Fix tick formatting for regular I-V plot
                ax.ticklabel_format(style='plain', axis='both')
                from matplotlib.ticker import MaxNLocator
                ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
                ax.yaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
            
            # Apply tight layout
            fig.tight_layout()
            
            # Force the figure to render completely before saving
            fig.canvas.draw()
            
            # Small delay to ensure rendering is complete
            time.sleep(0.1)
            
            # Save the plot
            plot_path = base_path + '.png'
            fig.savefig(plot_path, dpi=300, bbox_inches='tight', 
                       facecolor='#1e272e', edgecolor='none')
            
            # Clean up
            plt.close(fig)
            
            print(f"Plot saved to: {plot_path}")
            
        except Exception as e:
            print(f"Error saving plot: {str(e)}")
    