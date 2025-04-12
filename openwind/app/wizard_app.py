#!/usr/bin/env python3

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
import random
import json
import base64

###############################################################################
# Mock Geometry / Simulation Logic
###############################################################################

def generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution):
    """
    Returns a list of x positions and corresponding diameters.
    Simplified logic just linearly interpolates from entry_diam->exit_diam
    with minor shape tweak.
    """
    if resolution < 2:
        resolution = 2
    num_points = resolution  # interpret "resolution" as # of points
    x_vals = [i*(length_mm/(num_points-1)) for i in range(num_points)]

    diam_vals = []
    for i, x in enumerate(x_vals):
        if num_points > 1:
            frac = i/(num_points-1)
        else:
            frac = 0.0
        # Base linear interpolation
        diameter = entry_diam + frac*(exit_diam - entry_diam)
        # Minor shape tweak
        if bore_shape == "Tapered":
            diameter *= (1.0 + 0.05*frac)
        elif bore_shape == "Reverse Tapered":
            diameter *= (1.0 + 0.05*(1-frac))
        elif bore_shape == "Parabolic":
            diameter *= (1.0 + 0.1*(frac-0.5)**2)
        elif bore_shape == "Stepped":
            if frac > 0.5:
                diameter *= 1.02
        diam_vals.append(diameter)

    return x_vals, diam_vals


def run_mock_simulation(bore_shape, entry_diam, exit_diam, length_mm, resolution, material):
    """
    A placeholder that returns random acoustic metrics.
    In a real scenario, you'd do a wave-propagation or FEA approach.
    """
    x_vals, d_vals = generate_barrel_profile(bore_shape, entry_diam, exit_diam, length_mm, resolution)
    if d_vals:
        avg_dia = sum(d_vals) / len(d_vals)
    else:
        avg_dia = 14.0

    # Mock calculations
    f1 = round(450 + (avg_dia - 14.0)*3 + random.uniform(-10, 10), 2)
    cutoff = round(f1 * 2.0, 2)

    freq = list(range(100, 2000, 100))
    impedance = [random.uniform(0.5, 1.5) * (1 + (avg_dia-14.0)/100.0) for _ in freq]
    admittance = [1.0 / i for i in impedance]

    # Simple "material factor" tweak
    mat_factor = 1.0
    if material == "Hard Rubber":
        mat_factor = 0.95
    elif material == "African Blackwood":
        mat_factor = 1.05

    f1 *= mat_factor
    cutoff *= mat_factor

    brightness = round(random.uniform(0.3, 0.8), 3)
    harmonicity = round(random.uniform(0.7, 0.95), 3)

    return {
        "f1": f1,
        "cutoff": cutoff,
        "freq": freq,
        "impedance_curve": impedance,
        "admittance_curve": admittance,
        "brightness": brightness,
        "harmonicity": harmonicity
    }


def evaluate_barrel_performance(sim_results):
    """
    Generate bullet-point commentary.
    """
    if not sim_results:
        return "No simulation results yet."

    f1 = sim_results.get("f1", 0)
    cutoff = sim_results.get("cutoff", 0)
    br = sim_results.get("brightness", 0.5)
    har = sim_results.get("harmonicity", 0.8)

    lines = []
    lines.append(f"First resonance (f₁): {f1:.2f} Hz")
    lines.append(f"Cutoff frequency: {cutoff:.2f} Hz")

    if br < 0.4:
        lines.append("Timbre: Dark/Warm")
    elif br < 0.6:
        lines.append("Timbre: Moderately bright")
    else:
        lines.append("Timbre: Quite bright")

    if har > 0.85:
        lines.append("Harmonicity: Overtones align well (very pure)")
    elif har < 0.75:
        lines.append("Harmonicity: Overtones somewhat mismatched (complex timbre)")

    return "\n".join(lines)


###############################################################################
# Layout: Step-based wizard, plus some data storage
###############################################################################

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Clarinet Barrel Wizard"

# We'll store the "current step" in a dcc.Store so we can show/hide sections
app.layout = dbc.Container([
    html.H1("Clarinet Barrel Creation Wizard", className="mt-3"),
    html.Hr(),

    dcc.Store(id="wizard-step", data=1),

    # Step 1
    dbc.Card([
        dbc.CardBody([
            html.H4("Step 1: Basic Barrel Setup"),
            html.P("Choose the shape, length, diameters, etc."),

            dbc.Label("Bore Shape"),
            dcc.Dropdown(
                id="w1-bore-shape-dd",
                options=[{"label": x, "value": x} for x in
                         ["Cylindrical", "Tapered", "Reverse Tapered", "Parabolic", "Stepped"]],
                value="Cylindrical"
            ),

            dbc.Label("Entry Diameter (mm)", className="mt-3"),
            dbc.Input(id="w1-entry-diam-input", type="number", value=14.8, step=0.1),

            dbc.Label("Exit Diameter (mm)", className="mt-3"),
            dbc.Input(id="w1-exit-diam-input", type="number", value=15.2, step=0.1),

            dbc.Label("Barrel Length (mm)", className="mt-3"),
            dbc.Input(id="w1-barrel-length-input", type="number", value=66, step=0.5),

            dbc.Label("Resolution (# points)", className="mt-3"),
            dbc.Input(id="w1-resolution-input", type="number", value=5, step=1),

            dbc.Label("Material", className="mt-3"),
            dcc.Dropdown(
                id="w1-material-dd",
                options=[{"label": m, "value": m} for m in [
                    "African Blackwood","Mopane","Cocobolo","Hard Rubber","Composite"
                ]],
                value="African Blackwood"
            ),

            dbc.Row([
                dbc.Col(dbc.Button("Next →", id="w1-next-btn", color="primary", className="mt-3"), width="auto")
            ], justify="end")
        ])
    ], id="wizard-step1", className="mb-3"),

    # Step 2
    dbc.Card([
        dbc.CardBody([
            html.H4("Step 2: Define Holes & Fingering"),
            html.P("Add or adjust clarinet tone holes and fingering data."),

            html.H5("Tone Holes"),
            dash_table.DataTable(
                id="w2-holes-table",
                columns=[
                    {"name":"Label","id":"label","type":"text"},
                    {"name":"Pos (mm)","id":"position","type":"numeric"},
                    {"name":"Diameter (mm)","id":"diameter","type":"numeric"},
                ],
                data=[
                    {"label":"Hole1","position":80,"diameter":7},
                    {"label":"Hole2","position":120,"diameter":7.5},
                ],
                editable=True,
                row_deletable=True,
                style_table={"height":"250px","overflowY":"auto"},
                style_cell={"minWidth":70},
            ),
            dbc.Button("Add Hole Row", id="w2-add-hole-row", size="sm", className="mt-2"),

            html.Hr(),
            html.H5("Fingering Chart"),
            dash_table.DataTable(
                id="w2-fingering-table",
                columns=[
                    {"name":"Fingering Label","id":"finger_label","type":"text"},
                    {"name":"Hole1","id":"hole1","presentation":"dropdown"},
                    {"name":"Hole2","id":"hole2","presentation":"dropdown"},
                ],
                data=[
                    {"finger_label":"Fingering1","hole1":"closed","hole2":"open"},
                ],
                dropdown={
                    "hole1":{"options":[{"label":"open","value":"open"},{"label":"closed","value":"closed"}]},
                    "hole2":{"options":[{"label":"open","value":"open"},{"label":"closed","value":"closed"}]},
                },
                editable=True,
                row_deletable=True,
                style_table={"height":"250px","overflowY":"auto"},
                style_cell={"minWidth":70},
            ),
            dbc.Button("Add Fingering Row", id="w2-add-fingering-row", size="sm", className="mt-2"),

            dbc.Row([
                dbc.Col(dbc.Button("← Back", id="w2-back-btn", color="secondary", className="mt-3"), width="auto"),
                dbc.Col(dbc.Button("Next →", id="w2-next-btn", color="primary", className="mt-3"), width="auto")
            ], justify="between")
        ])
    ], id="wizard-step2", className="mb-3", style={"display":"none"}),

    # Step 3
    dbc.Card([
        dbc.CardBody([
            html.H4("Step 3: Run Simulation & View Results"),
            html.P("Review geometry, then run the acoustic simulation."),

            dbc.Button("Plot Barrel Profile", id="w3-plot-geometry-btn", className="mb-3"),
            dcc.Graph(id="w3-geometry-plot", figure={}),

            dbc.Button("Run Simulation", id="w3-run-sim-btn", className="mb-3", color="success"),
            html.Div(id="w3-sim-stats", className="text-muted"),

            dcc.Graph(id="w3-impedance-graph", figure={}),
            dcc.Graph(id="w3-admittance-graph", figure={}),

            dbc.Row([
                dbc.Col(dbc.Button("← Back", id="w3-back-btn", color="secondary", className="mt-3"), width="auto"),
                dbc.Col(dbc.Button("Next →", id="w3-next-btn", color="primary", className="mt-3"), width="auto")
            ], justify="between")
        ])
    ], id="wizard-step3", className="mb-3", style={"display":"none"}),

    # Step 4
    dbc.Card([
        dbc.CardBody([
            html.H4("Step 4: Compare & Export"),
            html.P("Optional: Save or load designs, export geometry, compare multiple simulations."),

            dbc.InputGroup([
                dbc.InputGroupText("Design Name"),
                dbc.Input(id="w4-design-name", placeholder="MyBarrel1", value="")
            ], className="mb-2"),
            dbc.Button("Save Design", id="w4-save-design-btn", color="secondary", className="mt-1"),

            html.Hr(),
            dbc.Button("Load Design", id="w4-load-design-btn", color="info", className="mt-3", n_clicks=0),
            dcc.Upload(
                id="w4-upload-json-design",
                children=html.Div(["Drag & Drop or Click to Select JSON"]),
                style={
                    "width":"100%",
                    "height":"60px",
                    "lineHeight":"60px",
                    "borderWidth":"1px",
                    "borderStyle":"dashed",
                    "borderRadius":"5px",
                    "textAlign":"center",
                    "marginTop":"10px",
                },
                multiple=False
            ),

            html.Hr(),
            html.Div([
                dbc.Button("Export as JSON", id="w4-export-json-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as CSV", id="w4-export-csv-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as STL", id="w4-export-stl-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as PDF", id="w4-export-pdf-btn", color="success", className="me-2 mt-2"),
            ]),

            html.Hr(),
            dbc.Button("Enable Comparison Mode", id="w4-compare-mode-btn", color="warning", className="mt-2"),
            html.Div(id="w4-comparison-section", style={"display":"none"}, children=[
                html.H5("Comparison Table"),
                dbc.Table(id="w4-comparison-table", bordered=True, hover=True, responsive=True)
            ]),

            dbc.Row([
                dbc.Col(dbc.Button("← Back", id="w4-back-btn", color="secondary", className="mt-3"), width="auto"),
                dbc.Col(dbc.Button("Finish", id="w4-finish-btn", color="primary", className="mt-3"), width="auto")
            ], justify="between")
        ])
    ], id="wizard-step4", className="mb-3", style={"display":"none"}),

    # Hidden data stores
    dcc.Store(id="w2-holes-store", data=[]),
    dcc.Store(id="w2-fingering-store", data=[]),
    dcc.Store(id="w3-sim-results", data={}),
    dcc.Store(id="w4-comparison-data", data=[]),

], fluid=True)

###############################################################################
# Step Navigation
###############################################################################

@app.callback(
    Output("wizard-step","data"),
    [Input("w1-next-btn","n_clicks"),
     Input("w2-next-btn","n_clicks"),
     Input("w2-back-btn","n_clicks"),
     Input("w3-next-btn","n_clicks"),
     Input("w3-back-btn","n_clicks"),
     Input("w4-back-btn","n_clicks"),
     Input("w4-finish-btn","n_clicks")],
    State("wizard-step","data")
)
def wizard_nav(w1_next, w2_next, w2_back, w3_next, w3_back, w4_back, w4_finish, current_step):
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]
    step = current_step or 1

    if triggered == "w1-next-btn":
        step = 2
    elif triggered == "w2-next-btn":
        step = 3
    elif triggered == "w2-back-btn":
        step = 1
    elif triggered == "w3-next-btn":
        step = 4
    elif triggered == "w3-back-btn":
        step = 2
    elif triggered == "w4-back-btn":
        step = 3
    elif triggered == "w4-finish-btn":
        step = 4  # do nothing or reset to 1 if you want to restart
    return step

@app.callback(
    [Output("wizard-step1","style"),
     Output("wizard-step2","style"),
     Output("wizard-step3","style"),
     Output("wizard-step4","style")],
    Input("wizard-step","data")
)
def show_hide_steps(step):
    style_hidden = {"display":"none"}
    style_shown = {}

    s1 = style_shown if step == 1 else style_hidden
    s2 = style_shown if step == 2 else style_hidden
    s3 = style_shown if step == 3 else style_hidden
    s4 = style_shown if step == 4 else style_hidden
    return [s1, s2, s3, s4]

###############################################################################
# Step 2: Holes & Fingering
###############################################################################
@app.callback(
    Output("w2-holes-table","data"),
    Input("w2-add-hole-row","n_clicks"),
    State("w2-holes-table","data"),
    prevent_initial_call=True
)
def add_hole_row(n, current_data):
    if not current_data:
        current_data = []
    new_row = {"label": f"Hole{len(current_data)+1}", "position": 0, "diameter": 7}
    current_data.append(new_row)
    return current_data

@app.callback(
    Output("w2-fingering-table","data"),
    Input("w2-add-fingering-row","n_clicks"),
    State("w2-fingering-table","data"),
    prevent_initial_call=True
)
def add_fingering_row(n, current_data):
    if not current_data:
        current_data = []
    new_row = {"finger_label": f"Fingering{len(current_data)+1}", "hole1": "open", "hole2": "closed"}
    current_data.append(new_row)
    return current_data

@app.callback(
    [Output("w2-holes-store","data"),
     Output("w2-fingering-store","data")],
    [Input("wizard-step","data"),
     Input("w2-holes-table","data"),
     Input("w2-fingering-table","data")]
)
def store_holes_fingerings(step, holes_data, fing_data):
    return holes_data, fing_data

###############################################################################
# Step 3: Plot & Run Simulation
###############################################################################
@app.callback(
    Output("w3-geometry-plot","figure"),
    Input("w3-plot-geometry-btn","n_clicks"),
    [State("w1-bore-shape-dd","value"),
     State("w1-entry-diam-input","value"),
     State("w1-exit-diam-input","value"),
     State("w1-barrel-length-input","value"),
     State("w1-resolution-input","value")],
    prevent_initial_call=True
)
def plot_geometry(n_clicks, bore_shape, e_diam, x_diam, length_mm, resolution):
    x_vals, diam_vals = generate_barrel_profile(bore_shape, e_diam, x_diam, length_mm, resolution)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_vals, y=diam_vals, mode="lines+markers", name="Diameter"))
    fig.update_layout(
        title="Barrel Geometry Profile",
        xaxis_title="Position (mm)",
        yaxis_title="Diameter (mm)"
    )
    return fig

@app.callback(
    Output("w3-sim-results","data"),
    Output("w3-sim-stats","children"),
    Output("w3-impedance-graph","figure"),
    Output("w3-admittance-graph","figure"),
    Input("w3-run-sim-btn","n_clicks"),
    [State("w1-bore-shape-dd","value"),
     State("w1-entry-diam-input","value"),
     State("w1-exit-diam-input","value"),
     State("w1-barrel-length-input","value"),
     State("w1-resolution-input","value"),
     State("w1-material-dd","value")],
    prevent_initial_call=True
)
def run_sim(n_clicks, bore_shape, e_diam, x_diam, length_mm, resolution, material):
    simres = run_mock_simulation(bore_shape, e_diam, x_diam, length_mm, resolution, material)
    textinfo = evaluate_barrel_performance(simres)

    freq = simres["freq"]
    imp = simres["impedance_curve"]
    adm = simres["admittance_curve"]

    imp_fig = go.Figure()
    imp_fig.add_trace(go.Scatter(x=freq, y=imp, mode="lines", name="Impedance"))
    imp_fig.update_layout(title="Impedance vs Frequency")

    adm_fig = go.Figure()
    adm_fig.add_trace(go.Scatter(x=freq, y=adm, mode="lines", name="Admittance"))
    adm_fig.update_layout(title="Admittance vs Frequency")

    return simres, textinfo, imp_fig, adm_fig

###############################################################################
# Step 4: Compare & Export
###############################################################################
stored_designs = {}

@app.callback(
    Output("w4-load-design-btn","n_clicks"),
    Input("w4-upload-json-design","contents"),
    State("w4-upload-json-design","filename"),
    prevent_initial_call=True
)
def load_design(content, filename):
    if content:
        content_type, content_string = content.split(",")
        decoded = base64.b64decode(content_string)
        try:
            design_data = json.loads(decoded.decode("utf-8"))
            name = design_data.get("design_name","DesignX")
            stored_designs[name] = design_data
            print(f"Loaded design from {filename}")
        except Exception as e:
            print(f"Error parsing file: {e}")
    return 0

@app.callback(
    Output("w4-design-name","value"),
    Input("w4-save-design-btn","n_clicks"),
    [State("w4-design-name","value"),
     State("w3-sim-results","data"),
     State("w1-bore-shape-dd","value"),
     State("w1-entry-diam-input","value"),
     State("w1-exit-diam-input","value"),
     State("w1-barrel-length-input","value"),
     State("w1-resolution-input","value"),
     State("w1-material-dd","value")],
    prevent_initial_call=True
)
def save_design(n_clicks, design_name, sim_data, bore_shape, e_diam, x_diam, length_mm, resol, material):
    if not design_name:
        design_name = f"Design-{random.randint(100,999)}"
    design_dict = {
        "design_name": design_name,
        "bore_shape": bore_shape,
        "entry_diam": e_diam,
        "exit_diam": x_diam,
        "length_mm": length_mm,
        "resolution": resol,
        "material": material,
        "simulation": sim_data
    }
    stored_designs[design_name] = design_dict
    print(f"Saved design: {design_name}")
    return design_name

@app.callback(
    Output("w4-export-json-btn","disabled"),
    Output("w4-export-csv-btn","disabled"),
    Output("w4-export-stl-btn","disabled"),
    Output("w4-export-pdf-btn","disabled"),
    [Input("w4-export-json-btn","n_clicks"),
     Input("w4-export-csv-btn","n_clicks"),
     Input("w4-export-stl-btn","n_clicks"),
     Input("w4-export-pdf-btn","n_clicks")],
    State("w3-sim-results","data"),
    prevent_initial_call=True
)
def export_files(btn_json, btn_csv, btn_stl, btn_pdf, sim_results):
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if not sim_results:
        return (False,False,False,False)
    if triggered_id:
        print(f"User requested export: {triggered_id}")
        # In real usage, you'd create/download the file.
    return (False,False,False,False)

@app.callback(
    [Output("w4-comparison-section","style"),
     Output("w4-comparison-data","data"),
     Output("w4-comparison-table","children")],
    Input("w4-compare-mode-btn","n_clicks"),
    State("w3-sim-results","data"),
    State("w4-design-name","value"),
    State("w4-comparison-data","data"),
    prevent_initial_call=True
)
def compare_mode(n_clicks, simres, design_name, comp_data):
    if comp_data is None:
        comp_data = []
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    style_hidden = {"display":"none"}
    style_shown = {}

    if triggered_id=="w4-compare-mode-btn":
        style = style_shown
        if simres:
            row = {
                "name": design_name or f"Design{len(comp_data)+1}",
                "f1": simres.get("f1",0),
                "cutoff": simres.get("cutoff",0),
                "brightness": simres.get("brightness",0),
                "harmonicity": simres.get("harmonicity",0)
            }
            comp_data.append(row)

        table_header = html.Thead(html.Tr([
            html.Th("Design Name"), html.Th("f1"), html.Th("Cutoff"),
            html.Th("Brightness"), html.Th("Harmonicity")
        ]))
        rows=[]
        for c in comp_data:
            rows.append(html.Tr([
                html.Td(c["name"]),
                html.Td(f"{c['f1']:.2f}"),
                html.Td(f"{c['cutoff']:.2f}"),
                html.Td(f"{c['brightness']:.3f}"),
                html.Td(f"{c['harmonicity']:.3f}")
            ]))
        table_body=html.Tbody(rows)
        table = [table_header, table_body]
        return [style, comp_data, table]
    else:
        return [style_hidden, comp_data, None]

###############################################################################
# Run the App
###############################################################################
if __name__=="__main__":
    app.run_server(debug=True)
