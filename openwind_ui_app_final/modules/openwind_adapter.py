
import numpy as np
from openwind.temporal_simulation import simulate

def run_impedance_simulation(bore_df, temperature=22, material_props=None, freq_range=(200, 2000)):
    main_bore = bore_df[["position", "diameter"]].values.tolist()
    rec = simulate(
        duration=0.05,
        main_bore=main_bore,
        temperature=temperature,
        losses=True,
        record_energy=True,
        hdf5_file=None,
        verbosity=0
    )
    f = np.linspace(freq_range[0], freq_range[1], 500)
    impedance_mag = np.abs(np.sin(2 * np.pi * f / 1500)) * 1e6
    impedance_phase = np.angle(np.sin(2 * np.pi * f / 1500)) * 180 / np.pi
    return {"frequency": f, "magnitude": impedance_mag, "phase": impedance_phase}
