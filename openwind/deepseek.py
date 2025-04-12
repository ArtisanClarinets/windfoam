import json
import random
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import numpy as np
import subprocess
import os
from pathlib import Path
from openwind import InstrumentGeometry, ImpedanceComputation
from scipy.optimize import minimize

# =============================================================================
# Configuration
# =============================================================================
OPENFOAM_TEMPLATE = Path("openfoam_template")
OPENFOAM_CASES = Path("openfoam_cases")
DESIGN_CACHE = Path("design_cache")
DESIGN_CACHE.mkdir(exist_ok=True)

# Initialize materials database
material_properties = {
    "African Blackwood": {
        "density": 1270,
        "kinematic_viscosity": 1.5e-5,
        "acoustic_properties": {
            "speed_of_sound": 4360,
            "impedance": 4.5e6
        }
    },
    "Hard Rubber": {
        "density": 1100,
        "kinematic_viscosity": 1.8e-5,
        "acoustic_properties": {
            "speed_of_sound": 2340,
            "impedance": 3.1e6
        }
    },
    "Composite": {
        "density": 950,
        "kinematic_viscosity": 1.6e-5,
        "acoustic_properties": {
            "speed_of_sound": 2800,
            "impedance": 3.8e6
        }
    }
}

# =============================================================================
# OpenFOAM Case Manager
# =============================================================================
class OpenFOAMCase:
    def __init__(self, case_name):
        self.case_path = OPENFOAM_CASES / case_name
        self.results = {}
        self._create_case_structure()
        
    def _create_case_structure(self):
        """Create OpenFOAM case directory structure"""
        dirs = ['0', 'system', 'constant', 'postProcessing']
        [os.makedirs(self.case_path/d, exist_ok=True) for d in dirs]
        
    def configure_case(self, geometry, material_props):
        """Generate OpenFOAM configuration files"""
        self._write_block_mesh(geometry)
        self._write_transport_properties(material_props)
        self._write_control_dict()
        self._write_boundary_conditions()
        
    def _write_block_mesh(self, geometry):
        """Create blockMeshDict based on barrel geometry"""
        length = geometry['length_mm'] / 1000  # Convert to meters
        inlet_radius = geometry['entry_diam'] / 2000
        outlet_radius = geometry['exit_diam'] / 2000
        
        template = f"""
        FoamFile {{
            version     2.0;
            format      ascii;
            class       dictionary;
            object      blockMeshDict;
        }}
        
        convertToMeters 1;
        
        vertices
        (
            (0 0 0)                   // 0
            ({length} 0 0)             // 1
            ({length} {outlet_radius} 0) // 2
            (0 {inlet_radius} 0)       // 3
            (0 0 {inlet_radius})       // 4
            ({length} 0 {outlet_radius}) // 5
            ({length} {outlet_radius} {outlet_radius}) // 6
            (0 {inlet_radius} {inlet_radius}) // 7
        );
        
        blocks
        (
            hex (0 1 2 3 4 5 6 7) (50 20 20) simpleGrading (1 1 1)
        );
        
        edges
        (
        );
        
        boundary
        (
            inlet
            {{
                type patch;
                faces
                (
                    (3 7 4 0)
                    (0 4 5 1)
                    (1 5 6 2)
                    (2 6 7 3)
                );
            }}
            outlet
            {{
                type patch;
                faces
                (
                    (4 7 6 5)
                );
            }}
            walls
            {{
                type wall;
                faces
                (
                    (0 3 2 1)
                    (0 1 5 4)
                    (1 2 6 5)
                    (2 3 7 6)
                    (3 0 4 7)
                );
            }}
        );
        
        mergePatchPairs
        (
        );
        """
        
        with open(self.case_path/"system"/"blockMeshDict", 'w') as f:
            f.write(template)
            
    def _write_transport_properties(self, material):
        """Set material properties for CFD simulation"""
        transport = f"""
        FoamFile
        {{
            version     2.0;
            format      ascii;
            class       dictionary;
            object      transportProperties;
        }}
        
        transportModel  Newtonian;
        
        nu              [0 2 -1 0 0 0 0] {material['kinematic_viscosity']};
        rho             [1 -3 0 0 0 0 0] {material['density']};
        """
        
        with open(self.case_path/"constant"/"transportProperties", 'w') as f:
            f.write(transport)
            
    def _write_control_dict(self):
        """Configure simulation parameters"""
        control = """
        FoamFile
        {
            version     2.0;
            format      ascii;
            class       dictionary;
            object      controlDict;
        }
        
        application     simpleFoam;
        startFrom       startTime;
        startTime       0;
        stopAt          endTime;
        endTime         500;
        deltaT          1;
        writeControl    timeStep;
        writeInterval   50;
        purgeWrite      0;
        writeFormat     ascii;
        writePrecision  6;
        runTimeModifiable yes;
        """
        
        with open(self.case_path/"system"/"controlDict", 'w') as f:
            f.write(control)
            
    def _write_boundary_conditions(self):
        """Set initial and boundary conditions"""
        # Velocity (U) file
        U_content = """
        FoamFile
        {
            version     2.0;
            format      ascii;
            class       volVectorField;
            object      U;
        }
        
        dimensions      [0 1 -1 0 0 0 0];
        
        internalField   uniform (0 0 0);
        
        boundaryField
        {
            inlet
            {
                type            fixedValue;
                value           uniform (1 0 0);
            }
            outlet
            {
                type            inletOutlet;
                inletValue      uniform (0 0 0);
                value           uniform (0 0 0);
            }
            walls
            {
                type            noSlip;
            }
        }
        """
        
        with open(self.case_path/"0"/"U", 'w') as f:
            f.write(U_content)
            
        # Pressure (p) file
        p_content = """
        FoamFile
        {
            version     2.0;
            format      ascii;
            class       volScalarField;
            object      p;
        }
        
        dimensions      [0 2 -2 0 0 0 0];
        
        internalField   uniform 0;
        
        boundaryField
        {
            inlet
            {
                type            zeroGradient;
            }
            outlet
            {
                type            fixedValue;
                value           uniform 0;
            }
            walls
            {
                type            zeroGradient;
            }
        }
        """
        
        with open(self.case_path/"0"/"p", 'w') as f:
            f.write(p_content)
            
    def run_simulation(self):
        """Execute OpenFOAM solver"""
        try:
            subprocess.run(["blockMesh"], cwd=self.case_path, check=True)
            subprocess.run(["simpleFoam"], cwd=self.case_path, check=True)
            self._parse_results()
            return True
        except subprocess.CalledProcessError as e:
            print(f"OpenFOAM error: {e}")
            return False
            
    def _parse_results(self):
        """Mock result parsing - in real implementation use PyFOAM or similar"""
        self.results['pressure'] = np.random.rand(100)
        self.results['velocity'] = np.random.rand(100)

# =============================================================================
# OpenWind Optimization Engine
# =============================================================================
class BarrelOptimizer:
    def __init__(self, target_f1=440, target_impedance=None):
        self.target_f1 = target_f1
        self.target_impedance = target_impedance
        
    def optimize_geometry(self, initial_params):
        """Optimize barrel geometry using scipy's minimize"""
        bounds = [
            (initial_params['entry_diam']*0.8, initial_params['entry_diam']*1.2),
            (initial_params['exit_diam']*0.7, initial_params['exit_diam']*1.3),
            (initial_params['length_mm']*0.9, initial_params['length_mm']*1.1)
        ]
        
        result = minimize(
            self._cost_function,
            x0=[initial_params['entry_diam'], initial_params['exit_diam'], initial_params['length_mm']],
            bounds=bounds,
            method='L-BFGS-B'
        )
        
        return {
            'entry_diam': result.x[0],
            'exit_diam': result.x[1],
            'length_mm': result.x[2],
            'success': result.success
        }
        
    def _cost_function(self, params):
        """Calculate optimization cost based on simulation results"""
        entry, exit_diam, length = params
        geometry = {
            'entry_diam': entry,
            'exit_diam': exit_diam,
            'length_mm': length
        }
        
        # Run OpenWind simulation
        result = self._run_openwind_simulation(geometry)
        
        # Calculate cost components
        f1_error = abs(result['f1'] - self.target_f1)/self.target_f1
        impedance_error = 0
        
        if self.target_impedance:
            impedance_error = np.mean(
                (result['impedance_curve'] - self.target_impedance)**2
            )
            
        return 0.7*f1_error + 0.3*impedance_error
        
    def _run_openwind_simulation(self, geometry):
        """Run OpenWind simulation for given geometry"""
        components = [
            ('barrel', 'cone', {
                'length': geometry['length_mm']/1000,
                'radius_0': geometry['entry_diam']/2000,
                'radius_1': geometry['exit_diam']/2000
            })
        ]
        
        instrument = InstrumentGeometry(components)
        frequencies = np.linspace(100, 2000, 100)
        impedance = ImpedanceComputation(frequencies, instrument)
        
        return {
            'f1': frequencies[np.argmax(np.abs(impedance))],
            'impedance_curve': np.abs(impedance),
            'frequencies': frequencies
        }

# =============================================================================
# Dash Application Core
# =============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "ClarinetFlow Studio Pro"

# Define options for UI components
bore_shape_options = [
    {"label": "Cylindrical", "value": "cylindrical"},
    {"label": "Tapered", "value": "tapered"},
    {"label": "Reverse Tapered", "value": "reverse_tapered"},
    {"label": "Parabolic", "value": "parabolic"},
    {"label": "Stepped", "value": "stepped"}
]

material_options = [{"label": k, "value": k} for k in material_properties.keys()]

# Application Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Clarinet Barrel Designer", className="text-center mb-4"),
            html.Hr()
        ], width=12)
    ]),
    
    dbc.Row([
        # Left Panel - Controls
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Design Parameters"),
                dbc.CardBody([
                    dbc.Form([
                        dbc.CardGroup([
                            dbc.Label("Bore Shape"),
                            dcc.Dropdown(
                                id="bore-shape",
                                options=bore_shape_options,
                                value="cylindrical"
                            )
                        ]),
                        
                        dbc.CardGroup([
                            dbc.Label("Material"),
                            dcc.Dropdown(
                                id="material",
                                options=material_options,
                                value="African Blackwood"
                            )
                        ]),
                        
                        dbc.CardGroup([
                            dbc.Label("Entry Diameter (mm)"),
                            dbc.Input(
                                id="entry-diam",
                                type="number",
                                min=10,
                                max=20,
                                step=0.1,
                                value=14.6
                            )
                        ]),
                        
                        dbc.CardGroup([
                            dbc.Label("Exit Diameter (mm)"),
                            dbc.Input(
                                id="exit-diam",
                                type="number",
                                min=10,
                                max=20,
                                step=0.1,
                                value=15.0
                            )
                        ]),
                        
                        dbc.CardGroup([
                            dbc.Label("Length (mm)"),
                            dbc.Input(
                                id="length",
                                type="number",
                                min=50,
                                max=100,
                                step=0.5,
                                value=66.0
                            )
                        ]),
                        
                        dbc.Button(
                            "Run Simulation",
                            id="run-simulation",
                            color="primary",
                            className="mt-3"
                        ),
                        
                        dbc.Button(
                            "Optimize Design",
                            id="optimize",
                            color="success",
                            className="mt-3"
                        )
                    ])
                ])
            ])
        ], width=4),
        
        # Right Panel - Results
        dbc.Col([
            dbc.Tabs([
                dbc.Tab([
                    dcc.Graph(id="bore-profile"),
                    dcc.Graph(id="impedance-plot")
                ], label="Acoustics"),
                
                dbc.Tab([
                    dcc.Graph(id="cfd-pressure"),
                    dcc.Graph(id="cfd-velocity")
                ], label="CFD Results"),
                
                dbc.Tab([
                    html.Div(id="optimization-results"),
                    html.Div(id="simulation-stats")
                ], label="Analysis")
            ])
        ], width=8)
    ]),
    
    dcc.Store(id="design-params"),
    dcc.Store(id="simulation-results")
], fluid=True)

# =============================================================================
# Callbacks
# =============================================================================
@app.callback(
    Output("design-params", "data"),
    Input("bore-shape", "value"),
    Input("material", "value"),
    Input("entry-diam", "value"),
    Input("exit-diam", "value"),
    Input("length", "value")
)
def update_design_params(bore_shape, material, entry_diam, exit_diam, length):
    return {
        "bore_shape": bore_shape,
        "material": material,
        "entry_diam": entry_diam,
        "exit_diam": exit_diam,
        "length_mm": length
    }

@app.callback(
    Output("bore-profile", "figure"),
    Input("design-params", "data")
)
def update_bore_profile(params):
    if params is None:
        return go.Figure()
    
    # Generate mock profile
    x = np.linspace(0, params["length_mm"], 50)
    if params["bore_shape"] == "cylindrical":
        y = np.linspace(params["entry_diam"], params["entry_diam"], 50)
    elif params["bore_shape"] == "tapered":
        y = np.linspace(params["entry_diam"], params["exit_diam"], 50)
    elif params["bore_shape"] == "reverse_tapered":
        y = np.linspace(params["exit_diam"], params["entry_diam"], 50)
    else:
        y = np.linspace(params["entry_diam"], params["exit_diam"], 50)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Bore Profile"))
    fig.update_layout(
        title="Bore Profile",
        xaxis_title="Length (mm)",
        yaxis_title="Diameter (mm)"
    )
    return fig

@app.callback(
    Output("simulation-results", "data"),
    Output("impedance-plot", "figure"),
    Input("run-simulation", "n_clicks"),
    State("design-params", "data"),
    prevent_initial_call=True
)
def run_simulation(n_clicks, params):
    if params is None:
        return {}, go.Figure()
    
    try:
        # Run OpenWind simulation
        components = [
            ('barrel', 'cone', {
                'length': params['length_mm']/1000,
                'radius_0': params['entry_diam']/2000,
                'radius_1': params['exit_diam']/2000
            })
        ]
        
        instrument = InstrumentGeometry(components)
        frequencies = np.linspace(100, 2000, 100)
        impedance = ImpedanceComputation(frequencies, instrument)
        
        results = {
            'frequencies': frequencies.tolist(),
            'impedance': np.abs(impedance).tolist(),
            'admittance': (1/np.abs(impedance)).tolist(),
            'f1': float(frequencies[np.argmax(np.abs(impedance))])
        }
        
        # Create impedance plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=frequencies,
            y=np.abs(impedance),
            mode="lines",
            name="Impedance"
        ))
        fig.update_layout(
            title="Impedance Curve",
            xaxis_title="Frequency (Hz)",
            yaxis_title="Impedance (Pa·s/m³)"
        )
        
        return results, fig
        
    except Exception as e:
        print(f"Simulation error: {e}")
        return {}, go.Figure()

@app.callback(
    Output("cfd-pressure", "figure"),
    Output("cfd-velocity", "figure"),
    Input("run-simulation", "n_clicks"),
    State("design-params", "data"),
    prevent_initial_call=True
)
def run_cfd_simulation(n_clicks, params):
    if params is None:
        return go.Figure(), go.Figure()
    
    try:
        case = OpenFOAMCase(f"design_{n_clicks}")
        case.configure_case(params, material_properties[params['material']])
        case.run_simulation()
        
        # Create mock CFD plots
        pressure_fig = go.Figure()
        pressure_fig.add_trace(go.Contour(
            z=np.random.rand(20, 20),
            colorscale="Viridis"
        ))
        pressure_fig.update_layout(title="Pressure Distribution")
        
        velocity_fig = go.Figure()
        velocity_fig.add_trace(go.Streamline(
            x=np.linspace(0, 1, 20),
            y=np.linspace(0, 1, 20),
            u=np.random.rand(20, 20),
            v=np.random.rand(20, 20)
        ))
        velocity_fig.update_layout(title="Velocity Field")
        
        return pressure_fig, velocity_fig
        
    except Exception as e:
        print(f"CFD error: {e}")
        return go.Figure(), go.Figure()

@app.callback(
    Output("optimization-results", "children"),
    Input("optimize", "n_clicks"),
    State("design-params", "data"),
    prevent_initial_call=True
)
def run_optimization(n_clicks, params):
    if params is None:
        return html.Div("No parameters available for optimization")
    
    try:
        optimizer = BarrelOptimizer(target_f1=440)
        result = optimizer.optimize_geometry(params)
        
        if result['success']:
            return dbc.Alert([
                html.H4("Optimization Results"),
                html.P(f"Optimal Entry Diameter: {result['entry_diam']:.2f} mm"),
                html.P(f"Optimal Exit Diameter: {result['exit_diam']:.2f} mm"),
                html.P(f"Optimal Length: {result['length_mm']:.2f} mm")
            ], color="success")
        else:
            return dbc.Alert("Optimization failed to converge", color="danger")
            
    except Exception as e:
        return dbc.Alert(f"Optimization error: {str(e)}", color="danger")

# =============================================================================
# Run Application
# =============================================================================
if __name__ == "__main__":
    app.run_server(debug=True, port=8051)