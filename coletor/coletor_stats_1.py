# Importa as bibliotecas necessárias
import psutil  # Biblioteca principal para acessar informações do sistema
import datetime # Para registrar o momento da coleta
import time     # Para adicionar pausas, se necessário rodar em loop
import platform # Para identificar o sistema operacional (útil para caminhos de disco)

def get_system_stats():
    """
    Coleta estatísticas de uso de CPU, memória e disco.

    Returns:
        dict: Um dicionário contendo as percentagens de uso e o timestamp.
              Retorna None para uma métrica se houver erro na coleta.
              Exemplo: {'timestamp': '...', 'cpu_percent': 10.5, 'memory_percent': 55.2, 'disk_percent': 40.1}
    """
    stats = {}
    try:
        # Adiciona timestamp no início da coleta
        stats['timestamp'] = datetime.datetime.now().isoformat()

        # --- Coleta de CPU ---
        # psutil.cpu_percent(interval=1) mede o uso da CPU durante 1 segundo.
        # O intervalo é importante para obter uma leitura média significativa e não bloquear outros processos.
        # Se interval=None, compara os tempos desde a última chamada ou desde a importação do módulo.
        stats['cpu_percent'] = psutil.cpu_percent(interval=1)

        # --- Coleta de Memória Virtual (RAM) ---
        memory_info = psutil.virtual_memory()
        # memory_info contém vários dados (total, available, percent, used, free, etc.)
        # Pegamos apenas a percentagem de uso.
        stats['memory_percent'] = memory_info.percent

        # --- Coleta de Uso de Disco ---
        # psutil.disk_usage('/') obtém informações sobre a partição onde o diretório raiz ('/') está montado.
        # Em Windows, você pode querer verificar 'C:'.
        # Adaptar conforme necessário para o seu sistema ou monitorar múltiplas partições.
        disk_path = '/'
        if platform.system() == "Windows":
            disk_path = 'C:\\' # Exemplo para Windows

        disk_info = psutil.disk_usage(disk_path)
        # disk_info contém (total, used, free, percent)
        # Pegamos a percentagem de uso.
        stats['disk_percent'] = disk_info.percent

    except Exception as e:
        # Captura qualquer erro durante a coleta e imprime
        print(f"Erro ao coletar estatísticas: {e}")
        # Garante que o timestamp esteja presente mesmo em caso de erro parcial
        if 'timestamp' not in stats:
             stats['timestamp'] = datetime.datetime.now().isoformat()
        # Preenche com None os campos que podem ter falhado
        stats.setdefault('cpu_percent', None)
        stats.setdefault('memory_percent', None)
        stats.setdefault('disk_percent', None)

    return stats

# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    print("Coletando estatísticas do sistema uma vez...")
    system_stats = get_system_stats()

    if system_stats:
        print("\n--- Estatísticas Coletadas ---")
        print(f"Timestamp: {system_stats.get('timestamp', 'N/A')}")
        print(f"Uso de CPU: {system_stats.get('cpu_percent', 'Erro')}%")
        print(f"Uso de Memória: {system_stats.get('memory_percent', 'Erro')}%")
        # Mostra qual disco foi verificado
        disk_label = '/' if platform.system() != "Windows" else 'C:'
        print(f"Uso de Disco ({disk_label}): {system_stats.get('disk_percent', 'Erro')}%")
        print("----------------------------\n")
    else:
        print("Não foi possível coletar as estatísticas.")

    # --- Exemplo de como rodar em loop (coleta contínua) ---
    # Descomente as linhas abaixo para testar a coleta a cada 5 segundos.
    # Pressione Ctrl+C no terminal para parar.
    # print("\nIniciando coleta contínua a cada 5 segundos (Pressione Ctrl+C para parar)...")
    # try:
    #     while True:
    #         stats = get_system_stats()
    #         if stats:
    #              print(f"{stats.get('timestamp', 'N/A')} - CPU: {stats.get('cpu_percent', 'Erro')}% | Mem: {stats.get('memory_percent', 'Erro')}% | Disco: {stats.get('disk_percent', 'Erro')}%")
    #         else:
    #              print("Falha na coleta nesta iteração.")
    #         # Espera 5 segundos antes da próxima coleta
    #         time.sleep(5)
    # except KeyboardInterrupt:
    #     print("\nColeta contínua interrompida pelo usuário.")
    # except Exception as e:
    #     print(f"\nErro inesperado durante o loop: {e}")

