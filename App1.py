import os, json, time, numpy as np, pandas as pd, dash
import plotly.express as px, plotly.graph_objs as go, dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, dash_table, ALL, MATCH, ctx
#region Start
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP, #Wygląd
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True
)
DATA_FOLDER = 'Dane Dash/' #Folder do zczytania gotowych danych
frames = []  
for filename in os.listdir(DATA_FOLDER):
    if filename.endswith('.json'):
        filepath = os.path.join(DATA_FOLDER, filename)
        frames.append(pd.read_json(filepath))
df = pd.concat(frames, ignore_index=True)
#endregion
#region --- 1. FUNKCJE POMOCNICZE ---
# --- DEFINICJA ZAWARTOŚCI FILTRÓW (OFFCANVAS) ---
def get_base_panel_style(left_pos="0px"):
    return {
        "top": HEADER_HEIGHT,
        "height": "fit-content",
        "maxHeight": f"calc(100vh - {HEADER_HEIGHT} - 20px)",
        "width": PANEL_WIDTH,
        "left": left_pos,
        
        "position": "fixed",   
        "border": "1px solid #dee2e6",
        "borderTop": "0", "borderLeft": "0",
        "borderRadius": "0 0 10px 10px",
        "boxShadow": "0px 10px 20px rgba(0,0,0,0.15)",
        "zIndex": 1045, # Pod paskiem menu
        
        # --- TU JEST NAPRAWA ---
        # Animujemy 'left' (do przesuwania za menu) ORAZ 'transform' (do chowania w górę)
        # Dzięki temu panel płynnie wjedzie pod pasek menu.
        "transition": "left 0.3s ease-in-out, transform 0.3s ease-in-out" 
    }
def create_global_filters_layout():
    return html.Div([
        # --- SEKCJA 1: CZAS ---
        html.H6("📅 Ustawienia Czasu", className="fw-bold text-primary mb-3"),
        
        dbc.Row([
            # Daty
            dbc.Col([
                html.Label("Zakres dat:", className="small text-muted fw-bold"),
                dcc.DatePickerRange(
                    id='watcher-date-picker',
                    min_date_allowed=None, max_date_allowed=None,
                    start_date=df['timestamp'].min().date() if not df.empty else None,
                    end_date=df['timestamp'].max().date() if not df.empty else None,
                    display_format='YYYY-MM-DD',
                    style={'width': '100%', 'fontSize': '0.8rem'}
                ),
            ], width=12, className="mb-3"),

            # Przywrócone Ładne Guziki AFK
            dbc.Col([
                html.Label("Tryb pracy:", className="small text-muted fw-bold mb-1"),
                dbc.RadioItems(
                    id="afk-mode-selector",
                    options=[
                        {
                            "label": html.Div([html.I(className="bi bi-circle-half me-2"), "Wszystko"]), 
                            "value": "all"
                        },
                        {
                            "label": html.Div([html.I(className="bi bi-person-check-fill me-2"), "Aktywność"]), 
                            "value": "active_only"
                        },
                        {
                            "label": html.Div([html.I(className="bi bi-robot me-2"), "AFK"]), 
                            "value": "afk_only"
                        },
                    ],
                    value="all",
                    className="btn-group w-100",       # w-100 rozciąga grupę na całą szerokość
                    inputClassName="btn-check",        # Ukrywa kropki radia
                    labelClassName="btn btn-outline-primary", # Styl guzików
                    labelCheckedClassName="active"     # Styl aktywnego guzika
                )
            ], width=12, className="mb-3"),

            # Min czas
            dbc.Col([
                html.Label("Ignoruj krótsze niż (min):", className="small text-muted fw-bold"),
                dbc.Input(id='min-duration-input', type='number', value=0, min=0, step=1, size="sm")
            ], width=12),
        ]),

        html.Hr(className="my-4"), # Linia oddzielająca

        # --- SEKCJA 2: UŻYTKOWNICY ---
        html.H6("👤 Użytkownicy i Urządzenia", className="fw-bold text-primary mb-3"),
        
        html.Div(create_filter_chips(df), id='user-device-filters-container')
    ], className="p-1")
def create_smart_slot(side, title, is_app_mode=False):
    
    
    # 1. Pobieramy listę użytkowników
    unique_users = sorted(df['osoba'].astype(str).unique())
    
    # 2. Budujemy opcje głównego Dropdowna (Scope)
    # Mamy opcję specjalną "comparison" oraz listę osób
    scope_options = [
        {'label': '👥 PORÓWNANIE (Ranking)', 'value': 'comparison'},
        {'label': '--- Użytkownicy ---', 'value': 'disabled', 'disabled': True}
    ] + [{'label': f"👤 {u}", 'value': u} for u in unique_users]

    # Kontrolki w nagłówku
    controls = []

    # A. WYBÓR TRYBU (Porównanie vs Osoba)
    scope_dd = dcc.Dropdown(
        id=f'smart-{side}-scope',
        options=scope_options,
        value='comparison', # Domyślnie tryb porównania
        clearable=False, searchable=False,
        style={'fontSize': '0.85rem'}
    )
    controls.append(dbc.Col(scope_dd, width=4))

    # B. INPUT "TOP N" (Tylko dla prawej strony - Aplikacje)
    if is_app_mode:
        limit_input = dbc.InputGroup([
            dbc.InputGroupText("Top:", style={'fontSize': '0.7rem', 'padding': '4px'}),
            dbc.Input(
                id=f'smart-{side}-limit',
                type='number',
                value=10, min=1, max=50, step=1,
                style={'fontSize': '0.8rem', 'textAlign': 'center'}
            )
        ], size="sm")
        controls.append(dbc.Col(limit_input, width=3))

    # C. WYBÓR RODZAJU WYKRESU (Opcje puste na start, wypełni je Callback UI)
    type_dd = dcc.Dropdown(
        id=f'smart-{side}-type',
        options=[], # Callback to wypełni
        value='bar_h',
        clearable=False, searchable=False,
        style={'fontSize': '0.85rem'}
    )
    # Dopasowanie szerokości w zależności czy jest Top N
    width_type = 4 if is_app_mode else 7 
    controls.append(dbc.Col(type_dd, width=width_type))

    # 3. Złożenie całości
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                # Nagłówek z tytułem
                html.H6(title, className="card-title mb-2 text-muted fw-bold"),
                # Pasek narzędzi
                dbc.Row(controls, className="g-1 mb-3 align-items-center"),
                # Wykres
                dcc.Graph(id=f'smart-{side}-chart', config={'displayModeBar': False}, style={'height': '350px'})
            ])
        ], className="shadow-sm h-100"),
        width=12, md=6, className="mb-4"
    )
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
def create_filtered_df(start_date, end_date, min_duration, filter_values, afk_mode,  filter_ids):
    """ Zwraca ramkę dannych przefiltrowaną zgodnie z głównym filtrem na górze. 
        Callbacki wykresów będą z tego korzystać """
     # 1. Sprawdzenie czy są dane
    if df.empty:
        return go.Figure().update_layout(title="Brak wczytanych danych")
    
    # 2. Logika filtrów (Data, Duration, Urządzenia) - BEZ ZMIAN
    s_date = pd.to_datetime(start_date).date() if start_date else df['timestamp'].min().date()
    e_date = pd.to_datetime(end_date).date() if end_date else df['timestamp'].max().date()

    allowed_combinations = set()
    if not filter_values:
        allowed_combinations = set(zip(df['osoba'], df['device']))
    else:
        for val, id_dict in zip(filter_values, filter_ids):
            if val:
                allowed_combinations.add((id_dict['user'], id_dict['device']))

    mask_date = (df['timestamp'].dt.date >= s_date) & (df['timestamp'].dt.date <= e_date)
    min_duration_sec = (min_duration or 0) * 60
    mask_dur = df['duration'] >= min_duration_sec
    mask_dev = df.apply(lambda x: (x['osoba'], x['device']) in allowed_combinations, axis=1)
    
    filtered_df = df[mask_date & mask_dur & mask_dev].copy()

    # 3. Filtr AFK - BEZ ZMIAN
    if 'status' in filtered_df.columns:
        if afk_mode == 'active_only':
            filtered_df = filtered_df[filtered_df['status'] != 'afk']
        elif afk_mode == 'afk_only':
            filtered_df = filtered_df[filtered_df['status'] == 'afk']
    return filtered_df
def create_options_for_weekly_screentime(df_in):
    # 1. Pobieramy listę użytkowników
    unique_users = sorted(df_in['osoba'].astype(str).unique())
    # 2. Budujemy opcje głównego Dropdowna (Scope)
    # Mamy  listę osób
    opcje = [{'label': f"👤 {u}", 'value': u} for u in unique_users]
    dropdown =  dcc.Dropdown(
    id=f'Wybor-osoby-weekly-time',
    options=opcje,
    value=unique_users[0], # Domyślnie pierwszy z listy
    clearable=False, searchable=False,
    style={'fontSize': '0.85rem'}
    )
    return dropdown

#endregion
#region --- 2. LAYOUTY (STRONY) ---
# STRONA 1 : Użytkownicy /
content_users = html.Div([
    html.H1("Panel kontroli danych wejściowych"),
    dbc.Alert("Poniżej znajduje się wykaz wczytanych plików.", color="light"),
    create_users_tables_view()
])
# STRONA 2 : Obserwatorium /watcher
content_watcher = html.Div([
    html.H2("Obserwatorium Danych", className="mb-4 display-6 text-primary"),

    # SEKCJA KPI
    html.Div(id='watcher-kpi-container', className="mb-4"),

    # --- TU BYŁY FILTRY - USUNIĘTE ---
    # Zostawiamy ewentualnie informację, jakie filtry są aktywne (opcjonalnie)
    
    html.H4("Analiza Szczegółowa", className="mb-3 text-secondary"),
    
    dbc.Row([
        create_smart_slot('left', "Analiza Kategorii", is_app_mode=False),
        create_smart_slot('right', "Analiza Aplikacji (Top N)", is_app_mode=True)
    ]),

    #html.Div(id='watcher-content-container')
])
# STRONA 3 : Podsumowanie /summary
content_summary= html.Div([
    html.H1('Typowy tydzień'),
    create_options_for_weekly_screentime(df),
    dcc.Graph(id='weekly_hours_plotly')
])
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
# endregion
#region --- 3. GŁÓWNA STRUKTURA ---
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
# --- STAŁE WYMIARY ---
HEADER_HEIGHT = "70px"
PANEL_WIDTH_NUM = 545      # Szerokość w pikselach (int do obliczeń)
PANEL_WIDTH = f"{PANEL_WIDTH_NUM}px" # String do CSS
filters_panel = dbc.Offcanvas(
    children=[create_global_filters_layout()],
    id="filters-offcanvas",
    title="Filtry Globalne",
    placement="top", scrollable=True, backdrop=False, is_open=False,
    # Styl startowy (zostanie nadpisany przez callback, ale musi być)
    style=get_base_panel_style("16rem") 
)
# Zwiększenie warstwy panel 2
extra_panel_style = get_base_panel_style("16rem")
# Ręcznie podbijamy warstwę (baza ma 1045)
extra_panel_style["zIndex"] = 1060 
extra_panel = dbc.Offcanvas(
    children=[
        html.H6("⚙️ Dodatkowe Opcje", className="fw-bold text-primary mb-3"),
        dbc.Alert("To jest drugi niezależny panel.", color="info"),
        html.P("Może zawierać ustawienia eksportu, zaawansowane parametry itp."),
        dbc.Button("Przykładowa akcja", color="dark", outline=True, size="sm")
    ],
    id="extra-offcanvas",
    title="Opcje Dodatkowe",
    placement="top", scrollable=True, backdrop=False, is_open=False,
    style=extra_panel_style
)
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    
    # Przechowujemy szerokość sidebara w pamięci przeglądarki (opcjonalnie), 
    # ale tutaj obliczymy to w locie.
    
    dbc.Collapse(sidebar, id="sidebar", is_open=True, dimension="width"),
    
    # DWA PANELE
    filters_panel,
    extra_panel,

    html.Div([
        dbc.Container([
            
            # --- NAGŁÓWEK Z 3 GUZIKAMI ---
            dbc.Row([
                # 1. Menu
                dbc.Col([
                    dbc.Button([html.I(className="bi bi-list me-2"), "Menu"], 
                               id="sidebar-toggle", color="secondary", outline=True, className="me-2"),
                ], width="auto"),
                
                # 2. Filtry
                dbc.Col([
                    dbc.Button([html.I(className="bi bi-funnel-fill me-2"), "Filtry"], 
                               id="open-filters-btn", color="primary", className="fw-bold shadow-sm me-2"),
                ], width="auto"),

                # 3. NOWY GUZIK (Opcje)
                dbc.Col([
                    dbc.Button([html.I(className="bi bi-gear-fill me-2"), "Opcje"], 
                               id="open-extra-btn", color="info", className="fw-bold shadow-sm text-white"),
                ], width="auto"),

                dbc.Col(width=True) # Reszta pusta
            ], 
            className="align-items-center border-bottom px-3",
            style={
                "height": HEADER_HEIGHT, 
                "overflow": "hidden", "position": "sticky", "top": "0", 
                "backgroundColor": "white", "zIndex": 2000
            }),

            html.Div(id="page-content", className="p-4")
            
        ], fluid=True, className="p-0")
    ], style={"flexGrow": 1, "padding": "0", "overflow": "auto", "height": "100vh"})
], className="d-flex")# --- 4. CALLBACKI ---
#endregion
# region CALLBACKS
# region CALLBACK - PAGE LOADERS
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
# endregion
# region CALLBACK - WYKRESY

@app.callback(
    Output('weekly_hours_plotly', 'figure'),
    [
        Input('watcher-date-picker', 'start_date'),
        Input('watcher-date-picker', 'end_date'),
        Input('min-duration-input', 'value'),
        Input({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'value'),
        Input('afk-mode-selector', 'value'),
    ],
    [State({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'id')],
    Input('Wybor-osoby-weekly-time','value')
)
def weekly_hours(start_date, end_date, min_duration, filter_values, afk_mode,  filter_ids,osoba):
    filtered_df = create_filtered_df(start_date, end_date, min_duration, filter_values, afk_mode,  filter_ids)
    # dodajemy kolumny z nazwą i numerem tygodnia i godziną
    timestamp = filtered_df['timestamp']
    timestamp_pl = timestamp.dt.tz_convert('Europe/Warsaw')
    filtered_df['timestamp_pl'] = timestamp_pl
    filtered_df['day_of_year'] = timestamp_pl.dt.day_of_year
    filtered_df['weekday'] = timestamp_pl.dt.day_name('Pl')
    filtered_df['weekday_number'] = timestamp_pl.dt.weekday + 1
    filtered_df['hour'] = timestamp_pl.dt.hour
    # Obliczam średni czas aktywności w danym dnium tygodniaz podziałem na kategorie
    df2 = filtered_df.groupby(["osoba","weekday","weekday_number","category","day_of_year"])['duration'].aggregate(total_activity = "sum").reset_index()
    df2 = df2.groupby(["osoba","weekday","weekday_number","category"])['total_activity'].aggregate(average_activity = "mean").reset_index()
    df2['average_activity'] /= 3600
    # Tworze wykres
    #osoba = "AK" # TODO
    df3 = df2[df2['osoba'] == osoba]
    ylim = np.ceil(df2.groupby(['osoba','weekday'])['average_activity'].sum().reset_index()['average_activity'].max())
    plot = px.bar(df3,
            x='weekday',
            y = 'average_activity',
            color='category',
            category_orders={'weekday':['Poniedziałek','Wtorek','Środa','Czwartek','Piątek','Sobota','Niedziela']},
            labels={'weekday':'dzień tygodnia','average_activity':'średnia aktywność (godz.)','category':'kategoria'},
            title=f"Średnia aktywność w dniach tygodnia: {osoba}",
            template='plotly_white',
            range_y=[0,ylim])
    return plot

@app.callback(
    Output('summary-bar-chart', 'figure'),
    [
        Input('watcher-date-picker', 'start_date'),
        Input('watcher-date-picker', 'end_date'),
        Input('min-duration-input', 'value'),
        Input({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'value'),
        Input('afk-mode-selector', 'value'),
        Input('chart-type-selector', 'value') # <--- NOWY INPUT (Typ wykresu)
    ],
    [State({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'id')]
)
def update_watcher_chart(start_date, end_date, min_duration, filter_values, afk_mode, chart_type, filter_ids):
    # to co tu było wcześniej, teraz robi poniższa funkcja
    filtered_df = create_filtered_df(start_date, end_date, min_duration, filter_values, afk_mode,  filter_ids)

    if filtered_df.empty:
        return go.Figure().update_layout(title="Brak danych dla wybranych filtrów")

    # 4. AGREGACJA DANYCH
    group_col = 'category' if 'category' in filtered_df.columns else 'activity'
    agg_df = filtered_df.groupby(group_col)['duration'].sum().reset_index()
    
    # Przeliczenie na godziny
    agg_df['duration'] = (agg_df['duration'] / 3600).round(2)

    # 5. GENEROWANIE WYKRESU ZALEŻNIE OD WYBORU (NOWOŚĆ)
    common_title = f"Sumaryczny Czas Trwania ({afk_mode}) [godziny]"
    
    if chart_type == 'pie' or chart_type == 'donut':
        # Wykresy kołowe
        fig = px.pie(
            agg_df, 
            names=group_col, 
            values='duration', 
            title=common_title,
            hole=0.4 if chart_type == 'donut' else 0, # Dziura dla donuta
            template='plotly_white'
        )
        fig.update_traces(textinfo='percent+label')
        
    elif chart_type == 'bar_h':
        # Wykres paskowy (poziomy)
        fig = px.bar(
            agg_df, 
            x='duration', 
            y=group_col, 
            title=common_title,
            orientation='h', # Kluczowe dla poziomego wykresu
            labels={'duration': 'Czas (h)', group_col: 'Aktywność'},
            color=group_col,
            text_auto=True,
            template='plotly_white'
        )
        
    else:
        # Domyślny (Kolumnowy pionowy)
        fig = px.bar(
            agg_df, 
            x=group_col, 
            y='duration', 
            title=common_title,
            labels={'duration': 'Czas (h)', group_col: 'Aktywność'},
            color=group_col,
            text_auto=True,
            template='plotly_white'
        )

    return fig
# endregion
# region --- CALLBACK 2: OBSŁUGA PRZEŁĄCZNIKA (Master Switch) ---
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
#endregion
# region --- CALLBACK ZAPAMIĘTYWANIE STANU (Memory Keeper) ---
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
@app.callback(
    [
        Output('chart-1', 'figure'),
        Output('chart-2', 'figure'),
        Output('chart-3', 'figure'),
        Output('chart-4', 'figure')
    ],
    [
        Input('watcher-date-picker', 'start_date'),
        Input('watcher-date-picker', 'end_date'),
        Input('min-duration-input', 'value'),
        Input({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'value'),
        Input('afk-mode-selector', 'value'),
        
        # Typy Wykresów
        Input('chart-selector-1', 'value'),
        Input('chart-selector-2', 'value'),
        Input('chart-selector-3', 'value'),
        Input('chart-selector-4', 'value'),
        
        # Specyficzne kontrolki
        Input('chart-1-user-select', 'value'), # User dla #1
        Input('chart-2-user-select', 'value'), # User dla #2
        Input('chart-2-limit', 'value'),       # Top N dla #2
        Input('chart-4-limit', 'value')        # Top N dla #4
    ],
    [State({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'id')]
)
def update_quad_charts(start_date, end_date, min_duration, filter_values, afk_mode, 
                       type1, type2, type3, type4, 
                       user_1, user_2, limit_2, limit_4, # Nowe argumenty
                       filter_ids):
    
    # --- 1. FILTROWANIE GLOBALNE ---
    empty = go.Figure().update_layout(title="Brak danych")
    if df.empty: return empty, empty, empty, empty

    s_date = pd.to_datetime(start_date).date() if start_date else df['timestamp'].min().date()
    e_date = pd.to_datetime(end_date).date() if end_date else df['timestamp'].max().date()

    allowed = set()
    if filter_values:
        for val, id_dict in zip(filter_values, filter_ids):
            if val: allowed.add((id_dict['user'], id_dict['device']))
    else:
        allowed = set(zip(df['osoba'], df['device']))

    mask_date = (df['timestamp'].dt.date >= s_date) & (df['timestamp'].dt.date <= e_date)
    min_dur_sec = (min_duration or 0) * 60
    mask_dur = df['duration'] >= min_dur_sec
    mask_dev = df.apply(lambda x: (x['osoba'], x['device']) in allowed, axis=1)
    
    main_df = df[mask_date & mask_dur & mask_dev].copy()

    if 'status' in main_df.columns:
        if afk_mode == 'active_only': main_df = main_df[main_df['status'] != 'afk']
        elif afk_mode == 'afk_only': main_df = main_df[main_df['status'] == 'afk']

    if main_df.empty: return empty, empty, empty, empty

    # --- 2. PRZYGOTOWANIE DANYCH ---
    
    # Wybieramy nazwę kolumny kategorii (bezpiecznik)
    cat_col = 'category' if 'category' in main_df.columns else 'activity'
    # Wybieramy nazwę kolumny aplikacji (bezpiecznik - jeśli nie ma 'app', użyj kategorii)
    app_col = 'app' if 'app' in main_df.columns else cat_col 

    # --- FUNKCJA POMOCNICZA: Top N Filtering ---
    def get_top_n_data(source_df, group_cols, value_col, limit):
        """Zwraca DF ograniczony do N najpopularniejszych wartości w kolumnie value_col."""
        # 1. Sumujemy czasy dla każdej apki
        totals = source_df.groupby(value_col)['duration'].sum().sort_values(ascending=False)
        # 2. Bierzemy top N nazw
        top_names = totals.head(limit).index.tolist()
        # 3. Filtrujemy dane, zostawiając tylko te apki
        filtered = source_df[source_df[value_col].isin(top_names)].copy()
        
        # Opcjonalnie: Resztę wrzucamy do worka "Inne" (dla czytelności wykresu)
        # Ale user prosił o ograniczenie, więc proste ucięcie jest czystsze.
        return filtered, top_names

    # --- DANE DLA WYKRESU #1 (Kategorie + User) ---
    df_1 = main_df.copy()
    title_1 = "Wszyscy"
    if user_1 and user_1 != 'all':
        df_1 = df_1[df_1['osoba'] == user_1]
        title_1 = user_1
    
    agg_1 = df_1.groupby([cat_col, 'osoba'])['duration'].sum().reset_index()
    agg_1['duration'] = (agg_1['duration']/3600).round(2)

    # --- DANE DLA WYKRESU #2 (Aplikacje + User + Limit) ---
    df_2 = main_df.copy()
    title_2 = "Wszyscy"
    if user_2 and user_2 != 'all':
        df_2 = df_2[df_2['osoba'] == user_2]
        title_2 = user_2
    
    # Najpierw ucinamy Top N Aplikacji dla wybranego zakresu
    df_2_limited, _ = get_top_n_data(df_2, [], app_col, limit_2 or 10)
    
    agg_2 = df_2_limited.groupby([app_col, 'osoba'])['duration'].sum().reset_index()
    agg_2['duration'] = (agg_2['duration']/3600).round(2)

    # --- DANE DLA WYKRESU #3 (Ranking Userów wg Kategorii) ---
    # Tutaj nie limitujemy kategorii, bo zazwyczaj jest ich mało (YouTube, Excel...)
    agg_3 = main_df.groupby(['osoba', cat_col])['duration'].sum().reset_index()
    agg_3['duration'] = (agg_3['duration']/3600).round(2)

    # --- DANE DLA WYKRESU #4 (Ranking Userów wg Aplikacji + Limit) ---
    # Tutaj limitujemy aplikacje globalnie (żeby kolory były spójne dla wszystkich userów)
    df_4_limited, _ = get_top_n_data(main_df, [], app_col, limit_4 or 10)
    
    agg_4 = df_4_limited.groupby(['osoba', app_col])['duration'].sum().reset_index()
    agg_4['duration'] = (agg_4['duration']/3600).round(2)


    # --- 3. GENEROWANIE WYKRESÓW ---
    def generate_fig(chart_type, data, x, color, title):
        if data.empty: return go.Figure().update_layout(title="Brak danych")
        
        # Sortowanie dla słupków skumulowanych (żeby największe kawałki były na dole/lewej)
        data = data.sort_values(by='duration', ascending=False)

        if chart_type in ['pie', 'donut']:
            # Kołowy sumuje po głównym wymiarze
            pie_d = data.groupby(x if x != 'duration' else color)['duration'].sum().reset_index()
            # Jeśli app/category jest osią, to używamy jej jako names
            names_col = x if x != 'duration' else color
            
            fig = px.pie(pie_d, names=names_col, values='duration', title=title,
                         hole=0.4 if chart_type=='donut' else 0, template='plotly_white')
            fig.update_traces(textinfo='percent+label')
        
        elif chart_type == 'bar_h':
            fig = px.bar(data, x='duration', y=x, color=color, title=title, orientation='h',
                         labels={'duration': 'h', x: ''}, text_auto=True, template='plotly_white')
        else:
            fig = px.bar(data, x=x, y='duration', color=color, title=title,
                         labels={'duration': 'h', x: ''}, text_auto=True, template='plotly_white')

        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", y=-0.2), # Legenda pod spodem
            # Skracanie etykiet osi Y dla aplikacji, bo nazwy plików exe bywają długie
            yaxis=dict(tickfont=dict(size=10)) 
        )
        return fig

    return (
        # #1: Kategorie (dla Usera)
        generate_fig(type1, agg_1, cat_col, 'osoba', f"Kat.: {title_1}"),
        
        # #2: Aplikacje (dla Usera) -> Oś X to Aplikacja, Kolor to Osoba (choć to jedna osoba)
        # Przy jednej osobie kolorowanie po osobie jest zbędne, ale zachowuje spójność.
        # Alternatywnie color=app_col by był bardziej kolorowy. Zróbmy color=app_col dla czytelności.
        generate_fig(type2, agg_2, app_col, app_col if user_2 != 'all' else 'osoba', f"Top {limit_2} App: {title_2}"),
        
        # #3: Ranking Userów (Kolor = Kategoria)
        generate_fig(type3, agg_3, 'osoba', cat_col, "Ranking (Kategorie)"),
        
        # #4: Ranking Userów (Kolor = Aplikacja)
        generate_fig(type4, agg_4, 'osoba', app_col, f"Ranking (Top {limit_4} App)")
    )
@app.callback(
    [Output('smart-left-type', 'options'), Output('smart-left-type', 'value'),
     Output('smart-right-type', 'options'), Output('smart-right-type', 'value')],
    [Input('smart-left-scope', 'value'), Input('smart-right-scope', 'value')]
)
def update_smart_options(left_scope, right_scope):
    """
    Dynamicznie zmienia listę dostępnych wykresów w zależności od tego,
    czy wybrano tryb 'comparison' czy konkretną osobę.
    """
    
    def get_opts(scope):
        if scope == 'comparison':
            return [
                {'label': 'Ranking (Paskowy)', 'value': 'bar_h'},
                {'label': 'Porównanie (Słupki)', 'value': 'bar'},
                {'label': 'Struktura (Stacked 100%)', 'value': 'bar_stack'}
            ], 'bar_h'
        else:
            return [
                {'label': 'Kołowy (Pie)', 'value': 'pie'},
                {'label': 'Pierścieniowy (Donut)', 'value': 'donut'},
                {'label': 'Paskowy (Bar H)', 'value': 'bar_h'},
                {'label': 'Kolumnowy (Bar V)', 'value': 'bar'}
            ], 'pie' # Dla osoby domyślnie kołowy

    l_opts, l_val = get_opts(left_scope)
    r_opts, r_val = get_opts(right_scope)
    
    return l_opts, l_val, r_opts, r_val
@app.callback(
    [
        Output("sidebar", "is_open"),           # 1. Stan Sidebara
        Output("filters-offcanvas", "is_open"), # 2. Stan Filtrów
        Output("filters-offcanvas", "style"),   # 3. Pozycja Filtrów
        Output("extra-offcanvas", "is_open"),   # 4. Stan Extra
        Output("extra-offcanvas", "style"),     # 5. Pozycja Extra
    ],
    [
        Input("sidebar-toggle", "n_clicks"),
        Input("open-filters-btn", "n_clicks"),
        Input("open-extra-btn", "n_clicks"),
    ],
    [
        State("sidebar", "is_open"),
        State("filters-offcanvas", "is_open"),
        State("extra-offcanvas", "is_open"),
    ]
)
def manage_layout(n_side, n_filt, n_extra, side_open, filt_open, extra_open):
    # Sprawdzamy, który guzik został kliknięty
    ctx_id = ctx.triggered_id

    # 1. AKTUALIZACJA STANÓW (OTWARTE/ZAMKNIĘTE)
    if ctx_id == "sidebar-toggle":
        side_open = not side_open
    elif ctx_id == "open-filters-btn":
        filt_open = not filt_open
    elif ctx_id == "open-extra-btn":
        extra_open = not extra_open

    # 2. OBLICZANIE PUNKTU STARTOWEGO (OFFSET)
    # Jeśli sidebar otwarty, startujemy od 16rem. Jeśli zamknięty, od 0.
    # Uwaga: 16rem to ok. 256px, ale dla bezpieczeństwa w CSS użyjemy stringa calc()
    base_offset_css = "16rem" if side_open else "0px"

    # 3. OBLICZANIE POZYCJI PANELI (LOGIKA SLOTÓW)
    
    # Styl bazowy
    style_filt = get_base_panel_style()
    style_extra = get_base_panel_style()

    # --- Logika dla Panelu 1 (Filtry) ---
    # Filtry zawsze chcą być pierwsze (Slot 1)
    style_filt["left"] = base_offset_css
    
    # --- Logika dla Panelu 2 (Extra) ---
    if filt_open:
        # Jeśli Filtry są otwarte, Extra musi stanąć OBOK nich (Slot 2)
        # Używamy CSS calc: Base + Szerokość Panelu
        style_extra["left"] = f"calc({base_offset_css} + {PANEL_WIDTH})"
    else:
        # Jeśli Filtry są zamknięte, Extra zajmuje pierwsze wolne miejsce (Slot 1)
        style_extra["left"] = base_offset_css

    # 4. ZWROT WYNIKÓW
    return side_open, filt_open, style_filt, extra_open, style_extra
@app.callback(
    [Output('smart-left-chart', 'figure'), Output('smart-right-chart', 'figure')],
    [
        Input('watcher-date-picker', 'start_date'),
        Input('watcher-date-picker', 'end_date'),
        Input('min-duration-input', 'value'),
        Input({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'value'),
        Input('afk-mode-selector', 'value'),
        
        # Nowe Inputy z inteligentnych okien
        Input('smart-left-scope', 'value'),  # Kto? (Lewe)
        Input('smart-left-type', 'value'),   # Jaki wykres? (Lewe)
        
        Input('smart-right-scope', 'value'), # Kto? (Prawe)
        Input('smart-right-type', 'value'),  # Jaki wykres? (Prawe)
        Input('smart-right-limit', 'value')  # Top N (Prawe)
    ],
    [State({'type': 'device-filter', 'user': ALL, 'device': ALL}, 'id')]
)
def update_smart_charts(start_date, end_date, min_duration, filter_values, afk_mode, 
                        l_scope, l_type, 
                        r_scope, r_type, r_limit,
                        filter_ids):

    # --- 1. FILTROWANIE GLOBALNE (Standard) ---
    empty = go.Figure().update_layout(title="Brak danych", template='plotly_white')
    if df.empty: return empty, empty

    s_date = pd.to_datetime(start_date).date() if start_date else df['timestamp'].min().date()
    e_date = pd.to_datetime(end_date).date() if end_date else df['timestamp'].max().date()

    allowed = set()
    if filter_values:
        for val, id_dict in zip(filter_values, filter_ids):
            if val: allowed.add((id_dict['user'], id_dict['device']))
    else:
        allowed = set(zip(df['osoba'], df['device']))

    mask_date = (df['timestamp'].dt.date >= s_date) & (df['timestamp'].dt.date <= e_date)
    min_dur_sec = (min_duration or 0) * 60
    mask_dur = df['duration'] >= min_dur_sec
    mask_dev = df.apply(lambda x: (x['osoba'], x['device']) in allowed, axis=1)
    
    main_df = df[mask_date & mask_dur & mask_dev].copy()

    if 'status' in main_df.columns:
        if afk_mode == 'active_only': main_df = main_df[main_df['status'] != 'afk']
        elif afk_mode == 'afk_only': main_df = main_df[main_df['status'] == 'afk']

    if main_df.empty: return empty, empty

    # --- 2. PRZYGOTOWANIE KOLUMN ---
    cat_col = 'category' if 'category' in main_df.columns else 'activity'
    app_col = 'app' if 'app' in main_df.columns else cat_col # Fallback

    # --- 3. UNIWERSALNA FUNKCJA GENERUJĄCA WYKRES ---
    def build_chart(scope, chart_type, data_source, group_col, limit=None):
        """
        scope: 'comparison' lub nazwa usera
        chart_type: 'bar', 'pie', etc.
        data_source: przefiltrowany DataFrame
        group_col: po czym grupujemy (kategoria lub app)
        limit: opcjonalny limit Top N
        """
        local_df = data_source.copy()

        # A. FILTRACJA ZAKRESU (Osoba czy Wszyscy?)
        if scope != 'comparison':
            local_df = local_df[local_df['osoba'] == scope]
            if local_df.empty: return empty

        # B. LOGIKA TOP N (Dla prawej strony)
        if limit:
            # Znajdź Top N wartości w całej wybranej populacji
            top_vals = local_df.groupby(group_col)['duration'].sum().sort_values(ascending=False).head(limit).index
            local_df = local_df[local_df[group_col].isin(top_vals)]

        # C. AGREGACJA
        # Jeśli Comparison -> Grupujemy po [Osoba, Kategoria] (żeby mieć kolory per kategoria)
        # Jeśli Single User -> Grupujemy po [Kategoria]
        
        if scope == 'comparison':
            # X=Osoba, Kolor=Kategoria
            agg = local_df.groupby(['osoba', group_col])['duration'].sum().reset_index()
            x_axis = 'osoba'
            color_axis = group_col
            title = "Ranking Zespołu"
        else:
            # X=Kategoria, Kolor=Kategoria
            agg = local_df.groupby(group_col)['duration'].sum().reset_index()
            x_axis = group_col
            color_axis = group_col
            title = f"Aktywność: {scope}"

        agg['duration'] = (agg['duration'] / 3600).round(2)
        agg = agg.sort_values(by='duration', ascending=True) # Sortowanie do wykresu

        # D. RYSOWANIE
        if chart_type in ['pie', 'donut']:
            fig = px.pie(agg, names=x_axis, values='duration', hole=0.4 if chart_type=='donut' else 0)
            fig.update_traces(textinfo='percent+label')
        
        elif chart_type == 'bar_h':
            fig = px.bar(agg, x='duration', y=x_axis, color=color_axis, orientation='h', text_auto=True)
            
        elif chart_type == 'bar':
            fig = px.bar(agg, x=x_axis, y='duration', color=color_axis, text_auto=True)
            
        elif chart_type == 'bar_stack':
            # Specjalny tryb znormalizowany (kto ma jaki % udziału w pracy)
            # W Plotly Express robi się to normalnym bar chartem, logika jest w danych
            fig = px.bar(agg, x='duration', y=x_axis, color=color_axis, orientation='h', text_auto=True)
            # Można dodać barnorm='percent' w update_layout jeśli chcesz % na osi

        fig.update_layout(title=title, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        return fig

    # --- 4. WYWOŁANIE DLA LEWEJ I PRAWEJ STRONY ---
    
    # LEWA: Kategorie (bez limitu)
    fig_left = build_chart(l_scope, l_type, main_df, cat_col, limit=None)
    
    # PRAWA: Aplikacje (z limitem Top N)
    fig_right = build_chart(r_scope, r_type, main_df, app_col, limit=r_limit)

    return fig_left, fig_right
# endregion
# endregion
if __name__ == "__main__":
    app.run(debug=True, port=8888)