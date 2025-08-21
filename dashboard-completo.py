import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado")

# =========================
# Carregamento de dados (CSV ou Excel)
# =========================
@st.cache_data(show_spinner=False)
def carregar_dados(arquivo):
    nome = getattr(arquivo, "name", "")
    tipo = getattr(arquivo, "type", "")

    df = None
    # Excel
    if str(nome).lower().endswith((".xlsx", ".xls")) or "excel" in str(tipo).lower():
        try:
            df = pd.read_excel(arquivo, sheet_name=0)
        except Exception as e:
            raise RuntimeError(f"Falha ao ler Excel: {e}")
    # CSV
    else:
        try:
            df = pd.read_csv(arquivo, encoding="latin1", sep=";")
        except Exception:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            # detecção automática
            df = pd.read_csv(arquivo, engine="python", sep=None)

    df.columns = df.columns.str.strip()

    # Texto da descrição
    df["DE_SERVICO"] = (
        df.get("DE_SERVICO", "")
          .fillna("")
          .astype(str)
          .str.lower()
          .str.strip()
    )

    # Datas (qualquer formato; dia primeiro)
    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Ano/Mês
    if "ENTRADA" in df.columns:
        df["Ano/Mes"] = df["ENTRADA"].dt.to_period("M").dt.to_timestamp()
    else:
        df["Ano/Mes"] = pd.NaT

    # Tempo de Permanência (h)
    if {"ENTRADA", "SAIDA"}.issubset(df.columns):
        df["Tempo de Permanência(h)"] = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    # Normaliza categorias usadas nos gráficos
    df["CD_EQUIPTO"] = (
        df.get("CD_EQUIPTO", pd.NA)
          .fillna("Não informado")
          .astype(str)
          .str.strip()
          .replace({"": "Não informado"})
    )
    df["CD_CLASMANU"] = (
        df.get("CD_CLASMANU", pd.NA)
          .fillna("Não informado")
          .astype(str)
          .str.strip()
          .replace({"": "Não informado"})
    )

    # Compatibilidade
    df["Origem"] = "NÃO INFORMADO"

    return df

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

# ======= Upload =======
st.sidebar.header("Arquivo de Dados")
arquivo = st.sidebar.file_uploader("Envie o arquivo (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
if arquivo is None:
    st.info("Envie o arquivo no painel lateral para carregar o dashboard.")
    st.stop()

df = carregar_dados(arquivo)
df["Componente Detectado"] = df["DE_SERVICO"].apply(classificar_componente)

# ======= Debug opcional =======
debug = st.sidebar.checkbox("Modo debug (mostrar heads)", value=False)

# ======= Filtros =======
st.sidebar.header("Filtro de Período (aplicado na maioria dos gráficos)")
hoje = pd.Timestamp.today().normalize()
inicio_padrao = (
    df["ENTRADA"].min().date() if "ENTRADA" in df.columns and pd.notna(df["ENTRADA"]).any()
    else (hoje - pd.Timedelta(days=30)).date()
)
data_inicio = st.sidebar.date_input("Data de Início", value=inicio_padrao)
data_fim    = st.sidebar.date_input("Data de Fim", value=hoje.date())

valores_clas = sorted(df["CD_CLASMANU"].dropna().unique().tolist())
op_clas = st.sidebar.multiselect(
    "Filtrar por CD_CLASMANU (opcional)",
    valores_clas,
    default=valores_clas if valores_clas else []
)

mask_periodo = (df["ENTRADA"] >= pd.to_datetime(data_inicio)) & (df["ENTRADA"] <= pd.to_datetime(data_fim)) if "ENTRADA" in df.columns else pd.Series(True, index=df.index)
mask_clas = df["CD_CLASMANU"].isin(op_clas) if len(op_clas) > 0 else pd.Series(True, index=df.index)
df_filtrado = df[mask_periodo & mask_clas].copy()

# =========================
# GRÁFICO 1 — Top 10 CD_CLASMANU
# =========================
st.subheader("Gráfico 1 - Top 10 Classificações (CD_CLASMANU)")
g1 = (
    df_filtrado["CD_CLASMANU"]
    .value_counts(dropna=False)
    .reset_index(name="Quantidade")
    .rename(columns={"index": "CD_CLASMANU"})
    .head(10)
)
if debug: st.write("g1 head:", g1.head())
if g1.empty:
    st.info("Sem dados para CD_CLASMANU no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g1).mark_bar().encode(
            y=alt.Y("CD_CLASMANU:N",
                    sort=alt.SortField(field="Quantidade", order="descending"),
                    title="CD_CLASMANU"),
            x=alt.X("Quantidade:Q", title="Quantidade"),
            tooltip=[alt.Tooltip("CD_CLASMANU:N", title="CD_CLASMANU"),
                     alt.Tooltip("Quantidade:Q", title="Qtd")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 2 — Top 10 OS por Equipamento
# =========================
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento (CD_EQUIPTO)")
g2 = (
    df_filtrado["CD_EQUIPTO"]
    .value_counts(dropna=False)
    .reset_index(name="OS")
    .rename(columns={"index": "CD_EQUIPTO"})
    .head(10)
)
if debug: st.write("g2 head:", g2.head())
if g2.empty:
    st.info("Sem dados de equipamentos no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g2).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N",
                    sort=alt.SortField(field="OS", order="descending"),
                    title="Equipamento"),
            x=alt.X("OS:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"),
                     alt.Tooltip("OS:Q", title="Qtd OS")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 3 — Tempo Total (h) por Equipamento
# =========================
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Equipamento (h)")
g3 = (
    df_filtrado.dropna(subset=["Tempo de Permanência(h)"])
    .groupby("CD_EQUIPTO", as_index=False)["Tempo de Permanência(h)"]
    .sum()
    .sort_values("Tempo de Permanência(h)", ascending=False)
    .head(10)
)
if debug: st.write("g3 head:", g3.head())
if g3.empty:
    st.info("Sem dados de tempo de permanência no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g3).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N",
                    sort=alt.SortField(field="Tempo de Permanência(h)", order="descending"),
                    title="Equipamento"),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=["CD_EQUIPTO",
                     alt.Tooltip("Tempo de Permanência(h):Q", format=".2f", title="Tempo (h)")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 4 — Ocorrências por Componente
# =========================
st.subheader("Gráfico 4 - Ocorrências por Componente (DE_SERVICO)")
g4 = (
    df_filtrado["Componente Detectado"]
    .value_counts(dropna=False)
    .reset_index(name="Ocorrências")
    .rename(columns={"index": "Componente"})
)
if debug: st.write("g4 head:", g4.head())
if g4.empty:
    st.info("Sem ocorrências por componente no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g4).mark_bar().encode(
            y=alt.Y("Componente:N",
                    sort=alt.SortField(field="Ocorrências", order="descending")),
            x=alt.X("Ocorrências:Q"),
            tooltip=["Componente", "Ocorrências"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 5 — Tendência Diária (filtrado)
# =========================
st.subheader("Gráfico 5 - Tendência Diária de Entrada de OS")
if "ENTRADA" in df_filtrado.columns:
    tend = df_filtrado[df_filtrado["ENTRADA"].notna()].copy()
    if tend.empty:
        st.info("Sem dados de ENTRADA no período/seleção.")
    else:
        tend["Data de Entrada"] = tend["ENTRADA"].dt.floor("D")
        g5 = tend.groupby("Data de Entrada").size().reset_index(name="Quantidade")
        if debug: st.write("g5 head:", g5.head())
        if g5.empty:
            st.info("Sem dados no período selecionado.")
        else:
            st.altair_chart(
                alt.Chart(g5).mark_bar().encode(
                    x=alt.X("Data de Entrada:T", title="Data de Entrada",
                            axis=alt.Axis(format="%d/%m")),
                    y=alt.Y("Quantidade:Q", title="Quantidade de OS",
                            scale=alt.Scale(domainMin=1)),
                    tooltip=[alt.Tooltip("Data de Entrada:T", title="Data"),
                             alt.Tooltip("Quantidade:Q", title="Qtd")]
                ).properties(width=800, height=380),
                use_container_width=True
            )
else:
    st.info("Coluna ENTRADA não encontrada.")

# =========================
# GRÁFICO 6 — Tendência Mensal (GERAL, sem filtro) — último
# =========================
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções (Geral, sem filtro de período)")
g6 = df.dropna(subset=["Ano/Mes"]).groupby("Ano/Mes").size().reset_index(name="Quantidade")
if debug: st.write("g6 head:", g6.head())
if g6.empty:
    st.info("Não foi possível construir a série mensal (dados insuficientes).")
else:
    st.altair_chart(
        alt.Chart(g6).mark_line(point=True).encode(
            x=alt.X("Ano/Mes:T", title="Ano/Mês"),
            y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("Ano/Mes:T", title="Ano/Mês"),
                     alt.Tooltip("Quantidade:Q", title="Qtd")]
        ).properties(width=800, height=380),
        use_container_width=True
    )
