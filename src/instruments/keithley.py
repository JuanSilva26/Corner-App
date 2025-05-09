"""
Keithley instrument interface for the Measurement App.

This module provides classes for communicating with Keithley source meters.
"""

import time
import pyvisa as visa
import numpy as np


class KeithleyError(Exception):
    """Exception raised for errors in the Keithley instrument communication."""
    pass


class KeithleyInstrument:
    """Base class for Keithley source meter instruments."""
    
    def __init__(self):
        self.instrument = None
        self.connected = False
        self.resource_manager = None
        self.resource_name = None
    
    def connect(self, resource_name):
        """Connect to the instrument."""
        try:
            self.resource_manager = visa.ResourceManager()
            self.instrument = self.resource_manager.open_resource(resource_name)
            self.connected = True
            self.resource_name = resource_name
            return True
        except Exception as e:
            self.connected = False
            raise KeithleyError(f"Failed to connect to {resource_name}: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the instrument."""
        if self.instrument:
            try:
                self.instrument.close()
                self.connected = False
                return True
            except Exception as e:
                raise KeithleyError(f"Failed to disconnect: {str(e)}")
        return False
    
    def write(self, command):
        """Send a command to the instrument."""
        if not self.connected:
            raise KeithleyError("Not connected to any instrument")
        
        try:
            self.instrument.write(command)
        except Exception as e:
            raise KeithleyError(f"Failed to write command: {str(e)}")
    
    def query(self, command):
        """Send a query to the instrument and return the response."""
        if not self.connected:
            raise KeithleyError("Not connected to any instrument")
        
        try:
            return self.instrument.query(command)
        except Exception as e:
            raise KeithleyError(f"Failed to query: {str(e)}")
    
    def is_connected(self):
        """Return the connection status."""
        return self.connected


class Keithley2400(KeithleyInstrument):
    """Interface for Keithley 2400/2450 SourceMeter."""
    
    def __init__(self):
        super().__init__()
    
    def setup_for_iv_sweep(self, current_compliance=0.01):
        """
        Set up the instrument for I-V sweep measurements.
        
        Args:
            current_compliance: Compliance current in Amps
        """
        if not self.connected:
            raise KeithleyError("Not connected to any instrument")
        
        try:
            # Reset the instrument to default settings
            self.write("*RST")
            time.sleep(0.5)
            
            # Set up as voltage source
            self.write(":SOUR:FUNC:MODE VOLT")
            self.write(f":SENS:CURR:PROT:LEV {current_compliance}")
            self.write(":SENS:CURR:RANGE:AUTO 1")  # Auto current range
            
            # Turn output on
            self.write(":OUTP ON")
            
            return True
        except Exception as e:
            raise KeithleyError(f"Failed to set up for I-V sweep: {str(e)}")
    
    def perform_iv_sweep(self, start_voltage, stop_voltage, num_points, bidirectional=False):
        """
        Perform an I-V sweep and return the measured data.
        
        Args:
            start_voltage: Starting voltage in Volts
            stop_voltage: Ending voltage in Volts
            num_points: Number of measurement points
            bidirectional: Whether to perform bidirectional sweep
            
        Returns:
            Dictionary with voltage and current arrays
        """
        if not self.connected:
            raise KeithleyError("Not connected to any instrument")
            
        try:
            # Create voltage points array
            upward_points = np.linspace(start_voltage, stop_voltage, num=num_points, endpoint=True)
            
            if bidirectional:
                # Downward sweep points (excluding first point to avoid duplication)
                downward_points = np.linspace(stop_voltage, start_voltage, num=num_points, endpoint=True)[1:]
                sweep_points = np.concatenate((upward_points, downward_points))
            else:
                sweep_points = upward_points
                
            # Arrays to store results
            voltage_measured = []
            current_measured = []
            
            # Perform the sweep
            for voltage in sweep_points:
                # Set voltage
                self.write(f":SOUR:VOLT {voltage}")
                time.sleep(0.0001)  # Short delay
                
                # Read values
                data = self.query(":READ?")
                values = data.split(',')
                
                # Extract and convert values
                # The first value is current, second is voltage
                current = float(values[0].replace('A', '')) * 1E3  # Convert to mA
                voltage_read = float(values[1].replace('V', ''))
                
                # Store values
                current_measured.append(current)
                voltage_measured.append(voltage_read)
            
            # Turn output off
            self.write(":OUTP OFF")
            
            # Separate data for bidirectional sweep
            if bidirectional:
                voltage_forward = voltage_measured[:num_points]
                current_forward = current_measured[:num_points]
                voltage_reverse = voltage_measured[num_points-1:]
                current_reverse = current_measured[num_points-1:]
                
                return {
                    'voltage_forward': voltage_forward,
                    'current_forward': current_forward,
                    'voltage_reverse': voltage_reverse,
                    'current_reverse': current_reverse
                }
            else:
                return {
                    'voltage': voltage_measured,
                    'current': current_measured
                }
                
        except Exception as e:
            # Ensure output is off in case of error
            try:
                self.write(":OUTP OFF")
            except:
                pass
            raise KeithleyError(f"Failed during I-V sweep: {str(e)}")
    
    def cleanup(self):
        """Clean up after measurements."""
        if self.connected:
            try:
                # Set output off
                self.write(":OUTP OFF")
                
                # Switch to current source mode
                self.write(":SOUR:FUNC:MODE CURR")
                
                # Return to local control
                self.write("SYSTEM:KEY 23")
            except Exception as e:
                raise KeithleyError(f"Failed during cleanup: {str(e)}")
                
    def get_instrument_info(self):
        """Get instrument identification information."""
        if not self.connected:
            raise KeithleyError("Not connected to any instrument")
            
        try:
            return self.query("*IDN?")
        except Exception as e:
            raise KeithleyError(f"Failed to get instrument info: {str(e)}")
            

# Factory function to create the appropriate Keithley instrument
def create_keithley_instrument(instrument_type="Keithley 2400/2450"):
    """Create and return a Keithley instrument of the specified type."""
    if instrument_type == "Keithley 2400/2450":
        return Keithley2400()
    else:
        raise ValueError(f"Unsupported instrument type: {instrument_type}")
