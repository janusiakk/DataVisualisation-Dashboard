import os
import json
import time
import dash
import pandas as pd
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
from dash import Input, Output, State, dcc, html

# --- 0. SYMULACJA DANYCH ---
DATA_FOLDER = 'Dane Dash2/'
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
    sample_data = [
        {"file": "PC_Jan_01.json", "osoba": "Jan", "device": "PC", "timestamps": ["2024-01-01 10:00", "2024-01-01 12:00"]},
        {"file": "Phone_Jan_02.json", "osoba": "Jan", "device": "Phone", "timestamps": ["2024-01-02 08:00", "2024-01-02 20:00"]},
        {"file": "PC_Anna_01.json", "osoba": "Anna", "device": "PC", "timestamps": ["2024-01-05 09:00", "2024-01-05 17:00"]},
        {"file": "Phone_Piotr_01.json", "osoba": "Piotr", "device": "Phone", "timestamps": ["2024-01-10 12:00", "2024-01-10 13:00"]},
    ]
    for item in sample_data:
        json_content = [{"osoba": item['osoba'], "device": item['device'], "timestamp": t} for t in item['timestamps']]
        with open(os.path.join(DATA_FOLDER, item['file']), 'w') as f:
            json.dump(json_content, f)
# Start
app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP], #Tu jest theme całości
    suppress_callback_exceptions=True
)
#Placeholder
df = pd.read_json('Dane Dash\Dane1.json')

# --- 1. FUNKCJE POMOCNICZE ---
def get_data_summary():
    summary_list = []
    if not os.path.exists(DATA_FOLDER):
        return pd.DataFrame()

    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_FOLDER, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    first_record = data[0]
                    summary_list.append({
                        'Osoba': first_record.get('osoba', 'N/A'),
                        'Plik': filename,
                        'Data Od': data[0].get('timestamp', 'N/A'),
                        'Data Do': data[-1].get('timestamp', 'N/A'),
                        'Liczba rekordów': len(data),
                        'Urządzenie': first_record.get('device', 'N/A')
                    })
            except Exception:
                pass
    return pd.DataFrame(summary_list)

def create_users_tables_view():
    df = get_data_summary()
    if df.empty:
        return dbc.Alert("Brak plików JSON.", color="warning")
    
    layout_elements = []
    unique_users = sorted(df['Osoba'].unique())
    
    for osoba in unique_users:
        layout_elements.append(
            html.H3(
                [html.I(className="bi bi-person-fill me-2"), f"Użytkownik: {osoba}"], 
                className="mt-4 text-primary"
            )
        )
        person_df = df[df['Osoba'] == osoba].drop(columns=['Osoba'])
        
        table = dbc.Table.from_dataframe(
            person_df, 
            striped=True, 
            bordered=True, 
            hover=True, 
            responsive=True, 
            className="mb-4 shadow-sm",
            style={"width": "auto"} 
        )
        layout_elements.append(table)
        layout_elements.append(html.Hr())
        
    return html.Div(layout_elements)

# LAYOUTY (STRONY) ---

# # STRONA : Startowa /
# content_home = html.Div([
#     html.H1("Strona Startowa", className="display-4"),
#     html.P("Witaj w panelu administracyjnym.", className="lead"),
#     html.Hr(className="my-2"),
#     html.P("Wybierz odpowiednią zakładkę z menu po lewej stronie, aby rozpocząć."),
#     dbc.Button("Przejdź do Użytkowników", color="primary", href="/uzytkownicy"), 
# ], className="p-5 bg-light rounded-3")

# STRONA 1 : Użytkownicy /
content_users = html.Div([
    html.H1("Panel kontroli danych wejściowych"),
    dbc.Alert("Poniżej znajduje się wykaz wczytanych plików.", color="light"),
    create_users_tables_view()
])

# STRONA 2 : Obserwatorium /watcher
content_watcher = html.Div([
    html.H2("Obserwatorium Danych (Watcher)", className="mb-4"),
    
    # HARMONIJKA (Accordion) do filtrów
    dbc.Accordion(
        [
            dbc.AccordionItem(
                [
                    dbc.Row([
                        dbc.Col([
                            html.Label("Wybierz zakres czasu:", className="fw-bold mb-2"),
                            dcc.DatePickerRange(
                                id='watcher-date-picker',
                                min_date_allowed=df['timestamp'].min().date() if not df.empty else None,
                                max_date_allowed=df['timestamp'].max().date() if not df.empty else None,
                                initial_visible_month=df['timestamp'].min().date() if not df.empty else None,
                                start_date=df['timestamp'].min().date() if not df.empty else None,
                                end_date=df['timestamp'].max().date() if not df.empty else None,
                                display_format='YYYY-MM-DD',
                                style={'width': '100%'}
                            ),
                            html.Div(id='watcher-date-debug', className="text-muted small mt-1")
                        ], width=12, md=6),
                        
                        dbc.Col([
                            html.Label("Filtruj po aplikacji (opcjonalnie):", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id='watcher-app-dropdown',
                                options=[{'label': app, 'value': app} for app in df['app'].unique()] if not df.empty else [],
                                placeholder="Wszystkie aplikacje",
                                multi=True
                            )
                        ], width=12, md=6)
                    ])
                ],
                title="⚙️ Filtry Czasu i Danych",
                item_id="filters"
            ),
        ],
        start_collapsed=False, # Domyślnie rozwinięte
        className="mb-4 shadow-sm"
    ),

    # KONTENER NA WYKRESY / DANE (Wypełniany przez callback)
    dbc.Spinner(html.Div(id='watcher-content-container'), color="primary")
])
# STRONA 3 : Podsumowanie /summary
content_summary=[]
# STRONA 4 : Oś czasu /timeline
content_timeline=[]
# STRONA 5 : Ustawienia /settings
content_settings = html.Div([html.H1("Ustawienia"), dbc.Alert("Panel administracyjny.", color="dark")])

# STRONA 6 : Dodaj nowe pliki /addFile (Docelowo to będzie surowy activity watch)
content_addFile = html.Div([
    html.H1("Dodaj nowe dane"),
    html.P("Przeciągnij pliki tutaj lub kliknij, aby otworzyć okno wyboru.", className="text-muted"),
    html.Hr(),
    
    # KOMPONENT UPLOAD
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            html.I(className="bi bi-cloud-arrow-up-fill display-4 text-primary"), # Ikona chmury
            html.H5("Przeciągnij i upuść pliki tutaj", className="mt-2"),
            html.Div("lub", className="small text-muted"),
            html.A("Wybierz pliki z dysku", className="btn btn-outline-primary mt-2 btn-sm")
        ]),
        style={
            'width': '100%',
            'height': '250px',
            'lineHeight': '60px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '10px',
            'textAlign': 'center',
            'borderColor': '#0d6efd', # Kolor primary bootstrapa
            'backgroundColor': '#f8f9fa',
            'display': 'flex',           # Centrowanie Flexbox
            'flexDirection': 'column',
            'justifyContent': 'center',
            'alignItems': 'center',
            'cursor': 'pointer'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    
    # MIEJSCE NA KOMUNIKAT ZWROTNY
    html.Div(id='output-file-upload', className="mt-4")
])

# --- 3. GŁÓWNA STRUKTURA ---
sidebar = html.Div(
    [
        html.H2("Menu", className="display-6"),
        html.Hr(),
        dbc.Nav([
            dbc.NavLink("Użytkownicy", href="/", active="exact"),
            dbc.NavLink("Obserwatorium", href="/watcher", active="exact"),
            dbc.NavLink("Podsumowanie", href="/summary", active="exact"),
            dbc.NavLink("Oś czasu", href="/timeline", active="exact"),
            dbc.NavLink("Ustawienia", href="/settings", active="exact"),
            dbc.NavLink("Załącz pliki", href="/addFile", active="exact"),
        ], vertical=True, pills=True),
    ],
    style={"width": "16rem", "height": "100vh", "background-color": "#f8f9fa", "padding": "2rem 1rem"}
)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dbc.Collapse(sidebar, id="sidebar", is_open=True, dimension="width"),
    html.Div([
        dbc.Container([
            dbc.Button("Menu", id="sidebar-toggle", color="secondary", outline=True, className="mb-3 mt-3"),
            html.Div(id="page-content")
        ], fluid=True)
    ], style={"flexGrow": 1, "padding": "0 2rem", "overflow": "auto", "height": "100vh"})
], className="d-flex")

# --- 4. CALLBACKI ---
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page_content(pathname):
    if pathname == "/": 
        return content_users
    elif pathname == "/watcher": 
        return content_watcher
    elif pathname == "/summary": 
        return content_summary
    elif pathname == "/timeline": 
        return content_timeline
    elif pathname == "/settings": 
        return content_settings
    elif pathname == "/addFile": 
        return content_addFile
    
    # Obsługa błędu 404
    return dbc.Alert(f"404: Nie znaleziono strony o adresie {pathname}", color="danger")

@app.callback(Output('output-file-upload', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))
def update_output(list_of_contents, list_of_names):
    if list_of_contents is not None:
        messages = []
        # Iterujemy przez wszystkie wrzucone pliki (obsługa multiple=True)
        for contents, name in zip(list_of_contents, list_of_names):
            # WYWOŁANIE FUNKCJI PLACEHOLDER
            result_msg = process_uploaded_file(name, contents)
            
            # Tworzymy ładny komunikat dla każdego pliku
            messages.append(
                dbc.Alert([
                    html.I(className="bi bi-check-circle-fill me-2"),
                    result_msg
                ], color="success", className="mb-2")
            )
        return messages
    return "" # Pusty string jeśli nic nie wrzucono

@app.callback(Output("sidebar", "is_open"), Input("sidebar-toggle", "n_clicks"), [State("sidebar", "is_open")])
def toggle_sidebar(n, is_open):
    if n: return not is_open
    return is_open

@app.callback(Output("tab-content", "children"), [Input("tabs", "active_tab"), Input("store", "data")])
def render_tab_content(active_tab, data):
    if active_tab and data:
        if active_tab == "scatter": return dcc.Graph(figure=data["scatter"])
        elif active_tab == "histogram": return dbc.Row([dbc.Col(dcc.Graph(figure=data["hist_1"]), width=6), dbc.Col(dcc.Graph(figure=data["hist_2"]), width=6)])
    return "Kliknij 'Generuj Wykresy'."

@app.callback(Output("store", "data"), [Input("button", "n_clicks")])
def generate_graphs(n):
    if not n: return None
    time.sleep(0.5)
    data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 100)
    return {
        "scatter": go.Figure(data=[go.Scatter(x=data[:, 0], y=data[:, 1], mode="markers")]),
        "hist_1": go.Figure(data=[go.Histogram(x=data[:, 0])]),
        "hist_2": go.Figure(data=[go.Histogram(x=data[:, 1])])
    }
@app.callback(
    Output('watcher-content-container', 'children'),
    [Input('watcher-date-picker', 'start_date'),
     Input('watcher-date-picker', 'end_date'),
     Input('watcher-app-dropdown', 'value')]
)
def update_watcher_content(start_date, end_date, selected_apps):
    if df.empty:
        return dbc.Alert("Brak danych w systemie.", color="warning")
    
    if not start_date or not end_date:
        return dbc.Alert("Wybierz pełny zakres dat.", color="info")

    # Filtrowanie danych
    mask = (df['timestamp'].dt.date >= pd.to_datetime(start_date).date()) & \
           (df['timestamp'].dt.date <= pd.to_datetime(end_date).date())
    filtered_df = df.loc[mask]

    if selected_apps:
        filtered_df = filtered_df[filtered_df['app'].isin(selected_apps)]

    if filtered_df.empty:
        return dbc.Alert("Brak danych dla wybranych kryteriów.", color="warning")

    # Tworzenie podglądu (prosta statystyka + tabela)
    total_duration = filtered_df['duration'].sum()
    top_app = filtered_df.groupby('app')['duration'].sum().idxmax()
    
    # Karta statystyk
    stats_card = dbc.Card(
        dbc.CardBody([
            html.H4("Podsumowanie wyboru", className="card-title"),
            html.Hr(),
            html.P(f"Liczba rekordów: {len(filtered_df)}"),
            html.P(f"Suma czasu trwania: {total_duration:.2f} s"),
            html.P(f"Najczęstsza aplikacja: {top_app}")
        ]),
        className="mb-4 bg-light"
    )

    # Tabela podglądowa (Dash DataTable dla lepszej wydajności niż dbc.Table przy dużych danych)
    table_preview = dash_table.DataTable(
        data=filtered_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in filtered_df.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
    )

    return html.Div([
        stats_card,
        html.H5("Podgląd danych surowych:"),
        table_preview
    ])

if __name__ == "__main__":
    app.run(debug=True, port=8888)