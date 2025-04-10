import sqlite3
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output

# Arquivos CSV
csv_sexo = "sexo.csv"
csv_idade = "idade.csv"
csv_pessoas_idade_trabalhar = "pessoas_idade_trabalhar.csv"

def criar_tabela_e_inserir_dados(csv_file, tabela):
    try:
        conn = sqlite3.connect("desemprego.db")
        cursor = conn.cursor()
        df = pd.read_csv(csv_file, delimiter=";")
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        cursor.execute(f"DROP TABLE IF EXISTS {tabela}")
        colunas = ", ".join([f'"{col}" TEXT' for col in df.columns])
        cursor.execute(f"CREATE TABLE {tabela} ({colunas})")
        df.to_sql(tabela, conn, if_exists="append", index=False)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao processar {csv_file}: {e}")

def carregar_dados(tabela):
    try:
        conn = sqlite3.connect("desemprego.db")
        df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Erro ao carregar dados da tabela {tabela}: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

# Criar tabelas para sexo, idade e pessoas em idade de trabalhar
criar_tabela_e_inserir_dados(csv_sexo, "desemprego_sexo")
criar_tabela_e_inserir_dados(csv_idade, "desemprego_idade")
criar_tabela_e_inserir_dados(csv_pessoas_idade_trabalhar, "pessoas_idade_trabalhar")

df_sexo = carregar_dados("desemprego_sexo")
df_idade = carregar_dados("desemprego_idade")
df_pessoas_idade_trabalhar = carregar_dados("pessoas_idade_trabalhar")

# Ajustando colunas do DataFrame de pessoas em idade de trabalhar
if len(df_pessoas_idade_trabalhar.columns) >= 5:
    df_pessoas_idade_trabalhar = df_pessoas_idade_trabalhar.iloc[:, :5]
    df_pessoas_idade_trabalhar.columns = [
        'data',
        'pessoas_em_idade_de_trabalhar',
        'pessoas_na_forca_de_trabalho',
        'pessoas_fora_da_forca_de_trabalho',
        'unidade'
    ]

# Converter colunas numéricas para float, substituindo vírgulas por pontos
numeric_cols = ['pessoas_em_idade_de_trabalhar', 'pessoas_na_forca_de_trabalho', 'pessoas_fora_da_forca_de_trabalho']
for col in numeric_cols:
    df_pessoas_idade_trabalhar[col] = df_pessoas_idade_trabalhar[col].str.replace(',', '.').astype(float)

df_sexo_melted = df_sexo.melt(id_vars=["sexo"], var_name="trimestre", value_name="taxa_desemprego")
df_idade_melted = df_idade.melt(id_vars=["grupo_de_idade"], var_name="trimestre", value_name="taxa_desemprego")

sexo_options = [{"label": s, "value": s} for s in df_sexo_melted["sexo"].dropna().unique()]
idade_options = [{"label": i, "value": i} for i in df_idade_melted["grupo_de_idade"].dropna().unique()]

app = dash.Dash(__name__)
server = app.server
app.title = "Dashboard de Desemprego"

app.layout = html.Div(children=[
    html.H1("Taxa de Desemprego na Região Sudeste do Brasil", style={"textAlign": "center", "backgroundColor": "#f0f8ff", "padding": "20px"}),

    html.Div(children=[
        html.Div(children=[
            html.H2("Taxa de desocupação por sexo", style={"textAlign": "center"}),
            dcc.Dropdown(id="sexo-dropdown", options=sexo_options, value=sexo_options[0]["value"], style={"width": "80%"}),
            dcc.Graph(id="grafico-desemprego-sexo")
        ], style={"width": "48%", "display": "inline-block", "padding": "20px", "backgroundColor": "#f9f9f9"}),

        html.Div(children=[
            html.H2("Taxa de desocupação por idade", style={"textAlign": "center"}),
            dcc.Dropdown(id="idade-dropdown", options=idade_options, value=idade_options[0]["value"], style={"width": "80%"}),
            dcc.Graph(id="grafico-desemprego-idade")
        ], style={"width": "48%", "display": "inline-block", "padding": "20px", "backgroundColor": "#f9f9f9", "marginLeft": "10px"})
    ], style={"display": "flex"}),

    html.Div(children=[
        html.H2("Pessoas em Idade de Trabalhar", style={"textAlign": "center"}),
        dcc.Graph(
            id="grafico-pessoas-idade-trabalhar",
            figure=px.line(df_pessoas_idade_trabalhar, x="data", y=["pessoas_em_idade_de_trabalhar", "pessoas_na_forca_de_trabalho", "pessoas_fora_da_forca_de_trabalho"],
                           title="Evolução das Pessoas em Idade de Trabalhar", template="plotly_white",
                           labels={"value": "Pessoas", "variable": "Legenda", "data": "Data"})
            .update_traces(marker=dict(line=dict(width=1)), selector=dict(type='scatter', mode='lines'))
            .update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis_title="Pessoas",
                xaxis_title="Data",
                yaxis=dict(range=[0, df_pessoas_idade_trabalhar[["pessoas_em_idade_de_trabalhar", "pessoas_na_forca_de_trabalho", "pessoas_fora_da_forca_de_trabalho"]].max().max() * 1.1]),
                xaxis=dict(tickmode="auto", nticks=10)
            )
            .add_annotation(
                x=df_pessoas_idade_trabalhar["data"].iloc[0],  # Anotação no primeiro ponto de dados
                y=df_pessoas_idade_trabalhar["pessoas_em_idade_de_trabalhar"].iloc[0] if not df_pessoas_idade_trabalhar.empty and df_pessoas_idade_trabalhar["pessoas_em_idade_de_trabalhar"].iloc[0] is not None else 0,
                text=f"{df_pessoas_idade_trabalhar['pessoas_em_idade_de_trabalhar'].iloc[0]:.3f} mil pessoas" if not df_pessoas_idade_trabalhar.empty and df_pessoas_idade_trabalhar["pessoas_em_idade_de_trabalhar"].iloc[0] is not None else "Dados indisponíveis",
                showarrow=False,
                xanchor="left",
                xshift=10
            )
            .add_vline(x=df_pessoas_idade_trabalhar["data"].iloc[0], line_width=2, line_dash="dash", line_color="gray")
        )
    ], style={"padding": "20px", "backgroundColor": "#e6f7ff"}),

    html.Div(children=[
        html.P("Fonte dos Dados: IBGE - PNAD Contínua", style={"textAlign": "center", "color": "#7f8c8d"})
    ], style={"backgroundColor": "#ecf0f1", "padding": "10px"})
])

sexo_colors = {
    "Homens": "#008B8B",
    "Mulheres": "#FF0000",
    "Total": ["#008000", "#008B8B", "#FF0000"]
}

idade_colors = {
    "14 a 17 anos": "#9400D3",
    "18 a 24 anos": "#FF4500",
    "25 a 39 anos": "#8B4513",
    "40 a 59 anos": "#FF1493",
    "60 anos ou mais": "#363636",
    "Total": ["#9400D3", "#FF4500", "#8B4513", "#FF1493", "#363636"]
}

@app.callback(
    Output("grafico-desemprego-sexo", "figure"),
    [Input("sexo-dropdown", "value")]
)
def atualizar_grafico_sexo(sexo_selecionado):
    df_filtrado = df_sexo_melted if sexo_selecionado == "Total" else df_sexo_melted[df_sexo_melted["sexo"] == sexo_selecionado]
    return px.line(df_filtrado, x="trimestre", y="taxa_desemprego", color="sexo", template="plotly_white", markers=True)

# Callback para gráfico por idade
@app.callback(
    Output("grafico-desemprego-idade", "figure"),
    [Input("idade-dropdown", "value")]
)
def atualizar_grafico_idade(idade_selecionada):
    df_filtrado = df_idade_melted if idade_selecionada == "Total" else df_idade_melted[df_idade_melted["grupo_de_idade"] == idade_selecionada]
    return px.line(df_filtrado, x="trimestre", y="taxa_desemprego", color="grupo_de_idade", template="plotly_white", markers=True)

if __name__ == "__main__":
    app.run(debug=True)