
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date

st.set_page_config(layout="wide")
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
    if "Saída Real" in df.columns:
        df["Saída"] = pd.to_datetime(df["Saída Real"], errors="coerce")
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

# FILTRO DE PERÍODO PERSONALIZADO
st.sidebar.header("Filtro de Período")
data_inicio = st.sidebar.date_input("Data de Início", value=date(2025, 3, 1))
data_fim = st.sidebar.date_input("Data de Fim", value=date.today())

if "Entrada" in df.columns:
    df = df[(df["Entrada"] >= pd.to_datetime(data_inicio)) & (df["Entrada"] <= pd.to_datetime(data_fim))]

origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

# GRÁFICO 1
if "Causa manutenção" in df_filtrado.columns:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(10).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    chart = alt.Chart(tipo_falha).mark_bar(color="green").encode(
        y=alt.Y("Tipo de Falha:N", sort="-x"),
        x=alt.X("Quantidade:Q"),
        tooltip=["Tipo de Falha", "Quantidade"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 1 - Top 10 Tipos de Falha")
    st.altair_chart(chart, use_container_width=True)

# GRÁFICO 2
os_por_frota = df_filtrado["Número de frota"].value_counts().head(10).reset_index()
os_por_frota.columns = ["Frota", "OS"]
chart2 = alt.Chart(os_por_frota).mark_bar(color="green").encode(
    y=alt.Y("Frota:N", sort="-x"),
    x=alt.X("OS:Q"),
    tooltip=["Frota", "OS"]
).properties(width=800, height=400)
st.subheader("Gráfico 2 - Top 10 Número de OS por Frota")
st.altair_chart(chart2, use_container_width=True)

# GRÁFICO 3
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_por_frota.columns = ["Frota", "Tempo (h)"]
tempo_top = tempo_por_frota.sort_values("Tempo (h)", ascending=False).head(10)
chart3 = alt.Chart(tempo_top).mark_bar(color="green").encode(
    y=alt.Y("Frota:N", sort="-x"),
    x=alt.X("Tempo (h):Q"),
    tooltip=["Frota", "Tempo (h)"]
).properties(width=800, height=400)
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Frota (h)")
st.altair_chart(chart3, use_container_width=True)

# GRÁFICO 4
df_periodo_tempo = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
df_periodo_tempo.columns = ["Frota", "Tempo (h)"]
if not df_periodo_tempo.empty:
    top1 = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).iloc[0]["Frota"]
    df_periodo_tempo = df_periodo_tempo[df_periodo_tempo["Frota"] != top1]
    df_top10_periodo = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).head(10)
    chart4 = alt.Chart(df_top10_periodo).mark_bar(color="green").encode(
        y=alt.Y("Frota:N", sort="-x"),
        x=alt.X("Tempo (h):Q"),
        tooltip=["Frota", "Tempo (h)"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 4 - Top 10 Tempo de Permanência por Frota no Período")
    st.altair_chart(chart4, use_container_width=True)
else:
    st.info("Nenhum dado encontrado no período selecionado para essa origem.")

# GRÁFICO 5
agrupado_componentes = df_filtrado["Componente Detectado"].value_counts().reset_index()
agrupado_componentes.columns = ["Componente", "Ocorrências"]
chart5 = alt.Chart(agrupado_componentes).mark_bar(color="green").encode(
    y=alt.Y("Componente:N", sort="-x"),
    x=alt.X("Ocorrências:Q"),
    tooltip=["Componente", "Ocorrências"]
).properties(width=800, height=400)
st.subheader("Gráfico 5 - Ocorrências por Componente (Descrição da OS)")
st.altair_chart(chart5, use_container_width=True)

# GRÁFICO 6 - Tendência Mensal
tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count().reset_index()
tendencia.columns = ["Ano/Mês", "Quantidade"]
chart6 = alt.Chart(tendencia).mark_line(point=True, color="green").encode(
    x=alt.X("Ano/Mês:T", title="Ano/Mês", axis=alt.Axis(format="%d/%m/%Y")),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
    tooltip=["Ano/Mês", "Quantidade"]
).properties(width=800, height=400)
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções")
st.altair_chart(chart6, use_container_width=True)

# GRÁFICO 7 - Tendência Diária de Entrada
df_entrada = df_filtrado[df_filtrado["Entrada"].notna() & (df_filtrado["Entrada"] >= pd.to_datetime(data_inicio)) & (df_filtrado["Entrada"] <= pd.to_datetime(data_fim))]
tendencia_entrada = df_entrada.groupby("Entrada")["Boletim"].count().reset_index()
tendencia_entrada.columns = ["Data de Entrada", "Quantidade"]
chart7 = alt.Chart(tendencia_entrada).mark_bar(color="green").encode(
    x=alt.X("Data de Entrada:T", title="Data de Entrada", axis=alt.Axis(format="%d/%m/%Y")),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
    tooltip=["Data de Entrada", "Quantidade"]
).properties(width=800, height=400)
st.subheader("Gráfico 7 - Tendência Diária de Entrada de OS")
st.altair_chart(chart7, use_container_width=True)

# GRÁFICO 8 - Tendência Diária de Saída
df_saida = df_filtrado[df_filtrado["Saída"].notna() & (df_filtrado["Saída"] >= pd.to_datetime(data_inicio)) & (df_filtrado["Saída"] <= pd.to_datetime(data_fim))]
tendencia_saida = df_saida.groupby("Saída")["Boletim"].count().reset_index()
tendencia_saida.columns = ["Data de Saída", "Quantidade"]
chart8 = alt.Chart(tendencia_saida).mark_bar(color="green").encode(
    x=alt.X("Data de Saída:T", title="Data de Saída", axis=alt.Axis(format="%d/%m/%Y")),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
    tooltip=["Data de Saída", "Quantidade"]
).properties(width=800, height=400)
st.subheader("Gráfico 8 - Tendência Diária de Saída de OS")
st.altair_chart(chart8, use_container_width=True)

# GRÁFICO 9 - Frotas mais Frequentes (Descrição da Frota)
if "Descrição  frota" in df_filtrado.columns:
    descricao_frota = df_filtrado["Descrição  frota"].value_counts().reset_index()
    descricao_frota.columns = ["Descrição da Frota", "Ocorrências"]
    descricao_frota = descricao_frota.sort_values("Ocorrências", ascending=False).head(10)
    chart9 = alt.Chart(descricao_frota).mark_bar(color="green").encode(
        y=alt.Y("Descrição da Frota:N", sort="-x"),
        x=alt.X("Ocorrências:Q"),
        tooltip=["Descrição da Frota", "Ocorrências"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 9 - Frotas mais Frequentes (Descrição da Frota)")
    st.altair_chart(chart9, use_container_width=True)

# GRÁFICO 10 - Distribuição por Tipo de Manutenção
if "Tipo de manutenção" in df_filtrado.columns and not df_filtrado["Tipo de manutenção"].dropna().empty:
    tipo_manutencao = df_filtrado["Tipo de manutenção"].value_counts().reset_index()
    tipo_manutencao.columns = ["Tipo de Manutenção", "Ocorrências"]
    tipo_manutencao = tipo_manutencao.sort_values("Ocorrências", ascending=False)
    chart10 = alt.Chart(tipo_manutencao).mark_bar(color="green").encode(
        y=alt.Y("Tipo de Manutenção:N", sort="-x"),
        x=alt.X("Ocorrências:Q"),
        tooltip=["Tipo de Manutenção", "Ocorrências"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 10 - Distribuição por Tipo de Manutenção")
    st.altair_chart(chart10, use_container_width=True)
