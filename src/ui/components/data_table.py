"""
Data table component for displaying measurement results.
"""

import os
import numpy as np
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PyQt6.QtCore import pyqtSlot, Qt


class DataTable(QWidget):
    """Widget for displaying measurement data in a table."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.voltage_forward = []
        self.current_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Create table
        self.table = QTableWidget(0, 4)  # rows, columns
        self.table.setHorizontalHeaderLabels([
            "Voltage Forward (V)", "Current Forward (mA)",
            "Voltage Reverse (V)", "Current Reverse (mA)"
        ])
        
        # Set table properties
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        
        # Add to layout
        self.layout.addWidget(self.table)
        
        # Create button bar
        self.create_button_bar()
    
    def create_button_bar(self):
        """Create button bar for table controls."""
        button_layout = QHBoxLayout()
        
        # Export button
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.on_export_clicked)
        button_layout.addWidget(self.export_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear Table")
        self.clear_button.clicked.connect(self.clear_table)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        self.layout.addLayout(button_layout)
    
    @pyqtSlot(dict)
    def update_table(self, data):
        """Update the table with new data."""
        bidirectional = 'voltage_reverse' in data and 'current_reverse' in data
        
        # Store the data
        if bidirectional:
            self.voltage_forward = data['voltage_forward']
            self.current_forward = data['current_forward']
            self.voltage_reverse = data['voltage_reverse']
            self.current_reverse = data['current_reverse']
        else:
            self.voltage_forward = data['voltage']
            self.current_forward = data['current']
            self.voltage_reverse = []
            self.current_reverse = []
        
        # Clear existing data
        self.table.setRowCount(0)
        
        # Determine number of rows needed
        num_rows = max(len(self.voltage_forward), len(self.voltage_reverse))
        
        # Add data to table
        self.table.setRowCount(num_rows)
        
        for i in range(num_rows):
            # Forward data
            if i < len(self.voltage_forward):
                self.table.setItem(
                    i, 0, 
                    QTableWidgetItem(f"{self.voltage_forward[i]:.6f}")
                )
                self.table.setItem(
                    i, 1, 
                    QTableWidgetItem(f"{self.current_forward[i]:.6f}")
                )
            else:
                self.table.setItem(i, 0, QTableWidgetItem(""))
                self.table.setItem(i, 1, QTableWidgetItem(""))
            
            # Reverse data
            if i < len(self.voltage_reverse):
                self.table.setItem(
                    i, 2, 
                    QTableWidgetItem(f"{self.voltage_reverse[i]:.6f}")
                )
                self.table.setItem(
                    i, 3, 
                    QTableWidgetItem(f"{self.current_reverse[i]:.6f}")
                )
            else:
                self.table.setItem(i, 2, QTableWidgetItem(""))
                self.table.setItem(i, 3, QTableWidgetItem(""))
    
    def clear_table(self):
        """Clear the table."""
        self.voltage_forward = []
        self.current_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        
        self.table.setRowCount(0)
    
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
                if self.voltage_reverse:
                    header.extend(["Voltage Reverse (V)", "Current Reverse (mA)"])
                writer.writerow(header)
                
                # Write data
                max_rows = max(len(self.voltage_forward), len(self.voltage_reverse))
                for i in range(max_rows):
                    row = []
                    
                    # Forward data
                    if i < len(self.voltage_forward):
                        row.append(f"{self.voltage_forward[i]:.6f}")
                        row.append(f"{self.current_forward[i]:.6f}")
                    else:
                        row.extend(["", ""])
                    
                    # Reverse data
                    if self.voltage_reverse and i < len(self.voltage_reverse):
                        row.append(f"{self.voltage_reverse[i]:.6f}")
                        row.append(f"{self.current_reverse[i]:.6f}")
                    
                    writer.writerow(row)
        except Exception as e:
            print(f"Error exporting data: {str(e)}") 