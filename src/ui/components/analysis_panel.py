"""
Analysis panel for TLM (Transmission Line Method) measurements and resistance extraction.
"""

import os
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
import scipy.constants
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QFormLayout, QFileDialog,
    QFrame, QScrollArea, QLineEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QSizePolicy, QDoubleSpinBox, QCheckBox, QInputDialog, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QLocale, QTimer
from ..theme import AppTheme


def rtd_iv_schulman(V, A, B, C, D, H, N1, N2):
    """
    Schulman model for RTD I-V characteristics.
    
    Parameters:
    V: voltage array
    A, B, C, D, H, N1, N2: fitting parameters
    
    Returns:
    Current array
    """
    k = scipy.constants.k
    qe = scipy.constants.e
    pi = scipy.constants.pi
    T = 300.0
    V = np.asarray(V, dtype=np.float64)
    
    a = (qe / (k * T)) * (B - C + N1 * V)
    b = (qe / (k * T)) * (B - C - N1 * V)
    J1 = A * np.log((1+np.exp(a))/(1+np.exp(b)))
    J2 = pi / 2.0 + np.arctan((C - N1 * V) / D)
    exp_arg = (qe / (k * T)) * (N2 * V)
    J3 = H * (np.exp(exp_arg)-1)

    return J1 * J2 + J3


class TLMCanvas(FigureCanvas):
    """Canvas for plotting TLM data."""
    
    def __init__(self, parent=None, width=20, height=8, dpi=100):
        # Much wider plot to use all available space
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # Set light theme to match measurement plots
        self.fig.patch.set_facecolor('#ffffff')  # White figure background
        self.axes.set_facecolor('#ffffff')  # White plot background
        
        # Apply light theme styling to axes
        self.axes.tick_params(colors='#333333', direction='out', width=1.5, labelsize=10)
        self.axes.spines['bottom'].set_color('#000000')
        self.axes.spines['top'].set_color('#000000')
        self.axes.spines['left'].set_color('#000000')
        self.axes.spines['right'].set_color('#000000')
        for spine in self.axes.spines.values():
            spine.set_linewidth(1.5)
        
        # Light theme text styling
        self.axes.xaxis.label.set_color('#333333')
        self.axes.xaxis.label.set_fontsize(12)
        self.axes.xaxis.label.set_fontweight('bold')
        
        self.axes.yaxis.label.set_color('#333333')
        self.axes.yaxis.label.set_fontsize(12)
        self.axes.yaxis.label.set_fontweight('bold')
        
        self.axes.title.set_color('#333333')
        self.axes.title.set_fontsize(14)
        self.axes.title.set_fontweight('bold')
        
        # Add grid like measurement plots
        self.axes.grid(True, linestyle='--', alpha=0.7, color='#cccccc')
        
        super(TLMCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # Make the canvas expandable
        FigureCanvas.setSizePolicy(self,
                                  QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        # Enable interactive features
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        
        
        # Connect mouse events for interactivity
        self.mpl_connect('button_press_event', self.on_click)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('scroll_event', self.on_scroll)
        
        # Store plot data for interaction
        self.plot_data = None
        self.annotations = []
    
    def plot_tlm_data(self, distances, resistances, slope, intercept, r_squared, min_voltage):
        """Plot the TLM data."""
        try:
            # Hide placeholder and show canvas
            if hasattr(self, 'plot_placeholder'):
                self.plot_placeholder.hide()
            self.show()
            
            # Clear the existing plot
            self.axes.clear()
            
            # Store data for interaction
            self.plot_data = (distances, resistances)
            
            # Auto-adjust resistance units based on values
            max_resistance = np.max(resistances)
            if max_resistance < 1000:  # Less than 1kΩ, use Ω
                resistances_display = resistances
                resistance_unit = "Ω"
                resistance_factor = 1.0
            elif max_resistance < 1000000:  # Less than 1MΩ, use kΩ
                resistances_display = resistances / 1000.0
                resistance_unit = "kΩ"
                resistance_factor = 1000.0
            else:  # 1MΩ or more, use MΩ
                resistances_display = resistances / 1000000.0
                resistance_unit = "MΩ"
                resistance_factor = 1000000.0
            
            # Plot the data points with enhanced styling
            self.axes.scatter(distances, resistances_display, color='#3498db', s=100, 
                          alpha=0.8, edgecolor='#2980b9', linewidth=2, 
                          label='Measured Data', zorder=3)
            
            # Plot the fitted line
            if len(distances) > 1:  # Only plot line if we have more than one point
                # Create a line from min to max distance
                x_line = np.linspace(min(distances), max(distances), 100)
                y_line = (slope * x_line + intercept) / resistance_factor  # Convert to display units
                
                # Plot fitted line with consistent styling
                self.axes.plot(x_line, y_line, color='#e74c3c', linewidth=3, 
                             linestyle='--', alpha=0.9, label=f'Fitted Line (R² = {r_squared:.4f})', zorder=2)
            
            # Set labels and title with improved formatting
            self.axes.set_xlabel('TLM Distance (μm)')
            self.axes.set_ylabel(f'Resistance ({resistance_unit})')
            self.axes.set_title('TLM Resistance')
            
            # Apply log scales if enabled
            self.apply_log_scales()
            
            # Add enhanced grid
            self.axes.grid(True, linestyle='--', alpha=0.5, color='#566573', linewidth=0.8)
            
            # Add legend with improved styling
            legend = self.axes.legend(loc='upper right', fontsize=10, framealpha=0.9)
            legend.get_frame().set_facecolor('#2c3e50')
            legend.get_frame().set_edgecolor('#34495e')
            
            # Add calculated parameters as text on the plot
            if len(distances) > 1:
                contact_resistance = intercept / 2.0 / resistance_factor  # Convert to display units
                sheet_resistance = slope / resistance_factor  # Convert to display units/μm
                
                # Check for negative resistances (physically impossible)
                if sheet_resistance < 0:
                    sheet_resistance_text = f"Sheet Resistance: {abs(sheet_resistance):.2f} {resistance_unit}/μm"
                    text_color = '#e74c3c'
                else:
                    sheet_resistance_text = f"Sheet Resistance: {sheet_resistance:.2f} {resistance_unit}/μm"
                
                # Check for negative contact resistance
                if contact_resistance < 0:
                    contact_resistance_text = f"Contact Resistance: {abs(contact_resistance):.2f} {resistance_unit}"
                    text_color = '#e74c3c'
                else:
                    contact_resistance_text = f"Contact Resistance: {contact_resistance:.2f} {resistance_unit}"
                
                # Create text box with parameters only (no quality assessment)
                textstr = f'{contact_resistance_text}\n{sheet_resistance_text}\nR² = {r_squared:.4f}'
                props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.9, edgecolor='#34495e', linewidth=2)
                self.axes.text(0.02, 0.98, textstr, transform=self.axes.transAxes, fontsize=10,
                             verticalalignment='top', bbox=props, color=text_color, fontweight='bold')
            
            # Improve axis scaling and layout
            x_min, x_max = self.axes.get_xlim()
            y_min, y_max = self.axes.get_ylim()
            
            # Set reasonable axis limits
            x_range = x_max - x_min
            y_range = y_max - y_min
            
            # Add 10% padding to axes
            x_padding = x_range * 0.1
            y_padding = y_range * 0.1
            
            self.axes.set_xlim(left=max(0, x_min - x_padding), right=x_max + x_padding)
            self.axes.set_ylim(bottom=max(0, y_min - y_padding), top=y_max + y_padding)
            
            # Improve tick formatting
            self.axes.tick_params(axis='both', which='major', labelsize=10, length=6, width=1)
            self.axes.tick_params(axis='both', which='minor', length=3, width=0.5)
            
            # Add minor ticks
            self.axes.minorticks_on()
            
            self.fig.tight_layout()
            self.draw()
            
        except Exception as e:
            pass
    
    def on_click(self, event):
        """Handle mouse click events for plot interaction."""
        pass
    
    def on_mouse_move(self, event):
        """Handle mouse movement for cursor updates."""
        pass
    
    def on_scroll(self, event):
        """Handle scroll events for zooming."""
        if event.inaxes != self.axes:
            return
        
        # Get current axis limits
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        
        # Calculate zoom factor
        zoom_factor = 1.1 if event.button == 'up' else 0.9
        
        # Calculate new limits
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        
        x_range = (xlim[1] - xlim[0]) * zoom_factor
        y_range = (ylim[1] - ylim[0]) * zoom_factor
        
        new_xlim = [x_center - x_range/2, x_center + x_range/2]
        new_ylim = [y_center - y_range/2, y_center + y_range/2]
        
        # Apply new limits
        self.axes.set_xlim((new_xlim[0], new_xlim[1]))
        self.axes.set_ylim((new_ylim[0], new_ylim[1]))
        self.draw()
    
    def add_annotation(self, x, y):
        """Add an annotation at the specified coordinates."""
        if x is None or y is None:
            return
        
        # Create annotation
        ann = self.axes.annotate(f'({x:.2f}, {y:.2f})', 
                               xy=(x, y), xytext=(10, 10),
                               textcoords='offset points',
                               bbox=dict(boxstyle='round,pad=0.3', 
                                       facecolor='yellow', alpha=0.7),
                               arrowprops=dict(arrowstyle='->', 
                                             connectionstyle='arc3,rad=0'))
        
        self.annotations.append(ann)
        self.draw()
    
    def remove_nearest_annotation(self, x, y):
        """Remove the annotation nearest to the specified coordinates."""
        if not self.annotations or x is None or y is None:
            return
        
        # Find nearest annotation
        min_dist = float('inf')
        nearest_ann = None
        
        for ann in self.annotations:
            ann_x, ann_y = ann.xy
            dist = np.sqrt((ann_x - x)**2 + (ann_y - y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_ann = ann
        
        if nearest_ann and min_dist < 50:  # Within reasonable distance
            nearest_ann.remove()
            self.annotations.remove(nearest_ann)
            self.draw()
    
    def clear_annotations(self):
        """Clear all annotations from the plot."""
        for ann in self.annotations:
            ann.remove()
        self.annotations.clear()
        self.draw()
    
    def reset_view(self):
        """Reset the plot view to show all data."""
        if self.plot_data is not None:
            distances, resistances = self.plot_data
            resistances_kohm = resistances / 1000.0
            
            # Calculate appropriate limits
            x_range = max(distances) - min(distances)
            y_range = max(resistances_kohm) - min(resistances_kohm)
            
            # Add 10% padding
            x_padding = x_range * 0.1
            y_padding = y_range * 0.1
            
            self.axes.set_xlim(min(distances) - x_padding, max(distances) + x_padding)
            self.axes.set_ylim(min(resistances_kohm) - y_padding, max(resistances_kohm) + y_padding)
            self.draw()
    
    def apply_log_scales(self):
        """Apply logarithmic scales based on checkbox states."""
        # This will be called from the parent AnalysisPanel
        pass
    
    def set_log_scales(self, log_x=False, log_y=False):
        """Set logarithmic scales for the axes."""
        if log_x:
            self.axes.set_xscale('log')
        else:
            self.axes.set_xscale('linear')
            
        if log_y:
            self.axes.set_yscale('log')
        else:
            self.axes.set_yscale('linear')
        
        self.draw()


class AnalysisPanel(QWidget):
    """Panel for analyzing TLM measurements."""
    
    # Signals
    analysis_completed = pyqtSignal(dict)  # Emits analysis results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get centralized theme colors and styles
        try:
            self.colors = AppTheme.get_colors()
        except Exception as e:
            print(f"Error loading theme: {e}")
            # Fallback colors
            self.colors = {
                'primary': '#2980b9',
                'secondary': '#27ae60',
                'danger': '#c0392b',
                'warning': '#d35400',
                'dark': '#1e272e',
                'darker': '#151c21',
                'light': '#485460',
                'lighter': '#808e9b',
                'text': '#ecf0f1',
                'text_secondary': '#bdc3c7',
                'border': '#34495e',
                'button': '#34495e',
                'input': '#2c3e50',
                'success_bg': '#274d36',
                'error_bg': '#532b2b',
                'warning_bg': '#553b21',
                'plot_bg': '#ffffff',
                'plot_fig_bg': '#ffffff',
                'plot_grid': '#cccccc',
                'plot_forward': '#2980b9',
                'plot_reverse': '#c0392b',
                'plot_text': '#333333',
            }
        try:
            self.HEADER_STYLE = AppTheme.header_style()
            self.GROUP_STYLE = AppTheme.group_box_style()
            self.BUTTON_STYLE = AppTheme.button_style()
        except Exception as e:
            print(f"Error loading theme styles: {e}")
            # Fallback styles
            self.HEADER_STYLE = "font-size: 16px; font-weight: bold; color: #ecf0f1;"
            self.GROUP_STYLE = "QGroupBox { font-weight: bold; border: 1px solid #34495e; border-radius: 6px; margin-top: 1.5ex; padding-top: 10px; padding-bottom: 8px; background-color: #1e272e; color: #ecf0f1; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 8px; color: #ecf0f1; }"
            self.BUTTON_STYLE = "QPushButton { background-color: #34495e; color: #ecf0f1; border-radius: 5px; padding: 8px 15px; font-weight: bold; border: none; } QPushButton:hover { background-color: #2980b9; } QPushButton:pressed { background-color: #1c6ea4; } QPushButton:disabled { background-color: #485460; color: #bdc3c7; }"
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
        self.INPUT_STYLE = AppTheme.input_style()
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
        
        # Create analysis tools selection at the top
        self.create_analysis_tools_selection()
        
        # Create TLM analysis group (initially visible)
        
        # Create IV Fit analysis group (initially hidden)
        self.create_iv_fit_group()
        
        # Create Multi-Region TLM analysis group (initially hidden)
        self.create_multi_region_tlm_group()
        self.create_multi_region_plot_section()
        
        # Create data table and results section (initially hidden)
        self.create_results_section()
        
        # Create placeholder for TLM plot (initially hidden)
        self.create_plot_section()
        
        # Show TLM analysis by default
        self.show_multi_region_tlm()
        
        # Connect signals (handled by multi-region TLM interface)
    
    def create_analysis_tools_selection(self):
        """Create analysis tools selection buttons at the top."""
        # Analysis tool buttons - horizontal layout at top
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # TLM Analysis button
        self.tlm_button = QPushButton("🔬 TLM Analysis")
        self.tlm_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['primary']};
            }}
            QPushButton:hover {{
                background-color: #3498db;
                border: 2px solid #3498db;
            }}
            QPushButton:pressed {{
                background-color: #1c6ea4;
                border: 2px solid #1c6ea4;
            }}
        """)
        self.tlm_button.clicked.connect(self.show_multi_region_tlm)
        self.tlm_button.setToolTip("Transmission Line Method analysis for contact and sheet resistance")
        buttons_layout.addWidget(self.tlm_button)
        
        # IV Fit Analysis button
        self.iv_fit_button = QPushButton("⚡ IV Fit Analysis")
        self.iv_fit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['secondary']};
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
                border: 2px solid #2ecc71;
            }}
            QPushButton:pressed {{
                background-color: #229954;
                border: 2px solid #229954;
            }}
        """)
        self.iv_fit_button.clicked.connect(self.show_iv_fit_analysis)
        self.iv_fit_button.setToolTip("I-V characteristic fitting to Schulman model")
        buttons_layout.addWidget(self.iv_fit_button)
        
        
        # More Tools button (placeholder)
        self.more_tools_button = QPushButton("🔧 More Tools")
        self.more_tools_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['button']};
                border: 2px solid {self.colors['button']};
            }}
        """)
        self.more_tools_button.clicked.connect(self.show_more_tools)
        self.more_tools_button.setToolTip("Additional analysis tools coming soon")
        buttons_layout.addWidget(self.more_tools_button)
        
        # Add stretch to push buttons to the left
        buttons_layout.addStretch()
        
        # Add buttons layout to main layout
        self.layout.addLayout(buttons_layout)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
    
    
    def show_iv_fit_analysis(self):
        """Show IV Fit analysis interface when IV Fit button is clicked."""
        # Show IV Fit analysis components
        self.iv_fit_group.show()
        self.iv_fit_plot_section.show()
        
        # Hide other analysis components
        if hasattr(self, 'multi_region_tlm_group'):
            self.multi_region_tlm_group.hide()
            self.multi_region_plot_section.hide()
        
        # Hide placeholders
        self.table_placeholder.hide()
        self.plot_placeholder.hide()
        
        # Update button states
        self.iv_fit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['secondary']};
            }}
        """)
        self.tlm_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
        """)
        self.analyze_multi_region_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
        """)
    
    def show_multi_region_tlm(self):
        """Show TLM analysis interface."""
        # Show TLM analysis components
        self.multi_region_tlm_group.show()
        self.multi_region_plot_section.show()
        
        # Hide other analysis components
        self.iv_fit_group.hide()
        self.iv_fit_plot_section.hide()
        
        # Hide placeholders
        self.table_placeholder.hide()
        self.plot_placeholder.hide()
        
        # Update button states
        self.tlm_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['primary']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['primary']};
            }}
        """)
        self.iv_fit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
        """)
    
    def back_to_tools(self):
        """Return to analysis tools selection."""
        # Hide IV Fit analysis components
        self.iv_fit_group.hide()
        self.iv_fit_plot_section.hide()
        
        # Reset button states
        self.tlm_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
        """)
        self.iv_fit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['lighter']};
                color: {self.colors['text']};
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid {self.colors['lighter']};
            }}
            QPushButton:hover {{
                background-color: {self.colors['light']};
                border: 2px solid {self.colors['light']};
            }}
        """)
    
    def show_more_tools(self):
        """Show P-I-V analysis tools."""
        # Create P-I-V analysis dialog
        piv_dialog = QMessageBox(self)
        piv_dialog.setWindowTitle("P-I-V Analysis Tools")
        piv_dialog.setText("P-I-V Analysis Tools")
        piv_dialog.setInformativeText(
            "Available P-I-V analysis tools:\n\n"
            "• Power vs Voltage plotting\n"
            "• Efficiency calculations\n"
            "• Power conversion analysis\n"
            "• Optical power characterization\n\n"
            "These tools will be available in the next update!"
        )
        piv_dialog.setIcon(QMessageBox.Icon.Information)
        piv_dialog.exec()
    
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
        # Set locale to use dot as decimal separator
        self.min_voltage_input.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        
        # Log scale options
        log_label = QLabel("Log Scale:")
        log_label.setStyleSheet(f"color: {self.colors['text']}; margin-left: 20px;")
        
        self.log_x_checkbox = QCheckBox("X-axis")
        self.log_x_checkbox.setStyleSheet(f"color: {self.colors['text']};")
        self.log_x_checkbox.setToolTip("Use logarithmic scale for X-axis")
        
        self.log_y_checkbox = QCheckBox("Y-axis")
        self.log_y_checkbox.setStyleSheet(f"color: {self.colors['text']};")
        self.log_y_checkbox.setToolTip("Use logarithmic scale for Y-axis")
        
        # Connect log scale changes
        self.log_x_checkbox.toggled.connect(self.update_plot_scales)
        self.log_y_checkbox.toggled.connect(self.update_plot_scales)
        
        fitting_layout.addWidget(fitting_label)
        fitting_layout.addWidget(self.min_voltage_input)
        fitting_layout.addWidget(log_label)
        fitting_layout.addWidget(self.log_x_checkbox)
        fitting_layout.addWidget(self.log_y_checkbox)
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
        
        # Plot control buttons
        self.reset_view_button = QPushButton("🔄 Reset View")
        self.reset_view_button.setStyleSheet(self.BUTTON_STYLE)
        self.reset_view_button.clicked.connect(self.reset_plot_view)
        self.reset_view_button.setToolTip("Reset plot to show all data")
        button_layout.addWidget(self.reset_view_button)
        
        self.clear_annotations_button = QPushButton("🗑️ Clear Annotations")
        self.clear_annotations_button.setStyleSheet(self.BUTTON_STYLE)
        self.clear_annotations_button.clicked.connect(self.clear_plot_annotations)
        self.clear_annotations_button.setToolTip("Remove all annotations from plot")
        button_layout.addWidget(self.clear_annotations_button)
        
        # Back button removed as requested
        
        tlm_layout.addLayout(button_layout)
        self.layout.addWidget(tlm_group)
        
        # Store reference and initially hide
        self.tlm_group = tlm_group
        self.tlm_group.hide()
    
    def create_results_section(self):
        """Create section for displaying TLM results and data table."""
        # Create a table to display the loaded files and distances
        self.tlm_table = QTableWidget(0, 4)  # Rows will be added dynamically
        self.tlm_table.setHorizontalHeaderLabels(['Filename', 'TLM Distance (μm)', 'Resistance', 'R²'])
        self.tlm_table.setStyleSheet(self.TABLE_STYLE)
        self.tlm_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tlm_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tlm_table.setMinimumHeight(150)
        self.tlm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add placeholder for empty table
        self.table_placeholder = QLabel("📋 No TLM files loaded\n\nClick 'Load TLM Files' to add measurement data")
        self.table_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_placeholder.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 14px;
            padding: 40px;
            background-color: {self.colors['input']};
            border-radius: 6px;
            border: 2px dashed {self.colors['border']};
        """)
        
        # Add both to layout
        self.layout.addWidget(self.table_placeholder)
        self.layout.addWidget(self.tlm_table)
        
        # Initially show placeholder, hide table
        self.tlm_table.hide()
        
        # Store reference and initially hide
        self.results_section = self.tlm_table
        self.results_section.hide()
    
    def create_plot_section(self):
        """Create section for displaying TLM plot."""
        # Create a single plot for the TLM analysis
        self.tlm_canvas = TLMCanvas(self)
        
        # Add placeholder for empty plot
        self.plot_placeholder = QLabel("📊 No analysis data\n\nLoad TLM files and click 'Analyze' to see results here")
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_placeholder.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 14px;
            padding: 40px;
            background-color: {self.colors['input']};
            border-radius: 6px;
            border: 2px dashed {self.colors['border']};
        """)
        
        # Add both to layout
        self.layout.addWidget(self.plot_placeholder)
        self.layout.addWidget(self.tlm_canvas, stretch=10)  # MUCH larger stretch for taller plot
        
        # Initially show placeholder, hide canvas
        self.tlm_canvas.hide()
        
        # Store reference and initially hide
        self.plot_section = self.tlm_canvas
        self.plot_section.hide()
        
        # Create IV Fit analysis components
        self.create_iv_fit_group()
        self.create_iv_fit_results_section()
        self.create_iv_fit_plot_section()
    
    def load_tlm_files(self):
        """Open file dialog to load multiple TLM measurement files. This clears any existing files."""
        options = QFileDialog.Option.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select TLM Measurement Files", "", 
            "All Supported Files (*.txt *.csv *.xlsx *.xls *.dat);;"
            "Text Files (*.txt);;"
            "CSV Files (*.csv);;"
            "Excel Files (*.xlsx *.xls);;"
            "Data Files (*.dat);;"
            "All Files (*)",
            options=options
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
        options = QFileDialog.Option.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add More TLM Measurement Files", "", 
            "Data Files (*.txt *.csv);;All Files (*)",
            options=options
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
        start_distance = 5
        increment = 5  # Default increment value defined outside the conditional blocks
        
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
                    # else: increment already has default value of 10
                # else: increment already has default value of 10
            # else: increment already has default value of 10
                
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
                # Load the data using the universal loader
                data = self.load_data_file(file_path)
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
        
        # Show table and hide placeholder if files were loaded
        if self.tlm_table.rowCount() > 0:
            self.table_placeholder.hide()
            self.tlm_table.show()
        else:
            self.table_placeholder.show()
            self.tlm_table.hide()
    
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
                    # Perform linear regression
                    slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_voltage, filtered_current_amps)
                    
                    # Check if slope is valid
                    if abs(slope) < 1e-10 or np.isnan(slope):
                        QMessageBox.warning(self, "Analysis Error", 
                                          f"Invalid slope for file {row+1}. The I-V data may not be suitable for resistance calculation.")
                        return
                        
                    resistance = 1.0 / slope  # R = 1/slope (now in ohms)
                    r_squared = r_value * r_value  # R² value
                    
                    # Store the resistance in ohms for TLM analysis
                    self.resistances.append(resistance)
                    
                    # Auto-format resistance for table display
                    if resistance < 1000:  # Less than 1kΩ, use Ω
                        resistance_display = f"{resistance:.1f} Ω"
                    elif resistance < 1000000:  # Less than 1MΩ, use kΩ
                        resistance_display = f"{resistance/1000.0:.4f} kΩ"
                    else:  # 1MΩ or more, use MΩ
                        resistance_display = f"{resistance/1000000.0:.4f} MΩ"
                    
                    # Update the table with auto-formatted resistance
                    self.tlm_table.setItem(row, 2, QTableWidgetItem(resistance_display))
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
                # Perform linear regression
                slope, intercept, r_value, p_value, std_err = stats.linregress(distances, resistances)
                
                # Check for valid regression results
                if np.isnan(slope) or np.isnan(intercept) or np.isnan(r_value):
                    QMessageBox.warning(self, "Regression Error", 
                                      "Could not perform valid linear regression on the TLM data.")
                    return
                    
                r_squared = r_value * r_value
                
                # Note: Warning popups removed - quality indicators are shown in the plot instead
                
                # Hide placeholder and show plot
                self.plot_placeholder.hide()
                self.tlm_canvas.show()
                
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
    
    def create_iv_fit_group(self):
        """Create IV Fit analysis control group with two-column layout."""
        # Create main container
        iv_fit_container = QWidget()
        iv_fit_layout = QHBoxLayout(iv_fit_container)
        iv_fit_layout.setContentsMargins(0, 0, 0, 0)
        iv_fit_layout.setSpacing(15)
        
        # Left column - Controls
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # Title and description
        title_label = QLabel("IV Fit Analysis")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.colors['text']};
            padding: 10px;
            background-color: {self.colors['darker']};
            border-radius: 8px;
            border: 1px solid {self.colors['border']};
        """)
        left_column.addWidget(title_label)
        
        # File loading section
        file_group = QGroupBox("File Loading")
        file_group.setStyleSheet(self.GROUP_STYLE)
        file_layout = QVBoxLayout(file_group)
        
        self.load_iv_button = QPushButton("📁 Load IV File")
        self.load_iv_button.setStyleSheet(self.BUTTON_STYLE)
        self.load_iv_button.clicked.connect(self.load_iv_file)
        file_layout.addWidget(self.load_iv_button)
        
        self.iv_filename_label = QLabel("No file loaded")
        self.iv_filename_label.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 5px;")
        file_layout.addWidget(self.iv_filename_label)
        
        left_column.addWidget(file_group)
        
        # Peak/Valley selection section
        peak_valley_group = QGroupBox("Peak/Valley Selection")
        peak_valley_group.setStyleSheet(self.GROUP_STYLE)
        peak_valley_layout = QFormLayout(peak_valley_group)
        
        # Peak interval
        peak_layout = QHBoxLayout()
        self.peak_min_spin = QDoubleSpinBox()
        self.peak_min_spin.setRange(-10.0, 10.0)
        self.peak_min_spin.setValue(0.5)
        self.peak_min_spin.setDecimals(3)
        self.peak_min_spin.setSuffix(" V")
        peak_layout.addWidget(self.peak_min_spin)
        
        peak_layout.addWidget(QLabel("to"))
        
        self.peak_max_spin = QDoubleSpinBox()
        self.peak_max_spin.setRange(-10.0, 10.0)
        self.peak_max_spin.setValue(0.62)
        self.peak_max_spin.setDecimals(3)
        self.peak_max_spin.setSuffix(" V")
        peak_layout.addWidget(self.peak_max_spin)
        
        peak_valley_layout.addRow("Peak Interval:", peak_layout)
        
        # Valley interval
        valley_layout = QHBoxLayout()
        self.valley_min_spin = QDoubleSpinBox()
        self.valley_min_spin.setRange(-10.0, 10.0)
        self.valley_min_spin.setValue(0.66)
        self.valley_min_spin.setDecimals(3)
        self.valley_min_spin.setSuffix(" V")
        valley_layout.addWidget(self.valley_min_spin)
        
        valley_layout.addWidget(QLabel("to"))
        
        self.valley_max_spin = QDoubleSpinBox()
        self.valley_max_spin.setRange(-10.0, 10.0)
        self.valley_max_spin.setValue(0.72)
        self.valley_max_spin.setDecimals(3)
        self.valley_max_spin.setSuffix(" V")
        valley_layout.addWidget(self.valley_max_spin)
        
        peak_valley_layout.addRow("Valley Interval:", valley_layout)
        
        # Data masking option
        self.mask_data_check = QCheckBox("Remove data between peak and valley")
        self.mask_data_check.setChecked(True)
        self.mask_data_check.setStyleSheet(f"color: {self.colors['text']}; padding: 5px;")
        peak_valley_layout.addRow("Data Masking:", self.mask_data_check)
        
        left_column.addWidget(peak_valley_group)
        
        # Fitting parameters section - more compact layout
        params_group = QGroupBox("Fitting Parameters")
        params_group.setStyleSheet(self.GROUP_STYLE)
        params_layout = QVBoxLayout(params_group)
        
        # Create parameter spin boxes in a grid layout for better space usage
        self.param_spins = {}
        param_names = ['A', 'B', 'C', 'D', 'H', 'N1', 'N2']
        param_ranges = [(1e-12, 1e3), (0.0, 2.0), (0.0, 3.0), (0.0, 3.5), (0.0, 1e3), (0.0, 5.0), (0.0, 5.0)]
        param_defaults = [5.71e-5, 1.746, 2.091, 0.189, 3.47e-3, 3.17, 0.044]
        
        # Create grid layout for parameters
        param_grid = QHBoxLayout()
        left_params = QVBoxLayout()
        right_params = QVBoxLayout()
        
        for i, (name, (min_val, max_val), default) in enumerate(zip(param_names, param_ranges, param_defaults)):
            # Create horizontal layout for each parameter
            param_layout = QHBoxLayout()
            
            # Parameter label
            label = QLabel(f"{name}:")
            label.setMinimumWidth(20)
            label.setStyleSheet(f"color: {self.colors['text']}; font-weight: bold;")
            param_layout.addWidget(label)
            
            # Parameter spin box
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setValue(default)
            spin.setDecimals(6)
            spin.setSingleStep(0.001)
            spin.setMaximumWidth(120)
            spin.setStyleSheet(f"""
                QDoubleSpinBox {{
                    background-color: {self.colors['input']};
                    color: {self.colors['text']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 4px;
                    padding: 4px;
                }}
                QDoubleSpinBox:focus {{
                    border: 2px solid {self.colors['primary']};
                }}
            """)
            # Connect value changed signal for automatic updates
            spin.valueChanged.connect(self.on_parameter_changed)
            self.param_spins[name] = spin
            param_layout.addWidget(spin)
            
            param_layout.addStretch()
            
            # Add to left or right column
            if i < 4:  # First 4 parameters on left
                left_params.addLayout(param_layout)
            else:  # Last 3 parameters on right
                right_params.addLayout(param_layout)
        
        param_grid.addLayout(left_params)
        param_grid.addLayout(right_params)
        params_layout.addLayout(param_grid)
        
        # Add auto-update info
        auto_update_label = QLabel("💡 Parameters update plot automatically")
        auto_update_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 11px; font-style: italic;")
        auto_update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        params_layout.addWidget(auto_update_label)
        
        left_column.addWidget(params_group)
        
        # Action buttons - more compact layout
        button_group = QGroupBox("Actions")
        button_group.setStyleSheet(self.GROUP_STYLE)
        button_layout = QVBoxLayout(button_group)
        
        # Top row buttons
        top_buttons = QHBoxLayout()
        self.select_points_button = QPushButton("🎯 Select Points")
        self.select_points_button.setStyleSheet(self.BUTTON_STYLE)
        self.select_points_button.clicked.connect(self.select_peak_valley_points)
        self.select_points_button.setEnabled(False)
        top_buttons.addWidget(self.select_points_button)
        
        self.fit_button = QPushButton("🔬 Fit Data")
        self.fit_button.setStyleSheet(self.BUTTON_STYLE)
        self.fit_button.clicked.connect(self.fit_iv_data)
        self.fit_button.setEnabled(False)
        top_buttons.addWidget(self.fit_button)
        
        button_layout.addLayout(top_buttons)
        
        # Bottom row buttons
        bottom_buttons = QHBoxLayout()
        self.clear_iv_button = QPushButton("🗑️ Clear")
        self.clear_iv_button.setStyleSheet(self.BUTTON_STYLE)
        self.clear_iv_button.clicked.connect(self.clear_iv_analysis)
        bottom_buttons.addWidget(self.clear_iv_button)
        
        button_layout.addLayout(bottom_buttons)
        
        left_column.addWidget(button_group)
        
        # Back button removed as requested
        
        left_column.addLayout(button_layout)
        
        # Right column - Plot (will be added in create_iv_fit_plot_section)
        self.right_column = QVBoxLayout()
        
        # Add columns to main layout
        iv_fit_layout.addLayout(left_column, 1)  # Left column takes 1/3 of space
        iv_fit_layout.addLayout(self.right_column, 2)  # Right column takes 2/3 of space
        
        self.layout.addWidget(iv_fit_container)
        
        # Store reference and initially hide
        self.iv_fit_group = iv_fit_container
        self.iv_fit_group.hide()
    
    def create_iv_fit_results_section(self):
        """Create section for displaying IV Fit results - now integrated into main layout."""
        # This is now handled in the main create_iv_fit_group method
        pass
    
    def create_iv_fit_plot_section(self):
        """Create section for displaying IV Fit plot in the right column."""
        # Create a single plot for the IV Fit analysis
        self.iv_fit_canvas = TLMCanvas(self, width=20, height=8)
        
        # Add the canvas to the right column
        self.right_column.addWidget(self.iv_fit_canvas, stretch=1)
        
        # Store reference and initially hide
        self.iv_fit_plot_section = self.iv_fit_canvas
        self.iv_fit_plot_section.hide()
    
    def create_multi_region_tlm_group(self):
        """Create Multi-Region TLM analysis control group."""
        # Create main container
        multi_region_container = QWidget()
        multi_region_layout = QHBoxLayout(multi_region_container)
        multi_region_layout.setContentsMargins(0, 0, 0, 0)
        multi_region_layout.setSpacing(15)
        
        # Left column - Controls
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # Title and description
        title_label = QLabel("TLM Analysis")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.colors['text']};
            padding: 10px;
            background-color: {self.colors['darker']};
            border-radius: 8px;
            border: 1px solid {self.colors['border']};
        """)
        left_column.addWidget(title_label)
        
        # Region management section
        region_group = QGroupBox("Region Management")
        region_group.setStyleSheet(self.GROUP_STYLE)
        region_layout = QVBoxLayout(region_group)
        
        # Add region button
        self.add_region_button = QPushButton("➕ Add Region")
        self.add_region_button.setStyleSheet(self.PRIMARY_BUTTON_STYLE)
        self.add_region_button.clicked.connect(self.add_region)
        region_layout.addWidget(self.add_region_button)
        
        # Region list
        self.region_list = QTableWidget(0, 4)
        self.region_list.setHorizontalHeaderLabels(['Region Name', 'Files', 'Status', 'Actions'])
        self.region_list.setStyleSheet(self.TABLE_STYLE)
        self.region_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.region_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.region_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.region_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.region_list.setMaximumHeight(200)
        region_layout.addWidget(self.region_list)
        
        left_column.addWidget(region_group)
        
        # Analysis settings section
        settings_group = QGroupBox("Analysis Settings")
        settings_group.setStyleSheet(self.GROUP_STYLE)
        settings_layout = QFormLayout(settings_group)
        
        # Min voltage setting
        self.multi_min_voltage_input = QDoubleSpinBox()
        self.multi_min_voltage_input.setRange(0.0, 10.0)
        self.multi_min_voltage_input.setValue(0.0)
        self.multi_min_voltage_input.setDecimals(3)
        self.multi_min_voltage_input.setSuffix(" V")
        self.multi_min_voltage_input.setStyleSheet(self.INPUT_STYLE)
        settings_layout.addRow("Min. Voltage for Fitting:", self.multi_min_voltage_input)
        
        # Plot title setting
        self.multi_plot_title_input = QLineEdit("TLM Analysis")
        self.multi_plot_title_input.setStyleSheet(self.INPUT_STYLE)
        settings_layout.addRow("Plot Title:", self.multi_plot_title_input)
        
        # File selection is now automatic - always use most recent
        
        # Plot will always use light style - no customization needed
        
        left_column.addWidget(settings_group)
        
        # File management section
        files_group = QGroupBox("File Management")
        files_group.setStyleSheet(self.GROUP_STYLE)
        files_layout = QVBoxLayout(files_group)
        
        # Combined load files button with dropdown menu
        self.load_files_button = QPushButton("📁 Load TLM Files")
        self.load_files_button.setStyleSheet(self.PRIMARY_BUTTON_STYLE)
        self.load_files_button.clicked.connect(self.show_load_files_menu)
        files_layout.addWidget(self.load_files_button)
        
        # Multi-assignment controls
        multi_assign_layout = QHBoxLayout()
        multi_assign_layout.addWidget(QLabel("Assign selected files to:"))
        
        self.multi_region_combo = QComboBox()
        self.multi_region_combo.addItem("Not assigned")
        self.multi_region_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors['input']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }}
        """)
        multi_assign_layout.addWidget(self.multi_region_combo)
        
        self.assign_selected_btn = QPushButton("Assign Selected")
        self.assign_selected_btn.clicked.connect(self.assign_selected_files)
        self.assign_selected_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors.get('button_hover', '#4A4A4A')};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors.get('button_pressed', '#3A3A3A')};
            }}
        """)
        multi_assign_layout.addWidget(self.assign_selected_btn)
        
        multi_assign_layout.addStretch()
        files_layout.addLayout(multi_assign_layout)
        
        # File list display
        self.multi_files_label = QLabel("No files loaded")
        self.multi_files_label.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 5px;")
        self.multi_files_label.setWordWrap(True)
        files_layout.addWidget(self.multi_files_label)
        
        # Files table with proper scrolling
        self.multi_files_table = QTableWidget(0, 3)
        self.multi_files_table.setHorizontalHeaderLabels(['File', 'Distance (μm)', 'Region'])
        self.multi_files_table.setStyleSheet(self.TABLE_STYLE)
        self.multi_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.multi_files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.multi_files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Set height to accommodate more rows and force scrolling
        self.multi_files_table.setFixedHeight(250)
        
        # Enable scrolling - force scrollbars to be visible
        self.multi_files_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.multi_files_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Ensure proper scrollbar behavior after window operations
        self.multi_files_table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)
        
        # Add timer to refresh scrollbar after window operations
        self.scrollbar_refresh_timer = QTimer()
        self.scrollbar_refresh_timer.setSingleShot(True)
        self.scrollbar_refresh_timer.timeout.connect(self.refresh_table_scrollbar)
        
        # Set row height
        self.multi_files_table.verticalHeader().setDefaultSectionSize(25)
        self.multi_files_table.setAlternatingRowColors(True)
        self.multi_files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.multi_files_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)  # Enable multi-selection
        self.multi_files_table.cellDoubleClicked.connect(self.edit_file_distance)
        # Also connect cell changed for immediate updates
        self.multi_files_table.cellChanged.connect(self.on_cell_changed)
        files_layout.addWidget(self.multi_files_table)
        
        left_column.addWidget(files_group)
        
        # Action buttons
        button_group = QGroupBox("Actions")
        button_group.setStyleSheet(self.GROUP_STYLE)
        button_layout = QVBoxLayout(button_group)
        
        # Analysis button
        self.analyze_multi_region_button = QPushButton("🔬 Analyze All Regions")
        self.analyze_multi_region_button.setStyleSheet(self.SECONDARY_BUTTON_STYLE)
        self.analyze_multi_region_button.clicked.connect(self.analyze_all_regions)
        self.analyze_multi_region_button.setEnabled(False)
        button_layout.addWidget(self.analyze_multi_region_button)
        
        # Bottom row buttons
        bottom_buttons = QHBoxLayout()
        self.clear_multi_region_button = QPushButton("🗑️ Clear All")
        self.clear_multi_region_button.setStyleSheet(self.BUTTON_STYLE)
        self.clear_multi_region_button.clicked.connect(self.clear_multi_region_analysis)
        bottom_buttons.addWidget(self.clear_multi_region_button)
        
        self.export_multi_region_button = QPushButton("💾 Export Results")
        self.export_multi_region_button.setStyleSheet(self.BUTTON_STYLE)
        self.export_multi_region_button.clicked.connect(self.export_multi_region_results)
        self.export_multi_region_button.setEnabled(False)
        bottom_buttons.addWidget(self.export_multi_region_button)
        
        button_layout.addLayout(bottom_buttons)
        
        # Back button removed as requested
        
        left_column.addWidget(button_group)
        
        # Right column - Plot (will be added in create_multi_region_plot_section)
        self.multi_region_right_column = QVBoxLayout()
        
        # Add columns to main layout
        multi_region_layout.addLayout(left_column, 1)  # Left column takes 1/3 of space
        multi_region_layout.addLayout(self.multi_region_right_column, 2)  # Right column takes 2/3 of space
        
        self.layout.addWidget(multi_region_container)
        
        # Store reference and initially hide
        self.multi_region_tlm_group = multi_region_container
        self.multi_region_tlm_group.hide()
        
        # Initialize data storage
        self.regions_data = {}  # Store data for each region
        self.multi_loaded_files = []  # Store loaded file paths
        self.file_data = {}  # Store file-specific data (distance, region)
        self.region_colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', '#7209B7', '#F77F00', '#4A4A4A']
        self.current_color_index = 0
    
    def create_multi_region_plot_section(self):
        """Create section for displaying Multi-Region TLM plot in the right column."""
        # Create a single plot for the Multi-Region TLM analysis
        self.multi_region_canvas = TLMCanvas(self, width=20, height=8)
        
        # Add the canvas to the right column
        self.multi_region_right_column.addWidget(self.multi_region_canvas, stretch=1)
        
        # Store reference and initially hide
        self.multi_region_plot_section = self.multi_region_canvas
        self.multi_region_plot_section.hide()
    
    def load_iv_file(self):
        """Load I-V measurement file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select I-V Measurement File", "", 
            "All Supported Files (*.txt *.csv *.xlsx *.xls *.dat);;"
            "Text Files (*.txt);;"
            "CSV Files (*.csv);;"
            "Excel Files (*.xlsx *.xls);;"
            "Data Files (*.dat);;"
            "All Files (*)"
        )
        
        if file_path:
            try:
                # Load data based on file extension
                data = self.load_data_file(file_path)
                
                if data.shape[1] < 2:
                    QMessageBox.warning(self, "File Error", "File must contain at least 2 columns (V, I)")
                    return
                
                self.iv_voltage = data[:, 0]
                self.iv_current = data[:, 1] * 1e-3  # Convert to mA
                self.iv_file_path = file_path
                
                # Update UI
                filename = os.path.basename(file_path)
                self.iv_filename_label.setText(f"Loaded: {filename}")
                self.iv_filename_label.setStyleSheet(f"color: {self.colors['secondary']}; padding: 5px;")
                
                # Enable buttons
                self.select_points_button.setEnabled(True)
                
                # Plot the data
                self.plot_iv_data()
                
            except Exception as e:
                QMessageBox.warning(self, "File Error", f"Error loading file: {str(e)}")
    
    def load_data_file(self, file_path):
        """Load data from various file formats."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.csv']:
            # Load CSV file
            try:
                # Try with pandas first (handles headers better)
                df = pd.read_csv(file_path, skipinitialspace=True)
                data = df.values
            except:
                # Fallback to numpy
                data = np.loadtxt(file_path, delimiter=',')
                
        elif file_ext in ['.xlsx', '.xls']:
            # Load Excel file
            try:
                df = pd.read_excel(file_path)
                data = df.values
            except Exception as e:
                raise Exception(f"Error reading Excel file: {str(e)}")
                
        elif file_ext in ['.txt', '.dat']:
            # Load text/data file
            try:
                # Try to load with pandas first (handles various separators)
                df = pd.read_csv(file_path, sep=None, engine='python', skipinitialspace=True)
                data = df.values
            except:
                # Fallback to numpy
                try:
                    data = np.loadtxt(file_path)
                except:
                    # Try with different delimiters
                    for delimiter in ['\t', ',', ';', ' ']:
                        try:
                            data = np.loadtxt(file_path, delimiter=delimiter)
                            break
                        except:
                            continue
                    else:
                        raise Exception("Could not parse file with any known delimiter")
        else:
            # Try generic loading
            try:
                data = np.loadtxt(file_path)
            except:
                try:
                    df = pd.read_csv(file_path, sep=None, engine='python')
                    data = df.values
                except:
                    raise Exception(f"Unsupported file format: {file_ext}")
        
        # Ensure we have numeric data
        try:
            data = data.astype(float)
        except:
            raise Exception("File contains non-numeric data")
        
        return data
    
    def plot_iv_data(self):
        """Plot the loaded I-V data."""
        if not hasattr(self, 'iv_voltage') or not hasattr(self, 'iv_current'):
            return
        
        try:
            self.iv_fit_canvas.axes.clear()
            
            # Plot the data
            self.iv_fit_canvas.axes.plot(self.iv_voltage, self.iv_current, 'o', 
                                       color='#3498db', markersize=3, alpha=0.7, label='Data')
            
            self.iv_fit_canvas.axes.set_xlabel('Voltage (V)')
            self.iv_fit_canvas.axes.set_ylabel('Current (mA)')
            self.iv_fit_canvas.axes.set_title('I-V Data for Schulman Fitting')
            self.iv_fit_canvas.axes.grid(True, alpha=0.3)
            self.iv_fit_canvas.axes.legend()
            
            self.iv_fit_canvas.fig.tight_layout()
            self.iv_fit_canvas.draw()
            
        except Exception as e:
            # Silently handle errors
            pass
    
    def select_peak_valley_points(self):
        """Find and display peak and valley points based on intervals."""
        if not hasattr(self, 'iv_voltage') or not hasattr(self, 'iv_current'):
            QMessageBox.warning(self, "No Data", "Please load I-V data first")
            return
        
        try:
            # Get intervals from spin boxes
            peak_interval = (self.peak_min_spin.value(), self.peak_max_spin.value())
            valley_interval = (self.valley_min_spin.value(), self.valley_max_spin.value())
            
            # Find peak and valley
            peak_x, valley_x = self.find_peak_valley(
                self.iv_voltage.tolist(), self.iv_current.tolist(),
                peak_interval, valley_interval
            )
            
            # Store the points
            self.peak_point = (peak_x, self.iv_current[np.argmin(np.abs(self.iv_voltage - peak_x))])
            self.valley_point = (valley_x, self.iv_current[np.argmin(np.abs(self.iv_voltage - valley_x))])
            
            # Plot with highlighted points
            self.plot_iv_data_with_points()
            
            # Enable fit button
            self.fit_button.setEnabled(True)
            
            QMessageBox.information(self, "Points Selected", 
                                  f"Peak: ({peak_x:.3f} V, {self.peak_point[1]:.3f} mA)\n"
                                  f"Valley: ({valley_x:.3f} V, {self.valley_point[1]:.3f} mA)")
            
        except Exception as e:
            # Silently handle errors
            pass
            QMessageBox.warning(self, "Selection Error", f"Error selecting points: {str(e)}")
    
    def find_peak_valley(self, x_values, y_values, peak_interval, valley_interval):
        """Find peak and valley points in specified intervals."""
        peak_y = -np.inf
        valley_y = np.inf
        peak_x = 0
        valley_x = 0
        
        for i, (x, y) in enumerate(zip(x_values, y_values)):
            if peak_interval[0] <= x <= peak_interval[1]:
                if y >= peak_y:
                    peak_y = y
                    peak_x = x
            if valley_interval[0] <= x <= valley_interval[1]:
                if y <= valley_y:
                    valley_y = y
                    valley_x = x
        
        return peak_x, valley_x
    
    def plot_iv_data_with_points(self):
        """Plot I-V data with highlighted peak and valley points."""
        if not hasattr(self, 'iv_voltage') or not hasattr(self, 'iv_current'):
            return
        
        try:
            self.iv_fit_canvas.axes.clear()
            
            # Plot the data
            self.iv_fit_canvas.axes.plot(self.iv_voltage, self.iv_current, 'o', 
                                       color='#3498db', markersize=3, alpha=0.7, label='Data')
            
            # Highlight peak and valley
            if hasattr(self, 'peak_point'):
                self.iv_fit_canvas.axes.plot(self.peak_point[0], self.peak_point[1], 'o', 
                                           color='#e74c3c', markersize=8, label='Peak')
            if hasattr(self, 'valley_point'):
                self.iv_fit_canvas.axes.plot(self.valley_point[0], self.valley_point[1], 'o', 
                                           color='#f39c12', markersize=8, label='Valley')
            
            self.iv_fit_canvas.axes.set_xlabel('Voltage (V)')
            self.iv_fit_canvas.axes.set_ylabel('Current (mA)')
            self.iv_fit_canvas.axes.set_title('I-V Data with Peak/Valley Points')
            self.iv_fit_canvas.axes.grid(True, alpha=0.3)
            self.iv_fit_canvas.axes.legend()
            
            self.iv_fit_canvas.fig.tight_layout()
            self.iv_fit_canvas.draw()
            
        except Exception as e:
            # Silently handle errors
            pass
    
    def fit_iv_data(self):
        """Fit the I-V data to the Schulman model."""
        if not hasattr(self, 'iv_voltage') or not hasattr(self, 'iv_current'):
            QMessageBox.warning(self, "No Data", "Please load I-V data first")
            return
        
        try:
            # Prepare data for fitting
            if self.mask_data_check.isChecked() and hasattr(self, 'peak_point') and hasattr(self, 'valley_point'):
                # Remove data between peak and valley
                voltage_fit, current_fit = self.remove_middle_data(
                    self.iv_voltage, self.iv_current, 
                    self.peak_point[0], self.valley_point[0]
                )
            else:
                voltage_fit = self.iv_voltage
                current_fit = self.iv_current
            
            # Initial parameter guess
            p0 = [5.71e-5, 1.746, 2.091, 0.189, 3.47e-3, 3.17, 0.044]
            lower_bounds = [1e-12, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            upper_bounds = [1e3, 2.0, 3.0, 3.5, 1e3, 5.0, 5.0]
            
            # Perform the fit
            popt, pcov = curve_fit(
                rtd_iv_schulman, voltage_fit, current_fit,
                p0=p0,
                bounds=(lower_bounds, upper_bounds),
                maxfev=200000
            )
            
            # Store fitted parameters
            self.fitted_params = popt
            self.fitted_voltage = voltage_fit
            self.fitted_current = current_fit
            
            # Update parameter spin boxes
            self.update_parameter_spins(popt)
            
            # Plot results
            self.plot_fit_results()
            
        except Exception as e:
            QMessageBox.warning(self, "Fit Error", f"Error fitting data: {str(e)}")
            print(f"IV Fit Error: {e}")  # Debug output
    
    def remove_middle_data(self, voltages, currents, peak_volt, valley_volt):
        """Remove data between peak and valley points."""
        peak_idx = np.argmin(np.abs(voltages - peak_volt))
        valley_idx = np.argmin(np.abs(voltages - valley_volt))
        
        # Take data before peak (with some buffer) and after valley
        first_part = slice(0, peak_idx + 4)
        second_part = slice(valley_idx, None)
        
        voltage_fit = np.concatenate((voltages[first_part], voltages[second_part]))
        current_fit = np.concatenate((currents[first_part], currents[second_part]))
        
        return voltage_fit, current_fit
    
    def update_parameter_spins(self, params):
        """Update parameter spin boxes with fitted values."""
        param_names = ['A', 'B', 'C', 'D', 'H', 'N1', 'N2']
        for name, value in zip(param_names, params):
            if name in self.param_spins:
                # Temporarily disconnect signal to avoid triggering update during programmatic change
                self.param_spins[name].valueChanged.disconnect()
                self.param_spins[name].setValue(value)
                # Reconnect signal
                self.param_spins[name].valueChanged.connect(self.on_parameter_changed)
    
    def on_parameter_changed(self):
        """Handle automatic parameter changes - update plot in real-time."""
        if not hasattr(self, 'iv_voltage') or not hasattr(self, 'iv_current'):
            return
        
        try:
            # Get current parameters from spin boxes
            params = [self.param_spins[name].value() for name in ['A', 'B', 'C', 'D', 'H', 'N1', 'N2']]
            
            # Store as current fitted parameters
            self.fitted_params = params
            
            # Update plot immediately
            self.plot_fit_results()
            
        except Exception as e:
            # Silently handle errors
            pass
            # Silently handle errors to avoid interrupting user input
    
    
    
    def plot_fit_results(self):
        """Plot the fitted curve along with the data."""
        if not hasattr(self, 'fitted_params'):
            return
        
        try:
            self.iv_fit_canvas.axes.clear()
            
            # Plot original data
            self.iv_fit_canvas.axes.plot(self.iv_voltage, self.iv_current, 'o', 
                                       color='#3498db', markersize=3, alpha=0.7, label='Data')
            
            # Plot fitted curve
            v_fit = np.linspace(self.iv_voltage.min(), self.iv_voltage.max(), 200)
            i_fit = rtd_iv_schulman(v_fit, *self.fitted_params)
            
            self.iv_fit_canvas.axes.plot(v_fit, i_fit, '--', 
                                       color='#e74c3c', linewidth=2, label='Schulman Fit')
            
            # Highlight peak and valley if available
            if hasattr(self, 'peak_point'):
                self.iv_fit_canvas.axes.plot(self.peak_point[0], self.peak_point[1], 'o', 
                                           color='#e74c3c', markersize=8, label='Peak')
            if hasattr(self, 'valley_point'):
                self.iv_fit_canvas.axes.plot(self.valley_point[0], self.valley_point[1], 'o', 
                                           color='#f39c12', markersize=8, label='Valley')
            
            self.iv_fit_canvas.axes.set_xlabel('Voltage (V)')
            self.iv_fit_canvas.axes.set_ylabel('Current (mA)')
            self.iv_fit_canvas.axes.set_title('I-V Data with Schulman Model Fit')
            self.iv_fit_canvas.axes.grid(True, alpha=0.3)
            self.iv_fit_canvas.axes.legend()
            
            self.iv_fit_canvas.fig.tight_layout()
            self.iv_fit_canvas.draw()
            
        except Exception as e:
            # Silently handle errors
            pass
    
    def clear_iv_analysis(self):
        """Clear IV Fit analysis data and plots."""
        # Clear data
        if hasattr(self, 'iv_voltage'):
            delattr(self, 'iv_voltage')
        if hasattr(self, 'iv_current'):
            delattr(self, 'iv_current')
        if hasattr(self, 'iv_file_path'):
            delattr(self, 'iv_file_path')
        if hasattr(self, 'peak_point'):
            delattr(self, 'peak_point')
        if hasattr(self, 'valley_point'):
            delattr(self, 'valley_point')
        if hasattr(self, 'fitted_params'):
            delattr(self, 'fitted_params')
        
        # Clear UI
        self.iv_filename_label.setText("No file loaded")
        self.iv_filename_label.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 5px;")
        self.select_points_button.setEnabled(False)
        self.fit_button.setEnabled(False)
        
        # Reset parameter spin boxes to defaults
        param_defaults = [5.71e-5, 1.746, 2.091, 0.189, 3.47e-3, 3.17, 0.044]
        param_names = ['A', 'B', 'C', 'D', 'H', 'N1', 'N2']
        for name, default in zip(param_names, param_defaults):
            if name in self.param_spins:
                self.param_spins[name].setValue(default)
        
        # Clear plot
        self.iv_fit_canvas.axes.clear()
        self.iv_fit_canvas.draw()
    
    def clear_analysis(self):
        """Clear all analysis data and plots."""
        # Clear TLM data
        self.tlm_files = []
        self.tlm_distances = []
        self.resistances = []
        
        # Clear IV Fit data
        self.clear_iv_analysis()
        self.iv_data = []
        
        # Clear the table
        self.tlm_table.setRowCount(0)
        
        # Show placeholders
        self.table_placeholder.show()
        self.tlm_table.hide()
        self.plot_placeholder.show()
        self.tlm_canvas.hide()
        
        # Clear the plots
        self.tlm_canvas.axes.clear()
        self.tlm_canvas.draw()
    
    def reset_plot_view(self):
        """Reset the plot view to show all data."""
        if hasattr(self, 'tlm_canvas'):
            self.tlm_canvas.reset_view()
    
    def clear_plot_annotations(self):
        """Clear all annotations from the plot."""
        if hasattr(self, 'tlm_canvas'):
            self.tlm_canvas.clear_annotations()
    
    def update_plot_scales(self):
        """Update plot scales based on checkbox states."""
        if hasattr(self, 'tlm_canvas') and hasattr(self, 'log_x_checkbox'):
            log_x = self.log_x_checkbox.isChecked()
            log_y = self.log_y_checkbox.isChecked()
            self.tlm_canvas.set_log_scales(log_x, log_y)
    
    def process_data(self, data):
        """
        Process measurement data for analysis.
        
        Args:
            data: Measurement data dictionary from IV sweep
        """
        try:
            # Handle bidirectional data (forward and reverse sweeps)
            if 'voltage_forward' in data and 'current_forward' in data:
                # Combine forward and reverse data
                voltage_forward = np.array(data['voltage_forward'])
                current_forward = np.array(data['current_forward'])
                voltage_reverse = np.array(data['voltage_reverse']) if 'voltage_reverse' in data else np.array([])
                current_reverse = np.array(data['current_reverse']) if 'current_reverse' in data else np.array([])
                
                # Combine all data
                if len(voltage_reverse) > 0:
                    self.iv_voltage = np.concatenate([voltage_forward, voltage_reverse])
                    self.iv_current = np.concatenate([current_forward, current_reverse]) * 1e-3  # Convert to mA
                else:
                    self.iv_voltage = voltage_forward
                    self.iv_current = current_forward * 1e-3  # Convert to mA
                    
                self.iv_file_path = "Measurement Data (Bidirectional)"
                
            # Handle single direction data
            elif 'voltage' in data and 'current' in data:
                self.iv_voltage = np.array(data['voltage'])
                self.iv_current = np.array(data['current']) * 1e-3  # Convert to mA
                self.iv_file_path = "Measurement Data"
                
            else:
                print("No voltage/current data found in measurement data")
                return
            
            # Enable IV fit button
            self.iv_fit_button.setEnabled(True)
            self.iv_fit_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppTheme.COLORS['primary']};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #1c6ea4;
                }}
                QPushButton:pressed {{
                    background-color: #155a8a;
                }}
            """)
            
            print(f"IV data loaded for analysis: {len(self.iv_voltage)} points")
            
        except Exception as e:
            print(f"Error processing measurement data: {e}")
            QMessageBox.warning(self, "Data Processing Error", f"Error processing measurement data: {str(e)}")
    
    # Multi-Region TLM Methods
    def add_region(self):
        """Add a new region to the multi-region analysis."""
        
        region_name, ok = QInputDialog.getText(
            self, 'Add Region', 'Enter region name:',
            text=f'Region {len(self.regions_data) + 1}'
        )
        
        if ok and region_name:
            if region_name in self.regions_data:
                QMessageBox.warning(self, "Duplicate Region", f"Region '{region_name}' already exists.")
                return
            
            # Add to regions data
            self.regions_data[region_name] = {
                'files': [],
                'distances': [],
                'resistances': [],
                'color': self.region_colors[self.current_color_index % len(self.region_colors)],
                'analyzed': False
            }
            self.current_color_index += 1
            
            # Update region list
            self.update_region_list()
            
            # Update multi-assignment combo
            self.multi_region_combo.addItem(region_name)
            
            # Update files table to include new region in dropdowns
            self.update_multi_files_table()
    
    def update_region_list(self):
        """Update the region list table."""
        self.region_list.setRowCount(len(self.regions_data))
        
        for row, (region_name, data) in enumerate(self.regions_data.items()):
            # Region name
            self.region_list.setItem(row, 0, QTableWidgetItem(region_name))
            
            # File count
            file_count = len(data['files'])
            self.region_list.setItem(row, 1, QTableWidgetItem(str(file_count)))
            
            # Status
            status = "✅ Analyzed" if data['analyzed'] else "⏳ Pending" if file_count > 0 else "📁 No Files"
            self.region_list.setItem(row, 2, QTableWidgetItem(status))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            remove_button = QPushButton("🗑️")
            remove_button.setToolTip("Remove this region")
            remove_button.setMaximumWidth(30)
            remove_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['danger']};
                    color: {self.colors['text']};
                    border-radius: 3px;
                    padding: 2px;
                    font-size: 10px;
                }}
            """)
            remove_button.clicked.connect(lambda checked, name=region_name: self.remove_region(name))
            actions_layout.addWidget(remove_button)
            
            self.region_list.setCellWidget(row, 3, actions_widget)
    
    def load_tlm_files_continuous(self):
        """Load TLM files continuously (adds to existing collection)."""
        options = QFileDialog.Option.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select TLM Files", "",
            "Text Files (*.txt);;All Files (*)",
            options=options
        )
        
        if file_paths:
            # Add new files to existing collection
            for file_path in file_paths:
                if file_path not in self.multi_loaded_files:
                    self.multi_loaded_files.append(file_path)
                    # Initialize file data
                    self.file_data[file_path] = {
                        'distance': 10.0,  # Default distance
                        'region': 'Not assigned'
                    }
            
            self.update_multi_files_display()
            # Only update table if it's empty, otherwise preserve existing UI
            if self.multi_loaded_files and self.multi_files_table.rowCount() == 0:
                self.update_multi_files_table()
            elif self.multi_loaded_files:
                # Just add new rows without resetting existing ones
                self.add_new_files_to_table()
            self.analyze_multi_region_button.setEnabled(True)
    
    def load_tlm_files_from_folders(self):
        """Load TLM files from selected folders (recursively searches subfolders)."""
        try:
            # Use a custom approach for multiple folder selection
            # First, let user select a parent directory
            parent_dir = QFileDialog.getExistingDirectory(
                self, 
                "Select Parent Directory (will scan all subdirectories)", 
                "",
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not parent_dir:
                return
            
            # Ask how they want to select folders
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Folder Selection Mode")
            msg_box.setText("How would you like to select folders?")
            msg_box.setInformativeText(
                "Choose your preferred method:\n\n" +
                "• Automatic: Scan ALL subdirectories\n" +
                "• Manual: Select specific folders one by one\n" +
                "• Multi-Select: Try to select multiple folders at once"
            )
            
            auto_btn = msg_box.addButton("Automatic Scan", QMessageBox.ButtonRole.AcceptRole)
            manual_btn = msg_box.addButton("Manual Selection", QMessageBox.ButtonRole.AcceptRole)
            multi_btn = msg_box.addButton("Multi-Select", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == cancel_btn:
                return
            
            if clicked_button == auto_btn:
                # Scan all subdirectories automatically
                folder_paths = []
                for root, dirs, files in os.walk(parent_dir):
                    # Check if this directory contains TLM files
                    has_tlm_files = any(
                        os.path.splitext(f)[1].lower() in ['.txt', '.xlsx', '.xls', '.csv']
                        for f in files
                    )
                    if has_tlm_files:
                        folder_paths.append(root)
                
                if not folder_paths:
                    QMessageBox.information(
                        self, "No TLM Files Found", 
                        f"No TLM files found in any subdirectories of:\n{parent_dir}"
                    )
                    return
            elif clicked_button == manual_btn:
                # Manual selection of specific folders
                folder_paths = []
                while True:
                    folder_path = QFileDialog.getExistingDirectory(
                        self, 
                        "Select TLM Folder (Cancel when done)", 
                        parent_dir,
                        QFileDialog.Option.ShowDirsOnly
                    )
                    
                    if not folder_path:
                        break
                    
                    folder_paths.append(folder_path)
                    
                    # Ask if they want to add more
                    more_reply = QMessageBox.question(
                        self, 
                        "Add More Folders?",
                        f"Added: {os.path.basename(folder_path)}\n\nAdd another folder?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if more_reply == QMessageBox.StandardButton.No:
                        break
            elif clicked_button == multi_btn:
                # Use a custom approach: show available folders and let user select multiple
                folder_paths = self.show_folder_selection_dialog(parent_dir)
                if not folder_paths:
                    return
            
            if not folder_paths:
                return
            
            # Find all relevant files in the selected folders
            found_files = []
            supported_extensions = ['.txt', '.xlsx', '.xls', '.csv']
            
            # Walk through all subdirectories of all selected folders
            for folder_path in folder_paths:
                try:
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                file_ext = os.path.splitext(file_path)[1].lower()
                                if file_ext in supported_extensions:
                                    found_files.append(file_path)
                            except Exception as e:
                                print(f"Error processing file {file}: {e}")
                                continue
                except Exception as e:
                    print(f"Error walking folder {folder_path}: {e}")
                    continue
            
            if found_files:
                # Group files by distance and select only upward + most recent
                try:
                    selected_files = self.process_and_select_files(found_files)
                except Exception as e:
                    print(f"Error in process_and_select_files: {e}")
                    import traceback
                    traceback.print_exc()
                    return
                
                # Add selected files to existing collection
                added_count = 0
                skipped_count = 0
                
                for file_path in selected_files:
                    if file_path not in self.multi_loaded_files:
                        try:
                            self.multi_loaded_files.append(file_path)
                            # Initialize file data with auto-detected distance from filename
                            distance = self.extract_distance_from_filename(os.path.basename(file_path))
                            self.file_data[file_path] = {
                                'distance': distance,
                                'region': 'Not assigned'
                            }
                            added_count += 1
                        except Exception as e:
                            print(f"Error adding file {file_path}: {e}")
                            import traceback
                            traceback.print_exc()
                            skipped_count += 1
                            continue
                    else:
                        skipped_count += 1
                
                # Show success message
                message = f"Successfully loaded {added_count} new files from {len(folder_paths)} folder(s)."
                message += f"\n\nProcessing summary:"
                message += f"\n• Folders processed: {len(folder_paths)}"
                message += f"\n• Files found: {len(found_files)}"
                message += f"\n• Files selected: {len(selected_files)} (most recent for each distance)"
                message += f"\n• Distance calculation: first digit of identifier × 5 µm"
                message += f"\n• Files added: {added_count}"
                if skipped_count > 0:
                    message += f"\n• Files skipped: {skipped_count} (duplicates or errors)"
                message += f"\n\nTotal files in collection: {len(self.multi_loaded_files)}"
                
                QMessageBox.information(self, "Files Loaded", message)
                
                self.update_multi_files_display()
                # Update table
                if self.multi_loaded_files and self.multi_files_table.rowCount() == 0:
                    self.update_multi_files_table()
                elif self.multi_loaded_files:
                    self.add_new_files_to_table()
                self.analyze_multi_region_button.setEnabled(True)
            else:
                QMessageBox.warning(
                    self, "No Files Found", 
                    f"No supported files (.txt, .xlsx, .xls, .csv) found in the selected folder(s)."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Folders",
                f"An error occurred while loading folders:\n{str(e)}\n\nPlease try again or load files individually."
            )
    
    def process_and_select_files(self, file_paths):
        """Process files and select the most recent file for each distance."""
        from collections import defaultdict
        
        # Group files by distance
        files_by_distance = defaultdict(list)
        
        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)
                distance = self.extract_distance_from_filename(filename)
                sweep_direction = self.detect_sweep_direction(filename)
                
                # Get file modification time safely
                try:
                    mod_time = os.path.getmtime(file_path)
                except (OSError, IOError):
                    mod_time = 0  # Default to 0 if can't get mod time
                
                files_by_distance[distance].append({
                    'path': file_path,
                    'filename': filename,
                    'distance': distance,
                    'sweep_direction': sweep_direction,
                    'mod_time': mod_time
                })
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        # Select files for each distance - always use most recent
        selected_files = []
        
        for distance, file_group in files_by_distance.items():
            # Always select the most recent file regardless of sweep direction
            most_recent = max(file_group, key=lambda x: x['mod_time'])
            selected_files.append(most_recent['path'])
        
        return selected_files
    
    def extract_distance_from_filename(self, filename):
        """Try to extract TLM distance from filename using common patterns."""
        import re
        
        print(f"DEBUG: Extracting distance from filename: {filename}")
        
        # Common patterns: "10um", "10_um", "10 um", "D10", "d10", etc.
        patterns = [
            r'(\d+\.?\d*)\s*[uμ]m',  # 10um, 10.5um, 10 um
            r'[dD](\d+\.?\d*)',       # D10, d10.5
            r'(\d+\.?\d*)\s*micron',  # 10micron
            r'_(\d+\.?\d*)_',         # _10_, _10.5_
            r'-(\d+\.?\d*)-',         # -34- (for files like "I-V Curve - 34 - ...")
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    distance = float(match.group(1))
                    print(f"DEBUG: Found distance {distance} using pattern: {pattern}")
                    return distance
                except Exception as e:
                    print(f"DEBUG: Error converting to float: {e}")
                    pass
        
        print("DEBUG: No pattern matched, using default distance 10.0")
        # Default distance if no pattern found
        return 10.0
    
    def detect_sweep_direction(self, filename):
        """Detect if filename indicates upward or downward sweep."""
        filename_lower = filename.lower()
        
        if 'upward' in filename_lower or 'up' in filename_lower:
            return 'upward'
        elif 'downward' in filename_lower or 'down' in filename_lower:
            return 'downward'
        else:
            return 'unknown'
    
    def select_best_file_from_group(self, file_paths, selection_mode='most_recent'):
        """Select one file from a group based on selection criteria."""
        
        if len(file_paths) == 1:
            return file_paths[0]
        
        if selection_mode == 'most_recent':
            # Get file modification times
            files_with_time = [(f, os.path.getmtime(f)) for f in file_paths]
            # Sort by modification time (newest first)
            files_with_time.sort(key=lambda x: x[1], reverse=True)
            return files_with_time[0][0]  # Return most recent file
        
        elif selection_mode == 'largest_file':
            # Use largest file (more data points usually)
            files_with_size = [(f, os.path.getsize(f)) for f in file_paths]
            files_with_size.sort(key=lambda x: x[1], reverse=True)
            return files_with_size[0][0]
        
        elif selection_mode == 'best_r_squared':
            # Use file with best R² value (requires analyzing all)
            best_file = file_paths[0]
            best_r2 = -1
            
            for file_path in file_paths:
                try:
                    data = self.load_data_file(file_path)
                    voltage = data[:, 0]
                    current = data[:, 1] * 1e-3
                    
                    min_voltage = self.multi_min_voltage_input.value()
                    valid_indices = voltage >= min_voltage
                    
                    if np.sum(valid_indices) < 2:
                        continue
                    
                    filtered_voltage = voltage[valid_indices]
                    filtered_current = current[valid_indices]
                    
                    slope, intercept, r_value, _, _ = stats.linregress(filtered_voltage, filtered_current)
                    r_squared = r_value * r_value
                    
                    if r_squared > best_r2:
                        best_r2 = r_squared
                        best_file = file_path
                except:
                    continue
            
            return best_file
        
        else:
            return file_paths[0]  # Default: first file
    
    def update_multi_files_display(self):
        """Update the files label display."""
        if not self.multi_loaded_files:
            self.multi_files_label.setText("No files loaded")
        else:
            file_count = len(self.multi_loaded_files)
            self.multi_files_label.setText(f"{file_count} file{'s' if file_count != 1 else ''} loaded")
    
    def refresh_table_scrollbar(self):
        """Refresh table scrollbar after window operations."""
        # Force table to recalculate its scroll area
        self.multi_files_table.resizeRowsToContents()
        self.multi_files_table.updateGeometry()
        # Ensure scrollbar is properly updated
        self.multi_files_table.verticalScrollBar().update()
    
    def schedule_scrollbar_refresh(self):
        """Schedule a scrollbar refresh after a short delay."""
        self.scrollbar_refresh_timer.start(100)  # 100ms delay
    
    def update_multi_region_combo(self):
        """Update the multi-assignment region combo with current regions."""
        current_text = self.multi_region_combo.currentText()
        self.multi_region_combo.clear()
        self.multi_region_combo.addItem("Not assigned")
        
        # Add all existing regions
        for region_name in self.regions_data.keys():
            self.multi_region_combo.addItem(region_name)
        
        # Try to restore the previous selection if it still exists
        if current_text in [self.multi_region_combo.itemText(i) for i in range(self.multi_region_combo.count())]:
            self.multi_region_combo.setCurrentText(current_text)
        else:
            self.multi_region_combo.setCurrentText("Not assigned")
    
    def update_multi_files_table(self):
        """Update the files table with current loaded files."""
        # Ensure table has correct number of rows
        self.multi_files_table.setRowCount(len(self.multi_loaded_files))
        
        # Force table to refresh and show all rows
        self.multi_files_table.resizeRowsToContents()
        
        # Refresh scrollbar after update
        self.refresh_table_scrollbar()
        
        # Update multi-assignment combo with current regions
        self.update_multi_region_combo()
        
        for row, file_path in enumerate(self.multi_loaded_files):
            filename = os.path.basename(file_path)
            
            # File name
            file_item = QTableWidgetItem(filename)
            file_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.multi_files_table.setItem(row, 0, file_item)
            
            # Distance (simple text like regular TLM)
            distance = self.file_data.get(file_path, {}).get('distance', 10.0)
            distance_item = QTableWidgetItem(f"{distance:.1f} μm")
            distance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.multi_files_table.setItem(row, 1, distance_item)
            
            # Region selection - using QPushButton instead of QComboBox for better alignment
            region_button = QPushButton(self.file_data.get(file_path, {}).get('region', 'Not assigned'))
            region_button.setMinimumHeight(23)
            region_button.setMaximumHeight(23)
            region_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['input']};
                    color: {self.colors['text']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 3px;
                    padding: 0px 4px 2px 4px;
                    text-align: center;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors.get('button_hover', '#4A4A4A')};
                }}
                QPushButton:pressed {{
                    background-color: {self.colors.get('button_pressed', '#3A3A3A')};
                }}
            """)
            region_button.clicked.connect(lambda checked, fp=file_path, btn=region_button: self.show_region_menu(fp, btn))
            self.multi_files_table.setCellWidget(row, 2, region_button)
    
    def add_new_files_to_table(self):
        """Add only new files to the table without resetting existing ones."""
        current_row_count = self.multi_files_table.rowCount()
        new_files_count = len(self.multi_loaded_files) - current_row_count
        
        if new_files_count > 0:
            # Add new rows for new files
            self.multi_files_table.setRowCount(len(self.multi_loaded_files))
            # Force table to refresh
            self.multi_files_table.resizeRowsToContents()
            # Refresh scrollbar after update
            self.refresh_table_scrollbar()
            
            # Update multi-assignment combo with current regions
            self.update_multi_region_combo()
            
            # Only populate the new rows
            for row in range(current_row_count, len(self.multi_loaded_files)):
                file_path = self.multi_loaded_files[row]
                filename = os.path.basename(file_path)
                
                # File name
                file_item = QTableWidgetItem(filename)
                file_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.multi_files_table.setItem(row, 0, file_item)
                
                # Distance (simple text like regular TLM)
                distance = self.file_data.get(file_path, {}).get('distance', 10.0)
                distance_item = QTableWidgetItem(f"{distance:.1f} μm")
                distance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.multi_files_table.setItem(row, 1, distance_item)
                
                # Region selection - using QPushButton instead of QComboBox for better alignment
                region_button = QPushButton(self.file_data.get(file_path, {}).get('region', 'Not assigned'))
                region_button.setMinimumHeight(23)
                region_button.setMaximumHeight(23)
                region_button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['input']};
                        color: {self.colors['text']};
                        border: 1px solid {self.colors['border']};
                        border-radius: 3px;
                        padding: 0px 4px 2px 4px;
                        text-align: center;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors.get('button_hover', '#4A4A4A')};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors.get('button_pressed', '#3A3A3A')};
                    }}
                """)
                region_button.clicked.connect(lambda checked, fp=file_path, btn=region_button: self.show_region_menu(fp, btn))
                self.multi_files_table.setCellWidget(row, 2, region_button)
    
    def update_file_distance(self, file_path, distance):
        """Update distance for a specific file."""
        if file_path in self.file_data:
            self.file_data[file_path]['distance'] = distance
            # Distance updated successfully
    
    def show_region_menu(self, file_path, button):
        """Show a context menu for region selection."""
        from PyQt6.QtWidgets import QMenu
        from functools import partial

        # Keep a persistent reference to avoid GC-related crashes on some platforms
        if not hasattr(self, "_region_menu") or self._region_menu is None:
            self._region_menu = QMenu(self)
        else:
            self._region_menu.clear()

        # Safety: guard against missing/invalid button
        if button is None:
            return

        # Build actions
        self._region_menu.addAction(
            "Not assigned",
            partial(self.update_file_region, file_path, "Not assigned", button),
        )

        for region_name in list(self.regions_data.keys()):
            self._region_menu.addAction(
                region_name,
                partial(self.update_file_region, file_path, region_name, button),
            )

        # Show menu at button position (non-blocking to avoid platform-specific aborts)
        button_rect = button.rect()
        self._region_menu.popup(button.mapToGlobal(button_rect.bottomLeft()))
    
    def show_load_files_menu(self):
        """Show a context menu for load files options."""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.addAction("📁 Load Individual Files", self.load_tlm_files_continuous)
        menu.addAction("📂 Load from Folders", self.load_tlm_files_from_folders)
        
        # Show menu at button position
        button_rect = self.load_files_button.rect()
        menu.exec(self.load_files_button.mapToGlobal(button_rect.bottomLeft()))
    
    def assign_selected_files(self):
        """Assign selected files to the selected region."""
        selected_region = self.multi_region_combo.currentText()
        selected_items = self.multi_files_table.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select files from the table first.")
            return
        
        # Get unique rows from selected items
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(item.row())
        
        # Update each selected file
        updated_count = 0
        for row in selected_rows:
            if row < len(self.multi_loaded_files):
                file_path = self.multi_loaded_files[row]
                if file_path in self.file_data:
                    self.file_data[file_path]['region'] = selected_region
                    # Update the button text
                    button = self.multi_files_table.cellWidget(row, 2)
                    if button:
                        button.setText(selected_region)
                    updated_count += 1
        
        if updated_count > 0:
            # Clear selection after successful assignment
            self.multi_files_table.clearSelection()
            QMessageBox.information(self, "Assignment Complete", 
                                  f"Assigned {updated_count} file(s) to '{selected_region}'.")
        else:
            QMessageBox.warning(self, "No Updates", "No files were updated.")
    
    def update_file_region(self, file_path, region, button=None):
        """Update region assignment for a specific file."""
        if file_path in self.file_data:
            self.file_data[file_path]['region'] = region
            if button:
                button.setText(region)
    
    def edit_file_distance(self, row, column):
        """Edit file distance when double-clicking on distance column."""
        if column == 1 and row < len(self.multi_loaded_files):  # Distance column
            file_path = self.multi_loaded_files[row]
            current_distance = self.file_data.get(file_path, {}).get('distance', 10.0)
            
            distance, ok = QInputDialog.getDouble(
                self, 'Edit Distance', f'Enter distance for {os.path.basename(file_path)}:',
                value=current_distance, min=0.1, max=1000.0, decimals=1
            )
            
            if ok:
                # Update file_data first
                if file_path in self.file_data:
                    self.file_data[file_path]['distance'] = distance
                # Update only the specific cell, don't recreate the whole table
                self.multi_files_table.setItem(row, 1, QTableWidgetItem(f"{distance:.1f} μm"))
    
    def on_cell_changed(self, row, column):
        """Handle when a cell is changed directly in the table."""
        if column == 1 and row < len(self.multi_loaded_files):  # Distance column
            file_path = self.multi_loaded_files[row]
            item = self.multi_files_table.item(row, column)
            if item:
                try:
                    # Extract numeric value from text like "10.0 μm"
                    text = item.text()
                    distance = float(text.replace(' μm', '').replace('μm', ''))
                    
                    # Update file_data
                    if file_path in self.file_data:
                        self.file_data[file_path]['distance'] = distance
                except ValueError:
                    pass  # Silently ignore invalid values
    
    def remove_region(self, region_name):
        """Remove a region from the analysis."""
        reply = QMessageBox.question(
            self, 'Remove Region', 
            f'Are you sure you want to remove region "{region_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.regions_data[region_name]
            self.update_region_list()
            
            # Update analyze button state
            has_files = any(len(data['files']) > 0 for data in self.regions_data.values())
            self.analyze_multi_region_button.setEnabled(has_files)
            
            # Replot if we have data
            if has_files:
                self.plot_multi_region_data()
    
    def analyze_all_regions(self):
        """Analyze all regions and create comparison plot."""
        if not self.regions_data:
            QMessageBox.warning(self, "No Regions", "Please add regions and assign files first.")
            return
        
        min_voltage = self.multi_min_voltage_input.value()
        
        # Group files by region from file_data
        region_files = {}
        for file_path, data in self.file_data.items():
            region = data['region']
            if region != 'Not assigned':
                if region not in region_files:
                    region_files[region] = []
                region_files[region].append({
                    'file_path': file_path,
                    'distance': data['distance']
                })
        
        if not region_files:
            QMessageBox.warning(self, "No Assigned Files", "Please assign files to regions in the table.")
            return
        
        # Check if we have valid distances
        for region, files in region_files.items():
            distances = [f['distance'] for f in files]
            if len(set(distances)) == 1:
                QMessageBox.warning(self, "Identical Distances", f"All distances in region {region} are identical: {distances[0]}")
        
        # Analyze each region
        for region_name, files in region_files.items():
            if region_name not in self.regions_data:
                continue
            
            try:
                # Process files for this region using the new structure
                distances, resistances = self.process_region_files_new(files, min_voltage)
                
                if len(distances) > 1:
                    # Perform linear regression: R = a*L + b
                    # where a = R_s/D and b = 2*R_c
                    slope, intercept, r_value, p_value, std_err = stats.linregress(distances, resistances)
                    r_squared = r_value * r_value
                    
                    # Calculate TLM parameters
                    D = 200  # Dimension (assumed)
                    R_c = intercept / 2  # Contact resistance: b = 2*R_c
                    R_s = slope * D      # Sheet resistance: a = R_s/D
                    
                    # Store results
                    self.regions_data[region_name]['distances'] = distances
                    self.regions_data[region_name]['resistances'] = resistances
                    self.regions_data[region_name]['slope'] = slope
                    self.regions_data[region_name]['intercept'] = intercept
                    self.regions_data[region_name]['r_squared'] = r_squared
                    self.regions_data[region_name]['R_c'] = R_c
                    self.regions_data[region_name]['R_s'] = R_s
                    self.regions_data[region_name]['analyzed'] = True
                else:
                    self.regions_data[region_name]['analyzed'] = False
                    
            except Exception as e:
                QMessageBox.warning(self, "Analysis Error", f"Error analyzing region {region_name}: {str(e)}")
                self.regions_data[region_name]['analyzed'] = False
        
        # Update region list
        self.update_region_list()
        
        # Plot comparison
        self.plot_multi_region_data()
        
        # Enable export button
        self.export_multi_region_button.setEnabled(True)
    
    def process_region_files(self, file_paths, min_voltage):
        """Process TLM files for a region and return distances and resistances."""
        distances = []
        resistances = []
        
        for file_path in file_paths:
            try:
                # Load and process the file (similar to single TLM analysis)
                voltage, current = self.load_iv_data_from_file(file_path)
                
                if len(voltage) == 0 or len(current) == 0:
                    continue
                
                # Extract TLM distance from filename or ask user
                distance = self.extract_distance_from_filename(file_path)
                if distance is None:
                    distance, ok = QInputDialog.getDouble(
                        self, 'TLM Distance', 
                        f'Enter TLM distance for {os.path.basename(file_path)}:',
                        value=10.0, min=0.1, max=1000.0, decimals=1
                    )
                    if not ok:
                        continue
                
                # Filter data based on minimum voltage
                valid_indices = voltage >= min_voltage
                if np.sum(valid_indices) < 2:
                    continue
                
                filtered_voltage = voltage[valid_indices]
                filtered_current = current[valid_indices]
                
                # Convert current from mA to A
                filtered_current_amps = filtered_current * 1e-3
                
                # Perform linear regression
                slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_voltage, filtered_current_amps)
                
                if abs(slope) < 1e-10 or np.isnan(slope):
                    continue
                
                resistance = 1.0 / slope  # R = 1/slope (in ohms)
                
                distances.append(distance)
                resistances.append(resistance)
                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        return np.array(distances), np.array(resistances)
    
    def process_region_files_simple(self, file_paths, distances, min_voltage):
        """Process TLM files for a region using the new simplified structure."""
        resistances = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # Load and process the file
                voltage, current = self.load_iv_data_from_file(file_path)
                
                if len(voltage) == 0 or len(current) == 0:
                    continue
                
                # Filter data based on minimum voltage
                valid_indices = voltage >= min_voltage
                if np.sum(valid_indices) < 2:
                    continue
                
                filtered_voltage = voltage[valid_indices]
                filtered_current = current[valid_indices]
                
                # Convert current from mA to A
                filtered_current_amps = filtered_current * 1e-3
                
                # Perform linear regression
                slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_voltage, filtered_current_amps)
                
                if abs(slope) < 1e-10 or np.isnan(slope):
                    continue
                
                resistance = 1.0 / slope  # R = 1/slope (in ohms)
                resistances.append(resistance)
                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        return np.array(distances), np.array(resistances)
    
    def process_region_files_new(self, files, min_voltage):
        """Process TLM files for a region using the new file structure with duplicate handling."""
        distances = []
        resistances = []
        
        # Group files by distance
        distance_groups = {}
        for file_info in files:
            dist = file_info['distance']
            if dist not in distance_groups:
                distance_groups[dist] = []
            distance_groups[dist].append(file_info)
        
        # Always use most recent file
        selection_mode = 'most_recent'
        
        # Process each distance group
        for distance, group_files in sorted(distance_groups.items()):
            # Filter for upward sweeps only (prefer upward over downward/unknown)
            upward_files = [f for f in group_files 
                           if self.detect_sweep_direction(os.path.basename(f['file_path'])) == 'upward']
            
            if not upward_files:
                # If no upward files, use all files
                upward_files = group_files
            
            # Select best file from group if multiple
            if len(upward_files) > 1:
                file_paths = [f['file_path'] for f in upward_files]
                selected_file_path = self.select_best_file_from_group(file_paths, selection_mode)
                # Get the file_info for the selected file
                selected_file_info = next(f for f in upward_files if f['file_path'] == selected_file_path)
                files_to_process = [selected_file_info]
            else:
                files_to_process = upward_files
            
            # Process the selected file(s)
            for file_info in files_to_process:
                file_path = file_info['file_path']
                
                try:
                    # Load and process the file
                    voltage, current = self.load_iv_data_from_file(file_path)
                    
                    if len(voltage) == 0 or len(current) == 0:
                        continue
                    
                    # Filter data based on minimum voltage
                    valid_indices = voltage >= min_voltage
                    if np.sum(valid_indices) < 2:
                        continue
                    
                    filtered_voltage = voltage[valid_indices]
                    filtered_current = current[valid_indices]
                    
                    # Convert current from mA to A
                    filtered_current_amps = filtered_current * 1e-3
                    
                    # Perform linear regression
                    slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_voltage, filtered_current_amps)
                    
                    if abs(slope) < 1e-10 or np.isnan(slope):
                        continue
                    
                    resistance = 1.0 / slope  # R = 1/slope (in ohms)
                    
                    distances.append(distance)
                    resistances.append(resistance)
                    
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    continue
        
        return np.array(distances), np.array(resistances)
    
    def extract_distance_from_filename(self, file_path):
        """Try to extract TLM distance from filename."""
        filename = os.path.basename(file_path)
        # Look for patterns like "5um", "10.5um", "5_um", etc.
        import re
        patterns = [
            r'(\d+\.?\d*)\s*um',
            r'(\d+\.?\d*)\s*μm',
            r'(\d+\.?\d*)_um',
            r'(\d+\.?\d*)_μm',
            r'dist[_-]?(\d+\.?\d*)',
            r'distance[_-]?(\d+\.?\d*)',
            r'Curve - (\d+\.?\d*) -',  # I-V Curve - 34 - (more specific)
            r'-(\d+\.?\d*)-',         # -34- (for files like "I-V Curve - 34 - ...")
            r'_(\d+\.?\d*)_',         # _10_, _10.5_
        ]
        
        # Special pattern for identifier-based distance calculation
        # Look for patterns like "12_upward_sweep" where 12 is the identifier
        # Make sure we don't match dates by being more specific
        identifier_patterns = [
            r'_(\d+)_upward_sweep',    # _12_upward_sweep
            r'_(\d+)_downward_sweep',  # _12_downward_sweep
            r'_(\d+)_sweep',           # _12_sweep
            r'Curve - (\d+) - \[',     # I-V Curve - 12 - [ (stops at the bracket)
        ]
        
        # First, try identifier-based distance calculation
        for pattern in identifier_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                identifier = int(match.group(1))
                # Use only the first digit of the identifier
                first_digit = int(str(identifier)[0])
                distance = first_digit * 5  # Distance = first_digit * 5
                return distance
        
        # If no identifier pattern found, try direct distance patterns
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                distance = float(match.group(1))
                return distance
        
        return 10.0  # Default distance instead of None
    
    def show_folder_selection_dialog(self, parent_dir):
        """Show a custom dialog to select multiple folders."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QListWidgetItem
        from PyQt6.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Folders Containing TLM Files")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Select multiple folders by clicking them (Ctrl+Click for multiple selection):")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # List widget to show available folders
        folder_list = QListWidget()
        folder_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Find all folders that contain TLM files
        available_folders = []
        for root, dirs, files in os.walk(parent_dir):
            # Check if this directory contains TLM files
            has_tlm_files = any(
                os.path.splitext(f)[1].lower() in ['.txt', '.xlsx', '.xls', '.csv']
                for f in files
            )
            if has_tlm_files:
                available_folders.append(root)
        
        # Add folders to the list
        for folder_path in available_folders:
            # Get relative path for display
            rel_path = os.path.relpath(folder_path, parent_dir)
            item = QListWidgetItem(rel_path)
            item.setData(Qt.ItemDataRole.UserRole, folder_path)
            folder_list.addItem(item)
        
        if not available_folders:
            no_folders = QLabel("No folders with TLM files found in the selected directory.")
            no_folders.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(no_folders)
        else:
            layout.addWidget(folder_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: folder_list.selectAll())
        button_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(lambda: folder_list.clearSelection())
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_folders = []
            for item in folder_list.selectedItems():
                folder_path = item.data(Qt.ItemDataRole.UserRole)
                selected_folders.append(folder_path)
            return selected_folders
        else:
            return []
    
    def load_iv_data_from_file(self, file_path):
        """Load I-V data from a file."""
        try:
            # Try to load as text file first
            data = np.loadtxt(file_path, skiprows=1)  # Skip header
            if data.shape[1] >= 2:
                voltage = data[:, 0]
                current = data[:, 1]
                return voltage, current
        except:
            pass
        
        # If that fails, try CSV
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            if len(df.columns) >= 2:
                voltage = df.iloc[:, 0].values
                current = df.iloc[:, 1].values
                return voltage, current
        except:
            pass
        
        return np.array([]), np.array([])
    
    def plot_multi_region_data(self):
        """Plot all regions on the same graph for comparison."""
        if not hasattr(self, 'multi_region_canvas'):
            return
        
        # Clear the plot
        self.multi_region_canvas.axes.clear()
        
        # Determine resistance units based on all data
        all_resistances = []
        for data in self.regions_data.values():
            if 'resistances' in data and len(data['resistances']) > 0:
                all_resistances.extend(data['resistances'])
        
        if not all_resistances:
            return
        
        max_resistance = max(all_resistances)
        if max_resistance < 1000:  # Less than 1kΩ, use Ω
            resistance_unit = "Ω"
            resistance_factor = 1.0
        elif max_resistance < 1000000:  # Less than 1MΩ, use kΩ
            resistance_unit = "kΩ"
            resistance_factor = 1000.0
        else:  # 1MΩ or more, use MΩ
            resistance_unit = "MΩ"
            resistance_factor = 1000000.0
        
        # Plot each region
        for region_name, data in self.regions_data.items():
            if not data['analyzed'] or 'distances' not in data or 'resistances' not in data:
                continue
            
            distances = data['distances']
            resistances = data['resistances']
            color = data['color']
            
            if len(distances) == 0 or len(resistances) == 0:
                continue
            
            # Convert resistances to display units
            resistances_display = resistances / resistance_factor
            
            # Plot data points (no debug spam)
            
            # Plot data points (no label for data points)
            scatter = self.multi_region_canvas.axes.scatter(
                distances, resistances_display, 
                color=color, s=100, alpha=0.8, 
                edgecolor='white', linewidth=2, 
                zorder=3
            )
            
            # Plot fitted line if we have enough points
            if len(distances) > 1 and 'slope' in data and 'intercept' in data:
                x_line = np.linspace(min(distances), max(distances), 100)
                y_line = (data['slope'] * x_line + data['intercept']) / resistance_factor
                
                # Get TLM parameters
                R_c = data.get('R_c', 0)
                R_s = data.get('R_s', 0)
                
                # Format R_c and R_s for display
                if R_c < 1:
                    R_c_text = f"{R_c:.3f} {resistance_unit}"
                elif R_c < 1000:
                    R_c_text = f"{R_c:.2f} {resistance_unit}"
                else:
                    R_c_text = f"{R_c:.1f} {resistance_unit}"
                
                if R_s < 1:
                    R_s_text = f"{R_s:.3f} {resistance_unit}"
                elif R_s < 1000:
                    R_s_text = f"{R_s:.2f} {resistance_unit}"
                else:
                    R_s_text = f"{R_s:.1f} {resistance_unit}"
                
                # Create legend label with TLM parameters using subscripts
                legend_label = f"{region_name}: R$_{{c}}$={R_c_text}, R$_{{s}}$={R_s_text}"
                
                self.multi_region_canvas.axes.plot(
                    x_line, y_line, 
                    color=color, linewidth=2, 
                    linestyle='--', alpha=0.8, 
                    label=legend_label, zorder=2
                )
        
        # Set labels and title with larger fonts
        self.multi_region_canvas.axes.set_xlabel('TLM Distance (μm)', fontsize=14, fontweight='bold')
        self.multi_region_canvas.axes.set_ylabel(f'Resistance ({resistance_unit})', fontsize=14, fontweight='bold')
        # Use editable title with larger font
        plot_title = self.multi_plot_title_input.text() if hasattr(self, 'multi_plot_title_input') else 'TLM Analysis'
        self.multi_region_canvas.axes.set_title(plot_title, fontsize=16, fontweight='bold')
        
        # Increase tick label font size
        self.multi_region_canvas.axes.tick_params(axis='both', which='major', labelsize=12)
        
        # Apply plot style settings
        self.update_multi_plot_style()
        
        # Force auto-scale to show all data points
        self.multi_region_canvas.axes.relim()
        self.multi_region_canvas.axes.autoscale_view()
        
        # Get current limits and add generous padding
        xlim = self.multi_region_canvas.axes.get_xlim()
        ylim = self.multi_region_canvas.axes.get_ylim()
        
        # Add 10% padding on both sides
        x_padding = (xlim[1] - xlim[0]) * 0.1
        y_padding = (ylim[1] - ylim[0]) * 0.1
        
        # Set new limits with padding
        self.multi_region_canvas.axes.set_xlim(xlim[0] - x_padding, xlim[1] + x_padding)
        self.multi_region_canvas.axes.set_ylim(ylim[0] - y_padding, ylim[1] + y_padding)
        
        # Force a complete redraw
        self.multi_region_canvas.axes.figure.tight_layout()
        
        # Refresh the plot
        self.multi_region_canvas.draw()
    
    def update_multi_plot_style(self):
        """Apply light style to the multi-region plot matching measurement plots."""
        if not hasattr(self, 'multi_region_canvas') or self.multi_region_canvas is None:
            return
        
        # Use theme colors for consistency with measurement plots
        self.multi_region_canvas.axes.set_facecolor(self.colors['plot_bg'])  # White background
        self.multi_region_canvas.figure.patch.set_facecolor(self.colors['plot_fig_bg'])  # White figure background
        
        # Text styling to match measurement plots
        self.multi_region_canvas.axes.tick_params(colors=self.colors['plot_text'], direction='out', width=1.5, labelsize=10)
        self.multi_region_canvas.axes.xaxis.label.set_color(self.colors['plot_text'])
        self.multi_region_canvas.axes.yaxis.label.set_color(self.colors['plot_text'])
        self.multi_region_canvas.axes.title.set_color(self.colors['plot_text'])
        
        # Grid styling to match measurement plots
        self.multi_region_canvas.axes.grid(True, linestyle='--', alpha=0.7, color=self.colors['plot_grid'])
        
        # Customize axes to match measurement plots
        for spine in self.multi_region_canvas.axes.spines.values():
            spine.set_color('#000000')  # Black spines
            spine.set_linewidth(1.5)    # Slightly thicker
        
        # Legend styling to match measurement plots
        legend = self.multi_region_canvas.axes.get_legend()
        if legend:
            legend.remove()
        legend = self.multi_region_canvas.axes.legend(loc='upper right', frameon=True, fontsize=13)
        legend.get_frame().set_facecolor('#ffffff')
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor('#000000')
        
        # Make legend text black for better visibility
        for text in legend.get_texts():
            text.set_color('#000000')
        
        # Redraw
        self.multi_region_canvas.draw()
    
    def clear_multi_region_analysis(self):
        """Clear all multi-region analysis data."""
        reply = QMessageBox.question(
            self, 'Clear All Data', 
            'Are you sure you want to clear all regions and analysis data?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear all data structures
                self.regions_data.clear()
                self.multi_loaded_files.clear()
                self.file_data.clear()
                self.current_color_index = 0
                
                # Update UI elements safely
                self.update_region_list()
                self.update_multi_files_display()
                self.update_multi_files_table()
                
                # Clear and reset the multi-assignment combo
                self.multi_region_combo.clear()
                self.multi_region_combo.addItem("Not assigned")
                
                # Disable buttons
                self.analyze_multi_region_button.setEnabled(False)
                self.export_multi_region_button.setEnabled(False)
                
                # Clear plot safely
                if hasattr(self, 'multi_region_canvas') and self.multi_region_canvas is not None:
                    self.multi_region_canvas.axes.clear()
                    self.multi_region_canvas.draw()
                    
            except Exception as e:
                print(f"Error during clear operation: {e}")
                # Try to reset to a clean state
                self.regions_data = {}
                self.multi_loaded_files = []
                self.file_data = {}
                self.current_color_index = 0
    
    def export_multi_region_results(self):
        """Export multi-region analysis results to file."""
        if not self.regions_data:
            QMessageBox.warning(self, "No Data", "No analysis data to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Multi-Region TLM Results", "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                import pandas as pd
                
                # Prepare data for export
                export_data = []
                for region_name, data in self.regions_data.items():
                    if data['analyzed'] and 'distances' in data and 'resistances' in data:
                        for i, (dist, res) in enumerate(zip(data['distances'], data['resistances'])):
                            export_data.append({
                                'Region': region_name,
                                'TLM_Distance_um': dist,
                                'Resistance_Ohm': res,
                                'Resistance_kOhm': res / 1000.0,
                                'Slope': data.get('slope', 0),
                                'Intercept': data.get('intercept', 0),
                                'R_squared': data.get('r_squared', 0)
                            })
                
                if export_data:
                    df = pd.DataFrame(export_data)
                    df.to_csv(file_path, index=False)
                    QMessageBox.information(self, "Export Successful", f"Results exported to {file_path}")
                else:
                    QMessageBox.warning(self, "No Data", "No analyzed data to export.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting data: {str(e)}") 