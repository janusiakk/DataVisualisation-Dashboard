import os
import json
import time
import dash
import pandas as pd
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from dash import Input, Output, State, dcc, html, dash_table, ALL
from dash import MATCH,ctx

external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
]

# Start
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP, 
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True
)


DATA_FOLDER = 'Dane Dash/'
frames = []  
for filename in os.listdir(DATA_FOLDER):
    if filename.endswith('.json'):
        filepath = os.path.join(DATA_FOLDER, filename)
        frames.append(pd.read_json(filepath))


df = pd.concat(frames, ignore_index=True)

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

def process_uploaded_file(name,cos):
    return
def create_filter_chips(df_in):
    if df_in.empty:
        return html.Div("Brak danych.", className="text-muted")
    
    users = sorted(df_in['osoba'].astype(str).unique())
    detected_devices = sorted(df_in['device'].astype(str).unique())
    icons = {'PC': 'bi-pc-display', 'Laptop': 'bi-laptop', 'Phone': 'bi-phone'}

    rows_list = []
    
    for user in users:
        user_df = df_in[df_in['osoba'] == user]
        buttons = []
        
        # Zbieramy domyślne wartości, żeby zainicjować pamięć
        initial_state = {} 

        for dev in detected_devices:
            has_data = dev in user_df['device'].unique()
            initial_state[dev] = has_data # Zapisujemy startowy stan (True/False)
            
            icon = icons.get(dev, 'bi-hdd')
            
            chk = dbc.Checkbox(
                id={'type': 'device-filter', 'user': user, 'device': dev},
                label=html.Div([html.I(className=f"bi {icon} me-2"), dev]),
                value=has_data,
                disabled=not has_data,
                input_class_name="btn-check", 
                label_class_name=f"btn btn-outline-primary rounded-pill me-2 mb-1 {'disabled opacity-50' if not has_data else ''}"
            )
            buttons.append(chk)
            
        user_row = dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Switch(
                        id={'type': 'user-master-switch', 'user': user},
                        value=True,
                        label=user,
                        label_class_name="fw-bold text-dark lead",
                        style={"fontSize": "1.1rem"}
                    ),
                    # --- NOWOŚĆ: Pamięć podręczna dla tego konkretnego użytkownika ---
                    dcc.Store(
                        id={'type': 'user-memory', 'user': user},
                        data=initial_state # Na start wpisujemy to, co wynika z danych
                    )
                    # -----------------------------------------------------------------
                ], className="d-flex align-items-center h-100")
            ], width=12, md=3, className="mb-2 mb-md-0"),
            
            dbc.Col(html.Div(buttons, className="d-flex flex-wrap"), width=12, md=9)
        ], className="py-2 border-bottom align-items-center")
        
        rows_list.append(user_row)
        
    return html.Div(rows_list, className="p-2")
    

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
# STRONA 2 : Obserwatorium /watcher
content_watcher = html.Div([
    html.H2("Obserwatorium Danych (Watcher)", className="mb-4"),
    
    # 2. FILTRY (Harmonijki)
    dbc.Accordion([
        # Harmonijka 1: Czas
        dbc.AccordionItem([
            dbc.Row([
                dbc.Col([
                    html.Label("Zakres dat:", className="fw-bold"),
                    dcc.DatePickerRange(
                        id='watcher-date-picker',
                        # Usunięte ograniczenia dat (min/max), aby zakres był dowolny
                        min_date_allowed=None,
                        max_date_allowed=None,
                        start_date=df['timestamp'].min().date() if not df.empty and pd.notnull(df['timestamp'].min()) else None,
                        end_date=df['timestamp'].max().date() if not df.empty and pd.notnull(df['timestamp'].max()) else None,
                        display_format='YYYY-MM-DD',
                        style={'width': '100%'}
                    ),
                ], width=4, md=4),

                dbc.Col([
                    html.Label("Tryb uwzględniania AFK:", className="fw-bold mb-2"),
                    dbc.RadioItems(
                        id="afk-mode-selector",
                        options=[
                            {"label": html.Div([html.I(className="bi bi-circle-half me-2"), "Wszystko"]), "value": "all"},
                            {"label": html.Div([html.I(className="bi bi-person-check-fill me-2"), "Bez AFK"]), "value": "active_only"},
                            {"label": html.Div([html.I(className="bi bi-robot me-2"), "Tylko AFK"]), "value": "afk_only"},
                        ],
                        value="all", # Domyślnie pokazujemy wszystko
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary",
                        labelCheckedClassName="active", # To sprawia, że wybrany przycisk jest "wypełniony"
                        style={"width": "100%"} # Opcjonalnie: rozciągnięcie na całą szerokość
                    )
                ], width=4, md=4),                           
                dbc.Col([
                    html.Label("Min. czas trwania odczytu (min):", className="fw-bold"),
                    dbc.Input(id='min-duration-input', type='number', value=0, min=0, step=1)
                ], width=4, md=4),
            ])
        ], title="📅 Filtry Czasu i Trwania"),
        
        # Harmonijka 2: Użytkownicy/Urządzenia (Pastylki)
        dbc.AccordionItem([
            # POPRAWIONE: dbc.Row i dbc.Col z dużej litery
            dbc.Row([
                dbc.Col([
                    html.Div(create_filter_chips(df), id='user-device-filters-container')
                ], width=12) # Zmieniłem na 12, żeby filtry zajmowały całą szerokość
            ])
        ], title="👤 Filtry Użytkowników i Urządzeń"), # POPRAWIONE: title jest po zamknięciu listy ']'
        
    ], start_collapsed=False, className="mb-4",always_open=True),

    # Wykres
    dbc.Card(
        dbc.CardBody([
            html.H5("Suma czasu wg Aktywności", className="card-title"),
            dcc.Graph(id='summary-bar-chart', config={'displayModeBar': False}, style={'height': '300px'})
        ]), className="mb-4 shadow-sm"
    ),

    html.Div(id='watcher-content-container')
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
    Output('summary-bar-chart', 'figure'),
    [
        Input('watcher-date-picker', 'start_date'),
        Input('watcher-date-picker', 'end_date'),
        Input('min-duration-input', 'value'),
        Input({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'value'),
        Input('afk-mode-selector', 'value')  # <--- NOWY INPUT (AFK)
    ],
    [State({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'id')]
)
def update_watcher_chart(start_date, end_date, min_duration, filter_values, afk_mode, filter_ids):
    # 1. Sprawdzenie czy są dane
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="Brak wczytanych danych")
        return fig
    
    # 2. Przygotowanie dat
    s_date = pd.to_datetime(start_date).date() if start_date else df['timestamp'].min().date()
    e_date = pd.to_datetime(end_date).date() if end_date else df['timestamp'].max().date()

    # 3. Przygotowanie dozwolonych urządzeń (Logika Pastylek)
    allowed_combinations = set()
    if not filter_values:
        # Jeśli lista filtrów jest pusta (np. start aplikacji), bierzemy wszystko
        allowed_combinations = set(zip(df['osoba'], df['device']))
    else:
        for val, id_dict in zip(filter_values, filter_ids):
            if val:
                allowed_combinations.add((id_dict['user'], id_dict['device']))

    # 4. Tworzenie masek filtrowania
    # Data
    mask_date = (df['timestamp'].dt.date >= s_date) & (df['timestamp'].dt.date <= e_date)
    
    # Duration (Minuty -> Sekundy)
    # Zabezpieczenie: (None or 0) * 60 = 0
    min_duration_sec = (min_duration or 0) * 60
    mask_dur = df['duration'] >= min_duration_sec
    
    # Urządzenia
    mask_dev = df.apply(lambda x: (x['osoba'], x['device']) in allowed_combinations, axis=1)
    
    # Wstępne filtrowanie
    filtered_df = df[mask_date & mask_dur & mask_dev].copy()

    # 5. FILTR AFK (Nowa logika)
    # Sprawdzamy czy w ogóle mamy kolumnę 'status' w danych
    if 'status' in filtered_df.columns:
        if afk_mode == 'active_only':
            # Pokaż tylko NIE-AFK (zakładamy, że afk to 'afk', reszta to praca)
            filtered_df = filtered_df[filtered_df['status'] != 'afk']
        elif afk_mode == 'afk_only':
            # Pokaż TYLKO AFK
            filtered_df = filtered_df[filtered_df['status'] == 'afk']
        # Dla 'all' nie robimy nic

    # Sprawdzenie czy po filtrach coś zostało
    if filtered_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Brak danych dla wybranych filtrów")
        return fig

    # --- AGREGACJA I PRZELICZENIE NA GODZINY ---
    
    # Inteligentny wybór kolumny (Category vs Activity)
    # Jeśli masz w plikach 'category', użyje jej. Jeśli 'activity', użyje 'activity'.
    group_col = 'category' if 'category' in filtered_df.columns else 'activity'
    
    agg_df = filtered_df.groupby(group_col)['duration'].sum().reset_index()
    
    # Sekundy -> Godziny
    agg_df['duration'] = agg_df['duration'] / 3600 
    agg_df['duration'] = agg_df['duration'].round(2) 

    # Rysowanie
    fig = px.bar(
        agg_df, 
        x=group_col, 
        y='duration', 
        title=f"Sumaryczny Czas Trwania ({afk_mode}) [godziny]", 
        labels={'duration': 'Czas (godziny)', group_col: 'Kategoria / Aktywność'},
        color=group_col,
        text_auto=True,
        template='plotly_white'
    )
    return fig

# --- CALLBACK 2: OBSŁUGA PRZEŁĄCZNIKA (Master Switch) ---
@app.callback(
    [
        Output({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'value'),
        Output({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'disabled'),
        Output({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'label_class_name')
    ],
    [Input({'type': 'user-master-switch', 'user': MATCH}, 'value')],
    [
        State({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'id'),
        State({'type': 'user-memory', 'user': MATCH}, 'data') # Pobieramy pamięć
    ]
)
def toggle_user_devices(master_switch_on, device_ids, saved_memory):
    new_values = []
    new_disabled = []
    new_classes = []
    
    # Pobieramy info o dostępności danych (z DF)
    # Uwaga: Musimy wiedzieć, czy dane w ogóle istnieją, żeby nie włączyć "pustego" urządzenia
    # nawet jak pamięć mówi True (np. z błędu).
    current_user = device_ids[0]['user']
    user_data = df[df['osoba'] == current_user]
    existing_devices = set(user_data['device'].unique()) # Set dla szybkości
    
    base_class = "btn btn-outline-primary rounded-pill me-2 mb-1"

    for dev_id in device_ids:
        device_name = dev_id['device']
        has_data = device_name in existing_devices
        
        if not master_switch_on:
            # WYŁĄCZANIE: Wszystko gaśnie
            new_values.append(False)
            new_disabled.append(True)
            new_classes.append(f"{base_class} disabled opacity-25")
        else:
            # WŁĄCZANIE: Przywracamy z pamięci
            # Sprawdzamy co było w pamięci. Domyślnie (jeśli brak w pamięci) -> True (o ile ma dane)
            should_be_checked = saved_memory.get(device_name, True) if saved_memory else True
            
            if has_data:
                # Jeśli urządzenie ma dane i było zaznaczone w pamięci -> Włączamy
                is_checked = should_be_checked
                new_values.append(is_checked)
                new_disabled.append(False)
                # Klasa zależy od tego czy zaznaczone (estetyka) - tu zawsze aktywna
                new_classes.append(base_class) 
            else:
                # Brak danych -> Zawsze wyłączone
                new_values.append(False)
                new_disabled.append(True)
                new_classes.append(f"{base_class} disabled opacity-50")

    return new_values, new_disabled, new_classes
    
# --- CALLBACK 1: ZAPAMIĘTYWANIE STANU (Memory Keeper) ---
@app.callback(
    Output({'type': 'user-memory', 'user': MATCH}, 'data'),
    Input({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'value'),
    State({'type': 'user-master-switch', 'user': MATCH}, 'value'),
    State({'type': 'device-filter', 'user': MATCH, 'device': ALL}, 'id'),
    State({'type': 'user-memory', 'user': MATCH}, 'data'),
    prevent_initial_call=True
)
def save_user_state(checkbox_values, is_master_on, checkbox_ids, current_memory):
    # Jeśli Master jest wyłączony, to znaczy, że zmiana wartości wynika 
    # z automatycznego wygaszania pastylek. NIE ZAPISUJEMY TEGO.
    if not is_master_on:
        return dash.no_update

    # Jeśli Master jest włączony, to użytkownik klika pastylki. ZAPISUJEMY.
    # Mapujemy listę wartości [True, False, True] na słownik {'PC': True, 'Phone': False...}
    new_memory = current_memory.copy() if current_memory else {}
    
    for val, id_dict in zip(checkbox_values, checkbox_ids):
        device_name = id_dict['device']
        new_memory[device_name] = val
        
    return new_memory
    

if __name__ == "__main__":
    app.run(debug=True, port=8888)