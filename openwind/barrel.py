import json
import random
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objects as go


###############################################################################
# Mock / Helper Functions (same as before)
###############################################################################
def generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution):
    """
    Returns a list of (x, diameter) points representing a simplified 2D cross-section
    of the bore profile, for demonstration purposes.
    """
    num_points = {"Low": 10, "Medium": 30, "High": 60}.get(resolution, 30)
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
    length = x_vals[-1] - x_vals[0] if x_vals else 0

    for i, x in enumerate(x_vals):
        outer_factor = 1.0
        if exterior_shape == "Hourglass (waist tapered)":
            midpoint = 0.5 * length
            dist_from_center = abs(x - midpoint)
            outer_factor = 1.1 - 0.0005 * dist_from_center
        elif exterior_shape == "Bell-like Flare (tuned for resonance)":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.2 * fraction
        elif exterior_shape == "Reverse Taper (bulged center)":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.25 * (1 - (fraction - 0.5)**2)
        elif exterior_shape == "Standard (parallel exterior)":
            outer_factor = 1.05
        elif exterior_shape == "User-Defined":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.05 * fraction

        outer_diam = bore_diam_vals[i] * outer_factor
        thickness = (outer_diam - bore_diam_vals[i]) / 2.0
        thickness_vals.append(thickness)
    return thickness_vals

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

    if sim_results["resistance"] < 30:
        comments.append("Very free-blowing (low resistance). Requires less air pressure but can sacrifice some control.")
    elif sim_results["resistance"] < 70:
        comments.append("Moderate resistance, balancing control and ease of airflow.")
    else:
        comments.append("High resistance—requires stronger air support but may offer greater dynamic control.")

    if sim_results["brightness"] < 0.4:
        comments.append("Leans toward a darker or warmer timbre.")
    elif sim_results["brightness"] < 0.6:
        comments.append("Moderately bright—somewhere between dark and brilliant.")
    else:
        comments.append("Quite bright—clear and projecting tone.")

    if sim_results["harmonicity"] >= 0.85:
        comments.append("Overtones align well (high harmonicity)—stable, pure core.")
    elif sim_results["harmonicity"] < 0.75:
        comments.append("Lower harmonicity—overtones may be slightly mismatched, potentially more complex or tricky to voice.")

    return html.Ul([html.Li(c) for c in comments])

###############################################################################
# Dash App Setup
###############################################################################
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Clarinet Barrel Designer"

bore_shape_options = [
    "Cylindrical", "Tapered", "Reverse Tapered", "Parabolic", "Stepped"
]
exterior_shape_options = [
    "Standard (parallel exterior)",
    "Hourglass (waist tapered)",
    "Reverse Taper (bulged center)",
    "Bell-like Flare (tuned for resonance)",
    "User-Defined"
]
resolution_options = ["Low", "Medium", "High"]
material_options = [
    "African Blackwood", "Mopane", "Cocobolo", "Hard Rubber", "Composite"
]

stored_designs = {}

###############################################################################
# Layout
###############################################################################
app.layout = dbc.Container([
    html.H1("Clarinet Barrel Designer & Simulation Wizard", className="mt-3"),
    html.Hr(),

    dbc.Row([
        # Left Column
        dbc.Col([
            # DESIGN PARAMETERS
            dbc.Card([
                dbc.CardBody([
                    html.H4("Design Parameters", className="card-title"),

                    dbc.Label("Bore Shape"),
                    dcc.Dropdown(
                        id="bore-shape-dd",
                        options=[{"label": bs, "value": bs} for bs in bore_shape_options],
                        value="Cylindrical"
                    ),

                    dbc.Label("Exterior Shape", className="mt-3"),
                    dcc.Dropdown(
                        id="exterior-shape-dd",
                        options=[{"label": ex, "value": ex} for ex in exterior_shape_options],
                        value="Standard (parallel exterior)"
                    ),

                    dbc.Label("Entry Diameter (mm)", className="mt-3"),
                    dbc.Input(
                        id="entry-diam-input",
                        type="number",
                        placeholder="e.g. 14.8",
                        value=14.8,
                        step=0.1
                    ),

                    dbc.Label("Exit Diameter (mm)", className="mt-3"),
                    dbc.Input(
                        id="exit-diam-input",
                        type="number",
                        placeholder="e.g. 15.2",
                        value=15.2,
                        step=0.1
                    ),

                    dbc.Label("Barrel Length (mm)", className="mt-3"),
                    dbc.Input(
                        id="barrel-length-input",
                        type="number",
                        placeholder="e.g. 66",
                        value=66,
                        step=0.5
                    ),

                    dbc.Label("Segment Resolution", className="mt-3"),
                    dcc.Dropdown(
                        id="resolution-dd",
                        options=[{"label": r, "value": r} for r in resolution_options],
                        value="Medium"
                    ),

                    dbc.Label("Material (Planned)", className="mt-3"),
                    dcc.Dropdown(
                        id="material-dd",
                        options=[{"label": m, "value": m} for m in material_options],
                        value="African Blackwood"
                    ),

                    dbc.Checklist(
                        options=[{"label": "Educational Overlay (Tooltips)", "value": 1}],
                        value=[1],
                        id="educational-mode-check",
                        switch=True,
                        className="my-3"
                    ),

                    dbc.Button(
                        "Run Simulation",
                        id="run-simulation-btn",
                        color="primary",
                        className="mt-3",
                        n_clicks=0
                    ),
                ])
            ], className="mb-3"),

            # EXPORT & COMPARE
            dbc.Card([
                dbc.CardBody([
                    html.H4("Export & Compare", className="card-title"),
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("Design Name"),
                                dbc.Input(id="save-design-name", placeholder="MyBarrel1", value="")
                            ]),
                            dbc.Button("Save Design", id="save-design-btn", color="secondary", className="mt-2"),
                        ])
                    ]),

                    dbc.Button("Load Design", id="load-design-btn", color="info", className="mt-3", n_clicks=0),
                    dcc.Upload(
                        id="upload-json-design",
                        children=html.Div(["Drag & Drop or Click to Select JSON"]),
                        style={
                            "width": "100%",
                            "height": "60px",
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "marginTop": "10px",
                        },
                        multiple=False
                    ),

                    html.Hr(),
                    html.Div([
                        dbc.Button("Export as JSON", id="export-json-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as CSV", id="export-csv-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as STL", id="export-stl-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as PDF", id="export-pdf-btn", color="success", className="me-2 mt-2"),
                    ]),

                    html.Hr(),
                    dbc.Button("Enable Comparison Mode", id="compare-mode-btn", color="warning", className="mt-2"),
                    html.Div(id="comparison-mode-section", style={"display": "none"}),
                ])
            ]),
        ], width=3),

        # Right Column
        dbc.Col([
            # CROSS-SECTION CARD
            dbc.Card([
                dbc.CardBody([
                    html.H4("Barrel Cross-Section & Wall Thickness", className="card-title"),
                    dcc.Graph(id="bore-profile-graph"),
                    html.Div(id="thickness-notes", className="text-muted", style={"fontSize": "0.9em"})
                ])
            ], className="mb-3"),

            # ACOUSTIC SIM RESULTS
            dbc.Card([
                dbc.CardBody([
                    html.H4("Acoustic Simulation Results", className="card-title"),
                    html.Div(id="simulation-stats", className="mb-3"),

                    html.Div(
                        "Impedance vs Frequency shows how much the barrel resists airflow at various pitches. "
                        "Higher impedance often means stronger resonance at those frequencies.",
                        className="text-muted",
                        style={"fontSize": "0.9em", "marginBottom": "6px"}
                    ),
                    dcc.Graph(id="impedance-graph"),

                    html.Div(
                        "Admittance vs Frequency is effectively the inverse of impedance—higher admittance means "
                        "the barrel allows airflow more easily. This can translate to an ‘open’ feel.",
                        className="text-muted",
                        style={"fontSize": "0.9em", "marginTop": "12px", "marginBottom": "6px"}
                    ),
                    dcc.Graph(id="admittance-graph"),
                ])
            ], className="mb-3"),

            # NEW CARD: CLARINET GEOMETRY
            dbc.Card([
                dbc.CardBody([
                    html.H4("Clarinet Geometry", className="card-title"),

                    # We'll create 3 DataTables here: Bore, Tone Holes, Fingering Chart
                    # each one references a separate piece of geometry data.

                    html.H5("Bore Segments"),
                    dash_table.DataTable(
                        id="bore-table",
                        columns=[
                            {"name": "Start Pos (mm)", "id": "start_pos", "type": "numeric"},
                            {"name": "End Pos (mm)",   "id": "end_pos",   "type": "numeric"},
                            {"name": "Start Dia (mm)","id": "start_dia","type": "numeric"},
                            {"name": "End Dia (mm)",  "id": "end_dia",  "type": "numeric"},
                            {"name": "Section Type",  "id": "sec_type", "presentation": "dropdown"},
                            {"name": "Param",         "id": "param",    "type": "numeric"},
                        ],
                        data=[
                            # Example default rows:
                            {"start_pos": 0,   "end_pos": 70,  "start_dia": 14.6, "end_dia": 14.6, "sec_type": "cone",  "param": None},
                            {"start_pos": 70,  "end_pos": 200, "start_dia": 14.6, "end_dia": 14.8, "sec_type": "circle","param": None},
                        ],
                        dropdown={
                            "sec_type": {
                                "options": [
                                    {"label": "circle", "value": "circle"},
                                    {"label": "cone", "value": "cone"},
                                    {"label": "exponential", "value": "exponential"},
                                    {"label": "bessel", "value": "bessel"}
                                ]
                            }
                        },
                        editable=True,
                        row_deletable=True,
                        row_selectable="multi",
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 80},
                    ),
                    dbc.Button("Add Bore Row", id="add-bore-row", size="sm", className="mt-2"),

                    html.Hr(),

                    html.H5("Tone Holes"),
                    dash_table.DataTable(
                        id="holes-table",
                        columns=[
                            {"name": "Label",     "id": "label",    "type": "text"},
                            {"name": "Pos (mm)",  "id": "position", "type": "numeric"},
                            {"name": "Chimney (mm)", "id": "chimney","type": "numeric"},
                            {"name": "Diameter (mm)","id": "diameter","type": "numeric"},
                        ],
                        data=[
                            {"label": "Hole1", "position": 80,  "chimney": 3, "diameter": 7},
                            {"label": "Hole2", "position": 120, "chimney": 3, "diameter": 7.5},
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 70},
                    ),
                    dbc.Button("Add Hole Row", id="add-holes-row", size="sm", className="mt-2"),

                    html.Hr(),

                    html.H5("Fingering Chart"),
                    dash_table.DataTable(
                        id="fingering-table",
                        columns=[
                            {"name": "Fingering Label", "id": "finger_label", "type": "text"},
                            {"name": "Hole1",          "id": "hole1",        "presentation": "dropdown"},
                            {"name": "Hole2",          "id": "hole2",        "presentation": "dropdown"},
                            {"name": "Hole3",          "id": "hole3",        "presentation": "dropdown"},
                            {"name": "Note (Opt.)",    "id": "note",         "type": "text"},
                        ],
                        data=[
                            {"finger_label": "Fingering1", "hole1": "closed", "hole2": "open", "hole3": "open", "note": "G3"},
                        ],
                        dropdown={
                            "hole1": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                            "hole2": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                            "hole3": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                        },
                        editable=True,
                        row_deletable=True,
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 80},
                    ),
                    dbc.Button("Add Fingering Row", id="add-fingering-row", size="sm", className="mt-2"),

                    html.Hr(),
                    dbc.Button("Update Geometry Plot", id="update-geometry-btn", color="primary", className="mt-2"),
                    dcc.Graph(id="clarinet-geometry-plot", figure={}),
                ])
            ], className="mb-3"),

            # COMPARATIVE MODE
            dbc.Card([
                dbc.CardBody([
                    html.H4("Comparative Mode", className="card-title"),
                    html.Div(id="comparison-table-container")
                ])
            ], className="mb-3"),
        ], width=9),
    ]),

    # Stores for data
    dcc.Store(id="stored-simulation-data", data={}),
    dcc.Store(id="stored-comparison-data", data=[]),

    # We'll also store the geometry from the 3 tables
    dcc.Store(id="clarinet-geometry-store", data={})
], fluid=True)

###############################################################################
# Callbacks
###############################################################################

# 1) BORE / HOLES / FINGERING TABLE "ADD ROW" BUTTONS
@app.callback(
    Output("bore-table", "data"),
    Input("add-bore-row", "n_clicks"),
    State("bore-table", "data"),
    prevent_initial_call=True
)
def add_bore_row(n_clicks, current_data):
    # Default new row
    new_row = {
        "start_pos": 0,
        "end_pos": 10,
        "start_dia": 14.6,
        "end_dia": 14.6,
        "sec_type": "cone",
        "param": None
    }
    current_data.append(new_row)
    return current_data

@app.callback(
    Output("holes-table", "data"),
    Input("add-holes-row", "n_clicks"),
    State("holes-table", "data"),
    prevent_initial_call=True
)
def add_holes_row(n_clicks, current_data):
    new_row = {
        "label": f"Hole{len(current_data)+1}",
        "position": 0,
        "chimney": 3,
        "diameter": 7
    }
    current_data.append(new_row)
    return current_data

@app.callback(
    Output("fingering-table", "data"),
    Input("add-fingering-row", "n_clicks"),
    State("fingering-table", "data"),
    prevent_initial_call=True
)
def add_fingering_row(n_clicks, current_data):
    new_row = {
        "finger_label": f"Fingering{len(current_data)+1}",
        "hole1": "open",
        "hole2": "open",
        "hole3": "closed",
        "note": ""
    }
    current_data.append(new_row)
    return current_data

# 2) Store clarinet geometry in dcc.Store whenever the user clicks “Update Geometry Plot”
@app.callback(
    Output("clarinet-geometry-store", "data"),
    Output("clarinet-geometry-plot", "figure"),
    Input("update-geometry-btn", "n_clicks"),
    State("bore-table", "data"),
    State("holes-table", "data"),
    State("fingering-table", "data"),
    prevent_initial_call=True
)
def update_clarinet_geometry(n, bore_data, holes_data, fingering_data):
    """
    This callback shows how you might gather Bore/Holes/Fingering data and
    produce some simple geometry plot. We'll simply plot the bore segments
    side by side. In a more advanced app, you could do a 2D cross-section,
    a 3D model, etc.
    """
    # Save everything in store
    geometry_dict = {
        "bore": bore_data,
        "holes": holes_data,
        "fingerings": fingering_data
    }

    # Create a simple line plot from the Bore data
    # We'll just do x vs diameter (start to end) to illustrate
    fig = go.Figure()
    for i, seg in enumerate(bore_data):
        # We treat each segment as a straight line from seg.start_pos to seg.end_pos
        x_segment = [seg["start_pos"], seg["end_pos"]]
        y_segment = [seg["start_dia"], seg["end_dia"]]
        fig.add_trace(go.Scatter(
            x=x_segment, y=y_segment,
            mode="lines+markers",
            name=f"Bore segment {i+1}"
        ))
    fig.update_layout(
        title="Clarinet Bore Segments (Start/End Diameters)",
        xaxis_title="Position (mm)",
        yaxis_title="Diameter (mm)"
    )

    return geometry_dict, fig

###############################################################################
# Your Existing Callbacks (unchanged except minor reorder)
###############################################################################
@app.callback(
    Output("bore-profile-graph", "figure"),
    Output("thickness-notes", "children"),
    Input("bore-shape-dd", "value"),
    Input("entry-diam-input", "value"),
    Input("exit-diam-input", "value"),
    Input("barrel-length-input", "value"),
    Input("resolution-dd", "value"),
    Input("exterior-shape-dd", "value"),
    Input("educational-mode-check", "value")
)
def update_bore_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution,
                        exterior_shape, edu_mode):
    if not (entry_diam and exit_diam and length_mm):
        fig = go.Figure()
        fig.update_layout(title="Please enter valid dimensions.")
        return fig, ""

    x_vals, bore_diam_vals = generate_barrel_profile(
        bore_shape, entry_diam, exit_diam, length_mm, resolution
    )
    thickness_vals = mock_thickness_map(x_vals, bore_diam_vals, exterior_shape)
    outer_diam_vals = [b + 2*t for b, t in zip(bore_diam_vals, thickness_vals)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=bore_diam_vals,
        mode="lines", name="Bore Diameter"
    ))
    fig.add_trace(go.Scatter(
        x=x_vals, y=outer_diam_vals,
        mode="lines", name="Outer Diameter"
    ))
    fig.update_layout(
        xaxis_title="Barrel Axis (mm)",
        yaxis_title="Diameter (mm)",
        title="Barrel Cross-Section View"
    )

    thickness_comment = ""
    if edu_mode and len(edu_mode) > 0:
        thickness_comment = (
            "Wall thickness is the difference between outer and bore radii. "
            "Thin walls can lead to tonal instability or undesirable resonance changes."
        )
    return fig, thickness_comment

@app.callback(
    Output("stored-simulation-data", "data"),
    Output("simulation-stats", "children"),
    Output("impedance-graph", "figure"),
    Output("admittance-graph", "figure"),
    Input("run-simulation-btn", "n_clicks"),
    State("bore-shape-dd", "value"),
    State("entry-diam-input", "value"),
    State("exit-diam-input", "value"),
    State("barrel-length-input", "value"),
    State("resolution-dd", "value"),
    State("exterior-shape-dd", "value"),
    State("material-dd", "value"),
    State("educational-mode-check", "value")
)
def run_simulation(n_clicks, bore_shape, entry_diam, exit_diam, length_mm,
                   resolution, exterior_shape, material, edu_mode):
    if n_clicks == 0:
        return {}, "", go.Figure(), go.Figure()

    x_vals, bore_diam_vals = generate_barrel_profile(
        bore_shape, entry_diam, exit_diam, length_mm, resolution
    )
    thickness_vals = mock_thickness_map(x_vals, bore_diam_vals, exterior_shape)
    avg_thickness = sum(thickness_vals) / len(thickness_vals)

    sim_results = run_mock_simulation(bore_diam_vals, material, avg_thickness)

    acoustic_table_header = html.Thead(html.Tr([
        html.Th("Parameter"),
        html.Th("Value"),
        html.Th("Definition")
    ]))

    table_rows = [
        html.Tr([
            html.Td("First Resonance (f₁)"),
            html.Td(f"{sim_results['f1']} Hz"),
            html.Td("Primary pitch at which the barrel resonates.")
        ]),
        html.Tr([
            html.Td("Cutoff Frequency"),
            html.Td(f"{sim_results['cutoff']} Hz"),
            html.Td("Above this range, resonances diminish.")
        ]),
        html.Tr([
            html.Td("Resistance Score"),
            html.Td(f"{sim_results['resistance']}/100"),
            html.Td("Indicates required air pressure.")
        ]),
        html.Tr([
            html.Td("Harmonicity Score"),
            html.Td(f"{sim_results['harmonicity']}"),
            html.Td("How closely overtones align with fundamental.")
        ]),
        html.Tr([
            html.Td("Timbre Brightness"),
            html.Td(f"{sim_results['brightness']}"),
            html.Td("Gauges ‘dark/warm’ vs ‘bright/clear.’")
        ]),
    ]
    acoustic_table_body = html.Tbody(table_rows)
    acoustic_table = dbc.Table([acoustic_table_header, acoustic_table_body],
                               bordered=True, hover=True, responsive=True)

    insights_header = html.H5("Performance Insights", className="mt-3")
    attribute_feedback = evaluate_barrel_attributes(sim_results)
    simulation_stats_section = [acoustic_table, html.Hr(), insights_header, attribute_feedback]

    if edu_mode and len(edu_mode) > 0:
        simulation_stats_section.append(
            html.Div(
                "Note: These metrics are rough indicators. Real-world testing remains essential.",
                style={"fontStyle": "italic", "marginTop": "10px"}
            )
        )

    imp_fig = go.Figure()
    imp_fig.add_trace(go.Scatter(
        x=sim_results["freq"],
        y=sim_results["impedance_curve"],
        mode="lines",
        name="Impedance"
    ))
    imp_fig.update_layout(
        xaxis_title="Frequency (Hz)",
        yaxis_title="Impedance (arb. units)",
        title="Impedance vs Frequency"
    )

    adm_fig = go.Figure()
    adm_fig.add_trace(go.Scatter(
        x=sim_results["freq"],
        y=sim_results["admittance_curve"],
        mode="lines",
        name="Admittance"
    ))
    adm_fig.update_layout(
        xaxis_title="Frequency (Hz)",
        yaxis_title="Admittance (arb. units)",
        title="Admittance vs Frequency"
    )

    return sim_results, simulation_stats_section, imp_fig, adm_fig


###############################################################################
# Comparison Mode
###############################################################################
@app.callback(
    Output("comparison-mode-section", "style"),
    Input("compare-mode-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_comparison_mode_section(n_clicks):
    if n_clicks % 2 == 1:
        return {"display": "block", "marginTop": "10px"}
    else:
        return {"display": "none"}

@app.callback(
    Output("stored-comparison-data", "data"),
    Output("comparison-table-container", "children"),
    Input("compare-mode-btn", "n_clicks"),
    Input("stored-simulation-data", "data"),
    State("save-design-name", "value"),
    State("stored-comparison-data", "data"),
    prevent_initial_call=True
)
def add_to_comparison(n_clicks, current_sim, design_name, comparison_data):
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if comparison_data is None:
        comparison_data = []

    if triggered_id == "compare-mode-btn":
        if not current_sim:
            return comparison_data, "No simulation results to compare."
        if not design_name:
            design_name = f"Design {len(comparison_data) + 1}"

        entry = {
            "name": design_name,
            "f1": current_sim.get("f1", 0),
            "cutoff": current_sim.get("cutoff", 0),
            "resistance": current_sim.get("resistance", 0),
            "brightness": current_sim.get("brightness", 0),
            "harmonicity": current_sim.get("harmonicity", 0)
        }
        comparison_data.append(entry)
        comparison_data = comparison_data[-5:]  # limit to 5

    if len(comparison_data) == 0:
        return comparison_data, "No designs currently in comparison."

    table_header = [
        html.Thead(html.Tr([
            html.Th("Design Name"),
            html.Th("f₁ (Hz)"),
            html.Th("Cutoff (Hz)"),
            html.Th("Resistance"),
            html.Th("Brightness"),
            html.Th("Harmonicity")
        ]))
    ]
    rows = []
    for c in comparison_data:
        rows.append(
            html.Tr([
                html.Td(c["name"]),
                html.Td(c["f1"]),
                html.Td(c["cutoff"]),
                html.Td(f"{c['resistance']}/100"),
                html.Td(c["brightness"]),
                html.Td(c["harmonicity"])
            ])
        )
    table_body = [html.Tbody(rows)]
    table = dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True)
    return comparison_data, table


###############################################################################
# Save / Load / Export
###############################################################################
@app.callback(
    Output("save-design-btn", "n_clicks"),
    Input("save-design-btn", "n_clicks"),
    State("save-design-name", "value"),
    State("bore-shape-dd", "value"),
    State("exterior-shape-dd", "value"),
    State("entry-diam-input", "value"),
    State("exit-diam-input", "value"),
    State("barrel-length-input", "value"),
    State("resolution-dd", "value"),
    State("material-dd", "value"),
    State("stored-simulation-data", "data"),
    prevent_initial_call=True
)
def save_design_to_memory(n_clicks, design_name, bore_shape, exterior_shape,
                          entry_diam, exit_diam, length_mm, resolution,
                          material, sim_data):
    if not design_name:
        return 0

    design_dict = {
        "bore_shape": bore_shape,
        "exterior_shape": exterior_shape,
        "entry_diam": entry_diam,
        "exit_diam": exit_diam,
        "length_mm": length_mm,
        "resolution": resolution,
        "material": material,
        "simulation": sim_data
    }
    stored_designs[design_name] = design_dict
    print(f"Saved design: {design_name}")
    return 0

@app.callback(
    Output("load-design-btn", "n_clicks"),
    Input("upload-json-design", "contents"),
    State("upload-json-design", "filename"),
    prevent_initial_call=True
)
def load_design_from_json(content, filename):
    if content is not None:
        import base64

        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        try:
            design_data = json.loads(decoded.decode("utf-8"))
            if "design_name" in design_data:
                stored_designs[design_data["design_name"]] = design_data
                print(f"Loaded design from {filename}")
        except Exception as e:
            print(f"Error parsing file: {e}")

    return 0

@app.callback(
    Output("export-json-btn", "disabled"),
    Output("export-csv-btn", "disabled"),
    Output("export-stl-btn", "disabled"),
    Output("export-pdf-btn", "disabled"),
    Input("export-json-btn", "n_clicks"),
    Input("export-csv-btn", "n_clicks"),
    Input("export-stl-btn", "n_clicks"),
    Input("export-pdf-btn", "n_clicks"),
    State("stored-simulation-data", "data"),
    prevent_initial_call=True
)
def export_design(json_click, csv_click, stl_click, pdf_click, sim_data):
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if not sim_data:
        return (False, False, False, False)
    if triggered_id:
        print(f"User requested export: {triggered_id}")
        # In a real app, create and prompt download of the file

    return (False, False, False, False)

###############################################################################
# Run the App
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True)
import json
import random
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objects as go


###############################################################################
# Mock / Helper Functions (same as before)
###############################################################################
def generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution):
    """
    Returns a list of (x, diameter) points representing a simplified 2D cross-section
    of the bore profile, for demonstration purposes.
    """
    num_points = {"Low": 10, "Medium": 30, "High": 60}.get(resolution, 30)
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
    length = x_vals[-1] - x_vals[0] if x_vals else 0

    for i, x in enumerate(x_vals):
        outer_factor = 1.0
        if exterior_shape == "Hourglass (waist tapered)":
            midpoint = 0.5 * length
            dist_from_center = abs(x - midpoint)
            outer_factor = 1.1 - 0.0005 * dist_from_center
        elif exterior_shape == "Bell-like Flare (tuned for resonance)":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.2 * fraction
        elif exterior_shape == "Reverse Taper (bulged center)":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.25 * (1 - (fraction - 0.5)**2)
        elif exterior_shape == "Standard (parallel exterior)":
            outer_factor = 1.05
        elif exterior_shape == "User-Defined":
            fraction = i / max(1, len(x_vals) - 1)
            outer_factor = 1.0 + 0.05 * fraction

        outer_diam = bore_diam_vals[i] * outer_factor
        thickness = (outer_diam - bore_diam_vals[i]) / 2.0
        thickness_vals.append(thickness)
    return thickness_vals

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

    if sim_results["resistance"] < 30:
        comments.append("Very free-blowing (low resistance). Requires less air pressure but can sacrifice some control.")
    elif sim_results["resistance"] < 70:
        comments.append("Moderate resistance, balancing control and ease of airflow.")
    else:
        comments.append("High resistance—requires stronger air support but may offer greater dynamic control.")

    if sim_results["brightness"] < 0.4:
        comments.append("Leans toward a darker or warmer timbre.")
    elif sim_results["brightness"] < 0.6:
        comments.append("Moderately bright—somewhere between dark and brilliant.")
    else:
        comments.append("Quite bright—clear and projecting tone.")

    if sim_results["harmonicity"] >= 0.85:
        comments.append("Overtones align well (high harmonicity)—stable, pure core.")
    elif sim_results["harmonicity"] < 0.75:
        comments.append("Lower harmonicity—overtones may be slightly mismatched, potentially more complex or tricky to voice.")

    return html.Ul([html.Li(c) for c in comments])

###############################################################################
# Dash App Setup
###############################################################################
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Clarinet Barrel Designer"

bore_shape_options = [
    "Cylindrical", "Tapered", "Reverse Tapered", "Parabolic", "Stepped"
]
exterior_shape_options = [
    "Standard (parallel exterior)",
    "Hourglass (waist tapered)",
    "Reverse Taper (bulged center)",
    "Bell-like Flare (tuned for resonance)",
    "User-Defined"
]
resolution_options = ["Low", "Medium", "High"]
material_options = [
    "African Blackwood", "Mopane", "Cocobolo", "Hard Rubber", "Composite"
]

stored_designs = {}

###############################################################################
# Layout
###############################################################################
app.layout = dbc.Container([
    html.H1("Clarinet Barrel Designer & Simulation Wizard", className="mt-3"),
    html.Hr(),

    dbc.Row([
        # Left Column
        dbc.Col([
            # DESIGN PARAMETERS
            dbc.Card([
                dbc.CardBody([
                    html.H4("Design Parameters", className="card-title"),

                    dbc.Label("Bore Shape"),
                    dcc.Dropdown(
                        id="bore-shape-dd",
                        options=[{"label": bs, "value": bs} for bs in bore_shape_options],
                        value="Cylindrical"
                    ),

                    dbc.Label("Exterior Shape", className="mt-3"),
                    dcc.Dropdown(
                        id="exterior-shape-dd",
                        options=[{"label": ex, "value": ex} for ex in exterior_shape_options],
                        value="Standard (parallel exterior)"
                    ),

                    dbc.Label("Entry Diameter (mm)", className="mt-3"),
                    dbc.Input(
                        id="entry-diam-input",
                        type="number",
                        placeholder="e.g. 14.8",
                        value=14.8,
                        step=0.1
                    ),

                    dbc.Label("Exit Diameter (mm)", className="mt-3"),
                    dbc.Input(
                        id="exit-diam-input",
                        type="number",
                        placeholder="e.g. 15.2",
                        value=15.2,
                        step=0.1
                    ),

                    dbc.Label("Barrel Length (mm)", className="mt-3"),
                    dbc.Input(
                        id="barrel-length-input",
                        type="number",
                        placeholder="e.g. 66",
                        value=66,
                        step=0.5
                    ),

                    dbc.Label("Segment Resolution", className="mt-3"),
                    dcc.Dropdown(
                        id="resolution-dd",
                        options=[{"label": r, "value": r} for r in resolution_options],
                        value="Medium"
                    ),

                    dbc.Label("Material (Planned)", className="mt-3"),
                    dcc.Dropdown(
                        id="material-dd",
                        options=[{"label": m, "value": m} for m in material_options],
                        value="African Blackwood"
                    ),

                    dbc.Checklist(
                        options=[{"label": "Educational Overlay (Tooltips)", "value": 1}],
                        value=[1],
                        id="educational-mode-check",
                        switch=True,
                        className="my-3"
                    ),

                    dbc.Button(
                        "Run Simulation",
                        id="run-simulation-btn",
                        color="primary",
                        className="mt-3",
                        n_clicks=0
                    ),
                ])
            ], className="mb-3"),

            # EXPORT & COMPARE
            dbc.Card([
                dbc.CardBody([
                    html.H4("Export & Compare", className="card-title"),
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("Design Name"),
                                dbc.Input(id="save-design-name", placeholder="MyBarrel1", value="")
                            ]),
                            dbc.Button("Save Design", id="save-design-btn", color="secondary", className="mt-2"),
                        ])
                    ]),

                    dbc.Button("Load Design", id="load-design-btn", color="info", className="mt-3", n_clicks=0),
                    dcc.Upload(
                        id="upload-json-design",
                        children=html.Div(["Drag & Drop or Click to Select JSON"]),
                        style={
                            "width": "100%",
                            "height": "60px",
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "marginTop": "10px",
                        },
                        multiple=False
                    ),

                    html.Hr(),
                    html.Div([
                        dbc.Button("Export as JSON", id="export-json-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as CSV", id="export-csv-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as STL", id="export-stl-btn", color="success", className="me-2 mt-2"),
                        dbc.Button("Export as PDF", id="export-pdf-btn", color="success", className="me-2 mt-2"),
                    ]),

                    html.Hr(),
                    dbc.Button("Enable Comparison Mode", id="compare-mode-btn", color="warning", className="mt-2"),
                    html.Div(id="comparison-mode-section", style={"display": "none"}),
                ])
            ]),
        ], width=3),

        # Right Column
        dbc.Col([
            # CROSS-SECTION CARD
            dbc.Card([
                dbc.CardBody([
                    html.H4("Barrel Cross-Section & Wall Thickness", className="card-title"),
                    dcc.Graph(id="bore-profile-graph"),
                    html.Div(id="thickness-notes", className="text-muted", style={"fontSize": "0.9em"})
                ])
            ], className="mb-3"),

            # ACOUSTIC SIM RESULTS
            dbc.Card([
                dbc.CardBody([
                    html.H4("Acoustic Simulation Results", className="card-title"),
                    html.Div(id="simulation-stats", className="mb-3"),

                    html.Div(
                        "Impedance vs Frequency shows how much the barrel resists airflow at various pitches. "
                        "Higher impedance often means stronger resonance at those frequencies.",
                        className="text-muted",
                        style={"fontSize": "0.9em", "marginBottom": "6px"}
                    ),
                    dcc.Graph(id="impedance-graph"),

                    html.Div(
                        "Admittance vs Frequency is effectively the inverse of impedance—higher admittance means "
                        "the barrel allows airflow more easily. This can translate to an ‘open’ feel.",
                        className="text-muted",
                        style={"fontSize": "0.9em", "marginTop": "12px", "marginBottom": "6px"}
                    ),
                    dcc.Graph(id="admittance-graph"),
                ])
            ], className="mb-3"),

            # NEW CARD: CLARINET GEOMETRY
            dbc.Card([
                dbc.CardBody([
                    html.H4("Clarinet Geometry", className="card-title"),

                    # We'll create 3 DataTables here: Bore, Tone Holes, Fingering Chart
                    # each one references a separate piece of geometry data.

                    html.H5("Bore Segments"),
                    dash_table.DataTable(
                        id="bore-table",
                        columns=[
                            {"name": "Start Pos (mm)", "id": "start_pos", "type": "numeric"},
                            {"name": "End Pos (mm)",   "id": "end_pos",   "type": "numeric"},
                            {"name": "Start Dia (mm)","id": "start_dia","type": "numeric"},
                            {"name": "End Dia (mm)",  "id": "end_dia",  "type": "numeric"},
                            {"name": "Section Type",  "id": "sec_type", "presentation": "dropdown"},
                            {"name": "Param",         "id": "param",    "type": "numeric"},
                        ],
                        data=[
                            # Example default rows:
                            {"start_pos": 0,   "end_pos": 70,  "start_dia": 14.6, "end_dia": 14.6, "sec_type": "cone",  "param": None},
                            {"start_pos": 70,  "end_pos": 200, "start_dia": 14.6, "end_dia": 14.8, "sec_type": "circle","param": None},
                        ],
                        dropdown={
                            "sec_type": {
                                "options": [
                                    {"label": "circle", "value": "circle"},
                                    {"label": "cone", "value": "cone"},
                                    {"label": "exponential", "value": "exponential"},
                                    {"label": "bessel", "value": "bessel"}
                                ]
                            }
                        },
                        editable=True,
                        row_deletable=True,
                        row_selectable="multi",
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 80},
                    ),
                    dbc.Button("Add Bore Row", id="add-bore-row", size="sm", className="mt-2"),

                    html.Hr(),

                    html.H5("Tone Holes"),
                    dash_table.DataTable(
                        id="holes-table",
                        columns=[
                            {"name": "Label",     "id": "label",    "type": "text"},
                            {"name": "Pos (mm)",  "id": "position", "type": "numeric"},
                            {"name": "Chimney (mm)", "id": "chimney","type": "numeric"},
                            {"name": "Diameter (mm)","id": "diameter","type": "numeric"},
                        ],
                        data=[
                            {"label": "Hole1", "position": 80,  "chimney": 3, "diameter": 7},
                            {"label": "Hole2", "position": 120, "chimney": 3, "diameter": 7.5},
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 70},
                    ),
                    dbc.Button("Add Hole Row", id="add-holes-row", size="sm", className="mt-2"),

                    html.Hr(),

                    html.H5("Fingering Chart"),
                    dash_table.DataTable(
                        id="fingering-table",
                        columns=[
                            {"name": "Fingering Label", "id": "finger_label", "type": "text"},
                            {"name": "Hole1",          "id": "hole1",        "presentation": "dropdown"},
                            {"name": "Hole2",          "id": "hole2",        "presentation": "dropdown"},
                            {"name": "Hole3",          "id": "hole3",        "presentation": "dropdown"},
                            {"name": "Note (Opt.)",    "id": "note",         "type": "text"},
                        ],
                        data=[
                            {"finger_label": "Fingering1", "hole1": "closed", "hole2": "open", "hole3": "open", "note": "G3"},
                        ],
                        dropdown={
                            "hole1": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                            "hole2": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                            "hole3": {"options": [{"label": "open", "value": "open"}, {"label": "closed", "value": "closed"}]},
                        },
                        editable=True,
                        row_deletable=True,
                        style_table={"height": "250px", "overflowY": "auto"},
                        style_cell={"minWidth": 80},
                    ),
                    dbc.Button("Add Fingering Row", id="add-fingering-row", size="sm", className="mt-2"),

                    html.Hr(),
                    dbc.Button("Update Geometry Plot", id="update-geometry-btn", color="primary", className="mt-2"),
                    dcc.Graph(id="clarinet-geometry-plot", figure={}),
                ])
            ], className="mb-3"),

            # COMPARATIVE MODE
            dbc.Card([
                dbc.CardBody([
                    html.H4("Comparative Mode", className="card-title"),
                    html.Div(id="comparison-table-container")
                ])
            ], className="mb-3"),
        ], width=9),
    ]),

    # Stores for data
    dcc.Store(id="stored-simulation-data", data={}),
    dcc.Store(id="stored-comparison-data", data=[]),

    # We'll also store the geometry from the 3 tables
    dcc.Store(id="clarinet-geometry-store", data={})
], fluid=True)

###############################################################################
# Callbacks
###############################################################################

# 1) BORE / HOLES / FINGERING TABLE "ADD ROW" BUTTONS
@app.callback(
    Output("bore-table", "data"),
    Input("add-bore-row", "n_clicks"),
    State("bore-table", "data"),
    prevent_initial_call=True
)
def add_bore_row(n_clicks, current_data):
    # Default new row
    new_row = {
        "start_pos": 0,
        "end_pos": 10,
        "start_dia": 14.6,
        "end_dia": 14.6,
        "sec_type": "cone",
        "param": None
    }
    current_data.append(new_row)
    return current_data

@app.callback(
    Output("holes-table", "data"),
    Input("add-holes-row", "n_clicks"),
    State("holes-table", "data"),
    prevent_initial_call=True
)
def add_holes_row(n_clicks, current_data):
    new_row = {
        "label": f"Hole{len(current_data)+1}",
        "position": 0,
        "chimney": 3,
        "diameter": 7
    }
    current_data.append(new_row)
    return current_data

@app.callback(
    Output("fingering-table", "data"),
    Input("add-fingering-row", "n_clicks"),
    State("fingering-table", "data"),
    prevent_initial_call=True
)
def add_fingering_row(n_clicks, current_data):
    new_row = {
        "finger_label": f"Fingering{len(current_data)+1}",
        "hole1": "open",
        "hole2": "open",
        "hole3": "closed",
        "note": ""
    }
    current_data.append(new_row)
    return current_data

# 2) Store clarinet geometry in dcc.Store whenever the user clicks “Update Geometry Plot”
@app.callback(
    Output("clarinet-geometry-store", "data"),
    Output("clarinet-geometry-plot", "figure"),
    Input("update-geometry-btn", "n_clicks"),
    State("bore-table", "data"),
    State("holes-table", "data"),
    State("fingering-table", "data"),
    prevent_initial_call=True
)
def update_clarinet_geometry(n, bore_data, holes_data, fingering_data):
    """
    This callback shows how you might gather Bore/Holes/Fingering data and
    produce some simple geometry plot. We'll simply plot the bore segments
    side by side. In a more advanced app, you could do a 2D cross-section,
    a 3D model, etc.
    """
    # Save everything in store
    geometry_dict = {
        "bore": bore_data,
        "holes": holes_data,
        "fingerings": fingering_data
    }

    # Create a simple line plot from the Bore data
    # We'll just do x vs diameter (start to end) to illustrate
    fig = go.Figure()
    for i, seg in enumerate(bore_data):
        # We treat each segment as a straight line from seg.start_pos to seg.end_pos
        x_segment = [seg["start_pos"], seg["end_pos"]]
        y_segment = [seg["start_dia"], seg["end_dia"]]
        fig.add_trace(go.Scatter(
            x=x_segment, y=y_segment,
            mode="lines+markers",
            name=f"Bore segment {i+1}"
        ))
    fig.update_layout(
        title="Clarinet Bore Segments (Start/End Diameters)",
        xaxis_title="Position (mm)",
        yaxis_title="Diameter (mm)"
    )

    return geometry_dict, fig

###############################################################################
# Your Existing Callbacks (unchanged except minor reorder)
###############################################################################
@app.callback(
    Output("bore-profile-graph", "figure"),
    Output("thickness-notes", "children"),
    Input("bore-shape-dd", "value"),
    Input("entry-diam-input", "value"),
    Input("exit-diam-input", "value"),
    Input("barrel-length-input", "value"),
    Input("resolution-dd", "value"),
    Input("exterior-shape-dd", "value"),
    Input("educational-mode-check", "value")
)
def update_bore_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution,
                        exterior_shape, edu_mode):
    if not (entry_diam and exit_diam and length_mm):
        fig = go.Figure()
        fig.update_layout(title="Please enter valid dimensions.")
        return fig, ""

    x_vals, bore_diam_vals = generate_barrel_profile(
        bore_shape, entry_diam, exit_diam, length_mm, resolution
    )
    thickness_vals = mock_thickness_map(x_vals, bore_diam_vals, exterior_shape)
    outer_diam_vals = [b + 2*t for b, t in zip(bore_diam_vals, thickness_vals)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=bore_diam_vals,
        mode="lines", name="Bore Diameter"
    ))
    fig.add_trace(go.Scatter(
        x=x_vals, y=outer_diam_vals,
        mode="lines", name="Outer Diameter"
    ))
    fig.update_layout(
        xaxis_title="Barrel Axis (mm)",
        yaxis_title="Diameter (mm)",
        title="Barrel Cross-Section View"
    )

    thickness_comment = ""
    if edu_mode and len(edu_mode) > 0:
        thickness_comment = (
            "Wall thickness is the difference between outer and bore radii. "
            "Thin walls can lead to tonal instability or undesirable resonance changes."
        )
    return fig, thickness_comment

@app.callback(
    Output("stored-simulation-data", "data"),
    Output("simulation-stats", "children"),
    Output("impedance-graph", "figure"),
    Output("admittance-graph", "figure"),
    Input("run-simulation-btn", "n_clicks"),
    State("bore-shape-dd", "value"),
    State("entry-diam-input", "value"),
    State("exit-diam-input", "value"),
    State("barrel-length-input", "value"),
    State("resolution-dd", "value"),
    State("exterior-shape-dd", "value"),
    State("material-dd", "value"),
    State("educational-mode-check", "value")
)
def run_simulation(n_clicks, bore_shape, entry_diam, exit_diam, length_mm,
                   resolution, exterior_shape, material, edu_mode):
    if n_clicks == 0:
        return {}, "", go.Figure(), go.Figure()

    x_vals, bore_diam_vals = generate_barrel_profile(
        bore_shape, entry_diam, exit_diam, length_mm, resolution
    )
    thickness_vals = mock_thickness_map(x_vals, bore_diam_vals, exterior_shape)
    avg_thickness = sum(thickness_vals) / len(thickness_vals)

    sim_results = run_mock_simulation(bore_diam_vals, material, avg_thickness)

    acoustic_table_header = html.Thead(html.Tr([
        html.Th("Parameter"),
        html.Th("Value"),
        html.Th("Definition")
    ]))

    table_rows = [
        html.Tr([
            html.Td("First Resonance (f₁)"),
            html.Td(f"{sim_results['f1']} Hz"),
            html.Td("Primary pitch at which the barrel resonates.")
        ]),
        html.Tr([
            html.Td("Cutoff Frequency"),
            html.Td(f"{sim_results['cutoff']} Hz"),
            html.Td("Above this range, resonances diminish.")
        ]),
        html.Tr([
            html.Td("Resistance Score"),
            html.Td(f"{sim_results['resistance']}/100"),
            html.Td("Indicates required air pressure.")
        ]),
        html.Tr([
            html.Td("Harmonicity Score"),
            html.Td(f"{sim_results['harmonicity']}"),
            html.Td("How closely overtones align with fundamental.")
        ]),
        html.Tr([
            html.Td("Timbre Brightness"),
            html.Td(f"{sim_results['brightness']}"),
            html.Td("Gauges ‘dark/warm’ vs ‘bright/clear.’")
        ]),
    ]
    acoustic_table_body = html.Tbody(table_rows)
    acoustic_table = dbc.Table([acoustic_table_header, acoustic_table_body],
                               bordered=True, hover=True, responsive=True)

    insights_header = html.H5("Performance Insights", className="mt-3")
    attribute_feedback = evaluate_barrel_attributes(sim_results)
    simulation_stats_section = [acoustic_table, html.Hr(), insights_header, attribute_feedback]

    if edu_mode and len(edu_mode) > 0:
        simulation_stats_section.append(
            html.Div(
                "Note: These metrics are rough indicators. Real-world testing remains essential.",
                style={"fontStyle": "italic", "marginTop": "10px"}
            )
        )

    imp_fig = go.Figure()
    imp_fig.add_trace(go.Scatter(
        x=sim_results["freq"],
        y=sim_results["impedance_curve"],
        mode="lines",
        name="Impedance"
    ))
    imp_fig.update_layout(
        xaxis_title="Frequency (Hz)",
        yaxis_title="Impedance (arb. units)",
        title="Impedance vs Frequency"
    )

    adm_fig = go.Figure()
    adm_fig.add_trace(go.Scatter(
        x=sim_results["freq"],
        y=sim_results["admittance_curve"],
        mode="lines",
        name="Admittance"
    ))
    adm_fig.update_layout(
        xaxis_title="Frequency (Hz)",
        yaxis_title="Admittance (arb. units)",
        title="Admittance vs Frequency"
    )

    return sim_results, simulation_stats_section, imp_fig, adm_fig


###############################################################################
# Comparison Mode
###############################################################################
@app.callback(
    Output("comparison-mode-section", "style"),
    Input("compare-mode-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_comparison_mode_section(n_clicks):
    if n_clicks % 2 == 1:
        return {"display": "block", "marginTop": "10px"}
    else:
        return {"display": "none"}

@app.callback(
    Output("stored-comparison-data", "data"),
    Output("comparison-table-container", "children"),
    Input("compare-mode-btn", "n_clicks"),
    Input("stored-simulation-data", "data"),
    State("save-design-name", "value"),
    State("stored-comparison-data", "data"),
    prevent_initial_call=True
)
def add_to_comparison(n_clicks, current_sim, design_name, comparison_data):
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if comparison_data is None:
        comparison_data = []

    if triggered_id == "compare-mode-btn":
        if not current_sim:
            return comparison_data, "No simulation results to compare."
        if not design_name:
            design_name = f"Design {len(comparison_data) + 1}"

        entry = {
            "name": design_name,
            "f1": current_sim.get("f1", 0),
            "cutoff": current_sim.get("cutoff", 0),
            "resistance": current_sim.get("resistance", 0),
            "brightness": current_sim.get("brightness", 0),
            "harmonicity": current_sim.get("harmonicity", 0)
        }
        comparison_data.append(entry)
        comparison_data = comparison_data[-5:]  # limit to 5

    if len(comparison_data) == 0:
        return comparison_data, "No designs currently in comparison."

    table_header = [
        html.Thead(html.Tr([
            html.Th("Design Name"),
            html.Th("f₁ (Hz)"),
            html.Th("Cutoff (Hz)"),
            html.Th("Resistance"),
            html.Th("Brightness"),
            html.Th("Harmonicity")
        ]))
    ]
    rows = []
    for c in comparison_data:
        rows.append(
            html.Tr([
                html.Td(c["name"]),
                html.Td(c["f1"]),
                html.Td(c["cutoff"]),
                html.Td(f"{c['resistance']}/100"),
                html.Td(c["brightness"]),
                html.Td(c["harmonicity"])
            ])
        )
    table_body = [html.Tbody(rows)]
    table = dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True)
    return comparison_data, table


###############################################################################
# Save / Load / Export
###############################################################################
@app.callback(
    Output("save-design-btn", "n_clicks"),
    Input("save-design-btn", "n_clicks"),
    State("save-design-name", "value"),
    State("bore-shape-dd", "value"),
    State("exterior-shape-dd", "value"),
    State("entry-diam-input", "value"),
    State("exit-diam-input", "value"),
    State("barrel-length-input", "value"),
    State("resolution-dd", "value"),
    State("material-dd", "value"),
    State("stored-simulation-data", "data"),
    prevent_initial_call=True
)
def save_design_to_memory(n_clicks, design_name, bore_shape, exterior_shape,
                          entry_diam, exit_diam, length_mm, resolution,
                          material, sim_data):
    if not design_name:
        return 0

    design_dict = {
        "bore_shape": bore_shape,
        "exterior_shape": exterior_shape,
        "entry_diam": entry_diam,
        "exit_diam": exit_diam,
        "length_mm": length_mm,
        "resolution": resolution,
        "material": material,
        "simulation": sim_data
    }
    stored_designs[design_name] = design_dict
    print(f"Saved design: {design_name}")
    return 0

@app.callback(
    Output("load-design-btn", "n_clicks"),
    Input("upload-json-design", "contents"),
    State("upload-json-design", "filename"),
    prevent_initial_call=True
)
def load_design_from_json(content, filename):
    if content is not None:
        import base64

        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        try:
            design_data = json.loads(decoded.decode("utf-8"))
            if "design_name" in design_data:
                stored_designs[design_data["design_name"]] = design_data
                print(f"Loaded design from {filename}")
        except Exception as e:
            print(f"Error parsing file: {e}")

    return 0

@app.callback(
    Output("export-json-btn", "disabled"),
    Output("export-csv-btn", "disabled"),
    Output("export-stl-btn", "disabled"),
    Output("export-pdf-btn", "disabled"),
    Input("export-json-btn", "n_clicks"),
    Input("export-csv-btn", "n_clicks"),
    Input("export-stl-btn", "n_clicks"),
    Input("export-pdf-btn", "n_clicks"),
    State("stored-simulation-data", "data"),
    prevent_initial_call=True
)
def export_design(json_click, csv_click, stl_click, pdf_click, sim_data):
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if not sim_data:
        return (False, False, False, False)
    if triggered_id:
        print(f"User requested export: {triggered_id}")
        # In a real app, create and prompt download of the file

    return (False, False, False, False)

###############################################################################
# Run the App
###############################################################################
if __name__ == "__main__":
    app.run_server(debug=True)
