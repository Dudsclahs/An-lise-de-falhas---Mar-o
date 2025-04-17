
import streamlit as st
import pandas as pd

st.title("Dashboard de Manutenção - Campo, Interna e Terceiros")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df.columns = df.columns.str.strip()  # Remover espaços extras
    if "Entrada" in df.columns:
        df["Entrada"] = pd.to_datetime(df["Entrada"], errors="coerce")
        df["Ano/Mes"] = df["Entrada"].dt.to_period("M")
    else:
        st.error("A coluna 'Entrada' não foi encontrada no arquivo Excel.")
    return df

df = carregar_dados()

if "Origem" in df.columns:
    origens = df["Origem"].dropna().unique()
    origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", sorted(origens))
    df_filtrado = df[df["Origem"] == origem_selecionada]

    st.subheader(f"Tipo selecionado: {origem_selecionada}")

    if "Causa manutenção" in df.columns:
        tipo_falha = df_filtrado["Causa manutenção"].value_counts().sort_values(ascending=False)
        st.bar_chart(tipo_falha, use_container_width=True)

    os_por_frota = df_filtrado["Número de frota"].value_counts().sort_values(ascending=False).head(15)
    st.subheader("Top 15 - Número de OS por Frota")
    st.bar_chart(os_por_frota, use_container_width=True)

    tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().sort_values(ascending=False).head(15)
    st.subheader("Top 15 - Tempo Total de Permanência por Frota (h)")
    st.bar_chart(tempo_por_frota, use_container_width=True)

    st.subheader("Gráfico de Pareto - Tempo por Tipo de Falha")
    if "Causa manutenção" in df.columns:
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

    if "Ano/Mes" in df.columns:
        st.subheader("Tendência Mensal de Manutenções")
        tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count()
        st.line_chart(tendencia)
else:
    st.error("A coluna 'Origem' não foi encontrada. Verifique os dados.")
