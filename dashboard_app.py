# Importa as bibliotecas necessárias
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc  # Para layout e estilo
import plotly.graph_objects as go
import pandas as pd
import sqlalchemy
import pickle
import os
import datetime
from flask import Flask  # Para integrar com Flask
from dotenv import load_dotenv

load_dotenv()
# --- Configurações (Reutilize as mesmas dos scripts anteriores) ---
DB_FILE = os.getenv("DB_FOLDER") + os.getenv("DB_FILE")
TABLE_NAME = os.getenv("TABLE_NAME")
DB_URL = f"sqlite:///{DB_FILE}"
MODEL_FILENAME = os.getenv("MODEL_FILENAME")
SCALER_FILENAME = os.getenv("SCALER_FILENAME")
FEATURE_COLUMNS = ['cpu_percent', 'memory_percent', 'disk_percent']
# Intervalo de atualização em milissegundos (30 segundos)
UPDATE_INTERVAL_MS = 30000

# --- Carregamento Inicial do Modelo e Scaler ---
# Carrega os objetos uma vez quando o aplicativo inicia para eficiência
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
    # O aplicativo pode continuar, mas a detecção de anomalias não funcionará
    loaded_model = None
    loaded_scaler = None

# --- Funções Auxiliares ---


def load_and_predict_data(scaler, model):
    """
    Carrega dados do DB, aplica scaler e modelo para prever anomalias.
    """
    if not os.path.exists(DB_FILE):
        print(f"Erro: Arquivo do banco de dados '{DB_FILE}' não encontrado.")
        # Retorna DF vazio
        return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])

    try:
        engine = sqlalchemy.create_engine(DB_URL)
        with engine.connect() as connection:
            if not sqlalchemy.inspect(engine).has_table(TABLE_NAME):
                print(
                    f"Erro: Tabela '{TABLE_NAME}' não encontrada no banco de dados.")
                return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])

            # Carrega dados ordenados por timestamp
            query = f"SELECT * FROM {TABLE_NAME} ORDER BY timestamp ASC"
            df = pd.read_sql_query(
                query, connection, parse_dates=['timestamp'])

            if df.empty:
                print("Tabela de dados vazia.")
                return df

            # Prepara dados para predição
            df_features = df[FEATURE_COLUMNS].copy()

            # Trata NaNs (consistente com o treinamento)
            if df_features.isnull().sum().any():
                print(
                    "Valores ausentes encontrados nos dados carregados. Preenchendo com a média.")
                for col in FEATURE_COLUMNS:
                    if df_features[col].isnull().any():
                        # Idealmente, usar a média do *conjunto de treinamento*
                        # Mas para simplificar, usamos a média dos dados atuais aqui.
                        # Ou carregar médias salvas do treinamento.
                        mean_val = df_features[col].mean()
                        df_features[col].fillna(mean_val, inplace=True)

            # Aplica scaler e modelo SE foram carregados com sucesso
            if scaler and model:
                # Normaliza os dados usando o scaler carregado
                data_scaled = scaler.transform(df_features)
                # Faz a predição de anomalias (-1 para anomalia, 1 para normal)
                predictions = model.predict(data_scaled)
                df['anomaly'] = predictions
            else:
                # Se o modelo/scaler não carregou, marca tudo como normal (ou indeterminado)
                df['anomaly'] = 1  # Ou 0, ou None, dependendo de como quer tratar

            return df

    except Exception as e:
        print(f"Erro ao carregar ou processar dados do banco: {e}")
        # Retorna DF vazio em caso de erro
        return pd.DataFrame(columns=['timestamp'] + FEATURE_COLUMNS + ['anomaly'])


def create_time_series_chart(df, y_column, title):
    """Cria um gráfico de série temporal com destaque para anomalias."""
    fig = go.Figure()

    # Linha principal com todos os dados
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df[y_column],
        mode='lines',
        name='Uso (%)',
        line=dict(color='blue')
    ))

    # Pontos de anomalia (se houver)
    anomalies = df[df['anomaly'] == -1]
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'],
            y=anomalies[y_column],
            mode='markers',
            name='Anomalia Detectada',
            marker=dict(color='red', size=8, symbol='x')
        ))

    fig.update_layout(
        title=title,
        xaxis_title='Tempo',
        yaxis_title='Uso (%)',
        yaxis_range=[0, 105],  # Define o range do eixo Y de 0 a 105%
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=20, r=20, t=40, b=20)  # Ajusta margens
    )
    return fig


# --- Inicialização do Flask e Dash ---
server = Flask(__name__)  # Cria o servidor Flask

# Cria o aplicativo Dash, conectando ao servidor Flask e usando tema Bootstrap
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    # Necessário se callbacks atualizam componentes definidos depois
    suppress_callback_exceptions=True,
    title="Dashboard de Monitoramento"
)

# --- Layout do Dashboard ---
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1(
        "Dashboard de Monitoramento de Recursos do Sistema", className="text-center my-4"))),

    dbc.Row([
        dbc.Col(dcc.Graph(id='cpu-graph'), width=12, lg=4),  # Gráfico CPU
        dbc.Col(dcc.Graph(id='memory-graph'),
                width=12, lg=4),  # Gráfico Memória
        dbc.Col(dcc.Graph(id='disk-graph'), width=12, lg=4),  # Gráfico Disco
    ]),

    # Componente de intervalo para atualizações automáticas
    dcc.Interval(
        id='interval-component',
        interval=UPDATE_INTERVAL_MS,  # Atualiza a cada X milissegundos
        n_intervals=0
    ),

    # Armazena os dados carregados no navegador para acesso pelos callbacks dos gráficos
    dcc.Store(id='data-store')

], fluid=True)  # fluid=True para ocupar toda a largura

# --- Callbacks ---

# Callback 1: Atualiza os dados armazenados (dcc.Store) em intervalos regulares


@app.callback(
    Output('data-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_data_store(n):
    """Carrega dados do DB, faz predições e armazena em JSON."""
    print(f"Atualizando dados... (Intervalo {n})")
    # Usa o modelo e scaler carregados globalmente
    df = load_and_predict_data(loaded_scaler, loaded_model)
    # Converte para JSON para armazenar no dcc.Store
    return df.to_json(date_format='iso', orient='split')

# Callback 2: Atualiza os gráficos quando os dados no dcc.Store mudam


@app.callback(
    [Output('cpu-graph', 'figure'),
     Output('memory-graph', 'figure'),
     Output('disk-graph', 'figure')],
    Input('data-store', 'data')
)
def update_graphs(json_data):
    """Lê os dados JSON do store e cria/atualiza os gráficos."""
    if json_data is None:
        # Retorna gráficos vazios se não houver dados
        empty_fig = go.Figure().update_layout(title="Aguardando dados...",
                                              xaxis_title='Tempo', yaxis_title='Uso (%)', yaxis_range=[0, 105])
        return empty_fig, empty_fig, empty_fig

    # Converte JSON de volta para DataFrame
    df = pd.read_json(json_data, orient='split')

    # Verifica se o DataFrame não está vazio e tem a coluna timestamp
    if df.empty or 'timestamp' not in df.columns:
        empty_fig = go.Figure().update_layout(title="Dados inválidos ou vazios",
                                              xaxis_title='Tempo', yaxis_title='Uso (%)', yaxis_range=[0, 105])
        return empty_fig, empty_fig, empty_fig

    # Garante que timestamp é datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Cria os gráficos
    fig_cpu = create_time_series_chart(df, 'cpu_percent', 'Uso de CPU (%)')
    fig_mem = create_time_series_chart(
        df, 'memory_percent', 'Uso de Memória (%)')
    fig_disk = create_time_series_chart(df, 'disk_percent', 'Uso de Disco (%)')

    print("Gráficos atualizados.")
    return fig_cpu, fig_mem, fig_disk


# --- Execução do Servidor ---
if __name__ == '__main__':
    # Verifica se o modelo e scaler foram carregados antes de iniciar
    if loaded_model is None or loaded_scaler is None:
        print("\nAVISO: Modelo ou Scaler não foram carregados. A detecção de anomalias estará desativada.")
        print("Verifique se os arquivos '.pkl' existem e se não houve erros na inicialização.\n")

    print("Iniciando o servidor Dash...")
    # Executa o servidor Flask (que contém o app Dash)
    # debug=True é útil para desenvolvimento, desative para produção
    app.run(debug=True, host='127.0.0.1', port=8050)
