"""
Thorlabs PM100D power meter interface for the Measurement App.

This module provides classes for communicating with Thorlabs PM100D power meters.
"""

import time
from pyThorlabsPM100x.driver import ThorlabsPM100x


class PM100DError(Exception):
    """Exception raised for errors in the PM100D instrument communication."""
    pass


class PM100DInstrument:
    """Interface for Thorlabs PM100D power meter."""
    
    def __init__(self):
        self.instrument = None
        self.connected = False
        self.device_address = None
    
    def connect(self):
        """Connect to the PM100D instrument."""
        try:
            self.instrument = ThorlabsPM100x()
            devices = self.instrument.list_devices()
            
            if not devices:
                raise PM100DError("No PM100D found. If you recently used Thorlabs OPM, use the Power Meter Driver Switcher to set 'PM100D NI-VISA' mode.")
            
            # Connect to the first available device
            self.device_address = devices[0][0]
            self.instrument.connect_device(device_addr=self.device_address)
            self.connected = True
            return True
            
        except Exception as e:
            self.connected = False
            raise PM100DError(f"Failed to connect to PM100D: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the instrument."""
        if self.instrument and self.connected:
            try:
                self.instrument.disconnect_device()
                self.connected = False
                return True
            except Exception as e:
                raise PM100DError(f"Failed to disconnect: {str(e)}")
        return False
    
    def configure(self, wavelength=633, auto_range=True, manual_range=None):
        """
        Configure the PM100D for measurements.
        
        Args:
            wavelength: Wavelength in nanometers
            auto_range: Whether to use auto range
            manual_range: Manual range in Watts (if auto_range=False)
        """
        if not self.connected:
            raise PM100DError("Not connected to any instrument")
        
        try:
            if not self.instrument:
                raise PM100DError("Not connected to any instrument")
                
            # Set wavelength
            self.instrument.wavelength = wavelength
            
            # Set range mode
            if auto_range:
                self.instrument.auto_power_range = True
            else:
                self.instrument.auto_power_range = False
                if manual_range is not None:
                    self.instrument.power_range = float(manual_range)
                else:
                    raise PM100DError("Manual range must be specified when auto_range=False")
            
            return True
        except Exception as e:
            raise PM100DError(f"Failed to configure PM100D: {str(e)}")
    
    def read_power(self):
        """
        Read power measurement.
        
        Returns:
            Tuple of (power_in_watts, unit)
        """
        if not self.connected:
            raise PM100DError("Not connected to any instrument")
        
        try:
            if not self.instrument:
                raise PM100DError("Not connected to any instrument")
                
            power, unit = self.instrument.power
            return float(power), unit
        except Exception as e:
            raise PM100DError(f"Failed to read power: {str(e)}")
    
    def is_connected(self):
        """Return the connection status."""
        return self.connected
    
    def get_instrument_info(self):
        """Get instrument identification information."""
        if not self.connected:
            raise PM100DError("Not connected to any instrument")
        
        try:
            if not self.instrument:
                raise PM100DError("Not connected to any instrument")
                
            # Get device info from the connected device
            devices = self.instrument.list_devices()
            if devices and self.device_address:
                for device in devices:
                    if device[0] == self.device_address:
                        return f"Thorlabs PM100D - {device[1]} - {device[2]}"
            return "Thorlabs PM100D - Connected"
        except Exception as e:
            raise PM100DError(f"Failed to get instrument info: {str(e)}")
    
    def cleanup(self):
        """Clean up after measurements."""
        if self.connected:
            try:
                # PM100D doesn't need special cleanup, just ensure it's ready
                pass
            except Exception as e:
                raise PM100DError(f"Failed during cleanup: {str(e)}")


# Factory function to create PM100D instrument
def create_pm100d_instrument():
    """Create and return a PM100D instrument."""
    return PM100DInstrument()
