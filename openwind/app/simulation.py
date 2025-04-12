# simulation.py
"""
Contains mock or actual acoustic simulation routines, performance evaluation,
and other analysis logic.
"""

import random
from dash import html

def run_mock_simulation(profile_points, material, thickness):
    """
    Demonstration 'simulation' that randomizes or calculates some
    acoustic metrics (f1, cutoff, etc.).
    """
    f1 = round(450 + random.uniform(-30, 30), 2)
    cutoff = round(f1 * 2.2, 2)
    resistance = round(random.uniform(20, 80), 2)

    freq = list(range(100, 2000, 50))
    impedance = [random.uniform(0.5, 1.5) for _ in freq]
    admittance = [1.0 / imp for imp in impedance]

    harmonicity = round(random.uniform(0.7, 0.95), 3)  # 0-1 scale
    brightness = round(random.uniform(0.3, 0.8), 3)    # 0-1 scale

    return {
        "f1": f1,
        "cutoff": cutoff,
        "resistance": resistance,
        "freq": freq,
        "impedance_curve": impedance,
        "admittance_curve": admittance,
        "harmonicity": harmonicity,
        "brightness": brightness
    }


def evaluate_barrel_attributes(sim_results):
    """
    Provides bullet-point "Performance Insights" based on thresholds for
    Resistance, Brightness, and Harmonicity.
    """
    comments = []

    # Resistance commentary
    if sim_results["resistance"] < 30:
        comments.append("Very free-blowing (low resistance). Requires less air pressure but can sacrifice some control.")
    elif sim_results["resistance"] < 70:
        comments.append("Moderate resistance, balancing control and ease of airflow.")
    else:
        comments.append("High resistance—requires stronger air support but may offer greater dynamic control.")

    # Brightness commentary
    if sim_results["brightness"] < 0.4:
        comments.append("Leans toward a darker or warmer timbre.")
    elif sim_results["brightness"] < 0.6:
        comments.append("Moderately bright—somewhere between dark and brilliant.")
    else:
        comments.append("Quite bright—clear and projecting tone.")

    # Harmonicity commentary
    if sim_results["harmonicity"] >= 0.85:
        comments.append("Overtones align well (high harmonicity)—stable, pure core.")
    elif sim_results["harmonicity"] < 0.75:
        comments.append("Lower harmonicity—overtones may be mismatched, potentially more complex or tricky to voice.")

    return html.Ul([html.Li(c) for c in comments])


def evaluate_barrel_performance(sim_results):
    """
    Provides a summary of performance metrics for a given acoustic design.
    Could be used as a convenience wrapper around evaluate_barrel_attributes.
    """
    return html.Div([
        html.H4("Performance Insights"),
        evaluate_barrel_attributes(sim_results)
    ])
def generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution):
    """
    Generate a mock barrel profile based on user inputs.

    :param bore_shape: str, one of ["Cylindrical", "Tapered", "Reverse Tapered", "Parabolic", "Stepped"], etc.
    :param entry_diam: float, diameter at the entry (mm).
    :param exit_diam: float, diameter at the exit (mm).
    :param length_mm: int, total length of the barrel (mm).
    :param resolution: int, distance step in mm for sampling x-positions.
    :return: (x_vals, diam_vals)
        x_vals: list of integer positions from 0..length_mm (inclusive) stepping by resolution
        diam_vals: list of diameters corresponding to each x in x_vals
    """
    # 1) Build a list of x positions from 0..length_mm (step=resolution)
    if resolution < 1:
        resolution = 1
    x_vals = list(range(0, length_mm + 1, resolution))

    # 2) Generate diam_vals by interpolating from entry_diam -> exit_diam
    #    then applying a simple shape adjustment.
    diam_vals = []
    total_steps = len(x_vals) - 1 if len(x_vals) > 1 else 1

    for i, x in enumerate(x_vals):
        # fraction of progress from start to end
        frac = i / total_steps if total_steps > 0 else 0.0

        # base diameter interpolation
        diameter = entry_diam + frac * (exit_diam - entry_diam)

        # shape-based modifications
        if bore_shape == "Tapered":
            # Example: apply a small taper factor
            diameter *= (1.0 + 0.05 * frac)
        elif bore_shape == "Reverse Tapered":
            diameter *= (1.0 + 0.05 * (1 - frac))
        elif bore_shape == "Parabolic":
            diameter *= (1.0 + 0.1 * (frac - 0.5)**2)
        elif bore_shape == "Stepped":
            # Simple step after halfway
            if frac > 0.5:
                diameter *= 1.02
        # "Cylindrical" or default is just the linear interpolation

        diam_vals.append(diameter)

    return x_vals, diam_vals


def mock_thickness_map(x_vals, bore_diam_vals, exterior_shape):
    """
    Returns a mock 'thickness' array, i.e. how thick the wall is at each x,
    based on the exterior shape.

    :param x_vals: list of positions along the barrel axis.
    :param bore_diam_vals: list of interior diameters at each x.
    :param exterior_shape: str describing the outer shape (e.g. "Standard", "Hourglass", etc.)
    :return: list of thicknesses (same length as x_vals).
    """
    if not x_vals or not bore_diam_vals or len(x_vals) != len(bore_diam_vals):
        return []

    thickness_vals = []
    length = x_vals[-1] - x_vals[0]

    for i, x in enumerate(x_vals):
        outer_factor = 1.0
        frac = 0.0 if length == 0 else (x / length)

        # Example modifications to "outer_factor" based on shape:
        if exterior_shape == "Standard":
            outer_factor = 1.05
        elif exterior_shape == "Hourglass (waist tapered)":
            # narrower near midpoint
            dist_from_center = abs(frac - 0.5)
            outer_factor = 1.1 - 0.2 * dist_from_center
        elif exterior_shape == "Reverse Taper (bulged center)":
            # bulge near the center
            outer_factor = 1.0 + 0.15 * (1 - (frac - 0.5)**2)
        elif exterior_shape == "Bell-like Flare (tuned)":
            outer_factor = 1.0 + 0.25 * frac
        elif exterior_shape == "User-Defined":
            # just a small random example
            outer_factor = 1.0 + 0.05 * frac

        # outer diameter
        outer_diam = bore_diam_vals[i] * outer_factor
        # thickness is difference between outer and inner diameters, halved
        thickness = (outer_diam - bore_diam_vals[i]) / 2.0

        thickness_vals.append(thickness)

    return thickness_vals


def run_real_simulation(bore_shape, entry_diam, exit_diam, length_mm, resolution, material, thickness):
    """
    Placeholder for a more advanced or 'real' simulation. In an actual app,
    you might do finite element analysis or a wave propagation model.

    :param bore_shape: str, shape of the bore.
    :param entry_diam: float, diameter at the entry.
    :param exit_diam: float, diameter at the exit.
    :param length_mm: int, total length of the barrel (mm).
    :param resolution: int, distance step or number of segments for discretization.
    :param material: str, e.g. "African Blackwood" or "Composite"
    :param thickness: float or list of thicknesses, representing the wall thickness at each segment.
    :return: dictionary of simulation results, e.g.:
        {
          "f1": 430.0,
          "cutoff": 950.0,
          "impedances": [...],
          ...
        }
    """

    # 1) create a geometry mesh or discretized model from the inputs
    # 2) run a wave simulation or an acoustic model
    # 3) produce relevant output metrics

    # For now, we do a mock result
    # (In real usage, you might call a Python library like openwind or a custom solver.)
    import random

    f1 = round(440 + random.uniform(-20, 20), 2)
    cutoff = round(f1 * 2.1, 2)
    # pretend we have a short list of frequencies
    freq = list(range(200, 2000, 100))
    # random impedances
    impedances = [random.uniform(0.5, 2.0) for _ in freq]

    # We'll also incorporate 'material' or 'thickness' in some small factor
    mat_factor = 1.0
    if material == "African Blackwood":
        mat_factor = 1.05
    elif material == "Hard Rubber":
        mat_factor = 0.95

    f1 *= mat_factor
    cutoff *= mat_factor

    # Adjust the impedances to reflect thickness in some simplistic way
    thickness_factor = (thickness if isinstance(thickness, (int, float)) else 1.0)
    impedances = [z * (1 + 0.01 * thickness_factor) for z in impedances]

    results = {
        "f1": f1,
        "cutoff": cutoff,
        "freq": freq,
        "impedances": impedances,
        "thickness_factor": thickness_factor,
        "material_factor": mat_factor
    }
    return results


def evaluate_real_barrel_performance(sim_results):
    """
    Given the results of run_real_simulation, interpret them and return
    a short textual or structured performance summary.

    :param sim_results: dict, presumably includes "f1", "cutoff", "impedances", etc.
    :return: str or dict describing performance
    """
    if not sim_results:
        return "No simulation results to evaluate."

    f1 = sim_results.get("f1", 0)
    cutoff = sim_results.get("cutoff", 0)
    freq = sim_results.get("freq", [])
    impedances = sim_results.get("impedances", [])

    # Just do a simplistic evaluation
    summary = []
    summary.append(f"First resonance (f₁): {f1:.2f} Hz")
    summary.append(f"Cutoff frequency: {cutoff:.2f} Hz")
    summary.append(f"Measured over {len(freq)} frequency points.")
    summary.append(f"Average impedance: {sum(impedances)/len(impedances):.2f}" if impedances else "No impedances found.")

    return "\n".join(summary)


