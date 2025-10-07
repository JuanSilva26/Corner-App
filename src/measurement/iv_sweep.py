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
    measurement_data_point_piv = pyqtSignal(float, float, float, bool)  # Emits voltage, current, power, is_reverse for P-I-V
    save_plot_requested = pyqtSignal(dict, str, bool)  # Emits data, device_name, bidirectional for plot saving
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.running = True
    
    def _setup_instruments(self):
        """Setup all required instruments for the measurement."""
        measurement_mode = self.params.get('measurement_mode', 'Single Source')
        instrument = self.params['instrument']
        compliance = self.params['compliance']
        
        # Setup primary instrument
        self.measurement_progress.emit(5)
        instrument.setup_for_iv_sweep(compliance)
        self.measurement_progress.emit(10)
        
        # Setup PM100D if in P-I-V mode
        if measurement_mode == "P-I-V Measurement":
            pm100d_instrument = self.params.get('pm100d_instrument')
            pm100d_params = self.params.get('pm100d_params')
            
            if pm100d_instrument and pm100d_params:
                # Skip PM100D setup entirely to prevent crashes
                # The measurement will continue with power=0
                self.measurement_progress.emit(12)
        
        # Setup second instrument for dual mode
        if measurement_mode == "DC Bias + Sweep":
            instrument2 = self.params.get('instrument2')
            dc_bias_params = self.params.get('dc_bias_params')
            
            if instrument2 and dc_bias_params:
                try:
                    instrument2.setup_for_iv_sweep(dc_bias_params['compliance'])
                    instrument2.write(f":SOUR:VOLT {dc_bias_params['voltage']}")
                    instrument2.write(":OUTP ON")
                    self.measurement_progress.emit(15)
                except Exception as e:
                    raise Exception(f"Failed to setup DC bias instrument: {str(e)}")
    
    def _generate_sweep_points(self):
        """Generate voltage sweep points based on parameters."""
        start_voltage = self.params['start_voltage']
        stop_voltage = self.params['stop_voltage']
        num_points = self.params['num_points']
        bidirectional = self.params['bidirectional']
        
        upward_points = np.linspace(start_voltage, stop_voltage, num=num_points, endpoint=True)
        
        if bidirectional:
            downward_points = np.linspace(stop_voltage, start_voltage, num=num_points, endpoint=True)[1:]
            sweep_points = np.concatenate((upward_points, downward_points))
        else:
            sweep_points = upward_points
        
        return sweep_points, len(upward_points)
    
    def _measure_single_point(self, voltage, is_reverse):
        """
        Measure a single voltage point.
        
        Returns:
            Tuple of (voltage_read, current, power)
        """
        instrument = self.params['instrument']
        measurement_mode = self.params.get('measurement_mode', 'Single Source')
        pm100d_instrument = self.params.get('pm100d_instrument')
        
        # Set voltage
        instrument.write(f":SOUR:VOLT {voltage}")
        time.sleep(0.0001)  # Short delay
        
        # Read I-V values
        data = instrument.query(":READ?")
        values = data.strip().split(',')
        
        # Check if we have enough values
        if len(values) < 2:
            # Keithley returned only current, use set voltage as voltage_read
            current = float(values[0].replace('A', '')) * 1E3  # Convert to mA
            voltage_read = voltage
        else:
            # Extract and convert values
            current = float(values[0].replace('A', '')) * 1E3  # Convert to mA
            voltage_read = float(values[1].replace('V', ''))
        
        # Read optical power if in P-I-V mode
        power = 0.0
        if measurement_mode == "P-I-V Measurement" and pm100d_instrument:
            try:
                if pm100d_instrument.is_connected():
                    power_watts, unit = pm100d_instrument.read_power()
                    power = float(power_watts) * 1000000  # Convert to µW
                else:
                    power = 0.0  # PM100D not connected
            except Exception as e:
                power = 0.0  # Continue with 0.0 if power reading fails
        
        # Emit real-time data point
        try:
            if measurement_mode == "P-I-V Measurement":
                self.measurement_data_point_piv.emit(voltage_read, current, power, is_reverse)
            else:
                self.measurement_data_point.emit(voltage_read, current, is_reverse)
        except Exception as e:
            print(f"Error emitting data point: {e}")
            # Continue without emitting
        
        return voltage_read, current, power
    
    def _execute_sweep(self, sweep_points, forward_points_count):
        """Execute the voltage sweep and collect data."""
        bidirectional = self.params['bidirectional']
        total_points = len(sweep_points)
        progress_per_point = 80 / total_points  # 80% of progress bar for the sweep
        
        voltage_measured = []
        current_measured = []
        power_measured = []
        
        for i, voltage in enumerate(sweep_points):
            if not self.running:
                raise Exception("Measurement was stopped")
            
            # Determine if we're in the reverse sweep
            is_reverse = bidirectional and i >= forward_points_count
            
            # Measure single point
            voltage_read, current, power = self._measure_single_point(voltage, is_reverse)
            
            # Store values
            voltage_measured.append(voltage_read)
            current_measured.append(current)
            power_measured.append(power)
            
            # Update progress
            progress = 10 + int((i + 1) * progress_per_point)
            self.measurement_progress.emit(progress)
        
        return voltage_measured, current_measured, power_measured
    
    def _process_measurement_data(self, voltage_measured, current_measured, power_measured):
        """Process measured data into the result format."""
        bidirectional = self.params['bidirectional']
        num_points = self.params['num_points']
        measurement_mode = self.params.get('measurement_mode', 'Single Source')
        is_piv = measurement_mode == "P-I-V Measurement"
        
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
            
            # Add power data for P-I-V measurements
            if is_piv:
                power_forward = power_measured[:num_points]
                power_reverse = power_measured[num_points-1:]
                result_data.update({
                    'power_forward': power_forward,
                    'power_reverse': power_reverse
                })
        else:
            result_data = {
                'voltage': voltage_measured,
                'current': current_measured
            }
            
            # Add power data for P-I-V measurements
            if is_piv:
                result_data['power'] = power_measured
        
        return result_data
    
    def _cleanup_instruments(self):
        """Clean up all instruments after measurement."""
        measurement_mode = self.params.get('measurement_mode', 'Single Source')
        instrument = self.params['instrument']
        
        if self.running:
            instrument.cleanup()
            
            # Cleanup second instrument if used
            if measurement_mode == "DC Bias + Sweep":
                instrument2 = self.params.get('instrument2')
                if instrument2:
                    try:
                        instrument2.cleanup()
                    except Exception as e:
                        print(f"Warning: Error cleaning up DC bias instrument: {str(e)}")
            
            # Cleanup PM100D if used
            if measurement_mode == "P-I-V Measurement":
                pm100d_instrument = self.params.get('pm100d_instrument')
                if pm100d_instrument:
                    try:
                        pm100d_instrument.cleanup()
                    except Exception as e:
                        print(f"Warning: Error cleaning up PM100D instrument: {str(e)}")
        
    def run(self):
        """Perform the actual measurement (runs in separate thread)."""
        instrument = self.params['instrument']
        save_files = self.params['save_files']
        device_name = self.params['device_name']
        bidirectional = self.params['bidirectional']
        measurement_mode = self.params.get('measurement_mode', 'I-V Sweep')
        
        try:
            self.measurement_started.emit()
            
            # Step 1: Setup all instruments
            self._setup_instruments()
            
            # Step 2: Generate sweep points
            sweep_points, forward_points_count = self._generate_sweep_points()
            
            # Step 3: Execute the sweep
            voltage_measured, current_measured, power_measured = self._execute_sweep(
                sweep_points, forward_points_count
            )
            
            # Step 4: Turn output off
            instrument.write(":OUTP OFF")
            self.measurement_progress.emit(90)
            
            # Step 5: Process the data
            result_data = self._process_measurement_data(
                voltage_measured, current_measured, power_measured
            )
            
            # Step 6: Save data if requested
            if save_files and self.running:
                self._save_measurement_data(result_data, device_name, bidirectional)
                self.save_plot_requested.emit(result_data, device_name, bidirectional)
            
            self.measurement_progress.emit(95)
            
            # Step 7: Cleanup instruments
            self._cleanup_instruments()
            
            self.measurement_progress.emit(100)
            
            # Step 8: Emit completed signal
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
    
    def _prepare_save_path(self, device_name):
        """
        Prepare the save path and create directory.
        
        Returns:
            Tuple of (base_path, folder_name)
        """
        os.makedirs(device_name, exist_ok=True)
        timestamp = time.strftime('%Y-%m-%d_%H%M.%S')
        folder_name = os.path.basename(device_name)
        base_path = os.path.join(device_name, f'I-V Curve - {folder_name} - [{timestamp}]')
        return base_path, folder_name
    
    def _format_data_for_save(self, data, is_piv, bidirectional):
        """
        Format measurement data for saving.
        
        Returns:
            Tuple of (data_array, header, suffix)
            For bidirectional: Returns (forward_array, reverse_array, header)
        """
        header_piv = "Voltage(V)\tCurrent(mA)\tOpticalPower(W)"
        header_iv = "Voltage(V)\tCurrent(mA)"
        
        if bidirectional:
            if is_piv:
                data_forward = np.stack([
                    data['voltage_forward'], 
                    data['current_forward'], 
                    data['power_forward']
                ], axis=1)
                data_reverse = np.stack([
                    data['voltage_reverse'], 
                    data['current_reverse'], 
                    data['power_reverse']
                ], axis=1)
                return data_forward, data_reverse, header_piv
            else:
                data_forward = np.stack([
                    data['voltage_forward'], 
                    data['current_forward']
                ], axis=1)
                data_reverse = np.stack([
                    data['voltage_reverse'], 
                    data['current_reverse']
                ], axis=1)
                return data_forward, data_reverse, header_iv
        else:
            if is_piv:
                data_single = np.stack([
                    data['voltage'], 
                    data['current'], 
                    data['power']
                ], axis=1)
                return data_single, header_piv
            else:
                data_single = np.stack([
                    data['voltage'], 
                    data['current']
                ], axis=1)
                return data_single, header_iv
    
    def _save_measurement_data(self, data, device_name, bidirectional):
        """
        Save measurement data to files.
        
        Args:
            data: Measurement data dictionary
            device_name: Device name/path for saving
            bidirectional: Whether this was a bidirectional sweep
        """
        try:
            # Prepare save path
            base_path, _ = self._prepare_save_path(device_name)
            
            # Check if this is P-I-V data
            is_piv = 'power' in data or 'power_forward' in data
            
            # Format data for saving
            if bidirectional:
                data_forward, data_reverse, header = self._format_data_for_save(data, is_piv, bidirectional)
                
                np.savetxt(
                    base_path + '_upward_sweep.txt', 
                    data_forward, 
                    delimiter="\t", 
                    header=header, 
                    comments=''
                )
                
                np.savetxt(
                    base_path + '_downward_sweep.txt', 
                    data_reverse, 
                    delimiter="\t", 
                    header=header, 
                    comments=''
                )
            else:
                data_single, header = self._format_data_for_save(data, is_piv, bidirectional)
                
                np.savetxt(
                    base_path + '.txt', 
                    data_single, 
                    delimiter="\t", 
                    header=header, 
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
    measurement_data_point_piv = pyqtSignal(float, float, float, bool)  # P-I-V real-time data points
    save_plot_requested = pyqtSignal(dict, str, bool)  # Emits data, device_name, bidirectional for plot saving
    
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
        self.worker.measurement_data_point_piv.connect(self.measurement_data_point_piv)
        self.worker.save_plot_requested.connect(self.save_plot_requested)
        
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
