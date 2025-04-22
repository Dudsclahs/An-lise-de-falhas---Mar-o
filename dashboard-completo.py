import streamlit as st
import pandas as pd
import altair as alt

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

# FILTRO DE PERÍODO PERSONALIZADO (SEM O ERRO DO FORMATO)
st.sidebar.header("Filtro de Período")
data_inicio = st.sidebar.date_input("Data de Início", value=pd.to_datetime("2025-03-01"))
data_fim = st.sidebar.date_input("Data de Fim", value=pd.to_datetime("today"))

# Este trecho será continuado com os gráficos conforme seu código completo anterior
