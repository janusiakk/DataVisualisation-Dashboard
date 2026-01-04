import time
import dash
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
from dash import Input, Output, State, dcc, html

EXPLAINER = """W tym przykładzie mamy dwa panele zwijane:
1. **Sidebar (Lewo):** Zwija się w poziomie (dimension="width").
2. **Filtry (Góra):** Zwija się w pionie (domyślne zachowanie), spychając treść w dół."""

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- 1. DEFINICJA SIDEBARA (LEWY PANEL) ---
sidebar_content = html.Div(
    [
        html.H2("Menu", className="display-6"),
        html.Hr(),
        dbc.Nav([
            dbc.NavLink("Użytkownicy", href="#", active=True),
            dbc.NavLink("Obserwatorium", href="#"),
            dbc.NavLink("Animacja czasu", href="#"),
            dbc.NavLink("Ustawienia", href="#"),
        ], vertical=True, pills=True),
    ],
    style={
        "width": "16rem", 
        "height": "100vh", 
        "background-color": "#f8f9fa", 
        "padding": "2rem 1rem",
        "border-right": "1px solid #dee2e6"
    }
)

# --- 2. DEFINICJA TOP PANELU (GÓRNY PANEL) ---
top_panel = dbc.Card(
    dbc.CardBody([
        html.H4("Zaawansowane Filtry", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.Label("Wybierz zakres dat:"),
                dcc.DatePickerRange(id='date-picker', start_date_placeholder_text="Start", end_date_placeholder_text="End")
            ], width=6),
            dbc.Col([
                html.Label("Wybierz kategorię:"),
                dcc.Dropdown(options=['Opcja A', 'Opcja B', 'Opcja C'], value='Opcja A')
            ], width=6),
        ]),
        html.Hr(),
        dbc.Button("Zastosuj filtry", color="success", size="sm")
    ]),
    className="mb-3 shadow-sm" # Margines dolny i cień
)


# --- 3. LAYOUT GŁÓWNY ---
app.layout = html.Div(
    [
        # A. LEWY SIDEBAR (wewnątrz Collapse poziomym)
        dbc.Collapse(
            sidebar_content,
            id="sidebar",
            is_open=True,
            dimension="width", # Zwijanie w bok
        ),
        
        # B. OBSZAR GŁÓWNY (Prawa strona)
        html.Div(
            [
                dbc.Container([
                    html.H1("Layout Hybrydowy"),
                    dcc.Markdown(EXPLAINER),
                    
                    # Pasek narzędzi (Przyciski sterujące)
                    dbc.Row([
                        dbc.Col(
                            dbc.ButtonGroup([
                                dbc.Button("Menu (Bok)", id="sidebar-toggle", color="secondary", outline=True),
                                dbc.Button("Filtry (Góra)", id="top-toggle", color="secondary", outline=True),
                            ]),
                            width="auto"
                        ),
                        dbc.Col(
                            dbc.Button("Regenerate graphs", id="button", color="primary"),
                            width="auto"
                        )
                    ], className="mb-3"),

                    # C. GÓRNY PANEL (wewnątrz Collapse pionowym)
                    dbc.Collapse(
                        top_panel,
                        id="top-collapse",
                        is_open=False, # Domyślnie zamknięty
                        # dimension="height" jest domyślne, więc nie trzeba pisać
                    ),

                    # D. ZAKŁADKI I WYKRESY
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Scatter", tab_id="scatter"),
                            dbc.Tab(label="Histograms", tab_id="histogram"),
                        ],
                        id="tabs",
                        active_tab="scatter",
                    ),
                    
                    dbc.Spinner(
                        [
                            dcc.Store(id="store"),
                            html.Div(id="tab-content", className="p-4"),
                        ],
                        delay_show=100,
                    ),
                ], fluid=True)
            ],
            # Styl prawej strony: flex-grow wypełnia resztę ekranu
            style={"flexGrow": 1, "padding": "2rem", "overflow": "auto", "height": "100vh"}
        )
    ],
    className="d-flex" # Flexbox utrzymuje Sidebar i Main Content obok siebie
)


# --- CALLBACK 1: OBSŁUGA LEWEGO SIDEBARA ---
@app.callback(
    Output("sidebar", "is_open"),
    Input("sidebar-toggle", "n_clicks"),
    [State("sidebar", "is_open")],
)
def toggle_sidebar(n, is_open):
    if n:
        return not is_open
    return is_open

# --- CALLBACK 2: OBSŁUGA GÓRNEGO PANELU (NOWY) ---
@app.callback(
    Output("top-collapse", "is_open"),
    Input("top-toggle", "n_clicks"),
    [State("top-collapse", "is_open")],
)
def toggle_top(n, is_open):
    if n:
        return not is_open
    return is_open

# --- CALLBACK 3: GENEROWANIE TREŚCI ZAKŁADEK ---
@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab"), Input("store", "data")],
)
def render_tab_content(active_tab, data):
    if active_tab and data is not None:
        if active_tab == "scatter":
            return dcc.Graph(figure=data["scatter"])
        elif active_tab == "histogram":
            return dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=data["hist_1"]), width=6),
                    dbc.Col(dcc.Graph(figure=data["hist_2"]), width=6),
                ]
            )
    return "No tab selected"

# --- CALLBACK 4: DANE (SYMULACJA) ---
@app.callback(Output("store", "data"), [Input("button", "n_clicks")])
def generate_graphs(n):
    if not n:
        return {k: go.Figure(data=[]) for k in ["scatter", "hist_1", "hist_2"]}
    
    # Krótszy czas dla wygody testowania
    time.sleep(0.5) 
    data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 100)

    scatter = go.Figure(data=[go.Scatter(x=data[:, 0], y=data[:, 1], mode="markers")])
    hist_1 = go.Figure(data=[go.Histogram(x=data[:, 0])])
    hist_2 = go.Figure(data=[go.Histogram(x=data[:, 1])])

    return {"scatter": scatter, "hist_1": hist_1, "hist_2": hist_2}

if __name__ == "__main__":
    app.run(debug=True, port=8888)