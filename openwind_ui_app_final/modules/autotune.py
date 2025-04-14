
import numpy as np
import pandas as pd
from .openwind_adapter import run_impedance_simulation

def autotune_bore(bore_df, target_freq, temperature, material_props, freq_range, max_iter=10):
    entry_range = np.linspace(12.5, 15.0, max_iter)
    exit_range = np.linspace(12.5, 15.0, max_iter)
    best_score = -np.inf
    best_bore = None
    best_result = None

    for entry_d in entry_range:
        for exit_d in exit_range:
            opt_x = bore_df["position"]
            opt_y = np.linspace(entry_d / 1000, exit_d / 1000, len(opt_x))
            test_bore = pd.DataFrame({"position": opt_x, "diameter": opt_y})
            result = run_impedance_simulation(test_bore, temperature, material_props, freq_range)
            f = result["frequency"]
            mag = result["magnitude"]
            idx = np.argmin(np.abs(f - target_freq))
            peak_value = mag[idx]
            if peak_value > best_score:
                best_score = peak_value
                best_bore = test_bore
                best_result = result
    return best_bore, best_result
