
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

# SELEÇÃO DE ORIGEM
origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

# GRÁFICO 1: Top 10 - Tipos de Falha
st.subheader("Top 10 - Tipos de Falha")
if "Causa manutenção" in df_filtrado.columns:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(10).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    chart_falha = alt.Chart(tipo_falha).mark_bar(color="green").encode(
        x=alt.X("Tipo de Falha:N", sort="-y"),
        y="Quantidade:Q",
        tooltip=["Tipo de Falha", "Quantidade"]
    )
    st.altair_chart(chart_falha, use_container_width=True)

# GRÁFICO 2: Top 10 - Número de OS por Frota
st.subheader("Top 10 - Número de OS por Frota")
os_por_frota = df_filtrado["Número de frota"].value_counts().head(10).reset_index()
os_por_frota.columns = ["Frota", "OS"]
chart_os = alt.Chart(os_por_frota).mark_bar(color="green").encode(
    x=alt.X("Frota:N", sort="-y"),
    y="OS:Q",
    tooltip=["Frota", "OS"]
)
st.altair_chart(chart_os, use_container_width=True)

# GRÁFICO 3: Top 10 - Tempo Total de Permanência por Frota
st.subheader("Top 10 - Tempo Total de Permanência por Frota (h)")
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_por_frota.columns = ["Frota", "Tempo (h)"]
tempo_top = tempo_por_frota.sort_values("Tempo (h)", ascending=False).head(10)
chart_tempo = alt.Chart(tempo_top).mark_bar(color="green").encode(
    x=alt.X("Frota:N", sort="-y"),
    y="Tempo (h):Q",
    tooltip=["Frota", "Tempo (h)"]
)
st.altair_chart(chart_tempo, use_container_width=True)

# GRÁFICO 4: Tempo de Permanência por Frota (a partir de 18/03/2025)
st.subheader("Top 10 - Tempo de Permanência por Frota (a partir de 18/03/2025)")
df_periodo = df_filtrado[df_filtrado["Entrada"] >= pd.to_datetime("2025-03-18")]
df_periodo_tempo = df_periodo.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
df_periodo_tempo.columns = ["Frota", "Tempo (h)"]

if not df_periodo_tempo.empty:
    top1 = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).iloc[0]["Frota"]
    df_periodo_tempo = df_periodo_tempo[df_periodo_tempo["Frota"] != top1]
    df_top10_periodo = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).head(10)

    chart_top10_periodo = alt.Chart(df_top10_periodo).mark_bar(color="green").encode(
        x=alt.X("Frota:N", sort="-y"),
        y="Tempo (h):Q",
        tooltip=["Frota", "Tempo (h)"]
    ).properties(width=700, height=400)

    st.altair_chart(chart_top10_periodo, use_container_width=True)
else:
    st.info("Nenhum dado encontrado a partir de 18/03/2025 para essa origem.")

# GRÁFICO 5: Interativo - Componentes por Origem
st.subheader("Ocorrências por Componente - Filtrado por Origem")
agrupado = df.groupby(["Origem", "Componente Detectado"]).size().reset_index(name="Ocorrências")
origem_selector = alt.selection_single(
    fields=["Origem"],
    bind=alt.binding_select(options=sorted(agrupado["Origem"].dropna().unique())),
    name="Origem"
)
grafico_componentes = alt.Chart(agrupado).mark_bar(color="green").encode(
    x=alt.X("Componente Detectado:N", sort="-y"),
    y=alt.Y("Ocorrências:Q"),
    tooltip=["Origem", "Componente Detectado", "Ocorrências"]
).add_params(
    origem_selector
).transform_filter(
    origem_selector
).properties(
    width=800,
    height=450
)
st.altair_chart(grafico_componentes, use_container_width=True)
