import streamlit as st
import pandas as pd
import altair as alt
import re, unicodedata

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado (somente NÃO PROGRAMADAS)")

# =============== utils ===============
def norm_txt(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r"[_\-.,;:/\\]+", " ", s)
    return s

# =============== carga CSV/Excel ===============
@st.cache_data(show_spinner=False)
def carregar_dados(arquivo):
    nome = getattr(arquivo, "name", "")
    tipo = getattr(arquivo, "type", "")
    if str(nome).lower().endswith((".xlsx", ".xls")) or "excel" in str(tipo).lower():
        df = pd.read_excel(arquivo, sheet_name=0)
    else:
        try:
            df = pd.read_csv(arquivo, encoding="latin1", sep=";")
        except Exception:
            if hasattr(arquivo, "seek"): arquivo.seek(0)
            df = pd.read_csv(arquivo, engine="python", sep=None)

    df.columns = df.columns.str.strip()
    df["DE_SERVICO"] = df.get("DE_SERVICO", "").fillna("").astype(str).map(norm_txt)

    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    df["Ano/Mes"] = df["ENTRADA"].dt.to_period("M").dt.to_timestamp() if "ENTRADA" in df.columns else pd.NaT

    if {"ENTRADA","SAIDA"}.issubset(df.columns):
        tmp = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
        df["Tempo de Permanência(h)"] = tmp.clip(lower=0)
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    df["CD_EQUIPTO"]  = df.get("CD_EQUIPTO", pd.NA).fillna("Não informado").astype(str).str.strip().replace({"": "Não informado"})
    df["CD_CLASMANU"] = df.get("CD_CLASMANU", pd.NA).fillna("Não informado").astype(str).str.strip().replace({"": "Não informado"})
    df["Origem"] = "NÃO INFORMADO"
    return df

# =============== filtro: excluir PLANEJADAS (preventiva/primária) ===============
PLANNED_COLS_CANDIDATES = [
    "CD_CLASMANU", "Tipo de manutenção", "TIPO_MANUTENCAO",
    "TP_MANU", "CLASSIFICACAO", "PLANO", "PLANO_MANUTENCAO", "TP_OS"
]
# padrões (sem acentos) para detectar planejadas
PLANNED_REGEX = re.compile(
    r"(preventiv|primar|inspec|lubrif|preditiv|planejad|programad|plano de manut|"
    r"\bpm\d*\b|\bpm\b)",
    flags=re.IGNORECASE
)

def aplicar_filtro_nao_programadas(df: pd.DataFrame):
    cols = [c for c in PLANNED_COLS_CANDIDATES if c in df.columns]
    if not cols:
        # Se não houver nenhuma coluna de classificação, não filtramos nada
        return df.copy(), pd.Series(False, index=df.index), cols

    texto_tipo = (
        df[cols]
        .astype(str)
        .applymap(norm_txt)
        .agg(" ".join, axis=1)
    )
    mask_planned = texto_tipo.str.contains(PLANNED_REGEX, na=False)
    df_np = df[~mask_planned].copy()
    return df_np, mask_planned, cols

# =============== classificador por descrição (já melhorado) ===============
def regras_base():
    R = {
        "Vazamento - Óleo": [re.compile(r"\bvaz[a-z]*\b.*\boleo\b"), re.compile(r"\boleo\b.*\bvaz[a-z]*\b"), re.compile(r"\bretentor\b"), re.compile(r"\bvedador(es)?\b")],
        "Vazamento - Hidráulico": [re.compile(r"\bvaz[a-z]*\b.*\bhidraul"), re.compile(r"\bhidraul.*\bvaz[a-z]*\b"), re.compile(r"\bcilindro hidraul"), re.compile(r"\bvalvula(s)?\b"), re.compile(r"\bbomba hidraul")],
        "Vazamento - Combustível": [re.compile(r"\bvaz[a-z]*\b.*\b(diesel|combust|gasol)"), re.compile(r"\b(diesel|combust|gasol).*vaz[a-z]*")],
        "Motor": [re.compile(r"\bmotor(?!ista)\b"), re.compile(r"\bcabecote\b"), re.compile(r"\bpist[aã]o\b"), re.compile(r"\bbiela\b"), re.compile(r"\bbronzina\b"), re.compile(r"\bbomba de oleo\b"), re.compile(r"\barrefe(c|ç)edor\b"), re.compile(r"\bturbina|turbo\b"), re.compile(r"\bcorreia dent")],
        "Transmissão / Câmbio": [re.compile(r"\b(cambio|transmiss[aã]o)\b"), re.compile(r"\bembreagem\b"), re.compile(r"\b(diferencial|planet[aá]ria|coroa|pinhao)\b"), re.compile(r"\bcarda?n\b")],
        "Freio": [re.compile(r"\bfreio(s)?\b"), re.compile(r"\bpastilh"), re.compile(r"\blona(s)?\b"), re.compile(r"\bdisco(s)?\b"), re.compile(r"\btambor(es)?\b"), re.compile(r"\bpin[cç]a\b"), re.compile(r"\bcilindro mestre\b"), re.compile(r"\bfluido de freio\b")],
        "Suspensão": [re.compile(r"\bamortecedor(es)?\b"), re.compile(r"\bmola(s)?\b"), re.compile(r"\bfeixe de mola\b"), re.compile(r"\bbucha(s)?\b"), re.compile(r"\bbandeja\b"), re.compile(r"\bpivo\b"), re.compile(r"\bestabilizador\b")],
        "Direção": [re.compile(r"\b(caixa|sistema) de dire[cç][aã]o\b"), re.compile(r"\bterminal de dire[cç][aã]o\b"), re.compile(r"\bbarra de dire[cç][aã]o\b"), re.compile(r"\borbitrol\b")],
        "Elétrica": [re.compile(r"\beletr[aí]c"), re.compile(r"\bchicote\b"), re.compile(r"\bfus[ií]vel\b"), re.compile(r"\brele\b"), re.compile(r"\bl[aâ]mpada|farol|lanterna\b"), re.compile(r"\bbateria\b"), re.compile(r"\bmotor de arranque\b"), re.compile(r"\balternador\b")],
        "Falha Eletrônica / Painel": [re.compile(r"\bpainel\b"), re.compile(r"\b(luz|lamp)\s*espia\b"), re.compile(r"\bc[oó]digo de falha\b"), re.compile(r"\b(sensor|atuador|modulo|ecu|can)\b"), re.compile(r"\bsem comunica[cç][aã]o\b"), re.compile(r"\binjet(or|or(es)?)\b")],
        "Sistema Hidráulico (sem vazamento)": [re.compile(r"\bbomba\b.*\bhidraul"), re.compile(r"\bvalvula\b.*\bhidraul"), re.compile(r"\bcilindro\b.*\bhidraul"), re.compile(r"\bhidromotor|hidrostat(ico|ica)\b")],
        "Pneus/Rodagem": [re.compile(r"\bpneu(s)?\b"), re.compile(r"\broda(s)?\b"), re.compile(r"\bc[aâ]mara\b")],
        "Rodantes": [re.compile(r"\brodante(s)?\b"), re.compile(r"\brolete(s)?\b"), re.compile(r"\broda motriz\b"), re.compile(r"\bcoroa\b"), re.compile(r"\besteira|sapata\b")],
        "Ar Condicionado": [re.compile(r"\bar condicionado\b|\bac\b"), re.compile(r"\bcompressor do ar\b|\bcompressor\b.*\bar\b"), re.compile(r"\bcondensador\b"), re.compile(r"\bevaporador\b"), re.compile(r"\bventilador\b"), re.compile(r"\bgas do ar\b")],
        "Mangueira (Vazamento)": [re.compile(r"\bmangueira(s)?\b"), re.compile(r"\bflex[ií]vel\b")],
        "Rádio": [re.compile(r"\br[aá]dio\b")],
        "Elevador": [re.compile(r"\belevador|elevat[oó]ria|plataforma\b")],
        "Acumulador": [re.compile(r"\bacumulador\b")],
        "Despontador": [re.compile(r"\bdespontador\b")],
        "Avaliar": [re.compile(r"\bavaliar|verificar|inspecionar|chec(ar|agem)|vistoriar\b")],
    }
    return R

PRIORIDADE = [
    "Vazamento - Óleo","Vazamento - Hidráulico","Vazamento - Combustível",
    "Falha Eletrônica / Painel","Elétrica",
    "Transmissão / Câmbio","Freio","Direção","Suspensão",
    "Sistema Hidráulico (sem vazamento)","Pneus/Rodagem","Rodantes",
    "Ar Condicionado","Mangueira (Vazamento)","Rádio","Elevador","Acumulador","Despontador",
    "Motor","Avaliar"
]

def classificar(texto: str, regras) -> str:
    t = norm_txt(texto)
    if not t: return "Não Classificado"
    if re.search(r"\bvaz[a-z]*\b", t):
        if re.search(r"\bhidraul", t):  return "Vazamento - Hidráulico"
        if re.search(r"\boleo\b", t):   return "Vazamento - Óleo"
        if re.search(r"\b(diesel|combust|gasol)\b", t): return "Vazamento - Combustível"
    for cat in PRIORIDADE:
        for patt in regras.get(cat, []):
            if patt.search(t): return cat
    return "Não Classificado"

# ======= Upload =======
st.sidebar.header("Arquivo de Dados")
arquivo = st.sidebar.file_uploader("Envie o arquivo (.csv, .xlsx, .xls)", type=["csv","xlsx","xls"])
if arquivo is None:
    st.info("Envie o arquivo no painel lateral para carregar o dashboard.")
    st.stop()

df_raw = carregar_dados(arquivo)

# --- aplica filtro para excluir preventivas/primárias (planejadas) ---
df, mask_planned, cols_usadas = aplicar_filtro_nao_programadas(df_raw)

st.sidebar.markdown(
    f"**Planejadas removidas:** {int(mask_planned.sum())}  \n"
    f"**Registros analisados (não programadas):** {len(df)}  \n"
    f"**Colunas usadas para detectar plano:** {', '.join(cols_usadas) if cols_usadas else '—'}"
)

# classifica por descrição apenas nas NÃO PROGRAMADAS
REGRAS = regras_base()
df["Componente Detectado"] = df["DE_SERVICO"].apply(lambda s: classificar(s, REGRAS))

# ======= Filtros =======
st.sidebar.header("Filtro de Período (aplicado na maioria dos gráficos)")
hoje = pd.Timestamp.today().normalize()
inicio_padrao = (df["ENTRADA"].min().date() if "ENTRADA" in df.columns and pd.notna(df["ENTRADA"]).any()
                 else (hoje - pd.Timedelta(days=30)).date())
data_inicio = st.sidebar.date_input("Data de Início", value=inicio_padrao)
data_fim    = st.sidebar.date_input("Data de Fim", value=hoje.date())

valores_clas = sorted(df["CD_CLASMANU"].dropna().unique().tolist()) if "CD_CLASMANU" in df.columns else []
op_clas = st.sidebar.multiselect("Filtrar por CD_CLASMANU (opcional)", valores_clas, default=valores_clas if valores_clas else [])

mask_periodo = (df["ENTRADA"] >= pd.to_datetime(data_inicio)) & (df["ENTRADA"] <= pd.to_datetime(data_fim)) if "ENTRADA" in df.columns else pd.Series(True, index=df.index)
mask_clas = df["CD_CLASMANU"].isin(op_clas) if (len(op_clas) > 0 and "CD_CLASMANU" in df.columns) else pd.Series(True, index=df.index)
df_filtrado = df[mask_periodo & mask_clas].copy()

debug = st.sidebar.checkbox("Modo debug (mostrar heads)", value=False)

# =========================
# GRÁFICO 1 — Top 10 CD_CLASMANU
# =========================
st.subheader("Gráfico 1 - Top 10 Classificações (CD_CLASMANU) — somente não programadas")
if "CD_CLASMANU" in df_filtrado.columns:
    g1 = df_filtrado["CD_CLASMANU"].value_counts(dropna=False).reset_index(name="Quantidade").head(10)
    g1.columns = ["CD_CLASMANU","Quantidade"]
    if g1.empty: st.info("Sem dados para CD_CLASMANU no período/seleção.")
    else:
        if debug: st.write("g1 head:", g1.head())
        st.altair_chart(
            alt.Chart(g1).mark_bar().encode(
                y=alt.Y("CD_CLASMANU:N", sort=alt.SortField(field="Quantidade", order="descending")),
                x=alt.X("Quantidade:Q"),
                tooltip=["CD_CLASMANU","Quantidade"]
            ).properties(width=800, height=380),
            use_container_width=True
        )
else:
    st.info("Coluna CD_CLASMANU não encontrada.")

# =========================
# GRÁFICO 2 — Top 10 OS por Equipamento
# =========================
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento (CD_EQUIPTO) — somente não programadas")
g2 = df_filtrado["CD_EQUIPTO"].value_counts(dropna=False).reset_index(name="OS").head(10)
g2.columns = ["CD_EQUIPTO","OS"]
if g2.empty: st.info("Sem dados de equipamentos no período/seleção.")
else:
    if debug: st.write("g2 head:", g2.head())
    st.altair_chart(
        alt.Chart(g2).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N", sort=alt.SortField(field="OS", order="descending"), title="Equipamento"),
            x=alt.X("OS:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"),"OS:Q"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 3 — Tempo Total (h) por Equipamento
# =========================
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Equipamento (h) — somente não programadas")
g3 = (df_filtrado.dropna(subset=["Tempo de Permanência(h)"])
      .groupby("CD_EQUIPTO", as_index=False)["Tempo de Permanência(h)"].sum()
      .sort_values("Tempo de Permanência(h)", ascending=False)
      .head(10))
if g3.empty: st.info("Sem dados de tempo de permanência no período/seleção.")
else:
    if debug: st.write("g3 head:", g3.head())
    st.altair_chart(
        alt.Chart(g3).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N", sort=alt.SortField(field="Tempo de Permanência(h)", order="descending")),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=["CD_EQUIPTO", alt.Tooltip("Tempo de Permanência(h):Q", format=".2f")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 4 — Ocorrências por Componente (DE_SERVICO)
# =========================
st.subheader("Gráfico 4 - Ocorrências por Componente (DE_SERVICO) — somente não programadas")
g4 = df_filtrado["Componente Detectado"].value_counts(dropna=False).reset_index(name="Ocorrências")
g4.columns = ["Componente","Ocorrências"]
if g4.empty: st.info("Sem ocorrências por componente no período/seleção.")
else:
    if debug: st.write("g4 head:", g4.head())
    st.altair_chart(
        alt.Chart(g4).mark_bar().encode(
            y=alt.Y("Componente:N", sort=alt.SortField(field="Ocorrências", order="descending")),
            x=alt.X("Ocorrências:Q"),
            tooltip=["Componente","Ocorrências"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# GRÁFICO 5 — Tendência Diária (filtrado)
# =========================
st.subheader("Gráfico 5 - Tendência Diária de Entrada de OS — somente não programadas")
if "ENTRADA" in df_filtrado.columns:
    tend = df_filtrado[df_filtrado["ENTRADA"].notna()].copy()
    if tend.empty: st.info("Sem dados de ENTRADA no período/seleção.")
    else:
        tend["Data de Entrada"] = tend["ENTRADA"].dt.floor("D")
        g5 = tend.groupby("Data de Entrada").size().reset_index(name="Quantidade")
        if debug: st.write("g5 head:", g5.head())
        st.altair_chart(
            alt.Chart(g5).mark_bar().encode(
                x=alt.X("Data de Entrada:T", axis=alt.Axis(format="%d/%m")),
                y=alt.Y("Quantidade:Q", title="Quantidade de OS", scale=alt.Scale(domainMin=1)),
                tooltip=[alt.Tooltip("Data de Entrada:T", title="Data"), alt.Tooltip("Quantidade:Q", title="Qtd")]
            ).properties(width=800, height=380),
            use_container_width=True
        )
else:
    st.info("Coluna ENTRADA não encontrada.")

# =========================
# GRÁFICO 6 — Tendência Mensal (GERAL, sem filtro de período)
# =========================
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções (Somente NÃO PROGRAMADAS)")
g6 = df.dropna(subset=["Ano/Mes"]).groupby("Ano/Mes").size().reset_index(name="Quantidade")
if g6.empty: st.info("Não foi possível construir a série mensal (dados insuficientes).")
else:
    if debug: st.write("g6 head:", g6.head())
    st.altair_chart(
        alt.Chart(g6).mark_line(point=True).encode(
            x=alt.X("Ano/Mes:T", title="Ano/Mês"),
            y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("Ano/Mes:T", title="Ano/Mês"), alt.Tooltip("Quantidade:Q", title="Qtd")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# Triagem — “Não Classificado” (somente não programadas)
# =========================
st.subheader("Amostras de descrições NÃO CLASSIFICADAS (para melhoria contínua)")
nao_cls = df_filtrado[df_filtrado["Componente Detectado"] == "Não Classificado"].copy()
if nao_cls.empty:
    st.success("Nenhuma descrição não classificada no período/seleção.")
else:
    top_descricoes = (nao_cls["DE_SERVICO"]
                      .value_counts()
                      .reset_index(name="Ocorrências")
                      .rename(columns={"index":"Descrição"})
                      .head(50))
    st.dataframe(top_descricoes, use_container_width=True)
    st.download_button(
        "Baixar CSV das não classificadas (top 50)",
        top_descricoes.to_csv(index=False).encode("utf-8-sig"),
        file_name="nao_classificadas_top50.csv",
        mime="text/csv"
    )
