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

df = carregar_dados()
df["Componente Detectado"] = df["Descrição do Trabalho / Observação (Ordem de serviço)"].apply(classificar_componente)

# SELEÇÃO DE ORIGEM
origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

# GRÁFICO 7: Tipos de Frota com Mais Ocorrências
st.subheader("Tipos de Frota com Mais Ocorrências")
if "Tipo de Frota" in df_filtrado.columns and not df_filtrado["Tipo de Frota"].dropna().empty:
    tipos_frota = df_filtrado["Tipo de Frota"].value_counts().reset_index()
    tipos_frota.columns = ["Tipo de Frota", "Ocorrências"]
    tipos_frota = tipos_frota.sort_values("Ocorrências", ascending=False)

    chart_tipos_frota = alt.Chart(tipos_frota).mark_bar(color="green").encode(
        x=alt.X("Tipo de Frota:N", sort=tipos_frota["Tipo de Frota"].tolist()),
        y="Ocorrências:Q",
        tooltip=["Tipo de Frota", "Ocorrências"]
    )
    labels_tipos_frota = alt.Chart(tipos_frota).mark_text(
        align='center', baseline='bottom', dy=-5, fontSize=12
    ).encode(
        x="Tipo de Frota:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.altair_chart(chart_tipos_frota + labels_tipos_frota, use_container_width=True)

# GRÁFICO 8: Frotas mais Frequentes (Descrição da Frota)
st.subheader("Frotas mais Frequentes (Descrição da Frota)")
if "Descrição da Frota" in df_filtrado.columns and not df_filtrado["Descrição da Frota"].dropna().empty:
    descricao_frota = df_filtrado["Descrição da Frota"].value_counts().reset_index()
    descricao_frota.columns = ["Descrição da Frota", "Ocorrências"]
    descricao_frota = descricao_frota.sort_values("Ocorrências", ascending=False)

    chart_desc_frota = alt.Chart(descricao_frota).mark_bar(color="green").encode(
        x=alt.X("Descrição da Frota:N", sort=descricao_frota["Descrição da Frota"].tolist()),
        y="Ocorrências:Q",
        tooltip=["Descrição da Frota", "Ocorrências"]
    )
    labels_desc_frota = alt.Chart(descricao_frota).mark_text(
        align='center', baseline='bottom', dy=-5, fontSize=12
    ).encode(
        x="Descrição da Frota:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.altair_chart(chart_desc_frota + labels_desc_frota, use_container_width=True)

# GRÁFICO 9: Distribuição por Tipo de Manutenção
st.subheader("Distribuição por Tipo de Manutenção")
if "Tipo de Manutenção" in df_filtrado.columns and not df_filtrado["Tipo de Manutenção"].dropna().empty:
    tipo_manutencao = df_filtrado["Tipo de Manutenção"].value_counts().reset_index()
    tipo_manutencao.columns = ["Tipo de Manutenção", "Ocorrências"]
    tipo_manutencao = tipo_manutencao.sort_values("Ocorrências", ascending=False)

    chart_tipo_manutencao = alt.Chart(tipo_manutencao).mark_bar(color="green").encode(
        x=alt.X("Tipo de Manutenção:N", sort=tipo_manutencao["Tipo de Manutenção"].tolist()),
        y="Ocorrências:Q",
        tooltip=["Tipo de Manutenção", "Ocorrências"]
    )
    labels_tipo_manutencao = alt.Chart(tipo_manutencao).mark_text(
        align='center', baseline='bottom', dy=-5, fontSize=12
    ).encode(
        x="Tipo de Manutenção:N",
        y="Ocorrências:Q",
        text="Ocorrências:Q"
    )
    st.altair_chart(chart_tipo_manutencao + labels_tipo_manutencao, use_container_width=True)
