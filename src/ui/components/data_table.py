"""
Data table component for displaying measurement results and plotting data.
"""

import os
import numpy as np
import csv
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QSplitter, QGroupBox, QLabel, QMessageBox
)
from PyQt6.QtCore import pyqtSlot, Qt
from ..theme import AppTheme
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class DataTable(QWidget):
    """Widget for displaying measurement data in a table and plotting data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.voltage_forward = []
        self.current_forward = []
        self.power_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        self.power_reverse = []
        self.loaded_data = None  # For loaded files
        
        # Get centralized theme colors
        self.colors = AppTheme.get_colors()
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for table and plot
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # Create left panel (controls and table)
        self.create_left_panel()
        
        # Create right panel (plot)
        self.create_right_panel()
        
        # Set splitter proportions (60% table, 40% plot)
        self.splitter.setSizes([600, 400])
    
    def create_left_panel(self):
        """Create left panel with controls and table."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # File loading section
        file_group = QGroupBox("Data Loading")
        file_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.colors['darker']};
                color: {self.colors['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        file_layout = QVBoxLayout(file_group)
        
        # File loading buttons
        button_layout = QHBoxLayout()
        
        self.load_file_button = QPushButton("📁 Load Data File")
        self.load_file_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: 2px solid {self.colors['primary']};
            }}
            QPushButton:hover {{
                background-color: #3498db;
                border: 2px solid #3498db;
            }}
        """)
        self.load_file_button.clicked.connect(self.load_data_file)
        button_layout.addWidget(self.load_file_button)
        
        self.filename_label = QLabel("No file loaded")
        self.filename_label.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 5px;")
        button_layout.addWidget(self.filename_label)
        
        button_layout.addStretch()
        file_layout.addLayout(button_layout)
        
        left_layout.addWidget(file_group)
        
        # Data table
        table_group = QGroupBox("Data Table")
        table_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.colors['darker']};
                color: {self.colors['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        table_layout = QVBoxLayout(table_group)
        
        # Create table with power columns for P-I-V data
        self.table = QTableWidget(0, 7)  # Added row number + power columns
        self.table.setHorizontalHeaderLabels([
            "#", "Voltage Forward (V)", "Current Forward (mA)", "Power Forward (mW)",
            "Voltage Reverse (V)", "Current Reverse (mA)", "Power Reverse (mW)"
        ])
        
        # Set table properties
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                gridline-color: {self.colors['border']};
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {self.colors['border']};
            }}
            QHeaderView::section {{
                background-color: {self.colors['dark']};
                color: {self.colors['text']};
                padding: 8px;
                border: none;
                border-right: 1px solid {self.colors['border']};
                border-bottom: 1px solid {self.colors['border']};
                font-weight: bold;
            }}
        """)
        
        # Add empty state message
        self.empty_state_label = QLabel("📊 No data loaded\n\nLoad a data file or perform a measurement to see data here")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 14px;
            padding: 40px;
            background-color: {self.colors['input']};
            border-radius: 6px;
            border: 2px dashed {self.colors['border']};
        """)
        self.empty_state_label.hide()  # Initially hidden
        table_layout.addWidget(self.empty_state_label)
        
        table_layout.addWidget(self.table)
        
        # Table action buttons
        table_buttons = QHBoxLayout()
        
        self.export_button = QPushButton("📤 Export Data")
        self.export_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: 2px solid {self.colors['secondary']};
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
                border: 2px solid #2ecc71;
            }}
        """)
        self.export_button.clicked.connect(self.on_export_clicked)
        table_buttons.addWidget(self.export_button)
        
        self.clear_button = QPushButton("🗑️ Clear Table")
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['danger']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: 2px solid {self.colors['danger']};
            }}
            QPushButton:hover {{
                background-color: #e74c3c;
                border: 2px solid #e74c3c;
            }}
        """)
        self.clear_button.clicked.connect(self.clear_table)
        table_buttons.addWidget(self.clear_button)
        
        table_buttons.addStretch()
        table_layout.addLayout(table_buttons)
        
        left_layout.addWidget(table_group)
        
        # Add to splitter
        self.splitter.addWidget(left_widget)
    
    def create_right_panel(self):
        """Create right panel with plot."""
        plot_group = QGroupBox("Data Visualization")
        plot_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.colors['darker']};
                color: {self.colors['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        plot_layout = QVBoxLayout(plot_group)
        
        # Create matplotlib canvas
        self.plot_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.plot_canvas.setStyleSheet(f"background-color: {self.colors['input']};")
        
        # Set dark theme for matplotlib
        plt.style.use('dark_background')
        
        # Add placeholder for empty visualization
        self.plot_placeholder = QLabel("📈 No data to visualize\n\nLoad a data file or perform a measurement to see plots here")
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_placeholder.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 14px;
            padding: 40px;
            background-color: {self.colors['input']};
            border-radius: 6px;
            border: 2px dashed {self.colors['border']};
        """)
        
        plot_layout.addWidget(self.plot_placeholder)
        plot_layout.addWidget(self.plot_canvas)
        
        # Initially show placeholder, hide canvas
        self.plot_canvas.hide()
        
        # Add to splitter
        self.splitter.addWidget(plot_group)
    
    def load_data_file(self):
        """Load data from various file formats."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", 
            "All Supported Files (*.txt *.csv *.xlsx *.xls *.dat);;"
            "Text Files (*.txt);;"
            "CSV Files (*.csv);;"
            "Excel Files (*.xlsx *.xls);;"
            "Data Files (*.dat);;"
            "All Files (*)"
        )
        
        if file_path:
            try:
                # Load data using the same method as analysis panel
                data = self.load_data_file_content(file_path)
                
                if data.shape[1] < 2:
                    QMessageBox.warning(self, "File Error", "File must contain at least 2 columns (V, I)")
                    return
                
                # Store loaded data
                self.loaded_data = data
                
                # Update filename label
                filename = os.path.basename(file_path)
                self.filename_label.setText(f"Loaded: {filename}")
                self.filename_label.setStyleSheet(f"color: {self.colors['secondary']}; padding: 5px;")
                
                # Update table and plot
                self.update_display_from_loaded_data()
                
            except Exception as e:
                QMessageBox.warning(self, "File Error", f"Error loading file: {str(e)}")
    
    def load_data_file_content(self, file_path):
        """Load data from various file formats."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.csv']:
            try:
                df = pd.read_csv(file_path, skipinitialspace=True)
                data = df.values
            except:
                data = np.loadtxt(file_path, delimiter=',')
                
        elif file_ext in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(file_path)
                data = df.values
            except Exception as e:
                raise Exception(f"Error reading Excel file: {str(e)}")
                
        elif file_ext in ['.txt', '.dat']:
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', skipinitialspace=True)
                data = df.values
            except:
                try:
                    data = np.loadtxt(file_path)
                except:
                    for delimiter in ['\t', ',', ';', ' ']:
                        try:
                            data = np.loadtxt(file_path, delimiter=delimiter)
                            break
                        except:
                            continue
                    else:
                        raise Exception("Could not parse file with any known delimiter")
        else:
            try:
                data = np.loadtxt(file_path)
            except:
                try:
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    data = df.values
                except:
                    raise Exception(f"Unsupported file format: {file_ext}")
        
        try:
            data = data.astype(float)
        except:
            raise Exception("File contains non-numeric data")
        
        return data
    
    def update_display_from_loaded_data(self):
        """Update table and plot from loaded data."""
        if self.loaded_data is None:
            return
        
        try:
            # Assume first column is voltage, second is current
            voltage = self.loaded_data[:, 0]
            current = self.loaded_data[:, 1]
            
            # Store as forward data
            self.voltage_forward = voltage.tolist()
            self.current_forward = current.tolist()
            self.voltage_reverse = []
            self.current_reverse = []
            
            # Update table
            self.update_table_display()
            
            # Update plot
            self.update_plot()
            
        except Exception as e:
            QMessageBox.warning(self, "Display Error", f"Error updating display: {str(e)}")
    
    def update_plot(self):
        """Update the plot with current data."""
        try:
            # Check if we have any data to plot
            has_data = (self.voltage_forward and self.current_forward) or (self.voltage_reverse and self.current_reverse)
            
            if not has_data:
                # Show placeholder, hide plot
                self.plot_placeholder.show()
                self.plot_canvas.hide()
                return
            
            # Hide placeholder, show plot
            self.plot_placeholder.hide()
            self.plot_canvas.show()
            
            # Clear the plot
            self.plot_canvas.figure.clear()
            ax = self.plot_canvas.figure.add_subplot(111)
            
            # Plot forward data if available
            if self.voltage_forward and self.current_forward:
                ax.plot(self.voltage_forward, self.current_forward, 'o-', 
                       color='#3498db', markersize=4, linewidth=2, 
                       alpha=0.8, label='Forward')
            
            # Plot reverse data if available
            if self.voltage_reverse and self.current_reverse:
                ax.plot(self.voltage_reverse, self.current_reverse, 's-', 
                       color='#e74c3c', markersize=4, linewidth=2, 
                       alpha=0.8, label='Reverse')
            
            # Set labels and title
            ax.set_xlabel('Voltage (V)')
            ax.set_ylabel('Current (mA)')
            ax.set_title('I-V Characteristics')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Apply dark theme
            ax.set_facecolor('#2c3e50')
            self.plot_canvas.figure.patch.set_facecolor('#2c3e50')
            
            # Refresh the plot
            self.plot_canvas.draw()
            
        except Exception as e:
            pass
    
    def update_table_display(self):
        """Update table display with current data."""
        # Clear existing data
        self.table.setRowCount(0)
        
        # Determine number of rows needed
        num_rows = max(len(self.voltage_forward), len(self.voltage_reverse))
        
        if num_rows == 0:
            # Show empty state
            self.empty_state_label.show()
            self.table.hide()
            return
        
        # Hide empty state and show table
        self.empty_state_label.hide()
        self.table.show()
        
        # Add data to table
        self.table.setRowCount(num_rows)
        
        for i in range(num_rows):
            # Row number
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # Forward data
            if i < len(self.voltage_forward):
                self.table.setItem(
                    i, 1, 
                    QTableWidgetItem(f"{self.voltage_forward[i]:.6f}")
                )
                self.table.setItem(
                    i, 2, 
                    QTableWidgetItem(f"{self.current_forward[i]:.6f}")
                )
                # Power forward (show if available)
                if i < len(self.power_forward) and self.power_forward[i] is not None:
                    self.table.setItem(
                        i, 3, 
                        QTableWidgetItem(f"{self.power_forward[i]:.6f}")
                    )
                else:
                    self.table.setItem(i, 3, QTableWidgetItem(""))
            else:
                self.table.setItem(i, 1, QTableWidgetItem(""))
                self.table.setItem(i, 2, QTableWidgetItem(""))
                self.table.setItem(i, 3, QTableWidgetItem(""))
            
            # Reverse data
            if i < len(self.voltage_reverse):
                self.table.setItem(
                    i, 4, 
                    QTableWidgetItem(f"{self.voltage_reverse[i]:.6f}")
                )
                self.table.setItem(
                    i, 5, 
                    QTableWidgetItem(f"{self.current_reverse[i]:.6f}")
                )
                # Power reverse (show if available)
                if i < len(self.power_reverse) and self.power_reverse[i] is not None:
                    self.table.setItem(
                        i, 6, 
                        QTableWidgetItem(f"{self.power_reverse[i]:.6f}")
                    )
                else:
                    self.table.setItem(i, 6, QTableWidgetItem(""))
            else:
                self.table.setItem(i, 4, QTableWidgetItem(""))
                self.table.setItem(i, 5, QTableWidgetItem(""))
                self.table.setItem(i, 6, QTableWidgetItem(""))
    
    @pyqtSlot(dict)
    def update_table(self, data):
        """Update the table with new measurement data."""
        bidirectional = 'voltage_reverse' in data and 'current_reverse' in data
        has_power = 'power' in data or 'power_forward' in data
        
        # Store the data
        if bidirectional:
            self.voltage_forward = data['voltage_forward']
            self.current_forward = data['current_forward']
            self.voltage_reverse = data['voltage_reverse']
            self.current_reverse = data['current_reverse']
            
            # Handle power data
            if has_power:
                self.power_forward = data.get('power_forward', [])
                self.power_reverse = data.get('power_reverse', [])
            else:
                self.power_forward = []
                self.power_reverse = []
        else:
            self.voltage_forward = data['voltage']
            self.current_forward = data['current']
            self.voltage_reverse = []
            self.current_reverse = []
            
            # Handle power data
            if has_power:
                self.power_forward = data.get('power', [])
                self.power_reverse = []
            else:
                self.power_forward = []
                self.power_reverse = []
        
        # Update display
        self.update_table_display()
        self.update_plot()
    
    def clear_table(self):
        """Clear the table and plot."""
        self.voltage_forward = []
        self.current_forward = []
        self.power_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        self.power_reverse = []
        self.loaded_data = None
        
        # Clear table
        self.table.setRowCount(0)
        
        # Show empty state
        self.empty_state_label.show()
        self.table.hide()
        
        # Clear plot and show placeholder
        self.plot_canvas.figure.clear()
        self.plot_canvas.draw()
        self.plot_placeholder.show()
        self.plot_canvas.hide()
        
        # Reset filename label
        self.filename_label.setText("No file loaded")
        self.filename_label.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 5px;")
    
    def on_export_clicked(self):
        """Handle export button click to save the data as a CSV file."""
        if not (self.voltage_forward or self.voltage_reverse):
            return  # Nothing to export
        
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data",
            os.path.expanduser("~/Desktop"),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        # Add .csv extension if not present
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
            
        # Write to CSV
        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                header = ["Voltage Forward (V)", "Current Forward (mA)"]
                if self.power_forward:
                    header.append("Power Forward (mW)")
                if self.voltage_reverse:
                    header.extend(["Voltage Reverse (V)", "Current Reverse (mA)"])
                    if self.power_reverse:
                        header.append("Power Reverse (mW)")
                writer.writerow(header)
                
                # Write data
                max_rows = max(len(self.voltage_forward), len(self.voltage_reverse))
                for i in range(max_rows):
                    row = []
                    
                    # Forward data
                    if i < len(self.voltage_forward):
                        row.append(f"{self.voltage_forward[i]:.6f}")
                        row.append(f"{self.current_forward[i]:.6f}")
                        if self.power_forward and i < len(self.power_forward) and self.power_forward[i] is not None:
                            row.append(f"{self.power_forward[i]:.6f}")
                        elif self.power_forward:
                            row.append("")
                    else:
                        row.extend(["", ""])
                        if self.power_forward:
                            row.append("")
                    
                    # Reverse data
                    if self.voltage_reverse and i < len(self.voltage_reverse):
                        row.append(f"{self.voltage_reverse[i]:.6f}")
                        row.append(f"{self.current_reverse[i]:.6f}")
                        if self.power_reverse and i < len(self.power_reverse) and self.power_reverse[i] is not None:
                            row.append(f"{self.power_reverse[i]:.6f}")
                        elif self.power_reverse:
                            row.append("")
                    
                    writer.writerow(row)
        except Exception as e:
            # Silently handle export errors
            pass