# Importa as bibliotecas necessárias
import psutil
import datetime
import time
import platform
import sqlalchemy  # Biblioteca para interagir com o banco de dados
from dotenv import load_dotenv
import os


load_dotenv()  # Carrega variáveis de ambiente do arquivo .env, se existir
# --- Configurações do Banco de Dados ---
# Nome do arquivo do banco de dados SQLite
DB_FILE = os.getenv("DB_FILE")
TABLE_NAME = os.getenv("TABLE_NAME")  # Nome da tabela no banco
DB_URL = f"sqlite:///{os.getenv("DB_FOLDER")}/{DB_FILE}"

# --- Setup do SQLAlchemy ---
# echo=True para ver os comandos SQL gerados
engine = sqlalchemy.create_engine(DB_URL, echo=False)
metadata = sqlalchemy.MetaData()

# Define a estrutura da tabela
stats_table = sqlalchemy.Table(
    TABLE_NAME,
    metadata,
    # Chave primária autoincrementável
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime,
                      nullable=False),  # Timestamp da coleta
    # % CPU (permite nulo se falhar)
    sqlalchemy.Column("cpu_percent", sqlalchemy.Float, nullable=True),
    # % Memória (permite nulo se falhar)
    sqlalchemy.Column("memory_percent", sqlalchemy.Float, nullable=True),
    # % Disco (permite nulo se falhar)
    sqlalchemy.Column("disk_percent", sqlalchemy.Float, nullable=True),
)


def setup_database():
    """Cria a tabela no banco de dados se ela não existir."""
    print(f"Verificando e configurando o banco de dados: {DB_FILE}")
    try:
        metadata.create_all(engine)
        print(f"Tabela '{TABLE_NAME}' pronta.")
    except Exception as e:
        print(f"Erro ao configurar o banco de dados: {e}")
        raise  # Re-levanta a exceção para parar a execução se o DB falhar


def get_system_stats():
    """
    Coleta estatísticas de uso de CPU, memória e disco.
    (Função adaptada da versão anterior - psutil_collector_example_v1)

    Returns:
        dict: Um dicionário contendo as percentagens de uso e o timestamp.
              Retorna None para uma métrica se houver erro na coleta.
    """
    stats = {}
    try:
        # Usa datetime.datetime.now() diretamente para compatibilidade com SQLAlchemy DateTime
        stats['timestamp'] = datetime.datetime.now()

        # Coleta de CPU
        stats['cpu_percent'] = psutil.cpu_percent(interval=1)

        # Coleta de Memória Virtual (RAM)
        memory_info = psutil.virtual_memory()
        stats['memory_percent'] = memory_info.percent

        # Coleta de Uso de Disco
        disk_path = '/'
        if platform.system() == "Windows":
            disk_path = 'C:\\'
        disk_info = psutil.disk_usage(disk_path)
        stats['disk_percent'] = disk_info.percent

    except Exception as e:
        print(f"Erro ao coletar estatísticas: {e}")
        # Garante que o timestamp esteja presente mesmo em caso de erro parcial
        if 'timestamp' not in stats:
            stats['timestamp'] = datetime.datetime.now()
        # Preenche com None os campos que podem ter falhado
        stats.setdefault('cpu_percent', None)
        stats.setdefault('memory_percent', None)
        stats.setdefault('disk_percent', None)

    return stats


def save_stats_to_db(stats_data):
    """
    Salva um dicionário de estatísticas no banco de dados SQLite.

    Args:
        stats_data (dict): Dicionário retornado por get_system_stats().
    """
    if not stats_data:
        print("Nenhum dado para salvar.")
        return

    # Cria a instrução de inserção
    insert_statement = stats_table.insert().values(
        timestamp=stats_data.get('timestamp'),
        cpu_percent=stats_data.get('cpu_percent'),
        memory_percent=stats_data.get('memory_percent'),
        disk_percent=stats_data.get('disk_percent')
    )

    # Conecta ao banco e executa a inserção dentro de uma transação
    try:
        with engine.connect() as connection:
            with connection.begin():  # Inicia uma transação
                connection.execute(insert_statement)
            # O 'commit' é feito automaticamente ao sair do bloco 'connection.begin()' sem erros
            # print(f"Dados salvos no DB: {stats_data.get('timestamp')}") # Log opcional
    except Exception as e:
        # O 'rollback' é feito automaticamente se ocorrer um erro dentro do 'connection.begin()'
        print(f"Erro ao salvar dados no banco de dados: {e}")


# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    try:
        # 1. Garante que o banco de dados e a tabela estão configurados
        setup_database()

        # 2. Coleta os dados uma vez e salva
        print("\nColetando e salvando estatísticas uma vez...")
        current_stats = get_system_stats()
        save_stats_to_db(current_stats)
        print("-> Dados da primeira coleta salvos no banco.")

        # --- Exemplo de como rodar em loop (coleta contínua) ---
        print("\nIniciando coleta contínua a cada 10 segundos (Pressione Ctrl+C para parar)...")
        try:
            while True:
                stats = get_system_stats()
                save_stats_to_db(stats)
                # Imprime um feedback simples no console
                print(f".", end='', flush=True)
                # Espera 10 segundos antes da próxima coleta
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nColeta contínua interrompida pelo usuário.")
        except Exception as e:
            print(f"\nErro inesperado durante o loop: {e}")

    except Exception as e:
        # Captura erros na configuração inicial do DB
        print(f"Erro fatal durante a inicialização: {e}")
