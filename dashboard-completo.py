
import streamlit as st
import pandas as pd
import altair as alt

st.title("Dashboard de Manutenção - Campo, Interna e Terceiros")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df.columns = df.columns.str.strip()
    if "Entrada" in df.columns:
        df["Entrada"] = pd.to_datetime(df["Entrada"], errors="coerce")
        df["Ano/Mes"] = df["Entrada"].dt.to_period("M")
    return df

df = carregar_dados()

if "Origem" in df.columns:
    origens = df["Origem"].dropna().unique()
    origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", sorted(origens))
    df_filtrado = df[df["Origem"] == origem_selecionada]

    st.subheader(f"Tipo selecionado: {origem_selecionada}")

    # Tipos de Falha
    if "Causa manutenção" in df_filtrado.columns:
        tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(15).reset_index()
        tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
        tipo_falha["Tipo de Falha"] = tipo_falha["Tipo de Falha"].astype(str)
        tipo_falha["Tipo de Falha"] = pd.Categorical(tipo_falha["Tipo de Falha"], categories=tipo_falha["Tipo de Falha"], ordered=True)

        bars_falha = alt.Chart(tipo_falha).mark_bar(color="green").encode(
            x=alt.X("Tipo de Falha:N"),
            y="Quantidade:Q"
        )

        labels_falha = alt.Chart(tipo_falha).mark_text(
            align="center", baseline="bottom", dy=-5, fontSize=12
        ).encode(
            x="Tipo de Falha:N",
            y="Quantidade:Q",
            text=alt.Text("Quantidade:Q", format=".0f")
        )

        st.subheader("Top 15 - Tipos de Falha")
        st.altair_chart(bars_falha + labels_falha, use_container_width=True)

    # Número de OS por Frota
    os_por_frota = df_filtrado["Número de frota"].value_counts().head(15).reset_index()
    os_por_frota.columns = ["Frota", "OS"]
    os_por_frota["Frota"] = os_por_frota["Frota"].astype(str)
    os_por_frota["Frota"] = pd.Categorical(os_por_frota["Frota"], categories=os_por_frota["Frota"], ordered=True)

    bars_os = alt.Chart(os_por_frota).mark_bar(color="green").encode(
        x=alt.X("Frota:N"),
        y="OS:Q"
    )

    labels_os = alt.Chart(os_por_frota).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Frota:N",
        y="OS:Q",
        text=alt.Text("OS:Q", format=".0f")
    )

    st.subheader("Top 15 - Número de OS por Frota")
    st.altair_chart(bars_os + labels_os, use_container_width=True)

    # Tempo de Permanência por Frota
    tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
    tempo_por_frota.columns = ["Frota", "Tempo (h)"]
    tempo_por_frota = tempo_por_frota.sort_values("Tempo (h)", ascending=False).head(15)
    tempo_por_frota["Frota"] = tempo_por_frota["Frota"].astype(str)
    tempo_por_frota["Frota"] = pd.Categorical(tempo_por_frota["Frota"], categories=tempo_por_frota["Frota"], ordered=True)

    bars_tempo = alt.Chart(tempo_por_frota).mark_bar(color="green").encode(
        x=alt.X("Frota:N"),
        y="Tempo (h):Q"
    )

    labels_tempo = alt.Chart(tempo_por_frota).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Frota:N",
        y="Tempo (h):Q",
        text=alt.Text("Tempo (h):Q", format=".0f")
    )

    st.subheader("Top 15 - Tempo Total de Permanência por Frota (h)")
    st.altair_chart(bars_tempo + labels_tempo, use_container_width=True)

    # Pareto
    if "Causa manutenção" in df_filtrado.columns:
        df_pareto = df_filtrado.groupby("Causa manutenção")["Tempo de Permanência(h)"].sum().sort_values(ascending=False)
        df_pareto = df_pareto[df_pareto > 0].reset_index()
        df_pareto.columns = ["Tipo de Falha", "Tempo"]
        df_pareto["Tipo de Falha"] = df_pareto["Tipo de Falha"].astype(str)
        df_pareto["Tipo de Falha"] = pd.Categorical(df_pareto["Tipo de Falha"], categories=df_pareto["Tipo de Falha"], ordered=True)
        df_pareto["Acumulado (%)"] = df_pareto["Tempo"].cumsum() / df_pareto["Tempo"].sum()

        bars_pareto = alt.Chart(df_pareto).mark_bar(color="green").encode(
            x=alt.X("Tipo de Falha:N"),
            y="Tempo:Q"
        )

        linha_pareto = alt.Chart(df_pareto).mark_line(point=True, color="orange").encode(
            x="Tipo de Falha:N",
            y=alt.Y("Acumulado (%):Q", axis=alt.Axis(format='%'))
        )

        st.subheader("Gráfico de Pareto - Tempo por Tipo de Falha")
        st.altair_chart(bars_pareto + linha_pareto, use_container_width=True)

    # Tendência Mensal
    if "Ano/Mes" in df_filtrado.columns:
        tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count().reset_index()
        tendencia.columns = ["Ano/Mês", "Quantidade"]

        chart_tendencia = alt.Chart(tendencia).mark_line(point=True, color="green").encode(
            x="Ano/Mês:T",
            y="Quantidade:Q"
        ).properties(width=700)

        st.subheader("Tendência Mensal de Manutenções")
        st.altair_chart(chart_tendencia, use_container_width=True)
else:
    st.error("A coluna 'Origem' não foi encontrada no arquivo.")
