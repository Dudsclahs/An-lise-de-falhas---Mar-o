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

# Carregar e preparar os dados
df = carregar_dados()
df["Componente Detectado"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].apply(classificar_componente)

# Filtro interativo
origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

# Gráfico 1: Top 10 - Tipos de Falha
if "Causa manutenção" in df_filtrado.columns:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(10).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    chart_falha = alt.Chart(tipo_falha).mark_bar(color="green").encode(
        x=alt.X("Tipo de Falha:N", sort="-y"),
        y="Quantidade:Q",
        tooltip=["Tipo de Falha", "Quantidade"]
    )
    labels_falha = alt.Chart(tipo_falha).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Tipo de Falha:N",
        y="Quantidade:Q",
        text="Quantidade:Q"
    )
    st.subheader("Top 10 - Tipos de Falha")
    st.altair_chart(chart_falha + labels_falha, use_container_width=True)

# Gráfico 2: Top 10 - Número de OS por Frota
os_por_frota = df_filtrado["Número de frota"].value_counts().head(10).reset_index()
os_por_frota.columns = ["Frota", "OS"]
chart_os = alt.Chart(os_por_frota).mark_bar(color="green").encode(
    x=alt.X("Frota:N", sort="-y"),
    y="OS:Q",
    tooltip=["Frota", "OS"]
)
labels_os = alt.Chart(os_por_frota).mark_text(
    align="center", baseline="bottom", dy=-5, fontSize=12
).encode(
    x="Frota:N",
    y="OS:Q",
    text="OS:Q"
)
st.subheader("Top 10 - Número de OS por Frota")
st.altair_chart(chart_os + labels_os, use_container_width=True)

# Gráfico 3: Top 10 - Tempo Total de Permanência
tempo_total = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_total.columns = ["Frota", "Tempo (h)"]
top_tempo_total = tempo_total.sort_values("Tempo (h)", ascending=False).head(10)
chart_tempo_total = alt.Chart(top_tempo_total).mark_bar(color="green").encode(
    x=alt.X("Frota:N", sort="-y"),
    y="Tempo (h):Q",
    tooltip=["Frota", "Tempo (h)"]
)
labels_tempo_total = alt.Chart(top_tempo_total).mark_text(
    align="center", baseline="bottom", dy=-5, fontSize=12
).encode(
    x="Frota:N",
    y="Tempo (h):Q",
    text="Tempo (h):Q"
)
st.subheader("Top 10 - Tempo Total de Permanência por Frota (h)")
st.altair_chart(chart_tempo_total + labels_tempo_total, use_container_width=True)

# Gráfico 4: Tempo de Permanência a partir de 18/03/2025
df_periodo = df_filtrado[df_filtrado["Entrada"] >= pd.to_datetime("2025-03-18")]
df_periodo_tempo = df_periodo.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
df_periodo_tempo.columns = ["Frota", "Tempo (h)"]

if not df_periodo_tempo.empty:
    top1_frota = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).iloc[0]["Frota"]
    df_sem_top1 = df_periodo_tempo[df_periodo_tempo["Frota"] != top1_frota]
    df_top10_periodo = df_sem_top1.sort_values("Tempo (h)", ascending=False).head(10)

    chart_periodo = alt.Chart(df_top10_periodo).mark_bar(color="green").encode(
        x=alt.X("Frota:N", sort="-y"),
        y="Tempo (h):Q",
        tooltip=["Frota", "Tempo (h)"]
    )
    labels_periodo = alt.Chart(df_top10_periodo).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Frota:N",
        y="Tempo (h):Q",
        text="Tempo (h):Q"
    )
    st.subheader("Top 10 - Tempo de Permanência por Frota (a partir de 18/03/2025)")
    st.altair_chart(chart_periodo + labels_periodo, use_container_width=True)
else:
    st.info("Nenhum dado encontrado a partir de 18/03/2025 para essa origem.")

# Gráfico 5: Ocorrências por Componente
st.subheader("Ocorrências por Componente (Descrição da OS)")
comp_counts = df_filtrado["Componente Detectado"].value_counts().reset_index()
comp_counts.columns = ["Componente", "Ocorrências"]
chart_comp = alt.Chart(comp_counts).mark_bar(color="green").encode(
    x=alt.X("Componente:N", sort="-y"),
    y="Ocorrências:Q",
    tooltip=["Componente", "Ocorrências"]
)
labels_comp = alt.Chart(comp_counts).mark_text(
    align="center", baseline="bottom", dy=-5, fontSize=12
).encode(
    x="Componente:N",
    y="Ocorrências:Q",
    text="Ocorrências:Q"
)
st.altair_chart(chart_comp + labels_comp, use_container_width=True)

# Gráfico 6: Tendência Mensal
if "Ano/Mes" in df_filtrado.columns:
    tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count().reset_index()
    tendencia.columns = ["Ano/Mês", "Quantidade"]
    chart_tend = alt.Chart(tendencia).mark_line(point=True, color="green").encode(
        x="Ano/Mês:T",
        y="Quantidade:Q",
        tooltip=["Ano/Mês", "Quantidade"]
    )
    st.subheader("Tendência Mensal de Manutenções")
    st.altair_chart(chart_tend, use_container_width=True)

# Gráfico 7: Tipos de Frota com Mais Ocorrências
if "Tipo de Frota" in df_filtrado.columns and not df_filtrado["Tipo de Frota"].dropna().empty:
    tipos = df_filtrado["Tipo de Frota"].value_counts().reset_index()
    tipos.columns = ["Tipo de Frota", "Ocorrências"]
    chart_tipos = alt.Chart(tipos).mark_bar(color="green").encode(
        x=alt.X("Tipo de Frota:N", sort="-y"),
        y="Ocorrências:Q",
        tooltip=["Tipo de Frota", "Ocorrências"]
    )
    labels_tipos = alt.Chart(tipos).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Tipo de Frota:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.subheader("Tipos de Frota com Mais Ocorrências")
    st.altair_chart(chart_tipos + labels_tipos, use_container_width=True)

# Gráfico 8: Frotas mais Frequentes (Descrição da Frota)
if "Descrição da Frota" in df_filtrado.columns and not df_filtrado["Descrição da Frota"].dropna().empty:
    descricoes = df_filtrado["Descrição da Frota"].value_counts().reset_index()
    descricoes.columns = ["Descrição da Frota", "Ocorrências"]
    chart_descricoes = alt.Chart(descricoes).mark_bar(color="green").encode(
        x=alt.X("Descrição da Frota:N", sort="-y"),
        y="Ocorrências:Q",
        tooltip=["Descrição da Frota", "Ocorrências"]
    )
    labels_descricoes = alt.Chart(descricoes).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Descrição da Frota:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.subheader("Frotas mais Frequentes (Descrição da Frota)")
    st.altair_chart(chart_descricoes + labels_descricoes, use_container_width=True)

# Gráfico 9: Distribuição por Tipo de Manutenção
if "Tipo de Manutenção" in df_filtrado.columns and not df_filtrado["Tipo de Manutenção"].dropna().empty:
    manutencoes = df_filtrado["Tipo de Manutenção"].value_counts().reset_index()
    manutencoes.columns = ["Tipo de Manutenção", "Ocorrências"]
    chart_manut = alt.Chart(manutencoes).mark_bar(color="green").encode(
        x=alt.X("Tipo de Manutenção:N", sort="-y"),
        y="Ocorrências:Q",
        tooltip=["Tipo de Manutenção", "Ocorrências"]
    )
    labels_manut = alt.Chart(manutencoes).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Tipo de Manutenção:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.subheader("Distribuição por Tipo de Manutenção")
    st.altair_chart(chart_manut + labels_manut, use_container_width=True)
