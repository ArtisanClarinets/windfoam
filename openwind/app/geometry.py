# geometry.py
"""
Contains helper functions for clarinet geometry generation,
bore profile creation, etc.
"""

import math

def generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution):
    """
    Returns a list of (x, diameter) points representing a simplified 2D cross-section
    of the barrel profile, for demonstration purposes.
    """
    num_points = {"Low": 10, "Medium": 30, "High": 60}.get(resolution, 30)
    if num_points < 2:
        num_points = 2

    x_vals = [i * (length_mm / (num_points - 1)) for i in range(num_points)]
    diam_vals = []

    for i in range(num_points):
        fraction = i / (num_points - 1)
        diameter = entry_diam + fraction * (exit_diam - entry_diam)

        if bore_shape == "Tapered":
            diameter *= (1.0 + 0.1 * fraction)
        elif bore_shape == "Reverse Tapered":
            diameter *= (1.0 + 0.1 * (1 - fraction))
        elif bore_shape == "Parabolic":
            # small parabolic shape as example
            diameter *= (1.0 + 0.15 * (fraction - 0.5)**2)
        elif bore_shape == "Stepped":
            if fraction > 0.5:
                diameter *= 1.05

        # "Cylindrical" is default linear interpolation
        diam_vals.append(diameter)

    return x_vals, diam_vals


def mock_thickness_map(x_vals, bore_diam_vals, exterior_shape):
    """
    Returns a 'thickness' array for each x in the barrel, mocking an outer shape.
    """
    thickness_vals = []
    if not x_vals:
        return thickness_vals

    length = x_vals[-1] - x_vals[0]
    for i, x in enumerate(x_vals):
        outer_factor = 1.0
        if exterior_shape == "Hourglass (waist tapered)":
            midpoint = 0.5 * length
            dist_from_center = abs(x - midpoint)
            outer_factor = 1.1 - 0.0005 * dist_from_center
        elif exterior_shape == "Bell-like Flare (tuned for resonance)":
            fraction = i / (len(x_vals) - 1)
            outer_factor = 1.0 + 0.2 * fraction
        elif exterior_shape == "Reverse Taper (bulged center)":
            fraction = i / (len(x_vals) - 1)
            outer_factor = 1.0 + 0.25 * (1 - (fraction - 0.5)**2)
        elif exterior_shape == "Standard (parallel exterior)":
            outer_factor = 1.05
        elif exterior_shape == "User-Defined":
            fraction = i / (len(x_vals) - 1)
            outer_factor = 1.0 + 0.05 * fraction

        outer_diam = bore_diam_vals[i] * outer_factor
        thickness = (outer_diam - bore_diam_vals[i]) / 2.0
        thickness_vals.append(thickness)

    return thickness_vals


def build_unfolded_bore_outline(bore_data):
    """
    Given an array of bore segments, produce two lists of (x, y):
     - top_edge: from left to right, y = + (diameter/2)
     - bot_edge: from right to left, y = - (diameter/2)

    We'll return (outline_x, outline_y) which you can feed to Plotly
    as a single polygon shape or as scatter lines.

    If the user wants a more detailed curve for each segment, they'd
    do their own interpolation. This method uses only start/end as a quick approach.
    """
    if not bore_data:
        return [], []

    # Sort segments by start_pos
    sorted_segments = sorted(bore_data, key=lambda seg: seg["start_pos"])

    # Build top edge (left-to-right)
    top_edge = []
    for seg in sorted_segments:
        x0 = seg.get("start_pos", 0)
        x1 = seg.get("end_pos", 0)
        d0 = seg.get("start_dia", 0)
        d1 = seg.get("end_dia", 0)

        top_edge.append((x0, d0 / 2.0))
        top_edge.append((x1, d1 / 2.0))

    # Build bottom edge (right-to-left)
    bot_edge = []
    for seg in reversed(sorted_segments):
        x0 = seg.get("start_pos", 0)
        x1 = seg.get("end_pos", 0)
        d0 = seg.get("start_dia", 0)
        d1 = seg.get("end_dia", 0)

        bot_edge.append((x1, -(d1 / 2.0)))
        bot_edge.append((x0, -(d0 / 2.0)))

    outline_x = [pt[0] for pt in top_edge] + [pt[0] for pt in bot_edge]
    outline_y = [pt[1] for pt in top_edge] + [pt[1] for pt in bot_edge]

    return outline_x, outline_y


def build_unfolded_bore_fill(bore_data):
    """
    Return a list of top-edge points (x, y) for a partial fill approach.
    For a fully-filled polygon, see build_unfolded_bore_outline.
    """
    if not bore_data:
        return []

    sorted_segments = sorted(bore_data, key=lambda seg: seg["start_pos"])

    top_edge = []
    for seg in sorted_segments:
        x0 = seg.get("start_pos", 0)
        x1 = seg.get("end_pos", 0)
        d0 = seg.get("start_dia", 0)
        d1 = seg.get("end_dia", 0)

        # We'll assume linear from start_dia -> end_dia
        top_edge.append((x0, d0 / 2.0))
        top_edge.append((x1, d1 / 2.0))

    return top_edge


def build_unfolded_holes(holes_data):
    """
    For each hole, let's produce a top/bottom edge or a simple line from
    hole center to some negative offset. This is purely illustrative.

    This function returns a list of points. You can adapt how you want
    to represent the hole geometry in your final plot.
    """
    results = []
    for h in holes_data:
        pos = h.get("position", 0)
        diam = h.get("diameter", 0)
        # Example: two points (top -> bottom)
        results.append((pos, 0))         # top = 0, if we treat center as y=0
        results.append((pos, -diam))     # bottom = -diam
    return results


def build_unfolded_fingering(fingering_data):
    """
    For each fingering item, produce a list of points to illustrate it.
    Many real fingering structures won't have 'position' or 'diameter'.
    So this is a placeholder for your custom logic.

    If your fingering_data doesn't have 'position' or 'diameter', you
    may want to revise or remove references below.
    """
    results = []
    for f in fingering_data:
        # For safety, use .get and default to 0
        pos = f.get("position", 0)
        diam = f.get("diameter", 0)
        results.append((pos, 0))
        results.append((pos, -diam))
    return results


def build_unfolded_chimney(chimney_data):
    """
    Similar placeholder for 'chimney' geometry. You can define the
    shape for each chimney based on its data structure.
    """
    results = []
    for c in chimney_data:
        pos = c.get("position", 0)
        diam = c.get("diameter", 0)
        results.append((pos, 0))
        results.append((pos, -diam))
    return results


def build_unfolded_tube(tube_data):
    """
    Another placeholder for a separate tube or extension.
    Again, references position/diameter as an example.
    """
    results = []
    for t in tube_data:
        pos = t.get("position", 0)
        diam = t.get("diameter", 0)
        results.append((pos, 0))
        results.append((pos, -diam))
    return results
