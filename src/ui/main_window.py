"""
Main application window for the Measurement App.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QLabel, QStatusBar, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

class MainWindow(QMainWindow):
    """Main window of the application with central widget layout."""
    
    def __init__(self):
        super().__init__()
        
        # Define dark mode color scheme
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
        }
        
        # Set up the main window
        self.setWindowTitle("Measurement App")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply modern styling
        self.apply_stylesheet()
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(10)
        
        # Create horizontal splitter for control panel and visualization
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.colors['border']};
            }}
            QSplitter::handle:hover {{
                background-color: {self.colors['primary']};
            }}
        """)
        self.main_layout.addWidget(self.main_splitter)
        
        # Left panel for controls
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(6)
        
        # Right panel for visualization
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(6)
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([300, 700])  # Initial sizes
        
        # Set up control panel with tabs
        self.setup_control_panel()
        
        # Set up visualization panel
        self.setup_visualization_panel()
        
        # Create status bar with modern styling
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {self.colors['darker']};
                color: {self.colors['text']};
                border-top: 1px solid {self.colors['border']};
                padding: 4px;
                font-size: 13px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def apply_stylesheet(self):
        """Apply dark mode stylesheet to the entire application."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['dark']};
            }}
            QWidget {{
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                color: {self.colors['text']};
                background-color: {self.colors['dark']};
            }}
            QTabWidget::pane {{ 
                border: 1px solid {self.colors['border']}; 
                border-radius: 5px;
                background-color: {self.colors['dark']};
            }}
            QTabWidget::tab-bar {{
                left: 5px;
            }}
            QTabBar::tab {{
                background-color: {self.colors['light']};
                border: 1px solid {self.colors['border']};
                border-bottom-color: {self.colors['border']};
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 100px;
                padding: 8px 12px;
                margin-right: 3px;
                color: {self.colors['text_secondary']};
            }}
            QTabBar::tab:selected {{
                background-color: {self.colors['dark']};
                border-bottom-color: {self.colors['dark']};
                color: {self.colors['primary']};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self.colors['darker']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                margin-top: 1.5ex;
                padding-top: 10px;
                padding-bottom: 8px;
                background-color: {self.colors['dark']};
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                color: {self.colors['text']};
            }}
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
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
                min-height: 25px;
            }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {self.colors['primary']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {self.colors['border']};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {self.colors['border']};
                border-radius: 0;
                background-color: {self.colors['input']};
                selection-background-color: {self.colors['primary']};
                selection-color: {self.colors['text']};
            }}
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
            QLabel {{
                color: {self.colors['text']};
            }}
        """)
    
    def setup_control_panel(self):
        """Set up the control panel with tabs for different settings."""
        self.tabs = QTabWidget()
        self.left_layout.addWidget(self.tabs)
        
        # Connection tab
        self.connection_tab = QWidget()
        self.connection_layout = QVBoxLayout(self.connection_tab)
        self.connection_layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(self.connection_tab, "Connection")
        
        # Placeholder for connection panel (to be added later)
        placeholder = QLabel("Connection panel will be added here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        self.connection_layout.addWidget(placeholder)
        
        # Measurement tab
        self.measurement_tab = QWidget()
        self.measurement_layout = QVBoxLayout(self.measurement_tab)
        self.measurement_layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(self.measurement_tab, "Measurement")
        
        # Placeholder for measurement settings
        placeholder = QLabel("Measurement settings will be added here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        self.measurement_layout.addWidget(placeholder)
        
        # Data tab
        self.data_tab = QWidget()
        self.data_layout = QVBoxLayout(self.data_tab)
        self.data_layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(self.data_tab, "Data")
        
        # Placeholder for data settings
        placeholder = QLabel("Data settings will be added here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        self.data_layout.addWidget(placeholder)
        
        # Analysis tab
        self.analysis_tab = QWidget()
        self.analysis_layout = QVBoxLayout(self.analysis_tab)
        self.analysis_layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(self.analysis_tab, "Analysis")
        
        # Placeholder for analysis settings
        placeholder = QLabel("Analysis tools will be added here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 14px;")
        self.analysis_layout.addWidget(placeholder)
    
    def setup_visualization_panel(self):
        """Set up the visualization panel for showing plots and data."""
        # Add title
        title = QLabel("Visualization")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.colors['text']};")
        self.right_layout.addWidget(title)
        
        # Placeholder for plot
        plot_label = QLabel("Plot will be shown here")
        plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plot_label.setStyleSheet(f"""
            font-size: 14px; 
            padding: 100px; 
            background-color: {self.colors['dark']}; 
            border: 1px solid {self.colors['border']}; 
            border-radius: 6px;
            color: {self.colors['text_secondary']};
        """)
        self.right_layout.addWidget(plot_label)
        
        # Placeholder for data table
        data_label = QLabel("Data table will be shown here")
        data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_label.setStyleSheet(f"""
            font-size: 14px; 
            padding: 50px; 
            background-color: {self.colors['dark']}; 
            border: 1px solid {self.colors['border']}; 
            border-radius: 6px;
            color: {self.colors['text_secondary']};
        """)
        self.right_layout.addWidget(data_label)
    
    def update_status(self, message):
        """Update the status bar message."""
        self.status_bar.showMessage(message)
