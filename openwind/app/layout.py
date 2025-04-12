# layout.py
"""
Defines the Dash layout (the overall page structure).
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table


def get_layout():
    """
    Returns the Dash layout (a Container with Rows and Columns, etc.).
    """
    layout = dbc.Container([
        html.H1("Clarinet Barrel Designer & Simulation Wizard", className="mt-3"),
        html.Hr(),

        dbc.Row([
            # Left Column: design parameters + export/compare
            dbc.Col([
                design_parameters_card(),
                export_compare_card(),  # ensures all export/compare IDs are present
            ], width=3),

            # Right Column
            dbc.Col([
                cross_section_card(),
                acoustic_results_card(),
                clarinet_geometry_card(),
                comparative_mode_card()  # "Comparative Mode" card
            ], width=9),
        ]),

        # dcc.Store objects
        dcc.Store(id="stored-simulation-data", data={}),
        dcc.Store(id="stored-comparison-data", data=[]),
        dcc.Store(id="clarinet-geometry-store", data={})
    ], fluid=True)
    return layout


def design_parameters_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Design Parameters", className="card-title"),

            dbc.Label("Bore Shape"),
            dcc.Dropdown(
                id="bore-shape-dd",
                options=[{"label": x, "value": x} for x in
                         ["Cylindrical", "Tapered", "Reverse Tapered", "Parabolic", "Stepped"]],
                value="Cylindrical"
            ),

            dbc.Label("Exterior Shape", className="mt-3"),
            dcc.Dropdown(
                id="exterior-shape-dd",
                options=[{"label": x, "value": x} for x in [
                    "Standard (parallel exterior)",
                    "Hourglass (waist tapered)",
                    "Reverse Taper (bulged center)",
                    "Bell-like Flare (tuned for resonance)",
                    "User-Defined"
                ]],
                value="Standard (parallel exterior)"
            ),

            dbc.Label("Entry Diameter (mm)", className="mt-3"),
            dbc.Input(id="entry-diam-input", type="number", value=14.8, step=0.1),

            dbc.Label("Exit Diameter (mm)", className="mt-3"),
            dbc.Input(id="exit-diam-input", type="number", value=15.2, step=0.1),

            dbc.Label("Barrel Length (mm)", className="mt-3"),
            dbc.Input(id="barrel-length-input", type="number", value=66, step=0.5),

            dbc.Label("Segment Resolution", className="mt-3"),
            dcc.Dropdown(
                id="resolution-dd",
                options=[{"label": r, "value": r} for r in ["Low", "Medium", "High"]],
                value="Medium"
            ),

            dbc.Label("Material (Planned)", className="mt-3"),
            dcc.Dropdown(
                id="material-dd",
                options=[{"label": m, "value": m} for m in [
                    "African Blackwood", "Mopane", "Cocobolo", "Hard Rubber", "Composite"]],
                value="African Blackwood"
            ),

            dbc.Checklist(
                options=[{"label": "Educational Overlay (Tooltips)", "value": 1}],
                value=[1],
                id="educational-mode-check",
                switch=True,
                className="my-3"
            ),

            dbc.Button("Run Simulation", id="run-simulation-btn", color="primary", className="mt-3", n_clicks=0),
        ])
    ], className="mb-3")


def export_compare_card():
    """
    Includes the 'Load Design' and 'Export' buttons, as well as the
    'Enable Comparison Mode' button, matching the callback IDs:
      'compare-mode-btn', 'export-json-btn', 'export-csv-btn',
      'export-stl-btn', 'export-pdf-btn', etc.
    """
    return dbc.Card([
        dbc.CardBody([
            html.H4("Export & Compare", className="card-title"),

            # Save design
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Design Name"),
                        dbc.Input(id="save-design-name", placeholder="MyBarrel1", value="")
                    ]),
                    dbc.Button("Save Design", id="save-design-btn", color="secondary", className="mt-2"),
                ])
            ]),

            # Load design
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
            # Export buttons
            html.Div([
                dbc.Button("Export as JSON", id="export-json-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as CSV", id="export-csv-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as STL", id="export-stl-btn", color="success", className="me-2 mt-2"),
                dbc.Button("Export as PDF", id="export-pdf-btn", color="success", className="me-2 mt-2"),
            ]),

            html.Hr(),
            # Compare mode
            dbc.Button("Enable Comparison Mode", id="compare-mode-btn", color="warning", className="mt-2"),
            html.Div(id="comparison-mode-section", style={"display": "none"}),
        ])
    ], className="mb-3")


def cross_section_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Barrel Cross-Section & Wall Thickness", className="card-title"),
            dcc.Graph(id="bore-profile-graph"),
            html.Div(id="thickness-notes", className="text-muted", style={"fontSize": "0.9em"})
        ])
    ], className="mb-3")


def acoustic_results_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Acoustic Simulation Results", className="card-title"),
            html.Div(id="simulation-stats", className="mb-3"),

            html.Div(
                "Impedance vs Frequency shows how the barrel resists airflow at various pitches. ",
                className="text-muted", style={"fontSize": "0.9em", "marginBottom": "6px"}
            ),
            dcc.Graph(id="impedance-graph"),

            html.Div(
                "Admittance vs Frequency is effectively the inverse of impedance—higher admittance means "
                "the barrel allows airflow more easily.",
                className="text-muted", style={"fontSize": "0.9em", "marginTop": "12px", "marginBottom": "6px"}
            ),
            dcc.Graph(id="admittance-graph"),
        ])
    ], className="mb-3")


def clarinet_geometry_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Clarinet Geometry", className="card-title"),

            # Bore DataTable
            html.H5("Bore Segments"),
            dash_table.DataTable(
                id="bore-table",
                columns=[
                    {"name": "Start Pos (mm)", "id": "start_pos", "type": "numeric"},
                    {"name": "End Pos (mm)",   "id": "end_pos",   "type": "numeric"},
                    {"name": "Start Dia (mm)", "id": "start_dia", "type": "numeric"},
                    {"name": "End Dia (mm)",   "id": "end_dia",   "type": "numeric"},
                    {"name": "Section Type",   "id": "sec_type",  "presentation": "dropdown"},
                    {"name": "Param",          "id": "param",     "type": "numeric"},
                ],
                data=[
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
    ], className="mb-3")


def comparative_mode_card():
    return dbc.Card([
        dbc.CardBody([
            html.H4("Comparative Mode", className="card-title"),
            html.Div(id="comparison-table-container")
        ])
    ], className="mb-3")
