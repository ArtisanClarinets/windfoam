# callbacks.py
"""
Registers all Dash callbacks, hooking them up to the app instance.
"""

import json
import base64
from dash import Input, Output, State, callback_context, html
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

from geometry import (
    generate_barrel_profile,
    mock_thickness_map,
    build_unfolded_bore_outline
)
from simulation import (
    run_mock_simulation,
    evaluate_barrel_attributes
)

def register_callbacks(app, stored_designs):
    """
    Wires up all the callbacks with `app.callback`.
    `stored_designs` is a shared dict for loaded/saved designs.
    """

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

        # Generate x, diameter for the "barrel"
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
                "Thin walls can affect resonance or stability."
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
        avg_thickness = sum(thickness_vals) / len(thickness_vals) if thickness_vals else 0

        # Run mock acoustic simulation
        sim_results = run_mock_simulation(bore_diam_vals, material, avg_thickness)

        # Build an HTML table for the acoustic results
        acoustic_table_header = html.Thead(html.Tr([
            html.Th("Parameter"), html.Th("Value"), html.Th("Definition")
        ]))
        table_rows = [
            html.Tr([html.Td("First Resonance (f₁)"), html.Td(f"{sim_results['f1']} Hz"),
                     html.Td("Primary pitch at which the barrel resonates.")]),
            html.Tr([html.Td("Cutoff Frequency"), html.Td(f"{sim_results['cutoff']} Hz"),
                     html.Td("Above this range, resonances diminish.")]),
            html.Tr([html.Td("Resistance Score"), html.Td(f"{sim_results['resistance']}/100"),
                     html.Td("Indicates required air pressure.")]),
            html.Tr([html.Td("Harmonicity Score"), html.Td(f"{sim_results['harmonicity']}"),
                     html.Td("How closely overtones align with fundamental.")]),
            html.Tr([html.Td("Timbre Brightness"), html.Td(f"{sim_results['brightness']}"),
                     html.Td("Dark/warm vs bright/clear scale.")]),
        ]
        acoustic_table_body = html.Tbody(table_rows)
        acoustic_table = dbc.Table([acoustic_table_header, acoustic_table_body],
                                   bordered=True, hover=True, responsive=True)

        insights_header = html.H5("Performance Insights", className="mt-3")
        attribute_feedback = evaluate_barrel_attributes(sim_results)
        simulation_stats_section = [
            acoustic_table,
            html.Hr(),
            insights_header,
            attribute_feedback
        ]
        if edu_mode and len(edu_mode) > 0:
            simulation_stats_section.append(
                html.Div(
                    "Note: These metrics are approximations. Real-world testing is essential.",
                    style={"fontStyle": "italic", "marginTop": "10px"}
                )
            )

        # Build impedance/admittance plots
        imp_fig = go.Figure()
        imp_fig.add_trace(go.Scatter(
            x=sim_results["freq"],
            y=sim_results["impedance_curve"],
            mode="lines",
            name="Impedance"
        ))
        imp_fig.update_layout(
            xaxis_title="Frequency (Hz)",
            yaxis_title="Impedance (arbitrary units)",
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
            yaxis_title="Admittance (arbitrary units)",
            title="Admittance vs Frequency"
        )

        return sim_results, simulation_stats_section, imp_fig, adm_fig

    # Comparison Mode
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
            comparison_data = comparison_data[-5:]

        if len(comparison_data) == 0:
            return comparison_data, "No designs currently in comparison."

        table_header = [html.Thead(html.Tr([
            html.Th("Design Name"), html.Th("f₁ (Hz)"), html.Th("Cutoff (Hz)"),
            html.Th("Resistance"), html.Th("Brightness"), html.Th("Harmonicity")
        ]))]
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

    # Save / Load
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

    # ========== Clarinet geometry "Add Row" & "Update Geometry Plot" callbacks ==========

    @app.callback(
        Output("bore-table", "data"),
        Input("add-bore-row", "n_clicks"),
        State("bore-table", "data"),
        prevent_initial_call=True
    )
    def add_bore_row(n_clicks, current_data):
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
            "hole2": "closed",
            "hole3": "open",
            "note": ""
        }
        current_data.append(new_row)
        return current_data

    @app.callback(
        Output("clarinet-geometry-store", "data"),
        Output("clarinet-geometry-plot", "figure"),
        Input("update-geometry-btn", "n_clicks"),
        State("bore-table", "data"),
        State("holes-table", "data"),
        State("fingering-table", "data"),
        prevent_initial_call=True
    )
    def update_clarinet_geometry(n_clicks, bore_data, holes_data, fingering_data):
        """
        Draws an unfolded clarinet bore polygon: top edge + bottom edge reversed,
        returning a filled shape in Plotly to visually approximate the clarinet's cross-section.
        """
        geometry_dict = {
            "bore": bore_data,
            "holes": holes_data,
            "fingerings": fingering_data
        }

        # 1) Build the polygon outline from the bore segments
        outline_x, outline_y = build_unfolded_bore_outline(bore_data)

        # 2) Construct the Plotly figure with 2 traces:
        #    - The polygon outline (lines)
        #    - The fill using fill="toself"
        fig = go.Figure()

        # Outline only
        fig.add_trace(
            go.Scatter(
                x=outline_x,
                y=outline_y,
                mode="lines",
                fill=None,
                line_color="black",
                name="Bore Outline"
            )
        )
        # Filled shape
        fig.add_trace(
            go.Scatter(
                x=outline_x,
                y=outline_y,
                mode="lines",
                fill="toself",
                fillcolor="rgba(100, 100, 200, 0.3)",  # light bluish fill
                line_color="rgba(0,0,0,0)",  # no line
                name="Bore Fill"
            )
        )

        # 3) Possibly add shapes/circles for holes
        # (Here, we'll do an optional marker at each hole center, ignoring diameter for brevity)
        for hole in holes_data:
            x_hole = hole["position"]
            # We'll do hole y=0 for center
            fig.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=x_hole - 2, x1=x_hole + 2,  # small circle of radius=2
                y0=-2, y1=2,
                line_color="red"
            )

        # 4) Layout
        fig.update_layout(
            title="Clarinet Bore (Unfolded Cross-Section)",
            xaxis_title="Unfolded Position (mm)",
            yaxis_title="Internal Bore (mm)",
            xaxis=dict(zeroline=False, showgrid=True),
            yaxis=dict(scaleanchor="x",  # lock aspect ratio
                       scaleratio=1,
                       zeroline=False, showgrid=True),
            margin=dict(l=40, r=40, t=40, b=40)
        )

        return geometry_dict, fig

