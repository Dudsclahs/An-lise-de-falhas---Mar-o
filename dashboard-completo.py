
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

def plotar_barra_rotulo(df, x_col, y_col, titulo, cor="green"):
    df[x_col] = df[x_col].astype(str)
    df[x_col] = pd.Categorical(df[x_col], categories=df[x_col], ordered=True)

    barra = alt.Chart(df).mark_bar(color=cor).encode(
        x=alt.X(f"{x_col}:N"),
        y=alt.Y(f"{y_col}:Q")
    )

    texto = alt.Chart(df).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x=f"{x_col}:N",
        y=f"{y_col}:Q",
        text=alt.Text(f"{y_col}:Q", format=".0f")
    )

    st.subheader(titulo)
    st.altair_chart(barra + texto, use_container_width=True)

df = carregar_dados()
df_filtrado = df  # usa tudo, sem filtro por origem

# Tipos de Falha
if "Causa manutenção" in df_filtrado.columns:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(15).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    plotar_barra_rotulo(tipo_falha, "Tipo de Falha", "Quantidade", "Top 15 - Tipos de Falha")

# OS por Frota
os_por_frota = df_filtrado["Número de frota"].value_counts().head(15).reset_index()
os_por_frota.columns = ["Frota", "OS"]
plotar_barra_rotulo(os_por_frota, "Frota", "OS", "Top 15 - Número de OS por Frota")

# Tempo por Frota
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_por_frota.columns = ["Frota", "Tempo (h)"]
tempo_por_frota = tempo_por_frota.sort_values("Tempo (h)", ascending=False).head(15)
plotar_barra_rotulo(tempo_por_frota, "Frota", "Tempo (h)", "Top 15 - Tempo Total de Permanência por Frota (h)")

# Gráfico de Pareto corrigido
if "Causa manutenção" in df_filtrado.columns:
    df_pareto = df_filtrado.groupby("Causa manutenção")["Tempo de Permanência(h)"].sum().sort_values(ascending=False)
    df_pareto = df_pareto[df_pareto > 0].reset_index()
    df_pareto.columns = ["Tipo de Falha", "Tempo"]
    df_pareto["Tipo de Falha"] = df_pareto["Tipo de Falha"].astype(str)
    df_pareto["Tipo de Falha"] = pd.Categorical(df_pareto["Tipo de Falha"], categories=df_pareto["Tipo de Falha"], ordered=True)
    df_pareto["Acumulado (%)"] = df_pareto["Tempo"].cumsum() / df_pareto["Tempo"].sum()

    bars = alt.Chart(df_pareto).mark_bar(color="green").encode(
        x=alt.X("Tipo de Falha:N"),
        y=alt.Y("Tempo:Q", axis=alt.Axis(title="Tempo Total (h)"))
    )

    labels = alt.Chart(df_pareto).mark_text(
        align="center", baseline="bottom", dy=-5, fontSize=12
    ).encode(
        x="Tipo de Falha:N",
        y="Tempo:Q",
        text=alt.Text("Tempo:Q", format=".0f")
    )

    linha = alt.Chart(df_pareto).mark_line(color="orange", point=alt.OverlayMarkDef(filled=True, color="orange")).encode(
        x="Tipo de Falha:N",
        y=alt.Y("Acumulado (%):Q", axis=alt.Axis(title="Acumulado (%)", format=".0%"), scale=alt.Scale(domain=[0, 1]))
    )

    pareto_chart = alt.layer(bars + labels, linha).resolve_scale(
        y='independent'
    )

    st.subheader("Gráfico de Pareto - Tempo por Tipo de Falha")
    st.altair_chart(pareto_chart, use_container_width=True)

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
