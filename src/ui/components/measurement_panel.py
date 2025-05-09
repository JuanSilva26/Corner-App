"""
Measurement configuration panel for I-V sweep settings with integrated visualization.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QGroupBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QFileDialog,
    QMessageBox, QProgressBar, QSplitter, QFrame, QToolBar,
    QComboBox, QToolButton, QSizePolicy, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction

# Import for real-time plotting
import numpy as np
import matplotlib
try:
    matplotlib.use('Qt6Agg')
except:
    matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy.linalg

# Import for CustomNavigationToolbar
from ui.components.visualization_panel import CustomNavigationToolbar


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
        
        # Define a dark mode color scheme
        self.colors = {
            'primary': '#2980b9',    # Primary blue
            'secondary': '#27ae60',  # Green for positive actions
            'danger': '#c0392b',     # Red for negative actions
            'warning': '#d35400',    # Orange for warnings/notifications
            'dark': '#1e272e',       # Dark background
            'darker': '#151c21',     # Darker background
            'light': '#485460',      # Light backgrounds (dark mode)
            'lighter': '#808e9b',    # Button/accent gray
            'text': '#ecf0f1',       # Text color
            'text_secondary': '#bdc3c7', # Secondary text
            'border': '#34495e',     # Border color
            'button': '#34495e',     # Button background
            'input': '#2c3e50',      # Input field background
            
            # Plot colors - keep white background but use dark mode for elements
            'plot_bg': '#ffffff',     # White background for plot
            'plot_fig_bg': '#1e272e', # Dark figure background (outside plot area)
            'plot_grid': '#cccccc',   # Light grid lines
            'plot_forward': '#2980b9', # Forward line - blue
            'plot_reverse': '#c0392b', # Reverse line - red
            'plot_text': '#333333',    # Dark text for plot labels
        }
        
        # Define some style constants with updated modern styling
        self.HEADER_STYLE = f"QLabel {{ font-size: 16px; font-weight: bold; color: {self.colors['text']}; }}"
        self.GROUP_STYLE = f"""
            QGroupBox {{ 
                font-weight: bold; 
                border: 1px solid {self.colors['border']}; 
                border-radius: 6px; 
                margin-top: 1.5ex; 
                padding-top: 10px;
                padding-bottom: 8px;
                background-color: {self.colors['dark']};
                color: {self.colors['text']};
            }} 
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                subcontrol-position: top center; 
                padding: 0 8px; 
                color: {self.colors['text']};
            }}
        """
        self.BUTTON_STYLE = f"""
            QPushButton {{ 
                background-color: {self.colors['button']}; 
                color: {self.colors['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: {self.colors['primary']}; 
            }} 
            QPushButton:pressed {{ 
                background-color: #1c6ea4;
            }}
            QPushButton:disabled {{ 
                background-color: {self.colors['light']}; 
                color: {self.colors['text_secondary']};
            }}
        """
        self.START_BUTTON_STYLE = f"""
            QPushButton {{ 
                background-color: {self.colors['secondary']}; 
                color: {self.colors['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: #219653; 
            }} 
            QPushButton:pressed {{ 
                background-color: #1e8449;
            }}
            QPushButton:disabled {{ 
                background-color: {self.colors['light']}; 
                color: {self.colors['text_secondary']};
            }}
        """
        self.STOP_BUTTON_STYLE = f"""
            QPushButton {{ 
                background-color: {self.colors['danger']}; 
                color: {self.colors['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: #a93226; 
            }} 
            QPushButton:pressed {{ 
                background-color: #922b21;
            }}
            QPushButton:disabled {{ 
                background-color: {self.colors['light']}; 
                color: {self.colors['text_secondary']};
            }}
        """
        self.SECTION_SEPARATOR_STYLE = f"background-color: {self.colors['border']}; border-radius: 2px;"
        
        # Define measurement presets
        self.presets = {
            "Standard I-V": {
                "start_voltage": 0.0,
                "stop_voltage": 0.8,
                "num_points": 100,
                "compliance": 0.01,
                "bidirectional": True
            },
            "High Resolution": {
                "start_voltage": 0.0,
                "stop_voltage": 0.8,
                "num_points": 500,
                "compliance": 0.01,
                "bidirectional": True
            },
            "Quick Test": {
                "start_voltage": 0.0,
                "stop_voltage": 0.5,
                "num_points": 20,
                "compliance": 0.01,
                "bidirectional": False
            },
            "Negative Voltage": {
                "start_voltage": -0.8,
                "stop_voltage": 0.0,
                "num_points": 100,
                "compliance": 0.01,
                "bidirectional": True
            }
        }
        
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
        self.create_save_settings()
        self.create_control_buttons()
        self.create_progress_section()
        self.settings_layout.addStretch()
        
        # Setup visualization
        self.setup_visualization()
        
        # Set initial state
        self.instrument = None
        self.is_measuring = False
        self.current_data = {"voltage": [], "current": []}
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
        
        # Presets dropdown
        preset_label = QLabel("Presets:")
        preset_label.setStyleSheet(f"font-weight: bold; padding-right: 5px; color: {self.colors['text']};")
        toolbar.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.presets.keys()))
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {self.colors['border']};
                border-radius: 3px;
                padding: 3px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
            }}
            QComboBox:focus {{
                border: 1px solid {self.colors['primary']};
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
        toolbar.addWidget(self.preset_combo)
        
        # Load preset button
        load_preset_action = QAction("Load Preset", self)
        load_preset_action.triggered.connect(self.load_preset)
        load_preset_action.setToolTip("Load the selected preset configuration")
        toolbar.addAction(load_preset_action)
        
        toolbar.addSeparator()
        
        # Save as preset button
        save_preset_action = QAction("Save Current as Preset", self)
        save_preset_action.triggered.connect(self.save_current_as_preset)
        save_preset_action.setToolTip("Save current settings as a new preset")
        toolbar.addAction(save_preset_action)
        
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
    
    def create_save_settings(self):
        """Create save settings group."""
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
        group_box = QGroupBox("Measurement Status")
        group_box.setStyleSheet(self.GROUP_STYLE)
        progress_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready")
        status_font = QFont()
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        # Progress bar with modern styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                text-align: center;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                height: 22px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['primary']};
                border-radius: 5px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        group_box.setLayout(progress_layout)
        self.settings_layout.addWidget(group_box)
    
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
        
        # Create the plot with enhanced styling
        self.ax = self.figure.add_subplot(111)
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
    
    def customize_plot(self):
        """Apply custom styling to the plot."""
        # Set plot appearance with black text for better visibility
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
        
        # Add forward and reverse line objects with enhanced styling and renamed legends
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
        
        # Enhanced legend with black text
        legend = self.ax.legend(loc='upper right', frameon=True, fontsize=11)
        legend.get_frame().set_facecolor('#ffffff')
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor('#000000')
        
        # Make legend text black for better visibility
        for text in legend.get_texts():
            text.set_color('#000000')
        
        # Set background colors - keep plot bg white but use dark figure bg
        self.figure.set_facecolor(self.colors['plot_fig_bg'])
        self.ax.set_facecolor(self.colors['plot_bg'])
        
        # Apply tight layout safely
        try:
            self.figure.tight_layout()
        except (ValueError, numpy.linalg.LinAlgError):
            pass
    
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
    
    def load_preset(self):
        """Load the selected preset configuration."""
        preset_name = self.preset_combo.currentText()
        if preset_name in self.presets:
            preset = self.presets[preset_name]
            
            # Apply preset values
            self.start_voltage_spin.setValue(preset["start_voltage"])
            self.stop_voltage_spin.setValue(preset["stop_voltage"])
            self.num_points_spin.setValue(preset["num_points"])
            self.compliance_spin.setValue(preset["compliance"])
            self.bidirectional_check.setChecked(preset["bidirectional"])
            
            # Show a brief status message
            self.status_label.setText(f"Loaded preset: {preset_name}")
    
    def save_current_as_preset(self):
        """Save current settings as a new preset."""
        # Get current settings
        current_settings = {
            "start_voltage": self.start_voltage_spin.value(),
            "stop_voltage": self.stop_voltage_spin.value(),
            "num_points": self.num_points_spin.value(),
            "compliance": self.compliance_spin.value(),
            "bidirectional": self.bidirectional_check.isChecked()
        }
        
        # Ask for preset name
        preset_name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        
        if ok and preset_name:
            # Add to presets dictionary
            self.presets[preset_name] = current_settings
            
            # Update combo box
            current_presets = [self.preset_combo.itemText(i) for i in range(self.preset_combo.count())]
            if preset_name not in current_presets:
                self.preset_combo.addItem(preset_name)
            
            # Select the new preset
            self.preset_combo.setCurrentText(preset_name)
            
            # Show a brief status message
            self.status_label.setText(f"Saved preset: {preset_name}")
    
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
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.device_name_edit.text()
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
            
        # Collect parameters
        params = {
            'start_voltage': start_voltage,
            'stop_voltage': stop_voltage,
            'num_points': self.num_points_spin.value(),
            'compliance': self.compliance_spin.value(),
            'bidirectional': self.bidirectional_check.isChecked(),
            'save_files': self.save_files_check.isChecked(),
            'device_name': self.device_name_edit.text(),
            'instrument': self.instrument
        }
        
        # Update UI state
        self.is_measuring = True
        self.status_label.setText("Measurement in progress...")
        self.status_indicator.set_status("running")
        self.progress_bar.setValue(0)
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
        self.status_label.setText("Measurement stopped")
        self.status_indicator.set_status("stopped")
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
    
    def update_plot(self, data):
        """Update the plot with final data after measurement is completed."""
        bidirectional = 'voltage_reverse' in data and 'current_reverse' in data
        
        # Store the data
        if bidirectional:
            self.current_data = {
                'voltage': data['voltage_forward'],
                'current': data['current_forward'],
                'voltage_reverse': data['voltage_reverse'],
                'current_reverse': data['current_reverse']
            }
            
            # Update line data
            self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
            self.line_reverse.set_data(self.current_data['voltage_reverse'], self.current_data['current_reverse'])
        else:
            self.current_data = {
                'voltage': data['voltage'],
                'current': data['current'],
                'voltage_reverse': [],
                'current_reverse': []
            }
            
            # Update line data
            self.line_forward.set_data(self.current_data['voltage'], self.current_data['current'])
            self.line_reverse.set_data([], [])
        
        # Adjust plot limits
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
            'current_reverse': []
        }
        
        self.line_forward.set_data([], [])
        self.line_reverse.set_data([], [])
        
        self.ax.relim()
        self.ax.autoscale_view()
        
        self.canvas.draw()
    
    def on_export_clicked(self):
        """Handle export button click to save the plot as an image."""
        if not (self.current_data['voltage'] or self.current_data['voltage_reverse']):
            return  # Nothing to export
        
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            os.path.expanduser("~/Desktop"),
            "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            try:
                # Higher quality export
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight',
                                   facecolor=self.figure.get_facecolor())
            except Exception as e:
                print(f"Error saving figure: {e}")
                QMessageBox.warning(self, "Export Error", f"Failed to save the plot: {str(e)}")
    
    def measurement_completed(self):
        """Handle measurement completion."""
        self.is_measuring = False
        self.status_label.setText("Measurement completed")
        self.status_indicator.set_status("completed")
        self.progress_bar.setValue(100)
        self.update_ui_state()
    
    def measurement_error(self, error_message):
        """Handle measurement error."""
        self.is_measuring = False
        self.status_label.setText(f"Error: {error_message}")
        self.status_indicator.set_status("error")
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI elements based on connection and measurement state."""
        has_instrument = self.instrument is not None
        is_measuring = self.is_measuring
        
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
        
        # Update status indicator
        if not has_instrument:
            self.status_indicator.set_status("idle")
        elif not is_measuring and not self.current_data['voltage']:
            self.status_indicator.set_status("idle") 