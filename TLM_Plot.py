import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# Make all fonts bigger
plt.rcParams.update({
    "font.size": 16,
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "legend.title_fontsize": 16
})

# Configuration - change this to select which folder(s) to plot
# Options: 'Bottom1', 'Bottom2', 'Bottom3', 'Top1', 'Top2', 'Top3'
# You can specify one or two folders as a list
# Examples:
#   FOLDERS_TO_PLOT = ['Bottom1']              # Plot only Bottom1
#   FOLDERS_TO_PLOT = ['Top1']                 # Plot only Top1
#   FOLDERS_TO_PLOT = ['Bottom1', 'Top1']      # Plot both Bottom1 and Top1
FOLDERS_TO_PLOT = ['Bottom2', 'Top1']

# Root directory
root = "Data/Annealing_Test_1B-2/TLMs"

if not os.path.isdir(root):
    raise FileNotFoundError(f"Folder not found: {root}")

# Verify all selected folders exist
for folder in FOLDERS_TO_PLOT:
    folder_path = os.path.join(root, folder)
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Selected folder not found: {folder_path}")

# Create figure
plt.figure(figsize=(12, 7))

# Color map for different contacts - using a different vibrant palette
cmap = plt.get_cmap("Dark2")
plotted_any = False

# Line styles for different folders (to distinguish between them)
line_styles = ['-', '--', '-.', ':']
markers = ['o', 's', '^', 'D']

# Process each folder
for folder_idx, folder_name in enumerate(FOLDERS_TO_PLOT):
    selected_folder = os.path.join(root, folder_name)
    
    # Find all subdirectories (12, 23, 34, etc.)
    contact_dirs = sorted([d for d in glob.glob(os.path.join(selected_folder, "*")) 
                           if os.path.isdir(d)])
    
    if not contact_dirs:
        print(f"Warning: No subdirectories found in {selected_folder}")
        continue
    
    print(f"\nProcessing {folder_name}:")
    
    # Get line style and marker for this folder
    linestyle = line_styles[folder_idx % len(line_styles)]
    marker = markers[folder_idx % len(markers)]
    
    for idx, contact_dir in enumerate(contact_dirs):
        contact_name = os.path.basename(contact_dir)
        
        # Try to find upward sweep file (for Top folders)
        upward_files = glob.glob(os.path.join(contact_dir, "*_upward_sweep.txt"))
        
        # If no upward sweep, try regular .txt files (for Bottom folders)
        if not upward_files:
            txt_files = glob.glob(os.path.join(contact_dir, "*.txt"))
            if txt_files:
                upward_files = txt_files
        
        if not upward_files:
            print(f"  Warning: No data files found in {contact_dir}")
            continue
        
        # Use the first file found
        fpath = upward_files[0]
        
        try:
            # Read the data file
            df = pd.read_csv(fpath, sep=r"\s+", engine="python")
            
            # Find voltage and current columns
            v_col = next((c for c in df.columns if 'Voltage' in c), df.columns[0])
            i_col = next((c for c in df.columns if 'Current' in c), df.columns[1])
            
            voltage = df[v_col].values
            current = df[i_col].values
            
            # Plot the data
            color = cmap(idx % 10)
            
            # Extract spacing from contact name (first digit * 5 microns)
            spacing_um = int(contact_name[0]) * 5
            
            # Create label with just spacing (no folder name in legend)
            label = f"{spacing_um}μm"
            
            plt.plot(voltage, current, 
                    label=label,
                    color=color,
                    linestyle=linestyle,
                    linewidth=2.0,
                    marker=marker,
                    markersize=3,
                    markevery=10)  # Show marker every 10 points to avoid clutter
            
            plotted_any = True
            print(f"  Plotted: {contact_name} from {os.path.basename(fpath)}")
            
        except Exception as e:
            print(f"  Error reading {fpath}: {e}")
            continue

if not plotted_any:
    print("\nNo data was plotted!")
    plt.close()
else:
    # Styling
    plt.xlabel("Voltage (V)")
    plt.ylabel("Current (mA)")
    
    # Create title based on folders plotted
    if len(FOLDERS_TO_PLOT) == 1:
        title = f"TLM I-V Curves"
    else:
        title = f"TLM I-V Curves"
    
    plt.title(title)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.grid(True, linestyle=":", alpha=0.7)
    
    # Set axis to start at 0
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    
    # Adjust legend - combined with clear titles, positioned on left
    if len(FOLDERS_TO_PLOT) > 1:
        # Clear existing legend if it exists
        if plt.gca().legend_ is not None:
            plt.gca().legend_.remove()
        
        # Create custom legend with proper line styles
        handles, labels = plt.gca().get_legend_handles_labels()
        
        # Split handles and labels by device type
        n_contacts = len(handles) // len(FOLDERS_TO_PLOT)
        handles1, labels1 = handles[:n_contacts], labels[:n_contacts]
        handles2, labels2 = handles[n_contacts:], labels[n_contacts:]
        
        # Create combined legend with proper order and ensure correct line styles
        combined_handles = []
        combined_labels = []
        
        # Add first device type (solid lines) - ensure they're solid
        for i in range(n_contacts):
            handle = handles1[i]
            handle.set_linestyle('-')  # Force solid line
            combined_handles.append(handle)
            combined_labels.append(labels1[i])
        
        # Add second device type (dashed lines) - ensure they're dashed
        for i in range(n_contacts):
            handle = handles2[i]
            handle.set_linestyle('--')  # Force dashed line
            combined_handles.append(handle)
            combined_labels.append(labels2[i])
        
        # Create the legend
        legend = plt.legend(combined_handles, combined_labels, ncol=2, loc='upper left', 
                           frameon=True, fancybox=True, shadow=True, fontsize=10)
        
        # Get legend position for accurate title placement
        legend_bbox = legend.get_window_extent().transformed(plt.gca().transData.inverted())
        
        # Add device type titles exactly above each column
        left_col_x = legend_bbox.x0 + legend_bbox.width * 0.25
        right_col_x = legend_bbox.x0 + legend_bbox.width * 0.75
        title_y = legend_bbox.y1 + 0.02
        
        plt.text(left_col_x, title_y, FOLDERS_TO_PLOT[0], transform=plt.gca().transData, 
                fontsize=11, ha='center', weight='bold', va='bottom',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9, edgecolor='gray'))
        plt.text(right_col_x, title_y, FOLDERS_TO_PLOT[1], transform=plt.gca().transData, 
                fontsize=11, ha='center', weight='bold', va='bottom',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.9, edgecolor='gray'))
    else:
        plt.legend(title="Spacing", loc="best")
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(root, "Plots")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the plot
    output_filename = "TLM_" + "_".join(FOLDERS_TO_PLOT) + "_combined.png"
    output_path = os.path.join(output_dir, output_filename)
    plt.savefig(output_path, dpi=200)
    print(f"\nPlot saved to: {output_path}")
    
    # Display the plot
    plt.show()
