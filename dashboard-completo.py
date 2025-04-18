
import streamlit as st
import pandas as pd
import altair as alt

st.title("Dashboard de Manutenção - Consolidado Final")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df.columns = df.columns.str.strip()
    df["Descrição do Trabalho / Observação (Ordem de serviço)"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].fillna("").str.lower()
    if "Local manutenção" in df.columns:
        df["Origem"] = df["Local manutenção"].str.upper().str.strip()
        df["Origem"] = df["Origem"].replace({
            "MANUTENÇÃO CAMPO": "CAMPO",
            "MANUTENÇÃO INTERNA": "INTERNA",
            "MANUTENÇÃO TERCEIRO": "TERCEIRO"
        })
    else:
        df["Origem"] = "NÃO INFORMADO"
    if "Entrada" in df.columns:
        df["Entrada"] = pd.to_datetime(df["Entrada"], errors="coerce")
        df = df[df["Entrada"] >= pd.to_datetime("2025-01-01")]
        df["Ano/Mes"] = df["Entrada"].dt.to_period("M")
    return df

def classificar_componente(texto):
    categorias = {
        "Suspensão": ["mola", "molas", "molejo", "estabilizador", "pneu", "freio"],
        "Motor": ["motor"],
        "Vazamento - Combustível": ["vazamento combustível", "vazamento de combustível", "vaz. combustível"],
        "Vazamento - Hidráulico": ["vazamento hidráulico", "vazamento de óleo hidráulico", "hidráulico"],
        "Vazamento - Óleo": ["vazamento óleo", "vazamento de óleo", "vaz. óleo"],
        "Rodantes": ["rodante", "esteira", "roletes", "coroa", "roda motriz"],
        "Elétrica": ["elétrica", "luz", "farol", "chicote", "bateria"],
        "Mangueira (Vazamento)": ["mangueira"],
        "Rádio": ["radio", "rádio"],
        "Avaliar": ["avaliar", "verificação", "verificar"],
        "Falha Eletrônica / Painel": ["painel", "computador", "tela", "falha", "eletrônico", "sistema", "display", "luz espia", "injetor"],
        "Ar Condicionado": ["ar condicionado", "ac", "climatizador", "evaporador", "ventilador", "condensador", "compressor do ar"],
        "Elevador": ["elevador", "elevatória", "plataforma"],
        "Acumulador": ["acumulador"],
        "Despontador": ["despontador"]
    }
    for categoria, palavras in categorias.items():
        if any(p in texto for p in palavras):
            return categoria
    return "Não Classificado"

df = carregar_dados()
df["Componente Detectado"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].apply(classificar_componente)

origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

def plot_horizontal_bar(data, x_col, y_col, tooltip, titulo):
    chart = alt.Chart(data).mark_bar(color="green").encode(
        y=alt.Y(f"{y_col}:N", sort="-x", axis=alt.Axis(labelLimit=400, titleLimit=400)),
        x=alt.X(f"{x_col}:Q", axis=alt.Axis(title="Quantidade")),
        tooltip=tooltip
    ).properties(width=1000, height=400)
    st.subheader(titulo)
    st.altair_chart(chart, use_container_width=True)

# GRÁFICO 6/7: Unificado - Dias com Mais OS (Barras + Linha)
st.subheader("Dias com Maior Número de Abertura de OS")
df_dias = df_filtrado.groupby("Entrada")["Boletim"].count().reset_index()
df_dias.columns = ["Data", "Quantidade"]
chart_barras = alt.Chart(df_dias).mark_bar(color="green").encode(
    x=alt.X("Data:T", title="Data da Entrada"),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
    tooltip=["Data", "Quantidade"]
)
chart_linha = alt.Chart(df_dias).mark_line(color="blue", point=True).encode(
    x="Data:T",
    y="Quantidade:Q"
)
st.altair_chart(chart_barras + chart_linha, use_container_width=True)
