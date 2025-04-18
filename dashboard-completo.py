
import streamlit as st
import pandas as pd
import altair as alt

st.title("Dashboard de Manutenção - Componentes por Descrição")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Consolidado")
    df.columns = df.columns.str.strip()
    df["Descrição do Trabalho / Observação (Ordem de serviço)"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].fillna("").str.lower()
    
    # Verificar e criar coluna Origem
    if "Local manutenção" in df.columns:
        df["Origem"] = df["Local manutenção"].str.upper().str.strip()
        df["Origem"] = df["Origem"].replace({
            "MANUTENÇÃO CAMPO": "CAMPO",
            "MANUTENÇÃO INTERNA": "INTERNA",
            "MANUTENÇÃO TERCEIRO": "TERCEIRO"
        })
    else:
        df["Origem"] = "NÃO INFORMADO"
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

# Carregar e classificar
df = carregar_dados()
df["Componente Detectado"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].apply(classificar_componente)

# Agrupar por origem e componente
agrupado = df.groupby(["Origem", "Componente Detectado"]).size().reset_index(name="Ocorrências")

# Dropdown interativo
origem_selector = alt.selection_single(
    fields=["Origem"],
    bind=alt.binding_select(options=sorted(agrupado["Origem"].dropna().unique())),
    name="Origem"
)

# Gráfico interativo
grafico = alt.Chart(agrupado).mark_bar(color="green").encode(
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
