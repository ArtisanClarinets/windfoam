# app.py
"""
Creates the Dash app, loads the layout, registers callbacks, etc.
"""

import dash
import dash_bootstrap_components as dbc

from layout import get_layout
from callbacks import register_callbacks

# Global dictionary to store loaded/saved designs:
STORED_DESIGNS = {}

# Create the Dash application:
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Clarinet Barrel Designer"

# Assign layout
app.layout = get_layout()

# Register callbacks
register_callbacks(app, STORED_DESIGNS)

# Expose server for production (e.g. gunicorn)
server = app.server
