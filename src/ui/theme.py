"""
Centralized theme and styling configuration for the Measurement App.

This module provides a single source of truth for colors, styles, and UI constants
used throughout the application.
"""


class AppTheme:
    """Centralized color scheme and styling for the application."""
    
    # Color Palette
    COLORS = {
        'primary': '#2980b9',        # Primary blue
        'secondary': '#27ae60',      # Green for positive actions
        'danger': '#c0392b',         # Red for negative actions
        'warning': '#d35400',        # Orange for warnings/notifications
        'dark': '#1e272e',           # Dark background
        'darker': '#151c21',         # Darker background
        'light': '#485460',          # Light backgrounds (dark mode)
        'lighter': '#808e9b',        # Button/accent gray
        'text': '#ecf0f1',           # Text color
        'text_secondary': '#bdc3c7', # Secondary text
        'border': '#34495e',         # Border color
        'button': '#34495e',         # Button background
        'input': '#2c3e50',          # Input field background
        'success_bg': '#274d36',     # Dark green background for success messages
        'error_bg': '#532b2b',       # Dark red background for error messages
        'warning_bg': '#553b21',     # Dark yellow background for warnings
        
        # Plot colors
        'plot_bg': '#ffffff',        # White background for plot
        'plot_fig_bg': '#ffffff',    # Figure background (outside plot area)
        'plot_grid': '#cccccc',      # Light grid lines
        'plot_forward': '#2980b9',   # Forward line - blue
        'plot_reverse': '#c0392b',   # Reverse line - red
        'plot_text': '#333333',      # Dark text for plot labels
    }
    
    @classmethod
    def get_colors(cls):
        """Get the color dictionary."""
        return cls.COLORS.copy()
    
    @classmethod
    def header_style(cls):
        """Get header label style."""
        return f"font-size: 16px; font-weight: bold; color: {cls.COLORS['text']};"
    
    @classmethod
    def group_box_style(cls):
        """Get QGroupBox style."""
        return f"""
            QGroupBox {{ 
                font-weight: bold; 
                border: 1px solid {cls.COLORS['border']}; 
                border-radius: 6px; 
                margin-top: 1.5ex; 
                padding-top: 10px;
                padding-bottom: 8px;
                background-color: {cls.COLORS['dark']};
                color: {cls.COLORS['text']};
            }} 
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                subcontrol-position: top center; 
                padding: 0 8px; 
                color: {cls.COLORS['text']};
            }}
        """
    
    @classmethod
    def button_style(cls):
        """Get standard button style."""
        return f"""
            QPushButton {{ 
                background-color: {cls.COLORS['button']}; 
                color: {cls.COLORS['text']}; 
                border-radius: 5px; 
                padding: 8px 15px; 
                font-weight: bold; 
                border: none;
            }} 
            QPushButton:hover {{ 
                background-color: {cls.COLORS['primary']}; 
            }} 
            QPushButton:pressed {{ 
                background-color: #1c6ea4;
            }}
            QPushButton:disabled {{ 
                background-color: {cls.COLORS['light']}; 
                color: {cls.COLORS['text_secondary']};
            }}
        """
    
    @classmethod
    def primary_button_style(cls):
        """Get primary action button style (green)."""
        return f"""
            QPushButton {{ 
                background-color: {cls.COLORS['secondary']}; 
                color: {cls.COLORS['text']}; 
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
                background-color: {cls.COLORS['light']}; 
                color: {cls.COLORS['text_secondary']};
            }}
        """
    
    @classmethod
    def danger_button_style(cls):
        """Get danger button style (red)."""
        return f"""
            QPushButton {{ 
                background-color: {cls.COLORS['danger']}; 
                color: {cls.COLORS['text']}; 
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
                background-color: {cls.COLORS['light']}; 
                color: {cls.COLORS['text_secondary']};
            }}
        """
    
    @classmethod
    def input_style(cls):
        """Get input field style."""
        return f"""
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
                padding: 5px;
                border: 1px solid {cls.COLORS['border']};
                border-radius: 4px;
                background-color: {cls.COLORS['input']};
                color: {cls.COLORS['text']};
                selection-background-color: {cls.COLORS['primary']};
                min-height: 25px;
            }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {cls.COLORS['primary']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {cls.COLORS['border']};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {cls.COLORS['border']};
                border-radius: 0;
                background-color: {cls.COLORS['input']};
                selection-background-color: {cls.COLORS['primary']};
                selection-color: {cls.COLORS['text']};
            }}
        """
    
    @classmethod
    def section_separator_style(cls):
        """Get section separator line style."""
        return f"background-color: {cls.COLORS['border']}; border-radius: 2px;"


class PlotTheme:
    """Centralized matplotlib plotting theme configuration."""
    
    @staticmethod
    def setup_matplotlib():
        """Setup matplotlib to use Qt backend."""
        import matplotlib
        try:
            matplotlib.use('Qt6Agg')
        except:
            matplotlib.use('Qt5Agg')
    
    @classmethod
    def configure_plot_style(cls, ax, title="", xlabel="", ylabel="", colors=None):
        """
        Apply consistent styling to a matplotlib axes object.
        
        Args:
            ax: Matplotlib axes object
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            colors: Color dictionary (defaults to AppTheme.COLORS)
        """
        if colors is None:
            colors = AppTheme.COLORS
        
        # Set labels and title
        ax.set_xlabel(xlabel, fontsize=12, color=colors['plot_text'], fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, color=colors['plot_text'], fontweight='bold')
        ax.set_title(title, fontsize=14, color=colors['plot_text'], fontweight='bold')
        
        # Grid styling
        ax.grid(True, linestyle='--', alpha=0.7, color=colors['plot_grid'])
        
        # Customize axes
        for spine in ax.spines.values():
            spine.set_color('#000000')
            spine.set_linewidth(1.5)
        
        # Tick styling
        ax.tick_params(colors='#000000', direction='out', width=1.5, labelsize=10)
        
        # Set background color
        ax.set_facecolor(colors['plot_bg'])
    
    @classmethod
    def configure_legend(cls, ax, colors=None):
        """
        Apply consistent legend styling.
        
        Args:
            ax: Matplotlib axes object
            colors: Color dictionary (defaults to AppTheme.COLORS)
        """
        if colors is None:
            colors = AppTheme.COLORS
        
        legend = ax.legend(loc='upper right', frameon=True, fontsize=11)
        legend.get_frame().set_facecolor('#ffffff')
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor('#000000')
        
        # Make legend text black for better visibility
        for text in legend.get_texts():
            text.set_color('#000000')
        
        return legend


# Convenience functions
def get_theme():
    """Get the application theme instance."""
    return AppTheme


def get_plot_theme():
    """Get the plot theme instance."""
    return PlotTheme

