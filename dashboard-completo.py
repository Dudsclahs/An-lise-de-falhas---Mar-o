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

origens = sorted(df["Origem"].dropna().unique())
origem_selecionada = st.selectbox("Selecione o tipo de manutenção:", origens)
df_filtrado = df[df["Origem"] == origem_selecionada]

def plot_horizontal_bar(data, x_col, y_col, tooltip, titulo):
    chart = alt.Chart(data).mark_bar(color="green").encode(
        y=alt.Y(f"{y_col}:N", sort="-x", axis=alt.Axis(labelLimit=400, titleLimit=400)),
        x=alt.X(f"{x_col}:Q", axis=alt.Axis(title="Quantidade")),
        tooltip=tooltip
    ).properties(width=1000, height=400)
    st.subheader(titulo)
    st.altair_chart(chart, use_container_width=True)

# GRÁFICO 1
if "Causa manutenção" in df_filtrado.columns:
    tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(10).reset_index()
    tipo_falha.columns = ["Tipo de Falha", "Quantidade"]
    plot_horizontal_bar(tipo_falha, "Quantidade", "Tipo de Falha", ["Tipo de Falha", "Quantidade"], "Top 10 - Tipos de Falha")

# GRÁFICO 2
os_por_frota = df_filtrado["Número de frota"].value_counts().head(10).reset_index()
os_por_frota.columns = ["Frota", "OS"]
plot_horizontal_bar(os_por_frota, "OS", "Frota", ["Frota", "OS"], "Top 10 - Número de OS por Frota")

# GRÁFICO 3
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
tempo_por_frota.columns = ["Frota", "Tempo (h)"]
tempo_top = tempo_por_frota.sort_values("Tempo (h)", ascending=False).head(10)
plot_horizontal_bar(tempo_top, "Tempo (h)", "Frota", ["Frota", "Tempo (h)"], "Top 10 - Tempo Total de Permanência por Frota (h)")

# GRÁFICO 4
df_periodo = df_filtrado[df_filtrado["Entrada"] >= pd.to_datetime("2025-03-18")]
df_periodo_tempo = df_periodo.groupby("Número de frota")["Tempo de Permanência(h)"].sum().reset_index()
df_periodo_tempo.columns = ["Frota", "Tempo (h)"]
if not df_periodo_tempo.empty:
    top1 = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).iloc[0]["Frota"]
    df_periodo_tempo = df_periodo_tempo[df_periodo_tempo["Frota"] != top1]
    df_top10_periodo = df_periodo_tempo.sort_values("Tempo (h)", ascending=False).head(10)
    plot_horizontal_bar(df_top10_periodo, "Tempo (h)", "Frota", ["Frota", "Tempo (h)"], "Top 10 - Tempo de Permanência por Frota (a partir de 18/03/2025)")
else:
    st.info("Nenhum dado encontrado a partir de 18/03/2025 para essa origem.")

# GRÁFICO 5
agrupado_componentes = df_filtrado["Componente Detectado"].value_counts().reset_index()
agrupado_componentes.columns = ["Componente", "Ocorrências"]
plot_horizontal_bar(agrupado_componentes, "Ocorrências", "Componente", ["Componente", "Ocorrências"], "Ocorrências por Componente (Descrição da OS)")

# GRÁFICO 6
if "Ano/Mes" in df_filtrado.columns:
    st.subheader("Tendência Mensal de Manutenções")
    tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count().reset_index()
    tendencia.columns = ["Ano/Mês", "Quantidade"]
    chart_tendencia = alt.Chart(tendencia).mark_line(point=True, color="green").encode(
        x=alt.X("Ano/Mês:T", title="Ano/Mês"),
        y="Quantidade:Q",
        tooltip=["Ano/Mês", "Quantidade"]
    ).properties(width=800, height=400)
    st.altair_chart(chart_tendencia, use_container_width=True)

# GRÁFICO 7
st.subheader("Tipos de Frota com Mais Ocorrências")
if "Tipo de Frota" in df_filtrado.columns:
    tipos_frota = df_filtrado["Tipo de Frota"].value_counts().reset_index()
    if not tipos_frota.empty:
        tipos_frota.columns = ["Tipo de Frota", "Ocorrências"]
        tipos_frota = tipos_frota.sort_values("Ocorrências", ascending=False)
        plot_horizontal_bar(tipos_frota, "Ocorrências", "Tipo de Frota", ["Tipo de Frota", "Ocorrências"], "")
    else:
        st.info("Nenhum dado disponível para Tipos de Frota.")


# GRÁFICO 8
st.subheader("Frotas mais Frequentes (Descrição da Frota)")
if "Descrição da Frota" in df_filtrado.columns:
    descricao_frota = df_filtrado["Descrição da Frota"].value_counts().reset_index().head(15)
    if not descricao_frota.empty:
        descricao_frota.columns = ["Descrição da Frota", "Ocorrências"]
        descricao_frota = descricao_frota.sort_values("Ocorrências", ascending=False)
        plot_horizontal_bar(descricao_frota, "Ocorrências", "Descrição da Frota", ["Descrição da Frota", "Ocorrências"], "")
    else:
        st.info("Nenhum dado disponível para Descrição da Frota.")


# GRÁFICO 9
st.subheader("Distribuição por Tipo de Manutenção")
if "Tipo de Manutenção" in df_filtrado.columns:
    tipo_manutencao = df_filtrado["Tipo de Manutenção"].value_counts().reset_index().head(15)
    if not tipo_manutencao.empty:
        tipo_manutencao.columns = ["Tipo de Manutenção", "Ocorrências"]
        tipo_manutencao = tipo_manutencao.sort_values("Ocorrências", ascending=False)
        plot_horizontal_bar(tipo_manutencao, "Ocorrências", "Tipo de Manutenção", ["Tipo de Manutenção", "Ocorrências"], "")
    else:
        st.info("Nenhum dado disponível para Tipo de Manutenção.")
