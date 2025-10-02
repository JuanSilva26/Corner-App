#!/usr/bin/env python3
"""
Measurement App - Main Entry Point

A PyQt6-based application for controlling a Keithley source meter 
to perform I-V characterization measurements.
"""

import sys
import os
import warnings

# Suppress warnings for clean startup
warnings.filterwarnings('ignore')

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import qInstallMessageHandler
from ui.main_window import MainWindow
from ui.components.connection_panel import ConnectionPanel
from ui.components.measurement_panel import MeasurementPanel
from ui.components.visualization_panel import VisualizationPanel
from ui.components.data_table import DataTable
from ui.components.analysis_panel import AnalysisPanel
from measurement.iv_sweep import IVSweepMeasurement

def _create_panels():
    """Create all UI panels."""
    return {
        'connection': ConnectionPanel(),
        'measurement': MeasurementPanel(),
        'visualization': VisualizationPanel(),
        'data_table': DataTable(),
        'analysis': AnalysisPanel()
    }


def _create_measurement_handler(window):
    """Create and configure the measurement handler."""
    iv_measurement = IVSweepMeasurement()
    window.iv_measurement = iv_measurement  # Store reference to prevent garbage collection
    return iv_measurement


def _connect_panel_signals(panels, window):
    """Connect signals between panels."""
    connection = panels['connection']
    measurement = panels['measurement']
    
    # Connection panel signals
    connection.instrument_connected.connect(measurement.set_instrument)
    connection.instrument2_connected.connect(measurement.set_instrument2)
    connection.pm100d_connected.connect(measurement.set_pm100d_instrument)
    connection.dual_instrument_mode_changed.connect(measurement.set_dual_mode)
    connection.connection_status_changed.connect(
        lambda connected, message: (
            window.update_status(message),
            measurement.clear_instrument() if not connected else None
        )
    )


def _connect_measurement_signals(panels, iv_measurement, window):
    """Connect measurement-related signals."""
    measurement = panels['measurement']
    data_table = panels['data_table']
    visualization = panels['visualization']
    analysis = panels['analysis']
    
    # Measurement control signals
    measurement.measurement_started.connect(iv_measurement.start_measurement)
    measurement.measurement_stopped.connect(iv_measurement.stop_measurement)
    
    # Measurement status signals
    iv_measurement.measurement_started.connect(
        lambda: window.update_status("Measurement in progress...")
    )
    iv_measurement.measurement_completed.connect(measurement.update_plot)
    iv_measurement.measurement_completed.connect(data_table.update_table)
    iv_measurement.measurement_completed.connect(analysis.process_data)
    iv_measurement.measurement_completed.connect(
        lambda data: (
            window.update_status("Measurement completed successfully"),
            measurement.measurement_completed(),
            window.right_panel.show()
        )
    )
    iv_measurement.measurement_error.connect(
        lambda error: (
            window.update_status(f"Error: {error}"),
            measurement.measurement_error(error),
            QMessageBox.critical(window, "Measurement Error", error)
        )
    )
    iv_measurement.measurement_progress.connect(measurement.update_progress)
    
    # Real-time data signals
    iv_measurement.measurement_data_point.connect(measurement.update_real_time_data)
    iv_measurement.measurement_data_point_piv.connect(measurement.update_real_time_data_piv)
    iv_measurement.save_plot_requested.connect(measurement.save_plot)
    
    # Visualization signals
    measurement.update_plot_signal.connect(visualization.update_plot)
    visualization.plot_cleared.connect(
        lambda: (
            window.right_panel.hide(),
            window.main_splitter.setSizes([1000, 0])
        )
    )


def _add_panels_to_window(window, panels):
    """Add panels to their respective tabs in the window."""
    # Remove placeholder widgets properly
    while window.connection_layout.count():
        child = window.connection_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
    
    while window.measurement_layout.count():
        child = window.measurement_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
    
    while window.data_layout.count():
        child = window.data_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
    
    while window.analysis_layout.count():
        child = window.analysis_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
    
    # Add panels to tabs
    window.connection_layout.addWidget(panels['connection'])
    window.measurement_layout.addWidget(panels['measurement'])
    window.data_layout.addWidget(panels['data_table'])
    window.analysis_layout.addWidget(panels['analysis'])
    
    # Replace placeholder visualization panel
    while window.right_layout.count() > 1:
        child = window.right_layout.takeAt(1)
        if child.widget():
            child.widget().deleteLater()
    
    window.right_layout.addWidget(panels['visualization'])
    
    # Store panels as window attributes to keep references
    window.connection_panel = panels['connection']
    window.measurement_panel = panels['measurement']
    window.visualization_panel = panels['visualization']
    window.data_table = panels['data_table']
    window.analysis_panel = panels['analysis']


def _configure_initial_window_state(window):
    """Configure the initial state of the window."""
    # Initially hide the right panel
    window.right_panel.hide()
    
    # Set left panel to take full width when right panel is hidden
    window.main_splitter.setSizes([1000, 0])


def main():
    """Application entry point."""
    # Suppress QLayout warnings (harmless)
    def qt_message_handler(mode, context, message):
        if 'QLayout::addChildLayout' not in message:
            pass  # Suppress QLayout warnings, allow others if needed
    
    qInstallMessageHandler(qt_message_handler)
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Create all UI panels
    panels = _create_panels()
    
    # Create measurement handler
    iv_measurement = _create_measurement_handler(window)
    
    # Connect all signals
    _connect_panel_signals(panels, window)
    _connect_measurement_signals(panels, iv_measurement, window)
    
    # Add panels to window
    _add_panels_to_window(window, panels)
    
    # Configure initial window state
    _configure_initial_window_state(window)
    
    # Show the window and start event loop
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()