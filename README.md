# 🔬 Measurement App - Advanced I-V & P-I-V Analysis

A professional PyQt6-based application for electrical characterization of semiconductor devices, featuring advanced I-V measurements, P-I-V analysis, and comprehensive data analysis tools.

## ✨ Features

### 🔌 **Instrument Control**
- **Keithley 2400/2450 SourceMeter** integration via PyVISA
- **Thorlabs PM100D Power Meter** support for optical power measurements
- **Real-time device detection** and connection management
- **Multi-device support** with automatic resource discovery

### 📊 **Measurement Capabilities**
- **I-V Sweep Measurements** - Standard current-voltage characterization
- **P-I-V Measurements** - Combined electrical and optical power analysis
- **Bidirectional Sweeps** - Forward and reverse bias measurements
- **Real-time Plotting** - Live data visualization during measurements
- **Customizable Parameters** - Voltage ranges, step sizes, compliance limits

### 📈 **Advanced Analysis Tools**
- **TLM Analysis** - Transmission Line Method for contact resistance extraction
- **I-V Curve Fitting** - Schulman model fitting for RTD characterization
- **Interactive Plotting** - Zoom, pan, annotations, and log scales
- **Statistical Analysis** - R² values, fit quality assessment
- **Data Export** - CSV, Excel, and publication-ready formats

### 🎨 **Professional Interface**
- **Dark Theme** - Modern, professional appearance
- **Responsive Layout** - Adaptive to different screen sizes
- **Real-time Updates** - Live data streaming and visualization
- **Intuitive Controls** - User-friendly parameter configuration
- **Status Monitoring** - Clear feedback on measurement progress

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- PyVISA and VISA drivers for instrument communication
- PyQt6 for the graphical interface

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/measurement-app.git
   cd measurement-app
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python src/main.py
   ```

## 📋 Requirements

```
PyQt6>=6.4.0
pyvisa>=1.12.0
numpy>=1.21.0
scipy>=1.9.0
matplotlib>=3.5.0
pandas>=1.4.0
pyThorlabsPM100x>=1.0.0
```

## 🔧 Usage

### 1. **Connection Setup**
- Connect your Keithley SourceMeter via USB/GPIB
- Connect Thorlabs PM100D power meter (for P-I-V measurements)
- Click "Refresh Devices" to detect connected instruments
- Click "Connect" to establish communication

### 2. **I-V Measurements**
- Select "I-V Sweep" measurement mode
- Configure voltage range and step size
- Set compliance limits and measurement parameters
- Click "Start" to begin measurement
- View real-time plots and data

### 3. **P-I-V Measurements**
- Select "P-I-V Measurement" mode
- Configure Keithley parameters as above
- Set PM100D wavelength and power range
- Enable "Add PM100D Power Meter" option
- Start measurement for combined electrical/optical analysis

### 4. **Data Analysis**
- **TLM Analysis**: Load multiple I-V files with different contact spacings
- **I-V Fitting**: Fit data to Schulman model for RTD characterization
- **Interactive Plots**: Zoom, annotate, and analyze data points
- **Export Results**: Save data in various formats

## 🎯 Key Features

### **Interactive Plotting**
- **Mouse wheel zoom** - Scroll to zoom in/out
- **Click annotations** - Left-click to add data point labels
- **Log scales** - Toggle linear/logarithmic axes
- **Reset view** - Return to full data view
- **Clear annotations** - Remove all plot labels

### **Advanced Analysis**
- **Quality Assessment** - Automatic fit quality evaluation
- **Parameter Validation** - Check for physically reasonable values
- **Error Handling** - Comprehensive error detection and reporting
- **Real-time Updates** - Live parameter adjustment and plotting

### **Professional Output**
- **Publication-ready plots** - High-quality figure generation
- **Comprehensive data export** - Multiple format support
- **Statistical metrics** - R² values, confidence intervals
- **Customizable styling** - Professional appearance

## 📁 Project Structure

```
measurement-app/
├── src/
│   ├── main.py                 # Application entry point
│   ├── instruments/            # Instrument drivers
│   │   ├── keithley.py        # Keithley SourceMeter interface
│   │   └── pm100d.py          # Thorlabs PM100D interface
│   ├── measurement/           # Measurement logic
│   │   └── iv_sweep.py        # I-V and P-I-V sweep implementation
│   └── ui/                    # User interface components
│       ├── main_window.py     # Main application window
│       ├── theme.py           # UI theming and styling
│       └── components/        # UI component modules
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## 🔬 Supported Instruments

- **Keithley 2400 SourceMeter** - Primary I-V measurement device
- **Keithley 2450 SourceMeter** - Advanced source-measure unit
- **Thorlabs PM100D** - Optical power meter for P-I-V analysis
- **Generic VISA devices** - Any SCPI-compatible instrument

## 📊 Measurement Modes

### **I-V Sweep**
- Standard current-voltage characterization
- Configurable voltage ranges and step sizes
- Bidirectional sweep support
- Real-time data visualization

### **P-I-V Measurement**
- Combined electrical and optical analysis
- Simultaneous voltage, current, and power measurement
- Dual-plot visualization (I-V and P-V curves)
- Wavelength and power range configuration

## 🛠️ Development

### **Code Structure**
- **Modular design** - Separate components for instruments, measurements, and UI
- **Signal-slot architecture** - PyQt6-based event handling
- **Theme system** - Centralized styling and appearance
- **Error handling** - Comprehensive exception management

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🤝 Support

For questions, issues, or feature requests, please:
- Open an issue on GitHub
- Check the documentation
- Review the code comments

## 🎉 Acknowledgments

- **PyQt6** - Modern Python GUI framework
- **PyVISA** - Instrument communication library
- **Matplotlib** - Scientific plotting capabilities
- **SciPy** - Scientific computing tools

---

**Built with ❤️ for the semiconductor research community**
