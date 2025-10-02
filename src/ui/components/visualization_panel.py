"""
Visualization panel for displaying measurement results.
"""

import os
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QFrame, QLabel
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt
from ..theme import AppTheme, PlotTheme

# Configure matplotlib with appropriate backend
PlotTheme.setup_matplotlib()

# Import backends after setting the backend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy.linalg
import matplotlib.pyplot as plt


class VisualizationPanel(QWidget):
    """Panel for visualizing measurement data with real-time plotting."""
    
    # Add a signal to notify when the plot is cleared
    plot_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get centralized theme colors
        self.colors = AppTheme.get_colors()
        
        # Data storage
        self.voltage_forward = []
        self.current_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Add header with title
        title_layout = QHBoxLayout()
        title = QLabel("Visualization")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.colors['text']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)
        self.layout.addLayout(title_layout)
        
        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.colors['border']}; border-radius: 2px;")
        self.layout.addWidget(separator)
        
        # Create a container for the plot that will expand
        plot_container = QWidget()
        plot_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create matplotlib figure and canvas with improved styling
        self.figure = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(300)
        
        # Create custom navigation toolbar with clear button
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
        
        # Add plot container to main layout with stretch factor
        self.layout.addWidget(plot_container, 1)
        
        # Create button bar - only hide panel button, remove export/clear
        self.create_button_bar()
        
        # Initial plot update
        self.canvas.draw()
    
    def customize_plot(self):
        """Apply custom styling to the plot with dark background matching Analysis tab."""
        # Set dark mode style for plots with improved aesthetics (same as Analysis tab)
        plt.style.use('dark_background')
        self.figure.patch.set_facecolor('#1e272e')
        self.ax.set_facecolor('#1e272e')
        
        # Apply enhanced styling to axes (same as Analysis tab)
        self.ax.tick_params(colors='#ecf0f1', labelsize=10, length=6, width=1)
        self.ax.spines['bottom'].set_color('#34495e')
        self.ax.spines['top'].set_color('#34495e')
        self.ax.spines['left'].set_color('#34495e')
        self.ax.spines['right'].set_color('#34495e')
        
        # Enhanced text styling (same as Analysis tab)
        self.ax.xaxis.label.set_color('#ecf0f1')
        self.ax.xaxis.label.set_fontsize(12)
        self.ax.xaxis.label.set_fontweight('bold')
        
        self.ax.yaxis.label.set_color('#ecf0f1')
        self.ax.yaxis.label.set_fontsize(12)
        self.ax.yaxis.label.set_fontweight('bold')
        
        self.ax.title.set_color('#ecf0f1')
        self.ax.title.set_fontsize(14)
        self.ax.title.set_fontweight('bold')
        
        # Set plot labels
        self.ax.set_xlabel('Voltage (V)')
        self.ax.set_ylabel('Current (mA)')
        self.ax.set_title('I-V Curve')
        
        # Grid styling - lighter grid for better contrast with data on dark background
        self.ax.grid(True, linestyle='--', alpha=0.3, color='#34495e')
        
        # Add forward and reverse line objects with enhanced styling and renamed legends
        self.line_forward, = self.ax.plot(
            [], [], 
            color=self.colors['plot_forward'], 
            marker='o', 
            markersize=6,       # Larger markers
            linestyle='-', 
            linewidth=2.5,      # Thicker line
            label='Upward'
        )
        
        self.line_reverse, = self.ax.plot(
            [], [], 
            color=self.colors['plot_reverse'], 
            marker='o', 
            markersize=6,       # Larger markers
            linestyle='-', 
            linewidth=2.5,      # Thicker line
            label='Downward'
        )
        
        # Enhanced legend with white text
        legend = self.ax.legend(
            loc='upper right', 
            frameon=True, 
            fontsize=12,        # Larger font
            framealpha=0.95     # More opaque background
        )
        legend.get_frame().set_facecolor('#2c3e50')  # Same as Analysis tab
        legend.get_frame().set_edgecolor('#34495e')
        legend.get_frame().set_linewidth(1.0)
        
        # Make legend text white and bold for better visibility
        for text in legend.get_texts():
            text.set_color('#ecf0f1')  # Same as Analysis tab
            text.set_fontweight('bold')
        
        # Background colors already set in customize_plot method
        
        # Apply tight layout safely (suppress warnings)
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='The figure layout has changed to tight')
                self.figure.tight_layout()
        except (ValueError, numpy.linalg.LinAlgError):
            pass
    
    def resizeEvent(self, event):
        """Handle resize events to keep the plot properly sized."""
        super().resizeEvent(event)
        if hasattr(self, 'figure'):
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', message='The figure layout has changed to tight')
                    self.figure.tight_layout()
                self.canvas.draw()
            except (ValueError, numpy.linalg.LinAlgError):
                # Skip tight_layout if it fails due to invalid figure dimensions
                pass
    
    def create_button_bar(self):
        """Create button bar for plot controls."""
        button_layout = QHBoxLayout()
        
        # Modern button style
        button_style = f"""
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
        
        # Hide panel button only
        self.hide_button = QPushButton("Hide Panel")
        self.hide_button.clicked.connect(self.hide_panel)
        self.hide_button.setStyleSheet(button_style)
        self.hide_button.setToolTip("Hide the visualization panel")
        button_layout.addWidget(self.hide_button)
        
        button_layout.addStretch()
        
        self.layout.addLayout(button_layout)
    
    @pyqtSlot(dict)
    def update_plot(self, data):
        """Update the plot with new data."""
        bidirectional = 'voltage_reverse' in data and 'current_reverse' in data
        
        # Store the data
        if bidirectional:
            self.voltage_forward = data['voltage_forward']
            self.current_forward = data['current_forward']
            self.voltage_reverse = data['voltage_reverse']
            self.current_reverse = data['current_reverse']
            
            # Update line data
            self.line_forward.set_data(self.voltage_forward, self.current_forward)
            self.line_reverse.set_data(self.voltage_reverse, self.current_reverse)
        else:
            self.voltage_forward = data['voltage']
            self.current_forward = data['current']
            self.voltage_reverse = []
            self.current_reverse = []
            
            # Update line data
            self.line_forward.set_data(self.voltage_forward, self.current_forward)
            self.line_reverse.set_data([], [])
        
        # Adjust plot limits with more padding for better visualization
        all_voltages = self.voltage_forward
        all_currents = self.current_forward
        
        if bidirectional:
            all_voltages = np.concatenate((all_voltages, self.voltage_reverse))
            all_currents = np.concatenate((all_currents, self.current_reverse))
        
        if len(all_voltages) > 0 and len(all_currents) > 0:
            # Calculate margins with at least 10% padding
            v_range = max(all_voltages) - min(all_voltages)
            c_range = max(all_currents) - min(all_currents)
            
            # Use at least 10% padding, but minimum of 0.005 for small ranges
            margin_x = max(0.15 * v_range if v_range > 0.01 else 0.005, 0.02)
            margin_y = max(0.15 * c_range if c_range > 0.01 else 0.005, 0.02)
            
            self.ax.set_xlim(min(all_voltages) - margin_x, max(all_voltages) + margin_x)
            self.ax.set_ylim(min(all_currents) - margin_y, max(all_currents) + margin_y)
        
        # Apply tight layout to maximize plot area - wrap with try/except to handle LinAlgError
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='The figure layout has changed to tight')
                self.figure.tight_layout()
        except (ValueError, numpy.linalg.LinAlgError):
            # Skip tight_layout if dimensions are invalid or matrix is singular
            pass
        
        # Redraw the canvas
        self.canvas.draw()
    
    
    def clear_plot(self):
        """Clear the plot."""
        self.voltage_forward = []
        self.current_forward = []
        self.voltage_reverse = []
        self.current_reverse = []
        
        self.line_forward.set_data([], [])
        self.line_reverse.set_data([], [])
        
        self.ax.relim()
        self.ax.autoscale_view()
        
        self.canvas.draw()
        
        # Emit the signal that the plot has been cleared
        self.plot_cleared.emit()
    
    def hide_panel(self):
        """Hide the visualization panel."""
        # Find the parent window's right panel and hide it
        parent = self.parent()
        while parent and not hasattr(parent, 'right_panel'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'right_panel'):
            parent.right_panel.hide()
            parent.main_splitter.setSizes([1000, 0])
    

class CustomNavigationToolbar(NavigationToolbar):
    """Custom navigation toolbar with added clear button functionality."""
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        # Initialize with standard matplotlib toolbar
    
    def add_clear_button(self, clear_callback):
        """Add a clear plot button to the toolbar."""
        # Create an action for clearing the plot
        # Place it next to the save button
        self.clear_action = self.addAction("Clear Plot", clear_callback)
        # Move it to be next to the save button (index 3)
        actions = self.actions()
        save_index = next((i for i, action in enumerate(actions) if action.text() == "Save"), 3)
        # Insert after save button
        self.insertAction(actions[save_index + 1], self.clear_action) 