
import streamlit as st
import pandas as pd
import altair as alt

st.title("Dashboard de Manutenção - Análise Consolidada (Debug)")

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

# DEBUG: Visualizar os dados filtrados de 18 de março em diante
st.subheader("📊 DEBUG - Dados a partir de 18/03/2025")
st.write(df[df["Entrada"] >= pd.to_datetime("2025-03-18")])

# Incluir o gráfico de tempo de permanência a partir de 18/03/2025
st.subheader("Top 10 - Tempo de Permanência por Frota (a partir de 18/03/2025)")
df_periodo = df[df["Entrada"] >= pd.to_datetime("2025-03-18")]
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
    st.warning("⚠️ Nenhum dado encontrado para o período a partir de 18/03/2025.")
