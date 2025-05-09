#!/usr/bin/env python3
"""
Measurement App - Main Entry Point

A PyQt6-based application for controlling a Keithley source meter 
to perform I-V characterization measurements.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from ui.components.connection_panel import ConnectionPanel
from ui.components.measurement_panel import MeasurementPanel
from ui.components.visualization_panel import VisualizationPanel
from ui.components.data_table import DataTable
from ui.components.analysis_panel import AnalysisPanel
from measurement.iv_sweep import IVSweepMeasurement

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Create panels
    connection_panel = ConnectionPanel()
    measurement_panel = MeasurementPanel()
    visualization_panel = VisualizationPanel()
    data_table = DataTable()
    analysis_panel = AnalysisPanel()
    
    # Create measurement handler and store it as an attribute of the window
    # to prevent it from being garbage collected
    iv_measurement = IVSweepMeasurement()
    window.iv_measurement = iv_measurement  # Store reference in window
    
    # Connect signals between panels
    connection_panel.instrument_connected.connect(measurement_panel.set_instrument)
    connection_panel.connection_status_changed.connect(
        lambda connected, message: (
            window.update_status(message),
            measurement_panel.clear_instrument() if not connected else None
        )
    )
    
    # Connect measurement panel to IV sweep handler
    measurement_panel.measurement_started.connect(iv_measurement.start_measurement)
    measurement_panel.measurement_stopped.connect(iv_measurement.stop_measurement)
    
    # Connect IV sweep signals to UI components
    iv_measurement.measurement_started.connect(
        lambda: window.update_status("Measurement in progress...")
    )
    iv_measurement.measurement_completed.connect(measurement_panel.update_plot)
    iv_measurement.measurement_completed.connect(data_table.update_table)
    iv_measurement.measurement_completed.connect(
        lambda data: (
            window.update_status("Measurement completed successfully"),
            measurement_panel.measurement_completed(),
            window.right_panel.show()  # Show visualization panel when measurement is completed
        )
    )
    iv_measurement.measurement_error.connect(
        lambda error: (
            window.update_status(f"Error: {error}"),
            measurement_panel.measurement_error(error),
            QMessageBox.critical(window, "Measurement Error", error)
        )
    )
    iv_measurement.measurement_progress.connect(measurement_panel.update_progress)
    
    # Connect real-time data signals
    iv_measurement.measurement_data_point.connect(measurement_panel.update_real_time_data)
    
    # Connect measurement panel plot signals to external visualization panel
    measurement_panel.update_plot_signal.connect(visualization_panel.update_plot)
    
    # Connect visualization panel signals
    visualization_panel.plot_cleared.connect(
        lambda: (
            window.right_panel.hide(),
            window.main_splitter.setSizes([1000, 0])
        )
    )
    
    # Connect measurement data to analysis panel
    iv_measurement.measurement_completed.connect(analysis_panel.process_data)
    
    # Add panels to their respective tabs
    window.connection_layout.removeWidget(window.connection_layout.itemAt(0).widget())
    window.connection_layout.addWidget(connection_panel)
    
    window.measurement_layout.removeWidget(window.measurement_layout.itemAt(0).widget())
    window.measurement_layout.addWidget(measurement_panel)
    
    window.data_layout.removeWidget(window.data_layout.itemAt(0).widget())
    window.data_layout.addWidget(data_table)
    
    window.analysis_layout.removeWidget(window.analysis_layout.itemAt(0).widget())
    window.analysis_layout.addWidget(analysis_panel)
    
    # Replace placeholder visualization panel
    window.right_layout.itemAt(1).widget().deleteLater()
    window.right_layout.itemAt(2).widget().deleteLater()
    window.right_layout.addWidget(visualization_panel)
    
    # Store panels as window attributes to keep references
    window.connection_panel = connection_panel
    window.measurement_panel = measurement_panel
    window.visualization_panel = visualization_panel
    window.data_table = data_table
    window.analysis_panel = analysis_panel
    
    # Initially hide the right panel
    window.right_panel.hide()
    
    # Set left panel to take full width when right panel is hidden
    window.main_splitter.setSizes([1000, 0])
    
    # Show the window
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()