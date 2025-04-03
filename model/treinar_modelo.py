# Importa as bibliotecas necessárias
import pandas as pd
import sqlalchemy
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle  # Para salvar o modelo e o scaler
import os  # Para verificar a existência de arquivos
from dotenv import load_dotenv


load_dotenv()
# --- Configurações (Reutilize as mesmas do script coletor) ---
DB_FILE = os.getenv("DB_FOLDER") + os.getenv("DB_FILE")
print(DB_FILE)
TABLE_NAME = os.getenv("TABLE_NAME")  # Nome da tabela no banco
DB_URL = f"sqlite:///{DB_FILE}"

# --- Nomes dos arquivos de saída ---
MODEL_FILENAME = os.getenv("MODEL_FILENAME")
SCALER_FILENAME = os.getenv("SCALER_FILENAME")

# --- Colunas a serem usadas para o treinamento ---
# Excluímos 'id' e 'timestamp' pois não são features diretas de uso do sistema
FEATURE_COLUMNS = ['cpu_percent', 'memory_percent', 'disk_percent']


def load_data_from_db(db_url, table_name):
    """
    Carrega os dados da tabela especificada no banco de dados SQLite.

    Args:
        db_url (str): URL de conexão do SQLAlchemy.
        table_name (str): Nome da tabela a ser carregada.

    Returns:
        pandas.DataFrame: DataFrame com os dados carregados, ou None se ocorrer erro.
    """
    print(f"Conectando ao banco de dados: {db_url}")
    if not os.path.exists(DB_FILE):
        print(f"Erro: Arquivo do banco de dados '{DB_FILE}' não encontrado.")
        print("Certifique-se de que o script coletor (psutil_sqlite_sqlalchemy_v1) foi executado e gerou dados.")
        return None
    try:
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as connection:
            # Verifica se a tabela existe antes de tentar ler
            if not sqlalchemy.inspect(engine).has_table(table_name):
                print(
                    f"Erro: Tabela '{table_name}' não encontrada no banco de dados.")
                return None
            print(f"Carregando dados da tabela '{table_name}'...")
            # Carrega a tabela inteira para um DataFrame do Pandas
            df = pd.read_sql_table(table_name, connection)
            print(f"Dados carregados com sucesso: {len(df)} registros.")
            return df
    except Exception as e:
        print(f"Erro ao carregar dados do banco de dados: {e}")
        return None


def preprocess_data(df, feature_columns):
    """
    Pré-processa os dados: seleciona features, trata NaNs e normaliza.

    Args:
        df (pandas.DataFrame): DataFrame com os dados brutos.
        feature_columns (list): Lista de nomes das colunas a serem usadas como features.

    Returns:
        tuple: Contendo:
            - numpy.ndarray: Dados normalizados.
            - sklearn.preprocessing.StandardScaler: Objeto scaler ajustado.
            Retorna (None, None) se o DataFrame for inválido ou vazio.
    """
    if df is None or df.empty:
        print("DataFrame vazio ou inválido para pré-processamento.")
        return None, None

    print("Iniciando pré-processamento...")
    # 1. Seleciona as colunas de features
    df_features = df[feature_columns].copy()

    # 2. Trata valores ausentes (NaN) - Estratégia: preencher com a média da coluna
    if df_features.isnull().sum().any():
        print("Valores ausentes encontrados. Preenchendo com a média da coluna...")
        for col in feature_columns:
            if df_features[col].isnull().any():
                mean_val = df_features[col].mean()
                df_features[col].fillna(mean_val, inplace=True)
                print(
                    f" - Coluna '{col}': NaNs preenchidos com {mean_val:.2f}")
    else:
        print("Nenhum valor ausente encontrado nas features.")

    # 3. Normalização (Standard Scaling) Z-score = (x - media) / desvio_padrao
    print("Aplicando normalização (StandardScaler)...")
    scaler = StandardScaler()
    # Ajusta o scaler aos dados e transforma os dados
    data_scaled = scaler.fit_transform(df_features)
    print("Dados normalizados.")

    return data_scaled, scaler


def train_isolation_forest(data_scaled, contamination=0.05, random_state=42):
    """
    Treina um modelo Isolation Forest.

    Args:
        data_scaled (numpy.ndarray): Dados normalizados para treinamento.
        contamination (float or 'auto'): Proporção esperada de anomalias nos dados.
                                         'auto' estima a contaminação.
        random_state (int): Semente para reprodutibilidade.

    Returns:
        sklearn.ensemble.IsolationForest: Modelo treinado, ou None se os dados forem inválidos.
    """
    if data_scaled is None or data_scaled.shape[0] == 0:
        print("Dados inválidos para treinamento.")
        return None

    print("Iniciando treinamento do Isolation Forest...")
    # Cria o modelo
    # 'contamination' é um parâmetro importante, 'auto' funciona bem em muitos casos.
    # Pode ser ajustado (ex: 0.01 para 1% de anomalias esperadas) se tiver conhecimento prévio.
    model = IsolationForest(contamination=contamination,
                            random_state=random_state, n_estimators=100)

    # Treina o modelo
    model.fit(data_scaled)
    print("Modelo Isolation Forest treinado com sucesso.")
    return model


def save_objects(model, scaler, model_filename, scaler_filename):
    """
    Salva o modelo treinado e o scaler usando pickle.

    Args:
        model: Objeto do modelo treinado.
        scaler: Objeto do scaler ajustado.
        model_filename (str): Nome do arquivo para salvar o modelo.
        scaler_filename (str): Nome do arquivo para salvar o scaler.
    """
    if model:
        print(f"Salvando modelo em '{model_filename}'...")
        try:
            with open(model_filename, 'wb') as f:
                pickle.dump(model, f)
            print("Modelo salvo com sucesso.")
        except Exception as e:
            print(f"Erro ao salvar o modelo: {e}")

    if scaler:
        print(f"Salvando scaler em '{scaler_filename}'...")
        try:
            with open(scaler_filename, 'wb') as f:
                pickle.dump(scaler, f)
            print("Scaler salvo com sucesso.")
        except Exception as e:
            print(f"Erro ao salvar o scaler: {e}")


# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    print("--- Script de Treinamento do Modelo de Detecção de Anomalias ---")

    # 1. Carregar Dados
    dataframe = load_data_from_db(DB_URL, TABLE_NAME)

    # Prosseguir apenas se os dados foram carregados com sucesso
    if dataframe is not None and not dataframe.empty:
        # 2. Pré-processar Dados
        scaled_data, fitted_scaler = preprocess_data(
            dataframe, FEATURE_COLUMNS)

        # Prosseguir apenas se o pré-processamento foi bem-sucedido
        if scaled_data is not None and fitted_scaler is not None:
            # 3. Treinar Modelo
            trained_model = train_isolation_forest(scaled_data)

            # 4. Salvar Modelo e Scaler
            if trained_model:
                save_objects(trained_model, fitted_scaler,
                             MODEL_FILENAME, SCALER_FILENAME)
            else:
                print("Treinamento falhou. Modelo e scaler não foram salvos.")
        else:
            print("Pré-processamento falhou. Treinamento cancelado.")
    else:
        print("Carregamento de dados falhou ou tabela vazia. Treinamento cancelado.")

    print("--- Script de Treinamento Concluído ---")
