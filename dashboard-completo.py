import streamlit as st
import pandas as pd
import altair as alt
import re, unicodedata

# =========================
# Config & título
# =========================
st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção — Ordens de Serviço")

# cor padrão dos gráficos
COLOR = "#2E7D32"  # verde

# ====== Mapa de códigos -> descrição (CD_CLASMANU) ======
CLASMANU_MAP = {
    12: "CORRETIVA",
    14: "PREVENTIVA SISTEMÁTICA",
    15: "PREDITIVA",
    16: "CENTRO DE CUSTO",
    17: "PREVENTIVA CONDICIONAL",
    18: "ENTRESSAFRA",
    19: "MELHORIA/CAPEX",
    20: "ENTRESSAFRA S/PLANO",
    21: "SRS/MINI REFORMA",
    23: "TECNOLOGIA AGRÍCOLA",
    24: "GEOTECNOLOGIA",
}

def _to_int_code(x):
    """Converte '12', '12.0', 12.0 etc para int 12; retorna None se não der."""
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return None
    s = s.replace(",", ".")
    try:
        return int(float(s))
    except:
        m = re.search(r"\d+", s)
        return int(m.group()) if m else None

# =========================
# Utils
# =========================
def norm_txt(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r"[_\-.,;:/\\]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

# =========================
# Carregamento (CSV/Excel)
# =========================
@st.cache_data(show_spinner=False)
def carregar_dados(arquivo):
    nome = getattr(arquivo, "name", "")
    tipo = getattr(arquivo, "type", "")

    # Excel?
    if str(nome).lower().endswith((".xlsx", ".xls")) or "excel" in str(tipo).lower():
        df = pd.read_excel(arquivo, sheet_name=0)
    else:
        # CSV: tenta latin-1 e ';', depois autoinferência
        try:
            df = pd.read_csv(arquivo, encoding="latin1", sep=";")
        except Exception:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            df = pd.read_csv(arquivo, engine="python", sep=None)

    df.columns = df.columns.str.strip()

    # Descrição normalizada
    df["DE_SERVICO"] = df.get("DE_SERVICO", "").fillna("").astype(str)
    df["DE_SERVICO_N"] = df["DE_SERVICO"].map(norm_txt)

    # Datas
    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Ano/Mês
    df["Ano/Mes"] = df["ENTRADA"].dt.to_period("M").dt.to_timestamp() if "ENTRADA" in df.columns else pd.NaT

    # Tempo de Permanência (h)
    if {"ENTRADA", "SAIDA"}.issubset(df.columns):
        tmp = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
        df["Tempo de Permanência(h)"] = tmp.clip(lower=0)
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    # CD_EQUIPTO (sem ".0")
    df["CD_EQUIPTO"] = (
        df.get("CD_EQUIPTO", pd.NA)
          .fillna("Não informado")
          .astype(str).str.strip()
          .str.replace(r"\.0$", "", regex=True)  # remove .0
          .replace({"": "Não informado"})
    )

    # CD_CLASMANU
    raw_clas = df.get("CD_CLASMANU", pd.NA).fillna("")
    df["CD_CLASMANU"] = raw_clas.astype(str).str.strip().replace({"": "Não informado"})
    df["CD_CLASMANU_CODE"] = df["CD_CLASMANU"].map(_to_int_code)
    df["CD_CLASMANU_DESC"] = df["CD_CLASMANU_CODE"].map(CLASMANU_MAP).fillna(df["CD_CLASMANU"].astype(str))

    return df

# =========================
# Filtro: remover planejadas (preventiva/primária)
# =========================
PLANNED_COLS_CANDIDATES = [
    "CD_CLASMANU", "Tipo de manutenção", "TIPO_MANUTENCAO",
    "TP_MANU", "CLASSIFICACAO", "PLANO", "PLANO_MANUTENCAO", "TP_OS"
]
PLANNED_REGEX = re.compile(
    r"(preventiv|primar|inspec|lubrif|preditiv|planejad|programad|plano\s*de\s*manut|\bpm\d*\b|\bpm\b|\brevis[aã]o)",
    flags=re.IGNORECASE
)

def aplicar_filtro_nao_programadas(df: pd.DataFrame):
    cols = [c for c in PLANNED_COLS_CANDIDATES if c in df.columns]
    if cols:
        texto_tipo = df[cols].astype(str).applymap(norm_txt).agg(" ".join, axis=1)
        mask_planned = texto_tipo.str.contains(PLANNED_REGEX, na=False)
    else:
        mask_planned = df["DE_SERVICO_N"].str.contains(PLANNED_REGEX, na=False)
    df_np = df[~mask_planned].copy()
    return df_np, mask_planned, cols

# =========================
# Classificador (regras + ML opcional) — usado no Gráfico 4
# =========================
def build_rules():
    rules_patterns = {
        "Estrutural/Chassi": [
            r"\bsolda(r|s|)\b|\bsoldar\b",
            r"\bparafuso(s)?\b", r"\bsuporte(s)?\b", r"\bpino(s)?\b",
            r"\bhaste(s)?\b", r"\bestirante(s)?\b",
            r"\btrinca(d|s|)\b|\bquebr(ad|ou|a|ado)\b", r"\bchassi\b",
        ],
        "Corte/Facão & Plataforma": [
            r"\bfac[aã]o\b", r"\bsincron", r"\bmancal\b",
            r"\bdivisor( de linha)?\b", r"\bplataforma\b", r"\bbarra de corte\b"
        ],
        "Cabine/Carroceria": [r"\bparabris|vidro|retrovisor|escada|porta(s)?\b", r"\bcap[oô]\b", r"\bgrade\b"],
        "Tanque/Combustível (sem vazamento)": [r"\btanque\b", r"\bcinta do tanque\b", r"\bboia do tanque\b"],
        "Vazamento - Óleo": [r"\bvaz[a-z]*\b.*\boleo\b", r"\boleo\b.*\bvaz[a-z]*\b", r"\bretentor\b", r"\bvedador(es)?\b"],
        "Vazamento - Hidráulico": [r"\bvaz[a-z]*\b.*\bhidraul", r"\bhidraul.*\bvaz[a-z]*\b", r"\bcilindro hidraul", r"\bbomba hidraul"],
        "Vazamento - Combustível": [r"\bvaz[a-z]*\b.*\b(diesel|combust|gasol)", r"\b(diesel|combust|gasol).*\bvaz[a-z]*\b"],
        "Freio": [r"\bfreio(s)?\b", r"\bpastilh", r"\blona(s)?\b", r"\bdisco(s)?\b", r"\btambor(es)?\b", r"\bpin[cç]a\b", r"\bcilindro mestre\b", r"\bfluido de freio\b"],
        "Suspensão": [r"\bamortecedor(es)?\b", r"\bmola(s)?\b", r"\bfeixe de mola\b", r"\bbucha(s)?\b", r"\bbandeja\b", r"\bpivo\b", r"\bestabilizador\b"],
        "Direção": [r"\b(caixa|sistema) de dire[cç][aã]o\b", r"\bterminal de dire[cç][aã]o\b", r"\bbarra de dire[cç][aã]o\b", r"\borbitrol\b"],
        "Elétrica": [r"\beletr[aí]c", r"\bchicote\b", r"\bfus[ií]vel\b", r"\brele\b", r"\bl[aâ]mpada|farol|lanterna\b", r"\bbateria\b", r"\bmotor de arranque\b", r"\balternador\b"],
        "Falha Eletrônica / Painel": [r"\bpainel\b", r"\b(luz|lamp)\s*espia\b", r"\bc[oó]digo de falha\b", r"\b(sensor|atuador|modulo|ecu|can)\b", r"\bsem comunica[cç][aã]o\b", r"\binjet(or|or(es)?)\b"],
        "Sistema Hidráulico (sem vazamento)": [r"\bbomba\b.*\bhidraul", r"\bvalvula\b.*\bhidraul", r"\bcilindro\b.*\bhidraul", r"\bhidromotor|hidrostat(ico|ica)\b"],
        "Pneus/Rodagem": [r"\bpneu(s)?\b", r"\broda(s)?\b", r"\bc[aâ]mara\b", r"\bcalibr", r"\bfuro\b"],
        "Rodantes": [r"\brodante(s)?\b", r"\brolete(s)?\b", r"\broda motriz\b", r"\bcoroa\b", r"\besteira|sapata\b"],
        "Ar Condicionado": [r"\bar condicionado\b|\bac\b", r"\bcompressor\b.*\bar\b|\bcompressor do ar\b", r"\bcondensador\b", r"\bevaporador\b", r"\bventilador\b", r"\bgas do ar\b"],
        "Transmissão / Câmbio": [r"\b(cambio|transmiss[aã]o)\b", r"\bembreagem\b", r"\b(diferencial|planet[aá]ria|coroa|pinhao)\b", r"\bcarda?n\b"],
        "Motor": [r"\bmotor(?!ista)\b", r"\bcabecote\b", r"\bpist[aã]o\b", r"\bbiela\b", r"\bbronzina\b", r"\bbomba de oleo\b", r"\barrefe(c|ç)edor\b", r"\bturbina|turbo\b", r"\bcorreia dent"],
        "Mangueira (Vazamento)": [r"\bmangueira(s)?\b", r"\bflex[ií]vel\b"],
        "Rádio": [r"\br[aá]dio\b"],
        "Elevador": [r"\belevador|elevat[oó]ria|plataforma\b"],
        "Acumulador": [r"\bacumulador\b"],
        "Despontador": [r"\bdespontador\b"],
        "Avaliar": [r"\bavaliar|verificar|inspecionar|chec(ar|agem)|vistoriar\b"],
    }
    return {cat: [re.compile(p) for p in pats] for cat, pats in rules_patterns.items()}

_RULES = build_rules()

def classify_rules(texto: str) -> str:
    t = norm_txt(texto)
    if not t:
        return "Não Classificado"
    if re.search(r"\bvaz[a-z]*\b", t):
        if re.search(r"\bhidraul", t):  return "Vazamento - Hidráulico"
        if re.search(r"\boleo\b", t):   return "Vazamento - Óleo"
        if re.search(r"\b(diesel|combust|gasol)\b", t): return "Vazamento - Combustível"
    for categoria, pats in _RULES.items():
        for pat in pats:
            if pat.search(t):
                return categoria
    if re.search(r"\bmotor(?!ista)\b", t):
        return "Motor"
    return "Não Classificado"

def ml_reclass_optional(df_base: pd.DataFrame, col_txt: str, col_cat_in: str, threshold: float = 0.6):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline
    except Exception:
        return df_base[col_cat_in]

    train = df_base[~df_base[col_cat_in].isin(["Não Classificado", "Avaliar"])].copy()
    if train.empty or train[col_txt].str.len().sum() == 0:
        return df_base[col_cat_in]

    pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=3)), ("clf", MultinomialNB())])
    pipe.fit(train[col_txt], train[col_cat_in])

    mask_nc = df_base[col_cat_in].eq("Não Classificado")
    if mask_nc.sum() == 0:
        return df_base[col_cat_in]

    proba = pipe.predict_proba(df_base.loc[mask_nc, col_txt])
    classes = pipe.classes_
    top_idx = proba.argmax(axis=1)
    top_prob = proba.max(axis=1)
    pred = classes[top_idx]

    out = df_base[col_cat_in].copy()
    idx = df_base.loc[mask_nc].index
    reassign = idx[top_prob >= threshold]
    out.loc[reassign] = pred[top_prob >= threshold]
    return out

# =========================
# Upload
# =========================
st.sidebar.header("Arquivo")
arquivo = st.sidebar.file_uploader("Envie o arquivo (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
if arquivo is None:
    st.info("Envie o arquivo no painel lateral para carregar o dashboard.")
    st.stop()

df_raw = carregar_dados(arquivo)

# =========================
# Remover planejadas
# =========================
df, mask_planned, cols_usadas = aplicar_filtro_nao_programadas(df_raw)
st.sidebar.markdown(
    f"**Planejadas removidas:** {int(mask_planned.sum())}  \n"
    f"**Registros analisados (NÃO programadas):** {len(df)}  \n"
    f"**Colunas usadas:** {', '.join(cols_usadas) if cols_usadas else 'Fallback por descrição'}"
)

# =========================
# Filtros gerais
# =========================
st.sidebar.header("Filtros")
hoje = pd.Timestamp.today().normalize()
inicio_padrao = (df["ENTRADA"].min().date() if "ENTRADA" in df.columns and pd.notna(df["ENTRADA"]).any()
                 else (hoje - pd.Timedelta(days=30)).date())

# datas em DD/MM/AAAA
data_inicio = st.sidebar.date_input("Data de Início", value=inicio_padrao, format="DD/MM/YYYY")
data_fim    = st.sidebar.date_input("Data de Fim", value=hoje.date(), format="DD/MM/YYYY")

# opções do filtro por classe: **mostrar descrição**, filtrar por código
codes_unique = sorted([c for c in df["CD_CLASMANU_CODE"].dropna().unique().tolist()])
format_func = lambda c: CLASMANU_MAP.get(int(c), str(c))
op_clas = st.sidebar.multiselect(
    "Filtrar por CD_CLASMANU (opcional)",
    options=codes_unique,
    default=codes_unique,
    format_func=format_func
)

mask_periodo = ((df["ENTRADA"] >= pd.to_datetime(data_inicio)) & (df["ENTRADA"] <= pd.to_datetime(data_fim))
                ) if "ENTRADA" in df.columns else pd.Series(True, index=df.index)
mask_clas = df["CD_CLASMANU_CODE"].isin(op_clas) if len(op_clas) > 0 else pd.Series(True, index=df.index)

df_filtrado = df[mask_periodo & mask_clas].copy()

debug = st.sidebar.checkbox("Modo debug (mostrar heads)", value=False)

# =========================
# Gráfico 1 — Top 10 - Classe de Manutenção (robusto)
# =========================
st.subheader("Gráfico 1 - Top 10 - Classe de Manutenção")
if "CD_CLASMANU_DESC" in df_filtrado.columns:
    g1 = (
        df_filtrado["CD_CLASMANU_DESC"]
        .astype(str)
        .replace({"": "Não informado"})
        .value_counts(dropna=False)
        .reset_index(name="Quantidade")
        .rename(columns={"index": "Descrição"})
        .head(10)
    )
    g1["Quantidade"] = pd.to_numeric(g1["Quantidade"], errors="coerce").fillna(0)

    if g1.empty:
        st.info("Sem dados para CD_CLASMANU no período/seleção.")
    else:
        if debug: st.write("g1 head:", g1.head())
        ordem = g1.sort_values("Quantidade", ascending=False)["Descrição"].tolist()
        st.altair_chart(
            alt.Chart(g1).mark_bar(color=COLOR).encode(
                y=alt.Y("Descrição:N", sort=ordem, title="Classe de Manutenção"),
                x=alt.X("Quantidade:Q", title="Quantidade"),
                tooltip=["Descrição", "Quantidade"]
            ).properties(width=800, height=380),
            use_container_width=True
        )
else:
    st.info("Coluna CD_CLASMANU não encontrada.")
python
Copiar
Editar
# =========================
# Gráfico 2 — Top 10 Número de OS por Equipamento (robusto)
# =========================
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento")
g2 = (
    df_filtrado["CD_EQUIPTO"]
    .astype(str).str.replace(r"\.0$", "", regex=True)  # remove .0
    .replace({"": "Não informado"})
    .value_counts(dropna=False)
    .reset_index(name="OS")
    .rename(columns={"index": "CD_EQUIPTO"})
    .head(10)
)
g2["OS"] = pd.to_numeric(g2["OS"], errors="coerce").fillna(0)

if g2.empty:
    st.info("Sem dados de equipamentos no período/seleção.")
else:
    if debug: st.write("g2 head:", g2.head())
    ordem = g2.sort_values("OS", ascending=False)["CD_EQUIPTO"].tolist()
    st.altair_chart(
        alt.Chart(g2).mark_bar(color=COLOR).encode(
            y=alt.Y("CD_EQUIPTO:N", sort=ordem, title="Equipamento"),
            x=alt.X("OS:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"), "OS:Q"]
        ).properties(width=800, height=380),
        use_container_width=True
    )
python
Copiar
Editar
# =========================
# Gráfico 3 — Top 10 Tempo Total de Permanência por Equipamento (h) (robusto)
# =========================
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Equipamento (h)")
g3 = (
    df_filtrado.assign(**{
        "CD_EQUIPTO": df_filtrado["CD_EQUIPTO"].astype(str).str.replace(r"\.0$", "", regex=True)
    })
    .dropna(subset=["Tempo de Permanência(h)"])
    .assign(**{
        "Tempo de Permanência(h)": pd.to_numeric(df_filtrado["Tempo de Permanência(h)"], errors="coerce")
    })
    .groupby("CD_EQUIPTO", as_index=False)["Tempo de Permanência(h)"].sum()
    .sort_values("Tempo de Permanência(h)", ascending=False)
    .head(10)
)

if g3.empty:
    st.info("Sem dados de tempo de permanência no período/seleção.")
else:
    if debug: st.write("g3 head:", g3.head())
    ordem = g3.sort_values("Tempo de Permanência(h)", ascending=False)["CD_EQUIPTO"].tolist()
    st.altair_chart(
        alt.Chart(g3).mark_bar(color=COLOR).encode(
            y=alt.Y("CD_EQUIPTO:N", sort=ordem, title="Equipamento"),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=[
                alt.Tooltip("CD_EQUIPTO:N", title="Equipamento"),
                alt.Tooltip("Tempo de Permanência(h):Q", title="Tempo (h)", format=".2f")
            ]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# Gráfico 4 — Ocorrências por Componente (Classificação aprimorada)
# =========================
st.subheader("Gráfico 4 - Ocorrências por Componente — NÃO programadas (classificação aprimorada)")

# 1) Regras
df_clf = df_filtrado.copy()
df_clf["Comp_Rules"] = df_clf["DE_SERVICO"].apply(classify_rules)

# 2) (Opcional) ML leve para reclassificar parte do "Não Classificado"
use_ml = st.sidebar.toggle("Auto-classificar Não Classificadas (beta)", value=True)
ml_threshold = st.sidebar.slider("Confiança mínima (beta)", 0.50, 0.90, 0.60, 0.05)

antes_nc = int((df_clf["Comp_Rules"] == "Não Classificado").sum())

if use_ml:
    df_clf["Componente Detectado (final)"] = ml_reclass_optional(df_clf, "DE_SERVICO_N", "Comp_Rules", threshold=ml_threshold)
else:
    df_clf["Componente Detectado (final)"] = df_clf["Comp_Rules"]

depois_nc = int((df_clf["Componente Detectado (final)"] == "Não Classificado").sum())

g4 = (
    df_clf["Componente Detectado (final)"].astype(str).replace({"": "Não Classificado"})
      .value_counts(dropna=False).reset_index()
)
g4.columns = ["Componente", "Ocorrências"]
g4["Ocorrências"] = pd.to_numeric(g4["Ocorrências"], errors="coerce").fillna(0)
ordem = g4.sort_values("Ocorrências", ascending=False)["Componente"].tolist()

if g4.empty:
    st.info("Sem ocorrências por componente no período/seleção.")
else:
    st.caption(f"‘Não Classificado’: {antes_nc} → {depois_nc}  |  ML={'on' if use_ml else 'off'}  |  conf. ≥ {ml_threshold:.2f}")
    chart_g4 = (
        alt.Chart(g4).mark_bar(color=COLOR).encode(
            y=alt.Y("Componente:N", sort=ordem, title="Componente"),
            x=alt.X("Ocorrências:Q", title="Ocorrências"),
            tooltip=[alt.Tooltip("Componente:N"), alt.Tooltip("Ocorrências:Q")]
        ).properties(width=800, height=380)
    )
    st.altair_chart(chart_g4, use_container_width=True)

# =========================
# Gráfico 5 — Tendência diária (filtrado)
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
        st.altair_chart(
            alt.Chart(g5).mark_bar(color=COLOR).encode(
                x=alt.X("Data de Entrada:T", title="Data", axis=alt.Axis(format="%d/%m")),
                y=alt.Y("Quantidade:Q", title="OS por dia", scale=alt.Scale(domainMin=1)),
                tooltip=[alt.Tooltip("Data de Entrada:T", title="Data"), alt.Tooltip("Quantidade:Q", title="Qtd")]
            ).properties(width=800, height=380),
            use_container_width=True
        )
else:
    st.info("Coluna ENTRADA não encontrada.")

# =========================
# Gráfico 6 — Tendência mensal (GERAL, sem filtro de período)
# =========================
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções")
g6 = df.dropna(subset=["Ano/Mes"]).groupby("Ano/Mes").size().reset_index(name="Quantidade")
if debug: st.write("g6 head:", g6.head())
if g6.empty:
    st.info("Não foi possível construir a série mensal (dados insuficientes).")
else:
    st.altair_chart(
        alt.Chart(g6).mark_line(point=True, color=COLOR).encode(
            x=alt.X("Ano/Mes:T", title="Ano/Mês"),
            y=alt.Y("Quantidade:Q", title="Quantidade de OS"),
            tooltip=[alt.Tooltip("Ano/Mes:T", title="Ano/Mês"), alt.Tooltip("Quantidade:Q", title="Qtd")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =========================
# Triagem — Não classificadas (para evoluir as regras)
# =========================
st.subheader("Amostras de descrições NÃO CLASSIFICADAS (para evolução das regras)")
nao_cls = df_clf[df_clf["Componente Detectado (final)"] == "Não Classificado"].copy()
if nao_cls.empty:
    st.success("Nenhuma descrição não classificada no período/seleção.")
else:
    top_descricoes = (
        nao_cls["DE_SERVICO"]
        .value_counts()
        .reset_index(name="Ocorrências")
        .rename(columns={"index": "Descrição"})
        .head(50)
    )
    st.dataframe(top_descricoes, use_container_width=True)
    st.download_button(
        "Baixar CSV das não classificadas (top 50)",
        top_descricoes.to_csv(index=False).encode("utf-8-sig"),
        file_name="nao_classificadas_top50.csv",
        mime="text/csv"
    )
