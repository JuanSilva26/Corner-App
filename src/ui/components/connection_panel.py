"""
Connection panel for instrument connectivity.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QLineEdit, QGroupBox,
    QFormLayout, QRadioButton, QMessageBox, QFrame,
    QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal

import pyvisa as visa
from instruments.keithley import create_keithley_instrument, KeithleyError


class ConnectionPanel(QWidget):
    """Panel for managing instrument connections."""
    
    # Signals
    connection_status_changed = pyqtSignal(bool, str)  # connected, message
    instrument_connected = pyqtSignal(object)  # Emits the instrument object when connected
    
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
            'success_bg': '#274d36', # Dark green background for success messages
            'error_bg': '#532b2b',   # Dark red background for error messages
            'warning_bg': '#553b21', # Dark yellow background for warnings
        }
        
        # Define style constants
        self.HEADER_STYLE = f"font-size: 16px; font-weight: bold; color: {self.colors['text']};"
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
        self.CONNECT_BUTTON_STYLE = f"""
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
        self.DISCONNECT_BUTTON_STYLE = f"""
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
        self.INPUT_STYLE = f"""
            QComboBox, QLineEdit {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
                min-height: 25px;
            }}
            QComboBox:focus, QLineEdit:focus {{
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
            QComboBox::down-arrow {{
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {self.colors['border']};
                border-radius: 0;
                background-color: {self.colors['input']};
                selection-background-color: {self.colors['primary']};
                selection-color: {self.colors['text']};
            }}
        """
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(8)
        
        # Initialize state
        self.connected = False
        self.instrument = None
        
        # Add title
        title = QLabel("Connection Settings")
        title.setStyleSheet(self.HEADER_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.layout.addWidget(title)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
        
        # Create UI components
        self.create_connection_settings()
        self.create_instrument_settings()
        self.create_connection_controls()
        self.create_status_section()
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
        
        # Update UI state
        self.update_ui_state()
        
        # Connect signals
        self.refresh_button.clicked.connect(self.refresh_devices)
        
        # Refresh device list after UI is fully set up
        self.refresh_devices()
    
    def create_connection_settings(self):
        """Create connection settings group."""
        group_box = QGroupBox("Connection Settings")
        group_box.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Connection type
        self.conn_type_combo = QComboBox()
        self.conn_type_combo.addItems(["USB", "GPIB"])
        self.conn_type_combo.currentIndexChanged.connect(self.on_connection_type_changed)
        self.conn_type_combo.setStyleSheet(self.INPUT_STYLE)
        form_layout.addRow("Connection Type:", self.conn_type_combo)
        
        # Container for connection specific controls
        self.conn_specific_widget = QWidget()
        self.conn_specific_layout = QVBoxLayout(self.conn_specific_widget)
        self.conn_specific_layout.setContentsMargins(0, 0, 0, 0)
        
        # USB settings
        self.usb_widget = QWidget()
        usb_layout = QFormLayout(self.usb_widget)
        usb_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.usb_resource_combo = QComboBox()
        self.usb_resource_combo.setEditable(True)
        self.usb_resource_combo.setStyleSheet(self.INPUT_STYLE)
        self.usb_resource_combo.setMinimumWidth(300)
        usb_layout.addRow("USB Resource:", self.usb_resource_combo)
        
        # GPIB settings
        self.gpib_widget = QWidget()
        gpib_layout = QFormLayout(self.gpib_widget)
        gpib_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.gpib_address_edit = QLineEdit("22")  # Default from notebook
        self.gpib_address_edit.setStyleSheet(self.INPUT_STYLE)
        gpib_layout.addRow("GPIB Address:", self.gpib_address_edit)
        
        # Add specific settings to container
        self.conn_specific_layout.addWidget(self.usb_widget)
        self.conn_specific_layout.addWidget(self.gpib_widget)
        
        # Show appropriate widget based on initial selection
        self.on_connection_type_changed(0)  # USB is default
        
        form_layout.addRow(self.conn_specific_widget)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Device List")
        self.refresh_button.setStyleSheet(self.BUTTON_STYLE)
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        form_layout.addRow(self.refresh_button)
        
        group_box.setLayout(form_layout)
        self.layout.addWidget(group_box)
    
    def create_instrument_settings(self):
        """Create instrument settings group."""
        group_box = QGroupBox("Instrument Settings")
        group_box.setStyleSheet(self.GROUP_STYLE)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Instrument type
        self.instrument_type_combo = QComboBox()
        self.instrument_type_combo.addItems(["Keithley 2400/2450", "Keithley 2600"])
        self.instrument_type_combo.setStyleSheet(self.INPUT_STYLE)
        form_layout.addRow("Instrument Type:", self.instrument_type_combo)
        
        group_box.setLayout(form_layout)
        self.layout.addWidget(group_box)
    
    def create_connection_controls(self):
        """Create connection control buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        self.connect_button.setStyleSheet(self.CONNECT_BUTTON_STYLE)
        self.connect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_button.setMinimumHeight(36)
        button_layout.addWidget(self.connect_button)
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        self.disconnect_button.setStyleSheet(self.DISCONNECT_BUTTON_STYLE)
        self.disconnect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconnect_button.setMinimumHeight(36)
        button_layout.addWidget(self.disconnect_button)
        
        self.layout.addLayout(button_layout)
    
    def create_status_section(self):
        """Create connection status section."""
        group_box = QGroupBox("Connection Status")
        group_box.setStyleSheet(self.GROUP_STYLE)
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Not connected")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 4px;
            background-color: {self.colors['input']};
            color: {self.colors['text']};
            font-weight: medium;
        """)
        status_layout.addWidget(self.status_label)
        
        group_box.setLayout(status_layout)
        self.layout.addWidget(group_box)
    
    def on_connection_type_changed(self, index):
        """Handle connection type change."""
        if index == 0:  # USB
            self.usb_widget.show()
            self.gpib_widget.hide()
        else:  # GPIB
            self.usb_widget.hide()
            self.gpib_widget.show()
    
    def refresh_devices(self):
        """Refresh the list of available devices."""
        try:
            # Clear existing items
            self.usb_resource_combo.clear()
            
            # Get all available resources
            rm = visa.ResourceManager()
            resources = rm.list_resources()
            
            # Add USB resources to the combo box
            for resource in resources:
                if "USB" in resource:
                    self.usb_resource_combo.addItem(resource)
            
            # Add default USB resources if none found
            if self.usb_resource_combo.count() == 0:
                self.usb_resource_combo.addItem("USB0::0x05E6::0x2280::4393711::INSTR")  # Example
                self.usb_resource_combo.addItem("USB0::0x05E6::0x2280::4593849::INSTR")  # Example
                
            self.set_status("Device list refreshed", False)
        except Exception as e:
            self.set_status(f"Error refreshing devices: {str(e)}", False)
            QMessageBox.warning(
                self,
                "Device Refresh Error",
                f"Failed to refresh device list: {str(e)}"
            )
    
    def on_connect_clicked(self):
        """Handle connect button click."""
        try:
            # Get the resource name based on connection type
            if self.conn_type_combo.currentIndex() == 0:  # USB
                resource_name = self.usb_resource_combo.currentText()
            else:  # GPIB
                address = self.gpib_address_edit.text()
                resource_name = f"GPIB::{address}"
            
            # Create instrument based on selected type
            instrument_type = self.instrument_type_combo.currentText()
            self.instrument = create_keithley_instrument(instrument_type)
            
            # Connect to the instrument
            self.instrument.connect(resource_name)
            
            # Update UI state
            self.connected = True
            self.update_ui_state()
            
            # Get instrument info for display
            instrument_info = self.instrument.get_instrument_info().strip()
            message = f"Connected to {instrument_info}"
            
            # Update status and emit signals
            self.set_status(message, True)
            self.connection_status_changed.emit(True, message)
            self.instrument_connected.emit(self.instrument)
            
        except KeithleyError as e:
            self.connected = False
            self.update_ui_state()
            self.set_status(f"Connection failed: {str(e)}", False)
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Failed to connect to instrument: {str(e)}"
            )
        except Exception as e:
            self.connected = False
            self.update_ui_state()
            self.set_status(f"Connection error: {str(e)}", False)
            QMessageBox.critical(
                self,
                "Connection Error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def on_disconnect_clicked(self):
        """Handle disconnect button click."""
        if not self.instrument:
            self.connected = False
            self.update_ui_state()
            self.set_status("Disconnected", False)
            self.connection_status_changed.emit(False, "Disconnected")
            return
            
        try:
            # Cleanup and disconnect
            self.instrument.cleanup()
            self.instrument.disconnect()
            
            # Update state
            self.connected = False
            self.instrument = None
            self.update_ui_state()
            
            # Update status and emit signal
            self.set_status("Disconnected", False)
            self.connection_status_changed.emit(False, "Disconnected")
            
        except Exception as e:
            self.set_status(f"Disconnect error: {str(e)}", False)
            QMessageBox.warning(
                self,
                "Disconnect Error",
                f"Error during disconnect: {str(e)}"
            )
    
    def update_ui_state(self):
        """Update UI elements based on connection state."""
        # Update controls enabled state
        self.conn_type_combo.setEnabled(not self.connected)
        self.usb_resource_combo.setEnabled(not self.connected)
        self.gpib_address_edit.setEnabled(not self.connected)
        self.instrument_type_combo.setEnabled(not self.connected)
        self.refresh_button.setEnabled(not self.connected)
        
        self.connect_button.setEnabled(not self.connected)
        self.disconnect_button.setEnabled(self.connected)
    
    def set_status(self, message, connected=False):
        """Set the connection status message and update display."""
        self.status_label.setText(message)
        
        if connected:
            self.status_label.setStyleSheet(f"""
                padding: 8px;
                border-radius: 4px;
                background-color: {self.colors['success_bg']};
                color: #2ecc71;
                font-weight: bold;
            """)
        else:
            if "error" in message.lower() or "failed" in message.lower():
                self.status_label.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['error_bg']};
                    color: #e74c3c;
                    font-weight: medium;
                """)
            elif "refreshed" in message.lower():
                self.status_label.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['warning_bg']};
                    color: #f39c12;
                    font-weight: medium;
                """)
            else:
                self.status_label.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['input']};
                    color: {self.colors['text']};
                    font-weight: medium;
                """) 