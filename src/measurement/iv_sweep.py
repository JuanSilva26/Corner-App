"""
I-V Sweep Measurement Module

This module handles I-V sweep measurements using Keithley source meters.
It processes measurement parameters, executes the measurement, and provides results.
"""

import os
import time
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class MeasurementWorker(QObject):
    """Worker class that performs the actual measurement in a separate thread."""
    
    # Signals
    measurement_started = pyqtSignal()
    measurement_completed = pyqtSignal(dict)  # Emits measurement data
    measurement_error = pyqtSignal(str)  # Emits error message
    measurement_progress = pyqtSignal(int)  # Emits progress percentage
    measurement_data_point = pyqtSignal(float, float, bool)  # Emits voltage, current, is_reverse
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True
        
    def run(self):
        """Perform the actual measurement (runs in separate thread)."""
        try:
            self.measurement_started.emit()
            
            # Extract parameters
            instrument = self.params['instrument']
            start_voltage = self.params['start_voltage']
            stop_voltage = self.params['stop_voltage']
            num_points = self.params['num_points']
            compliance = self.params['compliance']
            bidirectional = self.params['bidirectional']
            save_files = self.params['save_files']
            device_name = self.params['device_name']
            
            # Setup instrument
            self.measurement_progress.emit(5)
            instrument.setup_for_iv_sweep(compliance)
            self.measurement_progress.emit(10)
            
            # Create voltage points array for progress tracking
            upward_points = np.linspace(start_voltage, stop_voltage, num=num_points, endpoint=True)
            
            if bidirectional:
                # Downward sweep points (excluding first point to avoid duplication)
                downward_points = np.linspace(stop_voltage, start_voltage, num=num_points, endpoint=True)[1:]
                sweep_points = np.concatenate((upward_points, downward_points))
            else:
                sweep_points = upward_points
            
            # Determine progress increment per point
            total_points = len(sweep_points)
            progress_per_point = 80 / total_points  # 80% of progress bar for the sweep
            
            # Perform manual sweep to track progress
            voltage_measured = []
            current_measured = []
            
            # Flag to track if we're in the reverse part of the sweep
            is_reverse = False
            forward_points_count = len(upward_points)
            
            for i, voltage in enumerate(sweep_points):
                if not self.running:
                    self.measurement_error.emit("Measurement was stopped")
                    return
                
                # Determine if we're in the reverse sweep (if bidirectional)
                if bidirectional and i >= forward_points_count:
                    is_reverse = True
                
                # Set voltage
                instrument.write(f":SOUR:VOLT {voltage}")
                time.sleep(0.0001)  # Short delay
                
                # Read values
                data = instrument.query(":READ?")
                values = data.split(',')
                
                # Extract and convert values
                # The first value is current, second is voltage
                current = float(values[0].replace('A', '')) * 1E3  # Convert to mA
                voltage_read = float(values[1].replace('V', ''))
                
                # Emit the single data point for real-time plotting
                self.measurement_data_point.emit(voltage_read, current, is_reverse)
                
                # Store values
                current_measured.append(current)
                voltage_measured.append(voltage_read)
                
                # Update progress
                progress = 10 + int((i + 1) * progress_per_point)
                self.measurement_progress.emit(progress)
            
            # Turn output off
            instrument.write(":OUTP OFF")
            self.measurement_progress.emit(90)
            
            # Process data
            if bidirectional:
                voltage_forward = voltage_measured[:num_points]
                current_forward = current_measured[:num_points]
                voltage_reverse = voltage_measured[num_points-1:]
                current_reverse = current_measured[num_points-1:]
                
                result_data = {
                    'voltage_forward': voltage_forward,
                    'current_forward': current_forward,
                    'voltage_reverse': voltage_reverse,
                    'current_reverse': current_reverse
                }
            else:
                result_data = {
                    'voltage': voltage_measured,
                    'current': current_measured
                }
            
            # Save data if requested
            if save_files and self.running:
                self._save_measurement_data(result_data, device_name, bidirectional)
            
            self.measurement_progress.emit(95)
            
            # Cleanup instrument
            if self.running:
                instrument.cleanup()
            
            self.measurement_progress.emit(100)
            
            # Emit completed signal with data
            if self.running:
                self.measurement_completed.emit(result_data)
            
        except Exception as e:
            self.measurement_error.emit(str(e))
            
            # Try to clean up if there was an error
            try:
                if 'instrument' in self.params and self.params['instrument']:
                    self.params['instrument'].cleanup()
            except:
                pass
    
    def stop(self):
        """Stop the measurement process."""
        self.running = False
        
        # Try to clean up
        try:
            if 'instrument' in self.params and self.params['instrument']:
                self.params['instrument'].cleanup()
        except:
            pass
    
    def _save_measurement_data(self, data, device_name, bidirectional):
        """
        Save measurement data to files.
        
        Args:
            data: Measurement data dictionary
            device_name: Device name/path for saving
            bidirectional: Whether this was a bidirectional sweep
        """
        try:
            # Create folder if it doesn't exist
            os.makedirs(device_name, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = time.strftime('%Y-%m-%d_%H%M.%S')
            folder_name = os.path.basename(device_name)
            base_path = os.path.join(device_name, f'I-V Curve - {folder_name} - [{timestamp}]')
            
            # Save the forward sweep data
            if bidirectional:
                data_forward = np.stack([data['voltage_forward'], data['current_forward']], axis=1)
                np.savetxt(
                    base_path + '_upward_sweep.txt', 
                    data_forward, 
                    delimiter="\t", 
                    header="Voltage(V)\tCurrent(mA)", 
                    comments=''
                )
                
                # Save the reverse sweep data
                data_reverse = np.stack([data['voltage_reverse'], data['current_reverse']], axis=1)
                np.savetxt(
                    base_path + '_downward_sweep.txt', 
                    data_reverse, 
                    delimiter="\t", 
                    header="Voltage(V)\tCurrent(mA)", 
                    comments=''
                )
            else:
                # Save single sweep data
                data_single = np.stack([data['voltage'], data['current']], axis=1)
                np.savetxt(
                    base_path + '.txt', 
                    data_single, 
                    delimiter="\t", 
                    header="Voltage(V)\tCurrent(mA)", 
                    comments=''
                )
                
        except Exception as e:
            self.measurement_error.emit(f"Error saving data: {str(e)}")


class IVSweepMeasurement(QObject):
    """
    Class to handle I-V sweep measurements.
    
    This class manages the measurement process and worker thread.
    It emits signals with measurement progress and results.
    """
    
    # Signals
    measurement_started = pyqtSignal()
    measurement_completed = pyqtSignal(dict)  # Emits measurement data
    measurement_error = pyqtSignal(str)  # Emits error message
    measurement_progress = pyqtSignal(int)  # Emits progress percentage
    measurement_data_point = pyqtSignal(float, float, bool)  # Forward real-time data points
    
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.running = False
    
    def start_measurement(self, params):
        """
        Start a measurement with the given parameters.
        
        Args:
            params: Dictionary containing measurement parameters
                - instrument: Keithley instrument instance
                - start_voltage: Starting voltage
                - stop_voltage: Ending voltage
                - num_points: Number of measurement points
                - compliance: Current compliance
                - bidirectional: Whether to perform bidirectional sweep
                - save_files: Whether to save measurement files
                - device_name: Device name/path for saving
        """
        # Check if a measurement is already running
        if self.running:
            self.measurement_error.emit("A measurement is already in progress")
            return
        
        # Clean up any existing thread
        self._cleanup_thread()
        
        # Create a new thread and worker
        self.thread = QThread()
        self.worker = MeasurementWorker(params)
        
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        
        # Connect worker signals to our own signals
        self.worker.measurement_started.connect(self.measurement_started)
        self.worker.measurement_completed.connect(self.measurement_completed)
        self.worker.measurement_error.connect(self.measurement_error)
        self.worker.measurement_progress.connect(self.measurement_progress)
        self.worker.measurement_data_point.connect(self.measurement_data_point)
        
        # Connect thread signals
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self._handle_thread_finished)
        
        # Connect worker signals for cleanup
        self.worker.measurement_completed.connect(self._handle_measurement_completed)
        self.worker.measurement_error.connect(self._handle_measurement_error)
        
        # Start the thread
        self.running = True
        self.thread.start()
    
    def stop_measurement(self):
        """Stop the measurement process."""
        if self.running and self.worker:
            self.worker.stop()
            self._cleanup_thread()
            self.running = False
    
    def _handle_measurement_completed(self, data):
        """Handle measurement completion."""
        self._cleanup_thread()
        self.running = False
    
    def _handle_measurement_error(self, error):
        """Handle measurement error."""
        self._cleanup_thread()
        self.running = False
    
    def _handle_thread_finished(self):
        """Handle thread finishing."""
        self._cleanup_thread()
        self.running = False
    
    def _cleanup_thread(self):
        """Clean up the thread and worker."""
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)  # Wait up to 3 seconds
            
        if self.thread:
            self.thread.deleteLater()
            self.thread = None
            
        if self.worker:
            self.worker = None
