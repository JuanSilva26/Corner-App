import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# make all fonts bigger
plt.rcParams.update({
    "font.size": 16,        # base font size
    "axes.titlesize": 18,   # title font
    "axes.labelsize": 16,   # x and y labels
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 14,
    "legend.title_fontsize": 16
})

root = "Data/Annealing_Test_1B-2"

if not os.path.isdir(root):
    raise FileNotFoundError(f"Folder not found: {root}")

all_device_dirs = [d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)]
folder_re = re.compile(r"^(L_\d+)G_(\d+)(?:_rev)?$")

devices = []
for d in all_device_dirs:
    name = os.path.basename(d)
    m = folder_re.match(name)
    if not m:
        continue
    L_val = m.group(1)
    G_val = m.group(2)
    is_rev = name.endswith("_rev")
    devices.append({"L": L_val, "G": G_val, "dir": d, "rev": is_rev})

by_L = defaultdict(list)
for item in devices:
    by_L[item["L"]].append(item)

output_paths = []

for L_val, items in sorted(by_L.items(), key=lambda x: int(x[0].split("_")[1])):
    items_sorted = sorted(items, key=lambda x: (int(x["G"]), x["rev"]))
    
    plt.figure(figsize=(9, 7))
    seen_labels = set()
    colors = {}
    cmap = plt.get_cmap("tab10")
    color_idx = 0
    
    plotted_any = False
    
    for entry in items_sorted:
        ups = sorted(glob.glob(os.path.join(entry["dir"], "*_upward_sweep.txt")))
        if not ups:
            continue
        fpath = ups[0]
        try:
            df = pd.read_csv(fpath, sep=r"\s+", engine="python")
        except Exception:
            continue
        
        v_col = next((c for c in df.columns if 'Voltage' in c), df.columns[0])
        i_col = next((c for c in df.columns if 'Current' in c), df.columns[1])
        
        x, y = df[v_col].values, df[i_col].values
        if entry["rev"]:
            x, y = -x, -y
        
        base_label = f"G_{entry['G']}"
        
        if base_label not in colors:
            colors[base_label] = cmap(color_idx % 10)
            color_idx += 1
        
        label = base_label if base_label not in seen_labels else "_" + base_label
        if base_label not in seen_labels:
            seen_labels.add(base_label)
        
        plt.plot(
            x, y,
            linestyle="--" if entry["rev"] else "-",
            label=label,
            color=colors[base_label],
            linewidth=2.0
        )
        plotted_any = True
    
    if not plotted_any:
        plt.close()
        continue
    
    plt.xlabel("Voltage (V)")
    plt.ylabel("Current (mA)")
    plt.title(f"IV {L_val}")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.grid(True, linestyle=":")
    plt.legend(title="Device", loc="best")
    out_path = f"Data/Annealing_Test_1B-2/Plots/IV_{L_val}_combined.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    output_paths.append(out_path)

print(output_paths)
