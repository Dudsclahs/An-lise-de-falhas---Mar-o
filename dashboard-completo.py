
import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO, StringIO

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado (CSV)")

# =========================
# Carregamento de dados
# =========================
@st.cache_data(show_spinner=False)
def carregar_dados_csv(arquivo):
    """
    Lê CSV enviado no uploader.
    Tenta primeiro latin-1 + ';' e, se falhar, faz detecção automática.
    """
    # Primeira tentativa: latin-1 ; (mais comum em exportações BR)
    try:
        df = pd.read_csv(arquivo, encoding="latin1", sep=";")
    except Exception:
        # Volta o cursor para o início e tenta detectar
        if hasattr(arquivo, "seek"):
            arquivo.seek(0)
        try:
            df = pd.read_csv(arquivo, engine="python", sep=None)  # infere separador
        except Exception as e:
            raise RuntimeError(f"Falha ao ler o CSV: {e}")

    df.columns = df.columns.str.strip()

    # Padroniza descrição
    if "DE_SERVICO" in df.columns:
        df["DE_SERVICO"] = df["DE_SERVICO"].fillna("").astype(str).str.lower()
    else:
        df["DE_SERVICO"] = ""

    # Converte datas (dia primeiro). Aceita variações com/sem segundos.
    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Ano/Mês a partir de ENTRADA
    if "ENTRADA" in df.columns:
        df["Ano/Mes"] = df["ENTRADA"].dt.to_period("M").dt.to_timestamp()
    else:
        df["Ano/Mes"] = pd.NaT

    # Tempo de Permanência (h) = SAIDA - ENTRADA
    if {"ENTRADA", "SAIDA"}.issubset(df.columns):
        df["Tempo de Permanência(h)"] = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    # Compatibilidade
    if "CD_EQUIPTO" not in df.columns:
        df["CD_EQUIPTO"] = pd.NA
    if "CD_CLASMANU" not in df.columns:
        df["CD_CLASMANU"] = pd.NA

    # Origem não existe nesta base
    df["Origem"] = "NÃO INFORMADO"

    return df

# =========================
# Classificador de componente
# =========================
def classificar_componente(texto: str) -> str:
    categorias = {
        "Suspensão": ["mola", "molas", "molejo", "estabilizador", "pneu", "freio"],
        "Motor": [" motor", "motor "],  # evita "motorista"
        "Vazamento - Combustível": ["vazamento combustível", "vazamento de combustível", "vaz. combustível"],
        "Vazamento - Hidráulico": ["vazamento hidráulico", "vazamento de óleo hidráulico", "hidráulico"],
        "Vazamento - Óleo": ["vazamento óleo", "vazamento de óleo", "vaz. óleo"],
        "Rodantes": ["rodante", "esteira", "roletes", "coroa", "roda motriz"],
        "Elétrica": ["elétrica", "luz", "farol", "chicote", "bateria"],
        "Mangueira (Vazamento)": ["mangueira"],
        "Rádio": ["radio", "rádio"],
        "Avaliar": ["avaliar", "verificação", "verificar"],
        "Falha Eletrônica / Painel": ["painel", "computador", "tela", "falha", "eletrôn", "sistema", "display", "luz espia", "injetor"],
        "Ar Condicionado": ["ar condicionado", " ac ", "climatizador", "evaporador", "ventilador", "condensador", "compressor do ar"],
        "Elevador": ["elevador", "elevatória", "plataforma"],
        "Acumulador": ["acumulador"],
        "Despontador": ["despontador"]
    }
    if not isinstance(texto, str):
        return "Não Classificado"
    for categoria, palavras in categorias.items():
        if any(p in texto for p in palavras):
            return categoria
    return "Não Classificado"

# =========================
# Entrada de arquivo (OBRIGATÓRIO)
# =========================
st.sidebar.header("Arquivo de Dados")
arquivo = st.sidebar.file_uploader("Envie o CSV (delimitado por ';')", type=["csv"])

if arquivo is None:
    st.info("Envie o arquivo CSV no painel lateral para carregar o dashboard.")
    st.stop()

df = carregar_dados_csv(arquivo)
df["Componente Detectado"] = df["DE_SERVICO"].apply(classificar_componente)

# =========================
# Filtros
# =========================
st.sidebar.header("Filtro de Período (aplicado na maioria dos gráficos)")
hoje = pd.Timestamp.today().normalize()
inicio_padrao = (df["ENTRADA"].min().date()
                 if "ENTRADA" in df.columns and pd.notna(df["ENTRADA"]).any()
                 else (hoje - pd.Timedelta(days=30)).date())
data_inicio = st.sidebar.date_input("Data de Início", value=inicio_padrao)
data_fim = st.sidebar.date_input("Data de Fim", value=hoje.date())

# Filtro por classificação (CD_CLASMANU) opcional
valores_clas = sorted([v for v in df["CD_CLASMANU"].dropna().unique().tolist()])
op_clas = st.sidebar.multiselect("Filtrar por CD_CLASMANU (opcional)", valores_clas, default=valores_clas)

mask_periodo = pd.Series(True, index=df.index)
if "ENTRADA" in df.columns:
    mask_periodo = (df["ENTRADA"] >= pd.to_datetime(data_inicio)) & (df["ENTRADA"] <= pd.to_datetime(data_fim))
mask_clas = df["CD_CLASMANU"].isin(op_clas) if len(op_clas) > 0 else pd.Series(True, index=df.index)

df_filtrado = df[mask_periodo & mask_clas].copy()

# =========================
# GRÁFICO 1 — Top 10 Classificações (CD_CLASMANU)
# =========================
st.subheader("Gráfico 1 - Top 10 Classificações (CD_CLASMANU)")
g1 = (df_filtrado["CD_CLASMANU"]
      .value_counts()
      .reset_index()
      .rename(columns={"index": "CD_CLASMANU", "CD_CLASMANU": "Quantidade"})
      .head(10))
st.altair_chart(
    alt.Chart(g1).mark_bar().encode(
        y=alt.Y("CD_CLASMANU:N", sort="-x"),
        x=alt.X("Quantidade:Q"),
        tooltip=["CD_CLASMANU", "Quantidade"]
    ).properties(width=800, height=380),
    use_container_width=True
)

# =========================
# GRÁFICO 2 — Top 10 Número de OS por Equipamento (CD_EQUIPTO)
# =========================
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento (CD_EQUIPTO)")
g2 = (df_filtrado["CD_EQUIPTO"]
      .value_counts()
      .reset_index()
      .rename(columns={"index": "CD_EQUIPTO", "CD_EQUIPTO": "OS"})
      .head(10))
st.altair_chart(
    alt.Chart(g2).mark_bar().encode(
        y=alt.Y("CD_EQUIPTO:N", sort="-x", title="Equipamento"),
        x=alt.X("OS:Q", title="Quantidade de OS"),
        tooltip=[alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"), "OS:Q"]
    ).properties(width=800, height=380),
    use_container_width=True
)

# =========================
# GRÁFICO 3 — Top 10 Tempo Total de Permanência por Equipamento (filtrado)
# =========================
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Equipamento (h)")
if "Tempo de Permanência(h)" in df_filtrado.columns:
    g3 = (df_filtrado
          .dropna(subset=["Tempo de Permanência(h)"])
          .groupby("CD_EQUIPTO", as_index=False)["Tempo de Permanência(h)"]
          .sum()
          .sort_values("Tempo de Permanência(h)", ascending=False)
          .head(10))
    st.altair_chart(
        alt.Chart(g3).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N", sort="-x", title="Equipamento"),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=["CD_EQUIPTO", alt.Tooltip("Tempo de Permanência(h):Q", format=".2f", title="Tempo (h)")]
        ).properties(width=800, height=380),
        use_container_width=True
    )
else:
    st.info("Tempo de Permanência(h) não disponível.")

# =========================
# GRÁFICO 4 — Ocorrências por Componente (DE_SERVICO)
# =========================
st.subheader("Gráfico 4 - Ocorrências por Componente (DE_SERVICO)")
g4 = (df_filtrado["Componente Detectado"]
      .value_counts()
      .reset_index()
      .rename(columns={"index": "Componente", "Componente Detectado": "Ocorrências"}))
st.altair_chart(
    alt.Chart(g4).mark_bar().encode(
        y=alt.Y("Componente:N", sort="-x"),
        x=alt.X("Ocorrências:Q"),
        tooltip=["Componente", "Ocorrências"]
    ).properties(width=800, height=380),
    use_container_width=True
)

# =========================
# GRÁFICO 5 — Tendência Diária de Entrada de OS (filtrado)
# =========================
st.subheader("Gráfico 5 - Tendência Diária de Entrada de OS")
if "ENTRADA" in df_filtrado.columns:
    tend = df_filtrado[df_filtrado["ENTRADA"].notna()].copy()
    tend["Data de Entrada"] = tend["ENTRADA"].dt.floor("D")
    g5 = tend.groupby("Data de Entrada").size().reset_index(name="Quantidade")
    if not g5.empty:
        st.altair_chart(
            alt.Chart(g5).mark_bar().encode(
                x=alt.X("Data de Entrada:T", title="Data de Entrada", axis=alt.Axis(format="%d/%m")),
                y=alt.Y("Quantidade:Q", title="Quantidade de OS", scale=alt.Scale(domainMin=1), axis=alt.Axis(tickMinStep=1)),
                tooltip=["Data de Entrada:T", "Quantidade:Q"]
            ).properties(width=800, height=380),
            use_container_width=True
        )
    else:
        st.info("Sem dados no período selecionado.")
else:
    st.info("Coluna ENTRADA não encontrada.")

# =========================
# GRÁFICO 6 — Tendência Mensal de Manutenções (GERAL, sem filtro) — exibido por último
# =========================
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções (Geral, sem filtro de período)")
if "Ano/Mes" in df.columns:
    g6 = df.groupby("Ano/Mes").size().reset_index(name="Quantidade")
    st.altair_chart(
        alt.Chart(g6).mark_line(point=True).encode(
            x=alt.X("Ano/Mes:T", title="Ano/Mês"),
            y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
            tooltip=["Ano/Mes:T", "Quantidade:Q"]
        ).properties(width=800, height=380),
        use_container_width=True
    )
else:
    st.info("Não foi possível construir a série mensal (coluna Ano/Mes ausente).")

