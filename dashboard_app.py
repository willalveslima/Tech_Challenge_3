# Importa as bibliotecas necessárias
import dash
# ctx para saber qual input disparou
from dash import dcc, html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
# Para trocar tema
from dash_bootstrap_templates import ThemeSwitchAIO, load_figure_template
import dash_daq as daq  # Para o switch de tema visualmente melhor
import plotly.graph_objects as go
import pandas as pd
import sqlalchemy
import pickle
import os
import datetime
from flask import Flask
from dotenv import load_dotenv

# --- Configurações ---

load_dotenv()
DB_FILE = os.getenv("DB_FOLDER") + os.getenv("DB_FILE")
TABLE_NAME = os.getenv("TABLE_NAME")
DB_URL = f"sqlite:///{DB_FILE}"
MODEL_FILENAME = os.getenv("MODEL_FILENAME")
SCALER_FILENAME = os.getenv("SCALER_FILENAME")
FEATURE_COLUMNS = ['cpu_percent', 'memory_percent', 'disk_percent']
UPDATE_INTERVAL_MS = 30000  # 30 segundos

# --- Carregamento Inicial do Modelo e Scaler ---
loaded_model = None
loaded_scaler = None
print("Carregando modelo e scaler...")
try:
    if os.path.exists(MODEL_FILENAME):
        with open(MODEL_FILENAME, 'rb') as f:
            loaded_model = pickle.load(f)
        print(f"Modelo '{MODEL_FILENAME}' carregado.")
    else:
        print(f"Erro: Arquivo do modelo '{MODEL_FILENAME}' não encontrado.")
    if os.path.exists(SCALER_FILENAME):
        with open(SCALER_FILENAME, 'rb') as f:
            loaded_scaler = pickle.load(f)
        print(f"Scaler '{SCALER_FILENAME}' carregado.")
    else:
        print(f"Erro: Arquivo do scaler '{SCALER_FILENAME}' não encontrado.")
except Exception as e:
    print(f"Erro crítico ao carregar modelo ou scaler: {e}")
    loaded_model, loaded_scaler = None, None

# --- Inicialização do Flask e Dash ---
server = Flask(__name__)
# Templates para o ThemeSwitchAIO (temas claro e escuro do Bootstrap)
template_theme1 = "flatly"
template_theme2 = "darkly"
url_theme1 = dbc.themes.FLATLY
url_theme2 = dbc.themes.DARKLY
# Carrega templates Plotly correspondentes
load_figure_template([template_theme1, template_theme2])

app = dash.Dash(
    __name__,
    server=server,
    # Inicia com tema claro
    external_stylesheets=[url_theme1, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Dashboard de Monitoramento"
)

# --- Funções Auxiliares ---


def load_and_predict_data(scaler, model, start_date=None, end_date=None):
    """Carrega dados do DB, filtra por data, aplica scaler/modelo."""
    if not os.path.exists(DB_FILE):
        print(f"Erro: Arquivo do banco de dados '{DB_FILE}' não encontrado.")
        return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])

    try:
        engine = sqlalchemy.create_engine(DB_URL)
        with engine.connect() as connection:
            if not sqlalchemy.inspect(engine).has_table(TABLE_NAME):
                print(f"Erro: Tabela '{TABLE_NAME}' não encontrada.")
                return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])

            query = f"SELECT * FROM {TABLE_NAME} ORDER BY timestamp ASC"
            df = pd.read_sql_query(
                query, connection, parse_dates=['timestamp'])

            if df.empty:
                print("Tabela de dados vazia.")
                return df

            # Filtragem por Data (se start_date e end_date forem fornecidos)
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    # Adiciona 1 dia ao end_date para incluir o dia inteiro
                    end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
                    df = df[(df['timestamp'] >= start_dt)
                            & (df['timestamp'] < end_dt)]
                    print(
                        f"Filtrando dados entre {start_dt.date()} e {end_dt.date() - pd.Timedelta(days=1)}")
                except Exception as date_e:
                    print(f"Erro ao aplicar filtro de data: {date_e}")
                    # Continua sem filtro de data se houver erro

            if df.empty:
                print("Nenhum dado encontrado no período selecionado.")
                df['anomaly'] = 1  # Adiciona coluna vazia para consistência
                return df

            # Prepara dados para predição
            df_features = df[FEATURE_COLUMNS].copy()

            # Trata NaNs
            if df_features.isnull().sum().any():
                print("Valores ausentes encontrados. Preenchendo com a média.")
                for col in FEATURE_COLUMNS:
                    if df_features[col].isnull().any():
                        mean_val = df_features[col].mean()
                        df_features[col].fillna(mean_val, inplace=True)

            # Aplica scaler e modelo
            if scaler and model:
                data_scaled = scaler.transform(df_features)
                predictions = model.predict(data_scaled)
                df['anomaly'] = predictions
            else:
                df['anomaly'] = 1  # Marca como normal se não houver modelo/scaler

            return df

    except Exception as e:
        print(f"Erro ao carregar ou processar dados do banco: {e}")
        return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])


def create_time_series_chart(df, y_column, title, theme_template):
    """Cria gráfico de série temporal com destaque para anomalias, adaptado ao tema."""
    fig = go.Figure()
    if df.empty:  # Retorna figura vazia se não houver dados
        fig.update_layout(title=f"{title} (Sem dados)",
                          template=theme_template, yaxis_range=[0, 105])
        return fig

    fig.add_trace(go.Scatter(x=df['timestamp'],
                  y=df[y_column], mode='lines', name='Uso (%)'))

    anomalies = df[df['anomaly'] == -1]
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'], y=anomalies[y_column], mode='markers', name='Anomalia',
            marker=dict(color='red', size=8, symbol='x')
        ))

    fig.update_layout(
        title=title, xaxis_title='Tempo', yaxis_title='Uso (%)', yaxis_range=[0, 105],
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=20, r=20, t=40, b=20),
        template=theme_template  # Aplica o template de tema (claro/escuro)
    )
    return fig


def create_gauge_chart(value, title, theme_template):
    """Cria um gráfico gauge para um valor específico."""
    if value is None or pd.isna(value):
        value = 0  # Trata valor nulo

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            # Corrige a cor da barra para o tema correto
            'bar': {'color': "darkblue" if theme_template == template_theme2 else "lightblue"},
            'steps': [
                {'range': [0, 50], 'color': 'lightgreen'},
                {'range': [50, 80], 'color': 'yellow'},
                {'range': [80, 100], 'color': 'red'}],
            # Linha de threshold
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 90}
        }
    ))
    fig.update_layout(
        height=200,  # Ajusta altura
        margin=dict(l=10, r=10, t=40, b=10),
        template=theme_template
    )
    return fig


# --- Layout do Dashboard ---
# Componente para trocar tema claro/escuro
theme_switch = ThemeSwitchAIO(
    aio_id="theme",
    themes=[url_theme1, url_theme2],
    icons={
        "left": "fa fa-moon",  # Ícone de lua para o tema escuro
        "right": "fa fa-sun"   # Ícone de sol para o tema claro
    }
)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Dashboard de Monitoramento de Recursos do Sistema",
                className="text-center my-2"), width=10),
        dbc.Col(theme_switch, width=2,
                className="d-flex align-items-center justify-content-end")
    ]),

    dbc.Row([
        dbc.Col([
            html.Label("Selecione o Período:", style={'fontWeight': 'bold'}),
            dcc.DatePickerRange(
                id='date-picker-range',
                # Ajuste conforme necessário
                min_date_allowed=datetime.date(2020, 1, 1),
                max_date_allowed=datetime.date.today() + datetime.timedelta(days=1),
                # Default: últimos 7 dias
                start_date=datetime.date.today() - datetime.timedelta(days=7),
                end_date=datetime.date.today(),
                display_format='DD/MM/YYYY',
                className="mb-2"
            )
        ], width=12, md=4),
        # Espaço para tabela de estatísticas
        dbc.Col(html.Div(id='stats-table-div'), width=12, md=8)
    ], align="center", className="mb-3"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='gauge-cpu'), width=12, md=4),
        dbc.Col(dcc.Graph(id='gauge-memory'), width=12, md=4),
        dbc.Col(dcc.Graph(id='gauge-disk'), width=12, md=4),
    ], className="mb-3"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='cpu-graph'), width=12, lg=4),
        dbc.Col(dcc.Graph(id='memory-graph'), width=12, lg=4),
        dbc.Col(dcc.Graph(id='disk-graph'), width=12, lg=4),
    ]),

    dcc.Interval(id='interval-component',
                 interval=UPDATE_INTERVAL_MS, n_intervals=0),
    dcc.Store(id='data-store'),  # Armazena os dados filtrados
    dcc.Store(id='theme-store', data=template_theme1)  # Armazena o tema atual

], fluid=True, className="dbc")  # Adiciona classe dbc para templates funcionarem

# --- Callbacks ---

# Callback para atualizar o tema armazenado quando o switch é clicado


@app.callback(
    Output('theme-store', 'data'),
    Input(ThemeSwitchAIO.ids.switch("theme"), "value")  # Input do switch de tema
)
def update_theme_store(toggle):
    # Corrige a inversão dos temas
    return template_theme1 if toggle else template_theme2

# Callback para atualizar os dados no dcc.Store (acionado por intervalo ou mudança de data)


@app.callback(
    Output('data-store', 'data'),
    Input('interval-component', 'n_intervals'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_data_store(n_intervals, start_date, end_date):
    """Carrega dados, filtra por data e armazena em JSON."""
    triggered_id = ctx.triggered_id
    print(f"Atualizando dados... Trigger: {triggered_id}")
    df = load_and_predict_data(
        loaded_scaler, loaded_model, start_date, end_date)
    return df.to_json(date_format='iso', orient='split')

# Callback principal para atualizar todos os gráficos e a tabela de estatísticas


@app.callback(
    Output('cpu-graph', 'figure'),
    Output('memory-graph', 'figure'),
    Output('disk-graph', 'figure'),
    Output('gauge-cpu', 'figure'),
    Output('gauge-memory', 'figure'),
    Output('gauge-disk', 'figure'),
    # Output para a tabela de estatísticas
    Output('stats-table-div', 'children'),
    Input('data-store', 'data'),          # Input dos dados processados
    Input('theme-store', 'data')          # Input do tema atual
)
def update_outputs(json_data, current_theme):
    """Lê dados do store, tema e atualiza gráficos e tabela."""
    if json_data is None:
        # Retorna tudo vazio se não houver dados
        empty_fig = go.Figure().update_layout(title="Aguardando dados...",
                                              template=current_theme, yaxis_range=[0, 105])
        empty_gauge = create_gauge_chart(0, "...", current_theme)
        empty_table = dbc.Alert("Nenhum dado para exibir.", color="warning")
        return empty_fig, empty_fig, empty_fig, empty_gauge, empty_gauge, empty_gauge, empty_table

    # Converte JSON de volta para DataFrame
    df = pd.read_json(json_data, orient='split')

    # Verifica se o DataFrame não está vazio
    if df.empty:
        empty_fig = go.Figure().update_layout(title="Sem dados no período",
                                              template=current_theme, yaxis_range=[0, 105])
        empty_gauge = create_gauge_chart(0, "Sem dados", current_theme)
        empty_table = dbc.Alert(
            "Nenhum dado encontrado para o período selecionado.", color="info")
        return empty_fig, empty_fig, empty_fig, empty_gauge, empty_gauge, empty_gauge, empty_table

    # Garante que timestamp é datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # --- Cria Gráficos de Série Temporal ---
    fig_cpu = create_time_series_chart(
        df, 'cpu_percent', 'Uso de CPU (%)', current_theme)
    fig_mem = create_time_series_chart(
        df, 'memory_percent', 'Uso de Memória (%)', current_theme)
    fig_disk = create_time_series_chart(
        df, 'disk_percent', 'Uso de Disco (%)', current_theme)

    # --- Cria Gráficos Gauge (com o valor mais recente) ---
    latest_data = df.iloc[-1]  # Pega a última linha (dado mais recente)
    gauge_cpu = create_gauge_chart(
        latest_data['cpu_percent'], "CPU Atual", current_theme)
    gauge_mem = create_gauge_chart(
        latest_data['memory_percent'], "Memória Atual", current_theme)
    gauge_disk = create_gauge_chart(
        latest_data['disk_percent'], "Disco Atual", current_theme)

    # --- Cria Tabela de Estatísticas ---
    total_points = len(df)
    anomaly_points = df[df['anomaly'] == -
                        1].shape[0] if 'anomaly' in df.columns else 0
    anomaly_perc = (anomaly_points / total_points *
                    100) if total_points > 0 else 0
    first_ts = df['timestamp'].min().strftime(
        '%d/%m/%Y %H:%M') if total_points > 0 else "N/A"
    last_ts = df['timestamp'].max().strftime(
        '%d/%m/%Y %H:%M') if total_points > 0 else "N/A"

    stats_data = {
        "Métrica": ["Período Exibido", "Total de Leituras", "Anomalias Detectadas", "% de Anomalias"],
        "Valor": [f"{first_ts} - {last_ts}", f"{total_points}", f"{anomaly_points}", f"{anomaly_perc:.2f}%"]
    }
    stats_df = pd.DataFrame(stats_data)
    stats_table = dbc.Table.from_dataframe(
        stats_df, striped=True, bordered=True, hover=True, size='sm',
        className="table-dark" if current_theme == template_theme2 else ""
    )

    print("Gráficos e estatísticas atualizados.")
    return fig_cpu, fig_mem, fig_disk, gauge_cpu, gauge_mem, gauge_disk, stats_table

# Callback para alternar a classe CSS do fundo da página
@app.callback(
    Output('main-container', 'className'),
    Input('theme-store', 'data')
)
def update_page_theme(current_theme):
    # Retorna a classe CSS correspondente ao tema
    return "dbc-light" if current_theme == template_theme1 else "dbc-dark"

# --- Execução do Servidor ---
if __name__ == '__main__':
    if loaded_model is None or loaded_scaler is None:
        print(
            "\nAVISO: Modelo ou Scaler não carregados. Detecção de anomalias desativada.\n")
    print("Iniciando o servidor Dash...")
    app.run(debug=True, host='127.0.0.1', port=8050)
