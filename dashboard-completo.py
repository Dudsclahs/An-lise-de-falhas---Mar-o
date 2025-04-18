
import streamlit as st
import pandas as pd
import altair as alt

st.title("Dashboard de Manutenção - Análise por Componentes e Origem")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df.columns = df.columns.str.strip()
    df["Descrição do Trabalho / Observação (Ordem de serviço)"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].fillna("").str.lower()
    df["Origem"] = df["Local manutenção"].str.upper().str.strip()
    df["Origem"] = df["Origem"].replace({
        "MANUTENÇÃO CAMPO": "CAMPO",
        "MANUTENÇÃO INTERNA": "INTERNA",
        "MANUTENÇÃO TERCEIRO": "TERCEIRO"
    })
    return df

df = carregar_dados()

# Agrupar por Origem e Componente
if "Componente Detectado" in df.columns and "Origem" in df.columns:
    painel = df.groupby(["Origem", "Componente Detectado"]).size().reset_index(name="Ocorrências")

    # Dropdown interativo
    origem_selector = alt.selection_single(
        fields=["Origem"],
        bind=alt.binding_select(options=sorted(painel["Origem"].dropna().unique())),
        name="Origem"
    )

    grafico = alt.Chart(painel).mark_bar(color="green").encode(
        x=alt.X("Componente Detectado:N", sort="-y", title="Componente"),
        y=alt.Y("Ocorrências:Q"),
        tooltip=["Origem", "Componente Detectado", "Ocorrências"]
    ).add_params(
        origem_selector
    ).transform_filter(
        origem_selector
    ).properties(
        width=800,
        height=450,
        title="Ocorrências por Componente - Filtrado por Origem"
    )

    st.altair_chart(grafico, use_container_width=True)
else:
    st.warning("Colunas 'Componente Detectado' ou 'Origem' não foram encontradas.")
