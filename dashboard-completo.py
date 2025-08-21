import streamlit as st
import pandas as pd
import altair as alt
from collections import Counter
import re
import unicodedata

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado")

# =========================
# Carregamento de dados (CSV ou Excel)
# =========================
@st.cache_data(show_spinner=False)
def carregar_dados(arquivo):
    nome = getattr(arquivo, "name", "")
    tipo = getattr(arquivo, "type", "")

    # Excel?
    if str(nome).lower().endswith((".xlsx", ".xls")) or "excel" in str(tipo).lower():
        df = pd.read_excel(arquivo, sheet_name=0)
    else:
        # CSV: tenta latin-1 + ';' e depois detecção automática
        try:
            df = pd.read_csv(arquivo, encoding="latin1", sep=";")
        except Exception:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            df = pd.read_csv(arquivo, engine="python", sep=None)

    df.columns = df.columns.str.strip()

    # Descrição
    df["DE_SERVICO"] = (
        df.get("DE_SERVICO", "")
          .fillna("")
          .astype(str)
          .str.lower()
          .str.strip()
    )

    # Datas
    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Ano/Mês
    df["Ano/Mes"] = (
        df["ENTRADA"].dt.to_period("M").dt.to_timestamp()
        if "ENTRADA" in df.columns else pd.NaT
    )

    # Tempo de Permanência (h)
    if {"ENTRADA", "SAIDA"}.issubset(df.columns):
        df["Tempo de Permanência(h)"] = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    # Normalização de chaves categóricas
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

# ======= Debug =======
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
g1 = df_filtrado["CD_CLASMANU"].value_counts(dropna=False).reset_index(name="Quantidade").head(10)
# renomeia colunas corretamente (a 1ª vem com o nome da série)
g1.columns = ["CD_CLASMANU", "Quantidade"]
if debug: st.write("g1 head:", g1.head())
if g1.empty:
    st.info("Sem dados para CD_CLASMANU no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g1).mark_bar().encode(
            y=alt.Y("CD_CLASMANU:N", sort=alt.SortField(field="Quantidade", order="descending"), title="CD_CLASMANU"),
            x=alt.X("Quantidade:Q", title="Quantidade"),
            tooltip=["CD_CLASMANU", "Quantidade"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 2 — Top 10 OS por Equipamento
# =========================
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento (CD_EQUIPTO)")
g2 = df_filtrado["CD_EQUIPTO"].value_counts(dropna=False).reset_index(name="OS").head(10)
g2.columns = ["CD_EQUIPTO", "OS"]
if debug: st.write("g2 head:", g2.head())
if g2.empty:
    st.info("Sem dados de equipamentos no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g2).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N", sort=alt.SortField(field="OS", order="descending"), title="Equipamento"),
            x=alt.X("OS:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"), "OS:Q"]
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
            y=alt.Y("CD_EQUIPTO:N", sort=alt.SortField(field="Tempo de Permanência(h)", order="descending"), title="Equipamento"),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=["CD_EQUIPTO", alt.Tooltip("Tempo de Permanência(h):Q", format=".2f", title="Tempo (h)")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 4 — Ocorrências por Componente (DE_SERVICO)  **CORRIGIDO**
# =========================
st.subheader("Gráfico 4 - Ocorrências por Componente (DE_SERVICO)")
g4 = df_filtrado["Componente Detectado"].value_counts(dropna=False).reset_index(name="Ocorrências")
g4.columns = ["Componente", "Ocorrências"]  # <- correção chave
if debug: st.write("g4 head:", g4.head())
if g4.empty:
    st.info("Sem ocorrências por componente no período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g4).mark_bar().encode(
            y=alt.Y("Componente:N", sort=alt.SortField(field="Ocorrências", order="descending")),
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
                    x=alt.X("Data de Entrada:T", title="Data de Entrada", axis=alt.Axis(format="%d/%m")),
                    y=alt.Y("Quantidade:Q", title="Quantidade de OS", scale=alt.Scale(domainMin=1)),
                    tooltip=[alt.Tooltip("Data de Entrada:T", title="Data"), alt.Tooltip("Quantidade:Q", title="Qtd")]
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
            tooltip=[alt.Tooltip("Ano/Mes:T", title="Ano/Mês"), alt.Tooltip("Quantidade:Q", title="Qtd")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =====================================================================
# NOVO: Análise de descrições (mais recorrentes) — Termos e Bigramas
# =====================================================================

# Lista básica de stopwords PT + termos genéricos de manutenção
STOPWORDS = {
    "de","do","da","das","dos","e","a","o","os","as","em","no","na","nas","nos","para","por","com","sem",
    "ao","à","às","aos","um","uma","uns","umas","que","se","ser","foi","são","está","estar","nois","tá",
    "manutencao","manutenção","servico","serviço","ordem","os","teste","avaliar","verificar","realizar",
    "troca","substituicao","substituição","apresenta","apresentando","necessario","necessário","sistema"
}

def normalizar(txt: str) -> str:
    if not isinstance(txt, str):
        return ""
    # remove acentos
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")
    return txt

def tokenizar(texto: str):
    t = normalizar(texto.lower())
    # palavras com 3+ letras (ignora números e underscores)
    tokens = re.findall(r"\b[a-z]{3,}\b", t)
    # remove stopwords
    tokens = [w for w in tokens if w not in STOPWORDS]
    return tokens

def top_termos(series_texto: pd.Series, n=20):
    counter = Counter()
    for s in series_texto.dropna():
        counter.update(tokenizar(s))
    itens = counter.most_common(n)
    return pd.DataFrame(itens, columns=["Termo", "Ocorrências"])

def top_bigramas(series_texto: pd.Series, n=20):
    counter = Counter()
    for s in series_texto.dropna():
        toks = tokenizar(s)
        bigs = [" ".join(pair) for pair in zip(toks, toks[1:])]
        counter.update(bigs)
    itens = counter.most_common(n)
    return pd.DataFrame(itens, columns=["Bigrama", "Ocorrências"])

# --------- Termos ----------
st.subheader("Gráfico 7 - Termos mais recorrentes nas descrições (filtrado)")
topN = st.sidebar.slider("Top N termos/bigramas", min_value=10, max_value=40, value=20, step=5)
g7 = top_termos(df_filtrado["DE_SERVICO"], n=topN)
if debug: st.write("g7 head:", g7.head())
if g7.empty:
    st.info("Não há termos suficientes nas descrições para o período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g7).mark_bar().encode(
            y=alt.Y("Termo:N", sort=alt.SortField(field="Ocorrências", order="descending")),
            x=alt.X("Ocorrências:Q"),
            tooltip=["Termo", "Ocorrências"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# --------- Bigramas ----------
st.subheader("Gráfico 8 - Bigramas (pares de palavras) mais recorrentes nas descrições (filtrado)")
g8 = top_bigramas(df_filtrado["DE_SERVICO"], n=topN)
if debug: st.write("g8 head:", g8.head())
if g8.empty:
    st.info("Não há bigramas suficientes nas descrições para o período/seleção.")
else:
    st.altair_chart(
        alt.Chart(g8).mark_bar().encode(
            y=alt.Y("Bigrama:N", sort=alt.SortField(field="Ocorrências", order="descending")),
            x=alt.X("Ocorrências:Q"),
            tooltip=["Bigrama", "Ocorrências"]
        ).properties(width=800, height=380),
        use_container_width=True
    )
