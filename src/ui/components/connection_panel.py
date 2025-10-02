"""
Connection panel for instrument connectivity.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QLineEdit, QGroupBox,
    QFormLayout, QMessageBox, QFrame,
    QStyle, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal

import pyvisa as visa
from instruments.keithley import create_keithley_instrument, KeithleyError
from instruments.pm100d import create_pm100d_instrument, PM100DError
from ..theme import AppTheme


class ConnectionPanel(QWidget):
    """Panel for managing instrument connections."""
    
    # Signals
    connection_status_changed = pyqtSignal(bool, str)  # connected, message
    instrument_connected = pyqtSignal(object)  # Emits the instrument object when connected
    instrument2_connected = pyqtSignal(object)  # Emits the second instrument object when connected
    pm100d_connected = pyqtSignal(object)  # Emits the PM100D instrument object when connected
    dual_instrument_mode_changed = pyqtSignal(bool)  # Emits True when both instruments connected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get centralized theme colors and styles
        self.colors = AppTheme.get_colors()
        self.HEADER_STYLE = AppTheme.header_style()
        self.GROUP_STYLE = AppTheme.group_box_style()
        self.BUTTON_STYLE = AppTheme.button_style()
        self.CONNECT_BUTTON_STYLE = AppTheme.primary_button_style()
        self.DISCONNECT_BUTTON_STYLE = AppTheme.danger_button_style()
        self.INPUT_STYLE = AppTheme.input_style()
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(8)
        
        # Initialize state
        self.connected = False
        self.instrument = None
        self.connected2 = False
        self.instrument2 = None
        self.pm100d_is_connected = False
        self.pm100d_instrument = None
        
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
        self.create_status_section()  # Moved here - right after buttons
        self.create_add_second_instrument_section()
        self.create_pm100d_section()
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
        
        # Update UI state
        self.update_ui_state()
        
        # Connect signals
        self.refresh_button.clicked.connect(self.refresh_devices)
        
        # Refresh device list after UI is fully set up
        self.refresh_devices()
        self.refresh_devices2()
    
    def create_instrument(self, instrument_type):
        """Create an instrument instance based on the selected type."""
        if "Keithley" in instrument_type:
            return create_keithley_instrument(instrument_type)
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
    
    def create_connection_settings(self):
        """Create connection settings group."""
        group_box = QGroupBox("Device Connection")
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
    
    def create_add_second_instrument_section(self):
        """Create collapsible second instrument section."""
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
        
        # Create main container for the add second instrument section
        self.second_instrument_container = QWidget()
        self.second_instrument_layout = QVBoxLayout(self.second_instrument_container)
        self.second_instrument_layout.setContentsMargins(0, 0, 0, 0)
        self.second_instrument_layout.setSpacing(8)
        
        # Add checkbox to enable second instrument
        self.add_second_instrument_check = QCheckBox("➕ Add Second Instrument")
        self.add_second_instrument_check.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
                color: {self.colors['text']};
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: {self.colors['darker']};
                border-radius: 6px;
                border: 1px solid {self.colors['border']};
            }}
            QCheckBox:hover {{
                background-color: {self.colors['light']};
                border: 1px solid {self.colors['primary']};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {self.colors['border']};
                background-color: {self.colors['input']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """)
        self.add_second_instrument_check.toggled.connect(self.on_add_second_instrument_toggled)
        self.second_instrument_layout.addWidget(self.add_second_instrument_check)
        
        # Create the collapsible second instrument section
        self.create_instrument2_section()
        
        # Initially hide the second instrument section
        self.instrument2_section.hide()
        
        self.layout.addWidget(self.second_instrument_container)
    
    def create_instrument2_section(self):
        """Create second instrument section (called from collapsible container)."""
        # Create the second instrument section widget
        self.instrument2_section = QWidget()
        instrument2_layout = QVBoxLayout(self.instrument2_section)
        instrument2_layout.setContentsMargins(0, 0, 0, 0)
        instrument2_layout.setSpacing(8)
        
        # Add title
        title2 = QLabel("Instrument 2")
        title2.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self.colors['text']};")
        title2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        instrument2_layout.addWidget(title2)
        
        # Connection settings for instrument 2
        group_box2 = QGroupBox("Connection Settings")
        group_box2.setStyleSheet(self.GROUP_STYLE)
        form_layout2 = QFormLayout()
        form_layout2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout2.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Connection type for instrument 2
        self.conn_type_combo2 = QComboBox()
        self.conn_type_combo2.addItems(["USB", "GPIB"])
        self.conn_type_combo2.currentIndexChanged.connect(self.on_connection_type2_changed)
        self.conn_type_combo2.setStyleSheet(self.INPUT_STYLE)
        form_layout2.addRow("Connection Type:", self.conn_type_combo2)
        
        # Container for connection specific controls for instrument 2
        self.conn_specific_widget2 = QWidget()
        self.conn_specific_layout2 = QVBoxLayout(self.conn_specific_widget2)
        self.conn_specific_layout2.setContentsMargins(0, 0, 0, 0)
        
        # USB settings for instrument 2
        self.usb_widget2 = QWidget()
        usb_layout2 = QFormLayout(self.usb_widget2)
        usb_layout2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.usb_resource_combo2 = QComboBox()
        self.usb_resource_combo2.setEditable(True)
        self.usb_resource_combo2.setStyleSheet(self.INPUT_STYLE)
        self.usb_resource_combo2.setMinimumWidth(300)
        usb_layout2.addRow("USB Resource:", self.usb_resource_combo2)
        
        # GPIB settings for instrument 2
        self.gpib_widget2 = QWidget()
        gpib_layout2 = QFormLayout(self.gpib_widget2)
        gpib_layout2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.gpib_address_edit2 = QLineEdit("23")  # Default different from instrument 1
        self.gpib_address_edit2.setStyleSheet(self.INPUT_STYLE)
        gpib_layout2.addRow("GPIB Address:", self.gpib_address_edit2)
        
        # Add specific settings to container
        self.conn_specific_layout2.addWidget(self.usb_widget2)
        self.conn_specific_layout2.addWidget(self.gpib_widget2)
        
        # Show appropriate widget based on initial selection
        self.on_connection_type2_changed(0)  # USB is default
        
        form_layout2.addRow(self.conn_specific_widget2)
        
        # Instrument type for instrument 2
        self.instrument_type_combo2 = QComboBox()
        self.instrument_type_combo2.addItems(["Keithley 2400/2450", "Keithley 2600"])
        self.instrument_type_combo2.setStyleSheet(self.INPUT_STYLE)
        form_layout2.addRow("Instrument Type:", self.instrument_type_combo2)
        
        group_box2.setLayout(form_layout2)
        instrument2_layout.addWidget(group_box2)
        
        # Connection controls for instrument 2
        button_layout2 = QHBoxLayout()
        button_layout2.setSpacing(10)
        
        self.connect_button2 = QPushButton("Connect")
        self.connect_button2.clicked.connect(self.on_connect2_clicked)
        self.connect_button2.setStyleSheet(self.CONNECT_BUTTON_STYLE)
        self.connect_button2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_button2.setMinimumHeight(36)
        button_layout2.addWidget(self.connect_button2)
        
        self.disconnect_button2 = QPushButton("Disconnect")
        self.disconnect_button2.clicked.connect(self.on_disconnect2_clicked)
        self.disconnect_button2.setStyleSheet(self.DISCONNECT_BUTTON_STYLE)
        self.disconnect_button2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconnect_button2.setMinimumHeight(36)
        button_layout2.addWidget(self.disconnect_button2)
        
        instrument2_layout.addLayout(button_layout2)
        
        # Status section for instrument 2
        status_group2 = QGroupBox("Instrument 2 Status")
        status_group2.setStyleSheet(self.GROUP_STYLE)
        status_layout2 = QVBoxLayout()
        
        self.status_label2 = QLabel("Not connected")
        self.status_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label2.setStyleSheet(f"""
            padding: 8px;
            border-radius: 4px;
            background-color: {self.colors['input']};
            color: {self.colors['text']};
            font-weight: medium;
        """)
        status_layout2.addWidget(self.status_label2)
        
        status_group2.setLayout(status_layout2)
        instrument2_layout.addWidget(status_group2)
        
        # Add the instrument2 section to the main container
        self.second_instrument_layout.addWidget(self.instrument2_section)
    
    def create_pm100d_section(self):
        """Create PM100D power meter connection section."""
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
        
        # Create main container for PM100D section
        self.pm100d_container = QWidget()
        self.pm100d_container_layout = QVBoxLayout(self.pm100d_container)
        self.pm100d_container_layout.setContentsMargins(0, 0, 0, 0)
        self.pm100d_container_layout.setSpacing(8)
        
        # Add checkbox to enable PM100D
        self.add_pm100d_check = QCheckBox("➕ Add PM100D Power Meter")
        self.add_pm100d_check.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
                color: {self.colors['text']};
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: {self.colors['darker']};
                border-radius: 6px;
                border: 1px solid {self.colors['border']};
            }}
            QCheckBox:hover {{
                background-color: {self.colors['light']};
                border: 1px solid {self.colors['primary']};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {self.colors['border']};
                background-color: {self.colors['input']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['primary']};
                border: 2px solid {self.colors['primary']};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {self.colors['primary']};
            }}
        """)
        self.add_pm100d_check.toggled.connect(self.on_add_pm100d_toggled)
        self.pm100d_container_layout.addWidget(self.add_pm100d_check)
        
        # Create the PM100D section
        self.pm100d_section = QWidget()
        pm100d_layout = QVBoxLayout(self.pm100d_section)
        pm100d_layout.setContentsMargins(0, 0, 0, 0)
        pm100d_layout.setSpacing(8)
        
        # Add title
        title = QLabel("Thorlabs PM100D Power Meter")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self.colors['text']};")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pm100d_layout.addWidget(title)
        
        # Connection controls for PM100D
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.connect_pm100d_button = QPushButton("Connect PM100D")
        self.connect_pm100d_button.clicked.connect(self.on_connect_pm100d_clicked)
        self.connect_pm100d_button.setStyleSheet(self.CONNECT_BUTTON_STYLE)
        self.connect_pm100d_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_pm100d_button.setMinimumHeight(36)
        button_layout.addWidget(self.connect_pm100d_button)
        
        self.disconnect_pm100d_button = QPushButton("Disconnect PM100D")
        self.disconnect_pm100d_button.clicked.connect(self.on_disconnect_pm100d_clicked)
        self.disconnect_pm100d_button.setStyleSheet(self.DISCONNECT_BUTTON_STYLE)
        self.disconnect_pm100d_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconnect_pm100d_button.setMinimumHeight(36)
        button_layout.addWidget(self.disconnect_pm100d_button)
        
        pm100d_layout.addLayout(button_layout)
        
        # Status section for PM100D
        status_group = QGroupBox("PM100D Status")
        status_group.setStyleSheet(self.GROUP_STYLE)
        status_layout = QVBoxLayout()
        
        self.pm100d_status_label = QLabel("Not connected")
        self.pm100d_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pm100d_status_label.setStyleSheet(f"""
            padding: 8px;
            border-radius: 4px;
            background-color: {self.colors['input']};
            color: {self.colors['text']};
            font-weight: medium;
        """)
        status_layout.addWidget(self.pm100d_status_label)
        
        status_group.setLayout(status_layout)
        pm100d_layout.addWidget(status_group)
        
        # Add the PM100D section to the container
        self.pm100d_container_layout.addWidget(self.pm100d_section)
        
        # Initially hide the PM100D section
        self.pm100d_section.hide()
        
        # Add container to main layout
        self.layout.addWidget(self.pm100d_container)
    
    def on_add_pm100d_toggled(self, checked):
        """Handle the add PM100D checkbox toggle."""
        if checked:
            self.pm100d_section.show()
            self.add_pm100d_check.setText("➖ Hide PM100D Power Meter")
        else:
            self.pm100d_section.hide()
            self.add_pm100d_check.setText("➕ Add PM100D Power Meter")
            # Disconnect PM100D if connected
            if self.pm100d_is_connected and self.pm100d_instrument:
                try:
                    self.pm100d_instrument.cleanup()
                    self.pm100d_instrument.disconnect()
                except:
                    pass
                self.pm100d_is_connected = False
                self.pm100d_instrument = None
                self.set_pm100d_status("Disconnected", False)
                self.update_ui_state()
    
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
        # Simple status label without group box for cleaner look
        self.status_label = QLabel("Ready to connect")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            padding: 10px;
            border-radius: 5px;
            background-color: {self.colors['input']};
            color: {self.colors['text_secondary']};
            font-weight: medium;
            font-size: 12px;
            border: 1px solid {self.colors['border']};
        """)
        self.layout.addWidget(self.status_label)
    
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
                
            device_count = self.usb_resource_combo.count()
            self.set_status(f"Found {device_count} USB device(s)", False)
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
            # Create instrument based on selected type
            instrument_type = self.instrument_type_combo.currentText()
            self.instrument = self.create_instrument(instrument_type)
            
            # Connect to the instrument
            # Keithley instruments need resource name
            if self.conn_type_combo.currentIndex() == 0:  # USB
                resource_name = self.usb_resource_combo.currentText()
            else:  # GPIB
                address = self.gpib_address_edit.text()
                resource_name = f"GPIB::{address}"
            self.instrument.connect(resource_name)
            
            # Update UI state
            self.connected = True
            self.update_ui_state()
            
            # Get instrument info for display
            instrument_info = self.instrument.get_instrument_info()
            message = f"Connected to {instrument_info.strip()}"
            
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
        # Update controls enabled state for instrument 1
        self.conn_type_combo.setEnabled(not self.connected)
        self.usb_resource_combo.setEnabled(not self.connected)
        self.gpib_address_edit.setEnabled(not self.connected)
        self.instrument_type_combo.setEnabled(not self.connected)
        self.refresh_button.setEnabled(not self.connected)
        
        self.connect_button.setEnabled(not self.connected)
        self.disconnect_button.setEnabled(self.connected)
        
        # Update button styling based on enabled state
        if self.connected:
            self.connect_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #7f8c8d;
                    color: {self.colors['text']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    border: 2px solid #7f8c8d;
                }}
            """)
            self.disconnect_button.setStyleSheet(self.DISCONNECT_BUTTON_STYLE)
        else:
            self.connect_button.setStyleSheet(self.CONNECT_BUTTON_STYLE)
            self.disconnect_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #7f8c8d;
                    color: {self.colors['text']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    border: 2px solid #7f8c8d;
                }}
            """)
        
        # Update controls enabled state for instrument 2 (only if section is visible)
        if hasattr(self, 'instrument2_section') and self.instrument2_section.isVisible():
            self.conn_type_combo2.setEnabled(not self.connected2)
            self.usb_resource_combo2.setEnabled(not self.connected2)
            self.gpib_address_edit2.setEnabled(not self.connected2)
            self.instrument_type_combo2.setEnabled(not self.connected2)
            
            self.connect_button2.setEnabled(not self.connected2)
            self.disconnect_button2.setEnabled(self.connected2)
        
        # Update PM100D controls
        if hasattr(self, 'connect_pm100d_button'):
            self.connect_pm100d_button.setEnabled(not self.pm100d_is_connected)
            self.disconnect_pm100d_button.setEnabled(self.pm100d_is_connected)
            
            # Update button styling based on enabled state for instrument 2
            if self.connected2:
                self.connect_button2.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #7f8c8d;
                        color: {self.colors['text']};
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: bold;
                        border: 2px solid #7f8c8d;
                    }}
                """)
                self.disconnect_button2.setStyleSheet(self.DISCONNECT_BUTTON_STYLE)
            else:
                self.connect_button2.setStyleSheet(self.CONNECT_BUTTON_STYLE)
                self.disconnect_button2.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #7f8c8d;
                        color: {self.colors['text']};
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: bold;
                        border: 2px solid #7f8c8d;
                    }}
                """)
    
    def set_status(self, message, connected=False):
        """Set the connection status message and update display."""
        self.status_label.setText(message)
        
        if connected:
            self.status_label.setStyleSheet(f"""
                padding: 10px;
                border-radius: 5px;
                background-color: {self.colors['success_bg']};
                color: #2ecc71;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #27ae60;
            """)
        else:
            if "error" in message.lower() or "failed" in message.lower():
                self.status_label.setStyleSheet(f"""
                    padding: 10px;
                    border-radius: 5px;
                    background-color: {self.colors['error_bg']};
                    color: #e74c3c;
                    font-weight: medium;
                    font-size: 12px;
                    border: 1px solid #e74c3c;
                """)
            elif "found" in message.lower() or "refreshed" in message.lower():
                self.status_label.setStyleSheet(f"""
                    padding: 10px;
                    border-radius: 5px;
                    background-color: {self.colors['input']};
                    color: {self.colors['primary']};
                    font-weight: medium;
                    font-size: 12px;
                    border: 1px solid {self.colors['border']};
                """)
            else:
                self.status_label.setStyleSheet(f"""
                    padding: 10px;
                    border-radius: 5px;
                    background-color: {self.colors['input']};
                    color: {self.colors['text_secondary']};
                    font-weight: medium;
                    font-size: 12px;
                    border: 1px solid {self.colors['border']};
                """)
    
    def on_connection_type2_changed(self, index):
        """Handle connection type change for instrument 2."""
        if index == 0:  # USB
            self.usb_widget2.show()
            self.gpib_widget2.hide()
        else:  # GPIB
            self.usb_widget2.hide()
            self.gpib_widget2.show()
    
    def refresh_devices2(self):
        """Refresh the list of available devices for instrument 2."""
        try:
            # Clear existing items
            self.usb_resource_combo2.clear()
            
            # Get all available resources
            rm = visa.ResourceManager()
            resources = rm.list_resources()
            
            # Add USB resources to the combo box
            for resource in resources:
                if "USB" in resource:
                    self.usb_resource_combo2.addItem(resource)
            
            # Add default USB resources if none found
            if self.usb_resource_combo2.count() == 0:
                self.usb_resource_combo2.addItem("USB0::0x05E6::0x2280::4593849::INSTR")  # Example
                self.usb_resource_combo2.addItem("USB0::0x05E6::0x2280::4393711::INSTR")  # Example
                
        except Exception as e:
            self.set_status2(f"Error refreshing devices: {str(e)}", False)
    
    def on_connect2_clicked(self):
        """Handle connect button click for instrument 2."""
        try:
            # Create instrument based on selected type
            instrument_type = self.instrument_type_combo2.currentText()
            self.instrument2 = self.create_instrument(instrument_type)
            
            # Connect to the instrument
            # Keithley instruments need resource name
            if self.conn_type_combo2.currentIndex() == 0:  # USB
                resource_name = self.usb_resource_combo2.currentText()
            else:  # GPIB
                address = self.gpib_address_edit2.text()
                resource_name = f"GPIB::{address}"
            self.instrument2.connect(resource_name)
            
            # Update UI state
            self.connected2 = True
            self.update_ui_state()
            
            # Get instrument info for display
            instrument_info = self.instrument2.get_instrument_info()
            message = f"Connected to {instrument_info.strip()}"
            
            # Update status and emit signals
            self.set_status2(message, True)
            self.instrument2_connected.emit(self.instrument2)
            
            # Check if both instruments are connected
            self.check_dual_mode()
            
        except KeithleyError as e:
            self.connected2 = False
            self.update_ui_state()
            self.set_status2(f"Connection failed: {str(e)}", False)
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Failed to connect to instrument 2: {str(e)}"
            )
        except Exception as e:
            self.connected2 = False
            self.update_ui_state()
            self.set_status2(f"Connection error: {str(e)}", False)
            QMessageBox.critical(
                self,
                "Connection Error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def on_disconnect2_clicked(self):
        """Handle disconnect button click for instrument 2."""
        if not self.instrument2:
            self.connected2 = False
            self.update_ui_state()
            self.set_status2("Disconnected", False)
            self.check_dual_mode()
            return
            
        try:
            # Cleanup and disconnect
            self.instrument2.cleanup()
            self.instrument2.disconnect()
            
            # Update state
            self.connected2 = False
            self.instrument2 = None
            self.update_ui_state()
            
            # Update status and emit signal
            self.set_status2("Disconnected", False)
            self.check_dual_mode()
            
        except Exception as e:
            self.set_status2(f"Disconnect error: {str(e)}", False)
            QMessageBox.warning(
                self,
                "Disconnect Error",
                f"Error during disconnect: {str(e)}"
            )
    
    def set_status2(self, message, connected=False):
        """Set the connection status message for instrument 2."""
        self.status_label2.setText(message)
        
        if connected:
            self.status_label2.setStyleSheet(f"""
                padding: 8px;
                border-radius: 4px;
                background-color: {self.colors['success_bg']};
                color: #2ecc71;
                font-weight: bold;
            """)
        else:
            if "error" in message.lower() or "failed" in message.lower():
                self.status_label2.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['error_bg']};
                    color: #e74c3c;
                    font-weight: medium;
                """)
            else:
                self.status_label2.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['input']};
                    color: {self.colors['text']};
                    font-weight: medium;
                """)
    
    def check_dual_mode(self):
        """Check if both instruments are connected and emit dual mode signal."""
        dual_mode = self.connected and self.connected2
        self.dual_instrument_mode_changed.emit(dual_mode)
    
    def on_add_second_instrument_toggled(self, checked):
        """Handle the add second instrument checkbox toggle."""
        if checked:
            self.instrument2_section.show()
            # Update icon to show collapse
            self.add_second_instrument_check.setText("➖ Hide Second Instrument")
            # Refresh device list for instrument 2
            self.refresh_devices2()
        else:
            self.instrument2_section.hide()
            # Update icon to show expand
            self.add_second_instrument_check.setText("➕ Add Second Instrument")
            # Disconnect instrument 2 if connected
            if self.connected2 and self.instrument2:
                try:
                    self.instrument2.cleanup()
                    self.instrument2.disconnect()
                except:
                    pass
                self.connected2 = False
                self.instrument2 = None
                self.set_status2("Disconnected", False)
                self.check_dual_mode()
                self.update_ui_state()
    
    def on_connect_pm100d_clicked(self):
        """Handle PM100D connect button click."""
        try:
            # Create PM100D instrument
            self.pm100d_instrument = create_pm100d_instrument()
            
            # Connect to the instrument
            self.pm100d_instrument.connect()
            
            # Update UI state
            self.pm100d_is_connected = True
            self.update_ui_state()
            
            # Get instrument info for display
            instrument_info = self.pm100d_instrument.get_instrument_info()
            message = f"Connected to {instrument_info.strip()}"
            
            # Update status and emit signals
            self.set_pm100d_status(message, True)
            self.pm100d_connected.emit(self.pm100d_instrument)
            
        except PM100DError as e:
            self.pm100d_is_connected = False
            self.update_ui_state()
            self.set_pm100d_status(f"Connection failed: {str(e)}", False)
            QMessageBox.critical(
                self,
                "PM100D Connection Error",
                f"Failed to connect to PM100D: {str(e)}"
            )
        except Exception as e:
            self.pm100d_is_connected = False
            self.update_ui_state()
            self.set_pm100d_status(f"Connection error: {str(e)}", False)
            QMessageBox.critical(
                self,
                "PM100D Connection Error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def on_disconnect_pm100d_clicked(self):
        """Handle PM100D disconnect button click."""
        if not self.pm100d_instrument:
            self.pm100d_is_connected = False
            self.update_ui_state()
            self.set_pm100d_status("Disconnected", False)
            return
            
        try:
            # Cleanup and disconnect
            self.pm100d_instrument.cleanup()
            self.pm100d_instrument.disconnect()
            
            # Update state
            self.pm100d_is_connected = False
            self.pm100d_instrument = None
            self.update_ui_state()
            
            # Update status
            self.set_pm100d_status("Disconnected", False)
            
        except Exception as e:
            self.set_pm100d_status(f"Disconnect error: {str(e)}", False)
            QMessageBox.warning(
                self,
                "PM100D Disconnect Error",
                f"Error during disconnect: {str(e)}"
            )
    
    def set_pm100d_status(self, message, connected=False):
        """Set the PM100D connection status message."""
        self.pm100d_status_label.setText(message)
        
        if connected:
            self.pm100d_status_label.setStyleSheet(f"""
                padding: 8px;
                border-radius: 4px;
                background-color: {self.colors['success_bg']};
                color: #2ecc71;
                font-weight: bold;
            """)
        else:
            if "error" in message.lower() or "failed" in message.lower():
                self.pm100d_status_label.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['error_bg']};
                    color: #e74c3c;
                    font-weight: medium;
                """)
            else:
                self.pm100d_status_label.setStyleSheet(f"""
                    padding: 8px;
                    border-radius: 4px;
                    background-color: {self.colors['input']};
                    color: {self.colors['text']};
                    font-weight: medium;
                """) 