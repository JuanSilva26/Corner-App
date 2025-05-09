"""
Analysis panel for TLM (Transmission Line Method) measurements and resistance extraction.
"""

import os
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFormLayout, QFileDialog,
    QFrame, QScrollArea, QLineEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QSizePolicy, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class TLMCanvas(FigureCanvas):
    """Canvas for plotting TLM data."""
    
    def __init__(self, parent=None, width=8, height=5, dpi=100):
        # Increase size and DPI for better visuals
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # Set dark mode style for plots with improved aesthetics
        plt.style.use('dark_background')
        self.fig.patch.set_facecolor('#1e272e')
        self.axes.set_facecolor('#1e272e')
        
        # Apply enhanced styling to axes
        self.axes.tick_params(colors='#ecf0f1', labelsize=10, length=6, width=1)
        self.axes.spines['bottom'].set_color('#34495e')
        self.axes.spines['top'].set_color('#34495e')
        self.axes.spines['left'].set_color('#34495e')
        self.axes.spines['right'].set_color('#34495e')
        
        # Enhanced text styling
        self.axes.xaxis.label.set_color('#ecf0f1')
        self.axes.xaxis.label.set_fontsize(12)
        self.axes.xaxis.label.set_fontweight('bold')
        
        self.axes.yaxis.label.set_color('#ecf0f1')
        self.axes.yaxis.label.set_fontsize(12)
        self.axes.yaxis.label.set_fontweight('bold')
        
        self.axes.title.set_color('#ecf0f1')
        self.axes.title.set_fontsize(14)
        self.axes.title.set_fontweight('bold')
        
        super(TLMCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # Make the canvas expandable
        FigureCanvas.setSizePolicy(self,
                                  QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)
    
    def plot_tlm_data(self, distances, resistances, slope, intercept, r_squared, min_voltage):
        """Plot the TLM data."""
        try:
            # Clear the existing plot
            self.axes.clear()
            
            # Convert resistances from ohms to kilohms for plotting
            resistances_kohm = resistances / 1000.0
            
            # Plot the data points with enhanced styling
            self.axes.scatter(distances, resistances_kohm, color='#3498db', s=80, 
                          alpha=0.7, edgecolor='#2980b9', linewidth=1.5, 
                          label='Measured Data')
            
            # Set labels and title with improved formatting
            self.axes.set_xlabel('TLM Distance (μm)')
            self.axes.set_ylabel('Resistance (kΩ)')
            self.axes.set_title(f'TLM Analysis')
            
            # Add enhanced grid
            self.axes.grid(True, linestyle='--', alpha=0.5, color='#566573', linewidth=0.8)
            
            # Add legend with improved styling
            legend = self.axes.legend(loc='upper right', fontsize=10, framealpha=0.9)
            legend.get_frame().set_facecolor('#2c3e50')
            legend.get_frame().set_edgecolor('#34495e')
            
            # Make sure axes start from 0,0 if possible
            x_min, x_max = self.axes.get_xlim()
            y_min, y_max = self.axes.get_ylim()
            self.axes.set_xlim(left=max(0, x_min))
            self.axes.set_ylim(bottom=max(0, y_min))
            
            # Add some padding to the axes
            self.axes.margins(x=0.05, y=0.05)
            
            self.fig.tight_layout()
            self.draw()
            
        except Exception as e:
            # Print error to console for debugging
            print(f"Error in plot_tlm_data: {str(e)}")
            # Plot will remain blank if error occurs


class AnalysisPanel(QWidget):
    """Panel for analyzing TLM measurements."""
    
    # Signals
    analysis_completed = pyqtSignal(dict)  # Emits analysis results
    
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
        self.PRIMARY_BUTTON_STYLE = f"""
            QPushButton {{ 
                background-color: {self.colors['primary']}; 
                color: {self.colors['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: #3498db; 
            }} 
            QPushButton:pressed {{ 
                background-color: #1c6ea4;
            }}
            QPushButton:disabled {{ 
                background-color: {self.colors['light']}; 
                color: {self.colors['text_secondary']};
            }}
        """
        self.SECONDARY_BUTTON_STYLE = f"""
            QPushButton {{ 
                background-color: {self.colors['secondary']}; 
                color: {self.colors['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: #2ecc71; 
            }} 
            QPushButton:pressed {{ 
                background-color: #27ae60;
            }}
            QPushButton:disabled {{ 
                background-color: {self.colors['light']}; 
                color: {self.colors['text_secondary']};
            }}
        """
        self.INPUT_STYLE = f"""
            QLineEdit, QDoubleSpinBox {{
                padding: 5px;
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['primary']};
                min-height: 25px;
            }}
            QLineEdit:focus, QDoubleSpinBox:focus {{
                border: 1px solid {self.colors['primary']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                border: none;
                background-color: {self.colors['button']};
                color: {self.colors['text']};
                width: 16px;
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {self.colors['primary']};
            }}
        """
        self.TABLE_STYLE = f"""
            QTableWidget {{
                background-color: {self.colors['dark']};
                color: {self.colors['text']};
                gridline-color: {self.colors['border']};
                border: 1px solid {self.colors['border']};
                border-radius: 5px;
                selection-background-color: {self.colors['primary']};
                selection-color: {self.colors['text']};
            }}
            QHeaderView::section {{
                background-color: {self.colors['darker']};
                color: {self.colors['text']};
                padding: 5px;
                border: 1px solid {self.colors['border']};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {self.colors['primary']};
            }}
        """
        
        # Data storage for TLM analysis
        self.tlm_files = []  # List of file paths
        self.tlm_distances = []  # List of distances
        self.resistances = []  # List of extracted resistances
        self.iv_data = []  # List of (voltage, current) data for each file
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(8)
        
        # Add title
        title = QLabel("Analysis Tools")
        title.setStyleSheet(self.HEADER_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.layout.addWidget(title)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
        
        # Create TLM analysis group
        self.create_tlm_group()
        
        # Create data table and results section
        self.create_results_section()
        
        # Create placeholder for TLM plot
        self.create_plot_section()
        
        # Connect signals
        self.load_tlm_button.clicked.connect(self.load_tlm_files)
        self.add_files_button.clicked.connect(self.add_tlm_files)
        self.analyze_button.clicked.connect(self.perform_tlm_analysis)
        self.clear_button.clicked.connect(self.clear_analysis)
        # Connect min voltage change to trigger new analysis if analyze button is enabled
        self.min_voltage_input.valueChanged.connect(self.min_voltage_changed)
    
    def create_tlm_group(self):
        """Create TLM analysis control group."""
        tlm_group = QGroupBox("TLM Analysis")
        tlm_group.setStyleSheet(self.GROUP_STYLE)
        tlm_layout = QVBoxLayout(tlm_group)
        
        # Description label
        description = QLabel(
            "TLM (Transmission Line Method) analysis extracts contact and sheet resistance from "
            "a series of resistance measurements at different contact spacings."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {self.colors['text_secondary']};")
        tlm_layout.addWidget(description)
        
        # Create fitting options layout (for min voltage, etc.)
        fitting_layout = QHBoxLayout()
        fitting_label = QLabel("Min. Voltage for Fitting (V):")
        fitting_label.setStyleSheet(f"color: {self.colors['text']};")
        
        self.min_voltage_input = QDoubleSpinBox()
        self.min_voltage_input.setRange(0.0, 10.0)
        self.min_voltage_input.setValue(0.0)
        self.min_voltage_input.setSingleStep(0.1)
        self.min_voltage_input.setDecimals(2)
        self.min_voltage_input.setStyleSheet(self.INPUT_STYLE)
        self.min_voltage_input.setToolTip("Only consider data points above this voltage for resistance fitting")
        
        fitting_layout.addWidget(fitting_label)
        fitting_layout.addWidget(self.min_voltage_input)
        fitting_layout.addStretch()
        
        tlm_layout.addLayout(fitting_layout)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Load TLM files button
        self.load_tlm_button = QPushButton("Load TLM Files")
        self.load_tlm_button.setStyleSheet(self.PRIMARY_BUTTON_STYLE)
        self.load_tlm_button.setToolTip("Clear existing files and load new ones")
        button_layout.addWidget(self.load_tlm_button)
        
        # Add Files button - to add more files to the existing list
        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.setStyleSheet(self.BUTTON_STYLE)
        self.add_files_button.setToolTip("Add more files to the existing list")
        button_layout.addWidget(self.add_files_button)
        
        # Analyze button
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setStyleSheet(self.SECONDARY_BUTTON_STYLE)
        self.analyze_button.setEnabled(False)  # Disabled until files are loaded
        button_layout.addWidget(self.analyze_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet(self.BUTTON_STYLE)
        button_layout.addWidget(self.clear_button)
        
        tlm_layout.addLayout(button_layout)
        self.layout.addWidget(tlm_group)
    
    def create_results_section(self):
        """Create section for displaying TLM results and data table."""
        # Create a table to display the loaded files and distances
        self.tlm_table = QTableWidget(0, 4)  # Rows will be added dynamically
        self.tlm_table.setHorizontalHeaderLabels(['Filename', 'TLM Distance (μm)', 'Resistance (kΩ)', 'R²'])
        self.tlm_table.setStyleSheet(self.TABLE_STYLE)
        self.tlm_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tlm_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.setMinimumHeight(150)
        self.tlm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Connect table selection to show individual I-V curve
        self.tlm_table.itemSelectionChanged.connect(self.show_selected_iv_curve)
        
        self.layout.addWidget(self.tlm_table)
    
    def create_plot_section(self):
        """Create section for displaying TLM plot."""
        # Create a single plot for the TLM analysis
        self.tlm_canvas = TLMCanvas(self)
        
        # Add the canvas to the layout with stretch factor
        self.layout.addWidget(self.tlm_canvas, stretch=1)
    
    def load_tlm_files(self):
        """Open file dialog to load multiple TLM measurement files. This clears any existing files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select TLM Measurement Files", "", 
            "Data Files (*.txt *.csv);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        # Clear previous data
        self.tlm_files = []
        self.tlm_distances = []
        self.resistances = []
        self.iv_data = []
        
        # Clear the table
        self.tlm_table.setRowCount(0)
        
        # Load the selected files
        self._load_files(file_paths)
        
    def add_tlm_files(self):
        """Open file dialog to add more TLM measurement files to the existing list."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add More TLM Measurement Files", "", 
            "Data Files (*.txt *.csv);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        # Add to the existing files without clearing
        self._load_files(file_paths)
        
    def _load_files(self, file_paths):
        """
        Common method to load files into the table and data structures.
        
        Args:
            file_paths: List of file paths to load
        """
        # Starting distance for new files (increment by 10 from the last file if any)
        start_distance = 10
        if self.tlm_distances:
            # Try to determine a pattern from existing distances
            if len(self.tlm_distances) >= 2:
                # Use the average difference as the increment
                distances = [float(self.tlm_table.item(row, 1).text()) 
                            for row in range(self.tlm_table.rowCount())
                            if self.tlm_table.item(row, 1) and self.tlm_table.item(row, 1).text()]
                if distances:
                    sorted_distances = sorted(distances)
                    diffs = np.diff(sorted_distances)
                    if len(diffs) > 0 and np.mean(diffs) > 0:
                        increment = np.mean(diffs)
                    else:
                        increment = 10
                else:
                    increment = 10
            else:
                increment = 10
                
            # Get the last distance value from the table
            last_row = self.tlm_table.rowCount() - 1
            if last_row >= 0 and self.tlm_table.item(last_row, 1) and self.tlm_table.item(last_row, 1).text():
                try:
                    last_distance = float(self.tlm_table.item(last_row, 1).text())
                    start_distance = last_distance + increment
                except (ValueError, TypeError):
                    start_distance = 10
        
        # Load each file and add to the table
        for i, file_path in enumerate(file_paths):
            try:
                # Load the data - skip the header row (first row)
                data = np.loadtxt(file_path, delimiter=None, skiprows=1)
                voltage = data[:, 0]
                current = data[:, 1]
                
                # Store the IV data for later analysis
                self.iv_data.append((voltage, current))
                
                # Add the file to the list
                self.tlm_files.append(file_path)
                
                # Add a row to the table
                row = self.tlm_table.rowCount()
                self.tlm_table.insertRow(row)
                
                # Add filename (just the basename)
                filename_item = QTableWidgetItem(os.path.basename(file_path))
                filename_item.setFlags(filename_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tlm_table.setItem(row, 0, filename_item)
                
                # Add editable cell for TLM distance
                # Default to increments
                distance_value = start_distance + i * increment
                distance_item = QTableWidgetItem(f"{distance_value:.1f}")
                self.tlm_table.setItem(row, 1, distance_item)
                
                # Empty cells for resistance and R²
                self.tlm_table.setItem(row, 2, QTableWidgetItem(""))
                self.tlm_table.setItem(row, 3, QTableWidgetItem(""))
                
                # Add tooltip with full path on the filename cell
                filename_item.setToolTip(file_path)
                
            except Exception as e:
                QMessageBox.warning(self, "File Load Error", 
                                   f"Error loading {file_path}: {str(e)}")
        
        # Enable the analyze button if files were loaded
        self.analyze_button.setEnabled(self.tlm_table.rowCount() > 0)
    
    def min_voltage_changed(self):
        """Rerun analysis when min voltage changes, if analyze button is enabled."""
        if self.analyze_button.isEnabled() and self.tlm_table.rowCount() > 0:
            self.perform_tlm_analysis()
            
    def perform_tlm_analysis(self):
        """Extract resistances from each TLM file and perform the TLM analysis."""
        if self.tlm_table.rowCount() == 0:
            return
        
        # Get minimum voltage for fitting
        min_voltage = self.min_voltage_input.value()
        
        # Clear previous analysis results
        self.tlm_distances = []
        self.resistances = []
        
        # Process each file
        for row in range(self.tlm_table.rowCount()):
            try:
                # Get the TLM distance
                distance_item = self.tlm_table.item(row, 1)
                if not distance_item or not distance_item.text():
                    QMessageBox.warning(self, "Missing Data", 
                                       "Please enter TLM distances for all files.")
                    return
                
                distance = float(distance_item.text())
                self.tlm_distances.append(distance)
                
                # Get the IV data for this file
                voltage, current = self.iv_data[row]
                
                # Ensure data is valid
                if len(voltage) == 0 or len(current) == 0:
                    QMessageBox.warning(self, "Invalid Data", 
                                       f"File {row+1} has no valid data points.")
                    return
                
                # Check if the data is valid for linear regression
                if np.isnan(voltage).any() or np.isnan(current).any():
                    QMessageBox.warning(self, "Invalid Data", 
                                       f"File {row+1} contains NaN values.")
                    return
                
                # Filter data based on minimum voltage
                valid_indices = voltage >= min_voltage
                if np.sum(valid_indices) < 2:
                    QMessageBox.warning(self, "Insufficient Data", 
                                       f"File {row+1} has less than 2 data points above the minimum voltage of {min_voltage}V.")
                    return
                
                filtered_voltage = voltage[valid_indices]
                filtered_current = current[valid_indices]
                
                # Convert current from mA to A (multiply by 1e-3)
                filtered_current_amps = filtered_current * 1e-3
                    
                # Perform linear regression to extract resistance (V = IR, so slope = R)
                # We'll fit current vs. voltage (I = V/R) and take 1/slope for R
                try:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_voltage, filtered_current_amps)
                    
                    # Check if slope is valid
                    if abs(slope) < 1e-10 or np.isnan(slope):
                        QMessageBox.warning(self, "Analysis Error", 
                                          f"Invalid slope for file {row+1}. The I-V data may not be suitable for resistance calculation.")
                        return
                        
                    resistance = 1.0 / slope  # R = 1/slope (now in ohms)
                    resistance_kohms = resistance / 1000.0  # Convert to kilohms
                    r_squared = r_value * r_value  # R² value
                    
                    # Store the resistance in ohms for TLM analysis
                    self.resistances.append(resistance)
                    
                    # Update the table with resistance in kilohms
                    self.tlm_table.setItem(row, 2, QTableWidgetItem(f"{resistance_kohms:.4f}"))
                    self.tlm_table.setItem(row, 3, QTableWidgetItem(f"{r_squared:.4f}"))
                    
                except Exception as e:
                    QMessageBox.warning(self, "Regression Error", 
                                       f"Error performing linear regression on file {row+1}: {str(e)}")
                    return
                
            except Exception as e:
                QMessageBox.warning(self, "Analysis Error", 
                                   f"Error analyzing row {row+1}: {str(e)}")
                return
        
        # Perform TLM analysis - plot distance vs. resistance and fit line
        try:
            # Convert to numpy arrays for analysis
            distances = np.array(self.tlm_distances)
            resistances = np.array(self.resistances)
            
            # Check if we have enough data points for linear regression
            if len(distances) < 2:
                QMessageBox.warning(self, "Insufficient Data", 
                                   "At least two valid TLM measurements are required for analysis.")
                return
            
            # Sort by distance to ensure proper plotting
            sort_idx = np.argsort(distances)
            distances = distances[sort_idx]
            resistances = resistances[sort_idx]
            
            # Linear regression of resistance vs. distance
            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(distances, resistances)
                
                # Check for valid regression results
                if np.isnan(slope) or np.isnan(intercept) or np.isnan(r_value):
                    QMessageBox.warning(self, "Regression Error", 
                                      "Could not perform valid linear regression on the TLM data.")
                    return
                    
                r_squared = r_value * r_value
                
                # Plot the TLM data
                self.tlm_canvas.plot_tlm_data(distances, resistances, slope, intercept, r_squared, min_voltage)
                
                # Calculate the contact resistance (half of the y-intercept)
                contact_resistance = intercept / 2.0
                sheet_resistance = slope
                
                # Emit analysis results
                results = {
                    'contact_resistance': contact_resistance,
                    'sheet_resistance': sheet_resistance,
                    'r_squared': r_squared,
                    'distances': distances.tolist(),
                    'resistances': resistances.tolist(),
                    'min_voltage': min_voltage
                }
                self.analysis_completed.emit(results)
                
            except Exception as e:
                QMessageBox.warning(self, "TLM Regression Error", 
                                   f"Error performing linear regression on TLM data: {str(e)}")
                return
            
        except Exception as e:
            QMessageBox.warning(self, "TLM Analysis Error", 
                               f"Error performing TLM analysis: {str(e)}")
    
    def show_selected_iv_curve(self):
        """Method to handle selection changes in the table - now just highlights the row."""
        # Keep this method to avoid breaking connections, but it won't display I-V curves anymore
        pass
    
    def clear_analysis(self):
        """Clear all analysis data and plots."""
        # Clear data
        self.tlm_files = []
        self.tlm_distances = []
        self.resistances = []
        self.iv_data = []
        
        # Clear the table
        self.tlm_table.setRowCount(0)
        
        # Clear the plots
        self.tlm_canvas.axes.clear()
        self.tlm_canvas.draw()
    
    def process_data(self, data):
        """
        Process measurement data for analysis.
        
        Args:
            data: Measurement data dictionary from IV sweep
        """
        # This method can be implemented in the future to automatically 
        # add measurement data to the TLM analysis
        # Currently not used for direct data processing
        pass 