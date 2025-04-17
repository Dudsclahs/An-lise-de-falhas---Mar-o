
import streamlit as st
import pandas as pd

# Título do app
st.title("Dashboard de Manutenção - Campo, Interna e Terceiros")

# Carregar os dados
@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df["Entrada"] = pd.to_datetime(df["Entrada"], errors="coerce")
    df["Ano/Mes"] = df["Entrada"].dt.to_period("M")
    return df

df = carregar_dados()

# Filtro por tipo de origem
origens = df["Origem"].unique()
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", sorted(origens))
df_filtrado = df[df["Origem"] == origem_selecionada]

st.subheader(f"Tipo selecionado: {origem_selecionada}")

# Gráfico 1: Tipos de Falha (Causa de Manutenção)
tipo_falha = df_filtrado["Causa manutenção"].value_counts().sort_values(ascending=False)
st.bar_chart(tipo_falha, use_container_width=True)

# Gráfico 2: OS por Frota
os_por_frota = df_filtrado["Número de frota"].value_counts().sort_values(ascending=False).head(15)
st.subheader("Top 15 - Número de OS por Frota")
st.bar_chart(os_por_frota, use_container_width=True)

# Gráfico 3: Tempo de permanência por frota
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().sort_values(ascending=False).head(15)
st.subheader("Top 15 - Tempo Total de Permanência por Frota (h)")
st.bar_chart(tempo_por_frota, use_container_width=True)

# Gráfico 4: Pareto de tempo por tipo de falha
st.subheader("Gráfico de Pareto - Tempo por Tipo de Falha")
df_pareto = df_filtrado.groupby("Causa manutenção")["Tempo de Permanência(h)"].sum().sort_values(ascending=False)
df_pareto = df_pareto[df_pareto > 0]
df_pareto_pct = df_pareto.cumsum() / df_pareto.sum()

import matplotlib.pyplot as plt
fig, ax1 = plt.subplots(figsize=(10, 5))

ax1.bar(df_pareto.index, df_pareto.values, color='green')
ax1.set_ylabel("Tempo Total (h)", color='green')
ax1.tick_params(axis='x', rotation=45)

ax2 = ax1.twinx()
ax2.plot(df_pareto.index, df_pareto_pct.values, color='orange', marker='o')
ax2.set_ylabel("Acumulado (%)", color='orange')
ax2.set_ylim(0, 1.05)

st.pyplot(fig)

# Gráfico 5: Tendência Mensal
st.subheader("Tendência Mensal de Manutenções")
tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count()
st.line_chart(tendencia)
