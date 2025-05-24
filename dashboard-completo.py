
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado Final")

@st.cache_data
def carregar_dados():
    df = pd.read_excel("analise_manutencao_completa.xlsx", sheet_name="Planilha1")
    df.columns = df.columns.str.strip()
    df["Descrição do Trabalho/ Observação"] = df["Descrição do Trabalho/ Observação"].fillna("").str.lower()

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
        df["Ano/Mes"] = df["Entrada"].dt.to_period("M").dt.to_timestamp()

    if "Saída Real" in df.columns:
        df["Saída"] = pd.to_datetime(df["Saída Real"], errors="coerce")

    return df

def classificar_componente(texto):
    categorias = {
        "Suspensão": ["mola", "molas", "molejo", "estabilizador", "amortecedor"],
        "Pneu/Roda": ["cubo", "pneu", "pneus", "freio", "freios", "pastilha", "pinça", "disco", "cuica"],
        "Motor": ["motor", "cabeçote", "bloco", "pressão de óleo"],
        "Transmissão": ["não engata marcha", "não engata", "neutro", "transmissão", "cambio", "travou cambio", "embreagem"],
        "Perda de potência": ["Perca de potência", "Perca de potencia", "perda de potência", "perda de potencia", "falta potência", "falta potencia"],
        "Vazamento - Combustível": ["vazamento combustível", "vazamento de combustível", "vaz. combustível"],
        "Vazamento - Hidráulico": ["vazamento hidráulico", "vazamento de óleo hidráulico", "hidráulico"],
        "Vazamento - Óleo": ["vazamento óleo", "vazamento de óleo", "vaz. óleo"],
        "Rodantes": ["rodante", "esteira", "roletes", "coroa", "roda motriz"],
        "Elétrica": ["elétrica", "luz", "farol", "chicote", "bateria", "não liga", "sem partida"],
        "Mangueira (Vazamento)": ["mangueira", "mangueiras", "mangote", ],
        "Caldeiraria": ["soldagem", "solda", "soldar", "caldeiraria", ],
        "Tanque de combustível": ["Tanque de combustivel", "Tanque de combustível", "Tag de combustível", ],
        "Rádio": ["radio", "rádio"],
        "Faquinha": ["Trocar faquinha", "Girar faquinha", "Faquinha", "Atropelou faquinha"]
        "Falha Eletrônica / Painel": ["painel", "computador", "tela", "falha", "eletrônico", "sistema", "display", "luz espia", "injetor"],
        "Ar Condicionado": ["ar condicionado", "ac", "climatizador", "evaporador", "ventilador", "condensador", "compressor do ar"],
        "Elevador": ["elevador", "elevatória", "plataforma", "Descarrilhou esteira elevador"],
        "Acumulador": ["acumulador"],
        "Despontador": ["despontador"]
        "Avaliar": ["avaliar", "verificação", "verificar"],
    }
    for categoria, palavras in categorias.items():
        if any(p in texto for p in palavras):
            return categoria
    return "Não Classificado"

# Carrega os dados
df = carregar_dados()
df["Componente Detectado"] = df["Descrição do Trabalho/ Observação"].apply(classificar_componente)

# Filtro lateral de período
st.sidebar.header("Filtro de Período")
data_inicio = st.sidebar.date_input("Data de Início", value=pd.to_datetime("01-03-2025"), format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data de Fim", value=pd.to_datetime("today"), format="DD/MM/YYYY")

# Filtro de origem
origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)

# Filtros aplicados
filtro_entrada = (df["Entrada"] >= pd.to_datetime(data_inicio)) & (df["Entrada"] <= pd.to_datetime(data_fim))
filtro_saida = (df["Saída"] >= pd.to_datetime(data_inicio)) & (df["Saída"] <= pd.to_datetime(data_fim))

# Base filtrada para os gráficos 1 a 5, 7 a 10
df_filtrado = df[filtro_entrada & (df["Origem"] == origem_selecionada)]
df_saida_filtrado = df[filtro_saida & (df["Origem"] == origem_selecionada)]

# GRÁFICO 1 - Top 10 Tipos de Falha
if "Causa manutenção" in df_filtrado.columns and not df_filtrado["Causa manutenção"].dropna().empty:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(10).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    chart1 = alt.Chart(tipo_falha).mark_bar(color="green").encode(
        y=alt.Y("Tipo de Falha:N", sort="-x"),
        x=alt.X("Quantidade:Q"),
        tooltip=["Tipo de Falha", "Quantidade"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 1 - Top 10 Tipos de Falha")
    st.altair_chart(chart1, use_container_width=True)

# GRÁFICO 2 - Número de OS por Frota
os_por_frota = df_filtrado["Número de frota"].value_counts().head(10).reset_index()
os_por_frota.columns = ["Frota", "OS"]
chart2 = alt.Chart(os_por_frota).mark_bar(color="green").encode(
    y=alt.Y("Frota:N", sort="-x"),
    x=alt.X("OS:Q"),
    tooltip=["Frota", "OS"]
).properties(width=800, height=400)
st.subheader("Gráfico 2 - Top 10 Número de OS por Frota")
st.altair_chart(chart2, use_container_width=True)

# GRÁFICO 3 - Tempo Total por Frota (não filtrado por período)
tempo_total = df.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_total.columns = ["Frota", "Tempo (h)"]
tempo_top = tempo_total.sort_values("Tempo (h)", ascending=False).head(10)
chart3 = alt.Chart(tempo_top).mark_bar(color="green").encode(
    y=alt.Y("Frota:N", sort="-x"),
    x=alt.X("Tempo (h):Q"),
    tooltip=["Frota", "Tempo (h)"]
).properties(width=800, height=400)
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Frota (h)")
st.altair_chart(chart3, use_container_width=True)

# GRÁFICO 4 - Tempo Total por Frota (filtrado por período, exceto Top 1)
df_temp = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
df_temp.columns = ["Frota", "Tempo (h)"]
if not df_temp.empty:
    top1 = df_temp.sort_values("Tempo (h)", ascending=False).iloc[0]["Frota"]
    df_temp = df_temp[df_temp["Frota"] != top1]
    top10_restante = df_temp.sort_values("Tempo (h)", ascending=False).head(10)
    chart4 = alt.Chart(top10_restante).mark_bar(color="green").encode(
        y=alt.Y("Frota:N", sort="-x"),
        x=alt.X("Tempo (h):Q"),
        tooltip=["Frota", "Tempo (h)"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 4 - Top 10 Tempo de Permanência por Frota no Período (exceto Top 1)")
    st.altair_chart(chart4, use_container_width=True)

# GRÁFICO 5 - Ocorrências por Componente
ocorrencias_comp = df_filtrado["Componente Detectado"].value_counts().reset_index()
ocorrencias_comp.columns = ["Componente", "Ocorrências"]
chart5 = alt.Chart(ocorrencias_comp).mark_bar(color="green").encode(
    y=alt.Y("Componente:N", sort="-x"),
    x=alt.X("Ocorrências:Q"),
    tooltip=["Componente", "Ocorrências"]
).properties(width=800, height=400)
st.subheader("Gráfico 5 - Ocorrências por Componente (Descrição da OS)")
st.altair_chart(chart5, use_container_width=True)

# GRÁFICO 6 - Tendência Diária de Entrada de OS
# Agrupar corretamente por dia
tendencia_entrada = df[df["Entrada"].notna() & (df["Origem"] == origem_selecionada)].copy()
tendencia_entrada["Data de Entrada"] = tendencia_entrada["Entrada"].dt.floor("D")
tendencia_entrada = tendencia_entrada.groupby("Data de Entrada").size().reset_index(name="Quantidade")

# Criar gráfico com escala Y iniciando em 1
chart7 = alt.Chart(tendencia_entrada).mark_bar(color="green").encode(
    x=alt.X("Data de Entrada:T", title="Data de Entrada", axis=alt.Axis(format="%d/%m"), sort=None),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS", scale=alt.Scale(domainMin=1), axis=alt.Axis(tickMinStep=1)),
    tooltip=["Data de Entrada", "Quantidade"]
).properties(width=800, height=400)

# Exibir gráfico
st.subheader("Gráfico 6 - Tendência Diária de Entrada de OS")
st.altair_chart(chart7, use_container_width=True)


# GRÁFICO 7 - Frotas mais Frequentes (Descrição da Frota)
if "Descrição  frota" in df_filtrado.columns:
    descricao_frota = df_filtrado["Descrição  frota"].value_counts().reset_index().head(10)
    descricao_frota.columns = ["Descrição da Frota", "Ocorrências"]
    chart9 = alt.Chart(descricao_frota).mark_bar(color="green").encode(
        y=alt.Y("Descrição da Frota:N", sort="-x"),
        x=alt.X("Ocorrências:Q"),
        tooltip=["Descrição da Frota", "Ocorrências"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 7 - Frotas mais Frequentes (Descrição da Frota)")
    st.altair_chart(chart9, use_container_width=True)

# GRÁFICO 8 - Tipo de Manutenção
if "Tipo de manutenção" in df_filtrado.columns and not df_filtrado["Tipo de manutenção"].dropna().empty:
    tipo_manutencao = df_filtrado["Tipo de manutenção"].value_counts().reset_index()
    tipo_manutencao.columns = ["Tipo de Manutenção", "Ocorrências"]
    chart10 = alt.Chart(tipo_manutencao).mark_bar(color="green").encode(
        y=alt.Y("Tipo de Manutenção:N", sort="-x"),
        x=alt.X("Ocorrências:Q"),
        tooltip=["Tipo de Manutenção", "Ocorrências"]
    ).properties(width=800, height=400)
    st.subheader("Gráfico 8 - Distribuição por Tipo de Manutenção")
    st.altair_chart(chart10, use_container_width=True)

# GRÁFICO FINAL 9 - Tendência Mensal de Manutenções (não filtrado)
tendencia_geral = df[df["Entrada"].notna()].groupby("Ano/Mes")["Boletim"].count().reset_index()
tendencia_geral.columns = ["Ano/Mês", "Quantidade"]
chart6 = alt.Chart(tendencia_geral).mark_line(point=True, color="green").encode(
    x=alt.X("Ano/Mês:T", title="Ano/Mês"),
    y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
    tooltip=["Ano/Mês", "Quantidade"]
).properties(width=800, height=400)
st.subheader("Gráfico 9 - Tendência Mensal de Manutenções")
st.altair_chart(chart6, use_container_width=True)
