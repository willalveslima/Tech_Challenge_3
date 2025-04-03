# Projeto: Monitoramento de Recursos do Sistema com Detecção de Anomalias

## Visão Geral

Este projeto implementa um sistema de ponta a ponta para monitorar o uso de recursos (CPU, Memória, Disco) de um sistema local, detectar anomalias nesses dados usando Machine Learning (Isolation Forest) e visualizar os resultados em um dashboard web interativo.

O projeto foi desenvolvido como parte do **Tech Challenge - Fase 3** da Pós-Graduação em **Machine Learning Engineering** da **Pos Tech**. Ele abrange coleta de dados, armazenamento, treinamento de modelo e visualização/aplicação produtiva.


## Funcionalidades

- **Coleta de Dados:** Monitoramento periódico de CPU, Memória e Disco usando a biblioteca `psutil`.
- **Armazenamento:** Persistência dos dados coletados em um banco de dados SQLite gerenciado pelo `SQLAlchemy`.
- **Detecção de Anomalias:** Treinamento de um modelo `Isolation Forest` para identificar padrões anômalos nos dados históricos.
- **Dashboard Interativo:** Visualização dos dados e anomalias em gráficos de série temporal utilizando `Dash` e `Plotly`.
- **Atualização Automática:** O dashboard atualiza os dados em intervalos configuráveis.

## Estrutura do Projeto

```
.
├── coletor/                     # Scripts para coleta de dados
│   ├── coletor_stats.py         # Coleta dados do sistema e salva no banco
│   └── coletor_stats_1.py       # Versão alternativa do coletor
├── database/
│   └── system_stats.db          # Banco de dados SQLite
├── model/
│   ├── treinar_modelo.py        # Treinamento do modelo de detecção de anomalias
│   ├── isolation_forest_model.pkl # Modelo treinado
│   └── scaler.pkl               # Scaler para normalização dos dados
├── dashboard_app.py             # Dashboard interativo para visualização
├── .env                         # Configurações do projeto
├── .gitignore                   # Arquivos ignorados pelo Git
├── LICENSE                      # Licença do projeto
└── README.md                    # Documentação do projeto
```

## Tecnologias Utilizadas

- **Linguagem:** Python 3.8+
- **Bibliotecas Principais:** 
  - `psutil` para coleta de dados do sistema.
  - `SQLAlchemy` para gerenciamento do banco de dados SQLite.
  - `scikit-learn` para treinamento do modelo de Machine Learning.
  - `Dash` e `Plotly` para visualização interativa.
  - `dotenv` para gerenciamento de variáveis de ambiente.

## Pré-requisitos

- Python 3.8 ou superior
- Git (para clonar o repositório)

## Instalação

1. Clone o repositório:
    ```bash
    git clone https://github.com/willalveslima/Tech_Challenge_3.git
    cd Tech_Challenge_3
    ```

2. Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate   # Windows
    ```

3. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

4. Configure as variáveis de ambiente no arquivo `.env` (já fornecido no projeto).

## Como Usar

1. **Coletar Dados:**
    Execute o script de coleta para começar a popular o banco de dados:
    ```bash
    python coletor/coletor_stats.py
    ```

2. **Treinar o Modelo:**
    Após coletar dados suficientes, treine o modelo:
    ```bash
    python model/treinar_modelo.py
    ```

3. **Executar o Dashboard:**
    Inicie o dashboard para visualizar os dados e anomalias:
    ```bash
    python dashboard_app.py
    ```

4. **Acessar o Dashboard:**
    Abra o navegador e acesse:
    [http://127.0.0.1:8050/](http://127.0.0.1:8050/)

## Configurações

- **Intervalo de Coleta:** Ajuste no script `coletor_stats.py` (`time.sleep(...)`).
- **Parâmetros do Modelo:** Ajuste no script `treinar_modelo.py` (ex.: `contamination` do `Isolation Forest`).
- **Intervalo de Atualização do Dashboard:** Ajuste no script `dashboard_app.py` (`UPDATE_INTERVAL_MS`).

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## Melhorias Futuras

- Implementar uma API REST para coleta de dados.
- Migrar para um banco de dados mais robusto (ex.: PostgreSQL).
- Experimentar outros modelos de detecção de anomalias.
- Adicionar autenticação ao dashboard.
- Criar scripts para deploy (ex.: Docker).

## Autor

- **Willian Alves Lima**