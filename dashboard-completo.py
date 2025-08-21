import streamlit as st
import pandas as pd
import altair as alt
import re, unicodedata

st.set_page_config(layout="wide")
st.title("Dashboard de Manutenção - Consolidado")

# =============== util ===============
def norm_txt(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower().strip()
    # remove acentos
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    # normaliza separadores
    s = re.sub(r"[_\-.,;:/\\]+", " ", s)
    return s

# =============== carga CSV/Excel ===============
@st.cache_data(show_spinner=False)
def carregar_dados(arquivo):
    nome = getattr(arquivo, "name", "")
    tipo = getattr(arquivo, "type", "")
    # Excel?
    if str(nome).lower().endswith((".xlsx", ".xls")) or "excel" in str(tipo).lower():
        df = pd.read_excel(arquivo, sheet_name=0)
    else:
        try:
            df = pd.read_csv(arquivo, encoding="latin1", sep=";")
        except Exception:
            if hasattr(arquivo, "seek"): arquivo.seek(0)
            df = pd.read_csv(arquivo, engine="python", sep=None)

    df.columns = df.columns.str.strip()

    # Descrição
    df["DE_SERVICO"] = (
        df.get("DE_SERVICO", "")
          .fillna("")
          .astype(str)
          .map(norm_txt)
    )

    # Datas
    for col in ["ENTRADA", "SAIDA"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Ano/Mês
    df["Ano/Mes"] = df["ENTRADA"].dt.to_period("M").dt.to_timestamp() if "ENTRADA" in df.columns else pd.NaT

    # Tempo de Permanência (h)
    if {"ENTRADA","SAIDA"}.issubset(df.columns):
        tmp = (df["SAIDA"] - df["ENTRADA"]).dt.total_seconds() / 3600.0
        # evita negativos (OS abertas/ajustes de relógio)
        df["Tempo de Permanência(h)"] = tmp.clip(lower=0)
    else:
        df["Tempo de Permanência(h)"] = pd.NA

    # Categorias-chave
    df["CD_EQUIPTO"]  = df.get("CD_EQUIPTO", pd.NA).fillna("Não informado").astype(str).str.strip().replace({"": "Não informado"})
    df["CD_CLASMANU"] = df.get("CD_CLASMANU", pd.NA).fillna("Não informado").astype(str).str.strip().replace({"": "Não informado"})

    df["Origem"] = "NÃO INFORMADO"
    return df

# =============== dicionário externo opcional ===============
def carregar_dicionario(upload):
    """
    CSV com colunas: categoria, termo_ou_regex
    Exemplo:
      Motor, motor\b
      Suspensão, amortecedor|mola|feixe de mola
      Vazamento - Óleo, vaz(a|e)mento.*oleo|vazando.*oleo
    """
    dic = {}
    if upload is None: 
        return dic
    try:
        dd = pd.read_csv(upload)
    except Exception:
        upload.seek(0)
        dd = pd.read_csv(upload, sep=";")
    dd.columns = dd.columns.str.strip().str.lower()
    if not {"categoria","termo_ou_regex"}.issubset(dd.columns):
        st.warning("Dicionário inválido: precisa ter colunas 'categoria' e 'termo_ou_regex'.")
        return {}
    for _,row in dd.iterrows():
        cat = str(row["categoria"]).strip()
        patt = str(row["termo_ou_regex"]).strip()
        if not cat or not patt: 
            continue
        dic.setdefault(cat, []).append(re.compile(patt))
    return dic

# =============== regras base (regex compiladas) ===============
def regras_base():
    R = {
        # Vazamentos (prioridade alta; regras específicas)
        "Vazamento - Óleo": [
            re.compile(r"\bvaz[a-z]*\b.*\boleo\b"), re.compile(r"\boleo\b.*\bvaz[a-z]*\b"),
            re.compile(r"\bretentor\b"), re.compile(r"\bvedador(es)?\b")
        ],
        "Vazamento - Hidráulico": [
            re.compile(r"\bvaz[a-z]*\b.*\bhidraul"), re.compile(r"\bhidraul.*\bvaz[a-z]*\b"),
            re.compile(r"\bcilindro hidraul"), re.compile(r"\bvalvula(s)?\b"), re.compile(r"\bbomba hidraul")
        ],
        "Vazamento - Combustível": [
            re.compile(r"\bvaz[a-z]*\b.*\b(diesel|combust|gasol)"), re.compile(r"\b(diesel|combust|gasol).*vaz[a-z]*")
        ],
        # Itens de sistema
        "Motor": [
            re.compile(r"\bmotor(?!ista)\b"), re.compile(r"\bcabecote\b"), re.compile(r"\bpist[aã]o\b"),
            re.compile(r"\bbiela\b"), re.compile(r"\bbronzina\b"), re.compile(r"\bbomba de oleo\b"),
            re.compile(r"\barrefe(c|ç)edor\b"), re.compile(r"\bturbina|turbo\b"), re.compile(r"\bcorreia dent")
        ],
        "Transmissão / Câmbio": [
            re.compile(r"\b(cambio|transmiss[aã]o)\b"), re.compile(r"\bembreagem\b"), re.compile(r"\b(diferencial|planet[aá]ria|coroa|pinhao)\b"),
            re.compile(r"\bcarda?n\b")
        ],
        "Freio": [
            re.compile(r"\bfreio(s)?\b"), re.compile(r"\bpastilh"), re.compile(r"\blona(s)?\b"),
            re.compile(r"\bdisco(s)?\b"), re.compile(r"\btambor(es)?\b"), re.compile(r"\bpin[cç]a\b"),
            re.compile(r"\bcilindro mestre\b"), re.compile(r"\bfluido de freio\b")
        ],
        "Suspensão": [
            re.compile(r"\bamortecedor(es)?\b"), re.compile(r"\bmola(s)?\b"), re.compile(r"\bfeixe de mola\b"),
            re.compile(r"\bbucha(s)?\b"), re.compile(r"\bbandeja\b"), re.compile(r"\bpivo\b"), re.compile(r"\bestabilizador\b")
        ],
        "Direção": [
            re.compile(r"\b(caixa|sistema) de dire[cç][aã]o\b"), re.compile(r"\bterminal de dire[cç][aã]o\b"),
            re.compile(r"\bbarra de dire[cç][aã]o\b"), re.compile(r"\borbitrol\b")
        ],
        "Elétrica": [
            re.compile(r"\beletr[aí]c"), re.compile(r"\bchicote\b"), re.compile(r"\bfus[ií]vel\b"),
            re.compile(r"\brele\b"), re.compile(r"\bl[aâ]mpada|farol|lanterna\b"), re.compile(r"\bbateria\b"),
            re.compile(r"\bmotor de arranque\b"), re.compile(r"\balternador\b")
        ],
        "Falha Eletrônica / Painel": [
            re.compile(r"\bpainel\b"), re.compile(r"\b(luz|lamp)\s*espia\b"), re.compile(r"\bc[oó]digo de falha\b"),
            re.compile(r"\b(sensor|atuador|modulo|ecu|can)\b"), re.compile(r"\bsem comunica[cç][aã]o\b"), re.compile(r"\binjet(or|or(es)?)\b")
        ],
        "Sistema Hidráulico (sem vazamento)": [
            re.compile(r"\bbomba\b.*\bhidraul"), re.compile(r"\bvalvula\b.*\bhidraul"),
            re.compile(r"\bcilindro\b.*\bhidraul"), re.compile(r"\bhidromotor|hidrostat(ico|ica)\b")
        ],
        "Pneus/Rodagem": [
            re.compile(r"\bpneu(s)?\b"), re.compile(r"\broda(s)?\b"), re.compile(r"\bc[aâ]mara\b"),
        ],
        "Rodantes": [
            re.compile(r"\brodante(s)?\b"), re.compile(r"\brolete(s)?\b"), re.compile(r"\broda motriz\b"),
            re.compile(r"\bcoroa\b"), re.compile(r"\besteira|sapata\b")
        ],
        "Ar Condicionado": [
            re.compile(r"\bar condicionado\b|\bac\b"), re.compile(r"\bcompressor do ar\b|\bcompressor\b.*\bar\b"),
            re.compile(r"\bcondensador\b"), re.compile(r"\bevaporador\b"), re.compile(r"\bventilador\b"), re.compile(r"\bgas do ar\b")
        ],
        "Mangueira (Vazamento)": [
            re.compile(r"\bmangueira(s)?\b"), re.compile(r"\bflex[ií]vel\b")
        ],
        "Rádio": [ re.compile(r"\br[aá]dio\b") ],
        "Elevador": [ re.compile(r"\belevador|elevat[oó]ria|plataforma\b") ],
        "Acumulador": [ re.compile(r"\bacumulador\b") ],
        "Despontador": [ re.compile(r"\bdespontador\b") ],
        # "Avaliar" fica por último na prioridade
        "Avaliar": [ re.compile(r"\bavaliar|verificar|inspecionar|chec(ar|agem)|vistoriar\b") ],
    }
    return R

# prioridade das categorias (mais específicas primeiro; "Avaliar" por último)
PRIORIDADE = [
    "Vazamento - Óleo","Vazamento - Hidráulico","Vazamento - Combustível",
    "Falha Eletrônica / Painel","Elétrica",
    "Transmissão / Câmbio","Freio","Direção","Suspensão",
    "Sistema Hidráulico (sem vazamento)","Pneus/Rodagem","Rodantes",
    "Ar Condicionado","Mangueira (Vazamento)","Rádio","Elevador","Acumulador","Despontador",
    "Motor",   # (depois das específicas para evitar capturar tudo)
    "Avaliar"  # só se nada mais bater
]

def montar_regras(dic_user):
    R = regras_base()
    # injeta padrões do usuário (sobrescreve/adiciona)
    for cat, patt_list in dic_user.items():
        R.setdefault(cat, [])
        R[cat].extend(patt_list)
    return R

def classificar(texto: str, regras) -> str:
    t = norm_txt(texto)
    if not t: 
        return "Não Classificado"

    # regra especial para vazamentos genéricos + palavra alvo
    if re.search(r"\bvaz[a-z]*\b", t):
        if re.search(r"\bhidraul", t):  return "Vazamento - Hidráulico"
        if re.search(r"\boleo\b", t):   return "Vazamento - Óleo"
        if re.search(r"\b(diesel|combust|gasol)\b", t): return "Vazamento - Combustível"

    # prioridade por categoria
    for cat in PRIORIDADE:
        for patt in regras.get(cat, []):
            if patt.search(t):
                return cat

    return "Não Classificado"

# ================= Uploads =================
st.sidebar.header("Arquivos")
arquivo = st.sidebar.file_uploader("Envie o arquivo (.csv, .xlsx, .xls)", type=["csv","xlsx","xls"])
dic_upload = st.sidebar.file_uploader("Opcional: dicionário de termos (CSV: categoria,termo_ou_regex)", type=["csv"])
if arquivo is None:
    st.info("Envie o arquivo no painel lateral para carregar o dashboard.")
    st.stop()

df = carregar_dados(arquivo)
dic_user = carregar_dicionario(dic_upload)
REGRAS = montar_regras(dic_user)

# aplica classificador novo
df["Componente Detectado"] = df["DE_SERVICO"].apply(lambda s: classificar(s, REGRAS))

# =============== filtros ===============
st.sidebar.header("Filtro de Período (aplicado na maioria dos gráficos)")
hoje = pd.Timestamp.today().normalize()
inicio_padrao = (df["ENTRADA"].min().date() if "ENTRADA" in df.columns and pd.notna(df["ENTRADA"]).any()
                 else (hoje - pd.Timedelta(days=30)).date())
data_inicio = st.sidebar.date_input("Data de Início", value=inicio_padrao)
data_fim    = st.sidebar.date_input("Data de Fim", value=hoje.date())

valores_clas = sorted(df["CD_CLASMANU"].dropna().unique().tolist())
op_clas = st.sidebar.multiselect("Filtrar por CD_CLASMANU (opcional)", valores_clas, default=valores_clas if valores_clas else [])

mask_periodo = (df["ENTRADA"] >= pd.to_datetime(data_inicio)) & (df["ENTRADA"] <= pd.to_datetime(data_fim)) if "ENTRADA" in df.columns else pd.Series(True, index=df.index)
mask_clas = df["CD_CLASMANU"].isin(op_clas) if len(op_clas) > 0 else pd.Series(True, index=df.index)
df_filtrado = df[mask_periodo & mask_clas].copy()

debug = st.sidebar.checkbox("Modo debug (mostrar heads)", value=False)

# =============== Gráfico 1 — Top 10 CD_CLASMANU ===============
st.subheader("Gráfico 1 - Top 10 Classificações (CD_CLASMANU)")
g1 = df_filtrado["CD_CLASMANU"].value_counts(dropna=False).reset_index(name="Quantidade").head(10)
g1.columns = ["CD_CLASMANU","Quantidade"]
if g1.empty:
    st.info("Sem dados para CD_CLASMANU no período/seleção.")
else:
    if debug: st.write("g1 head:", g1.head())
    st.altair_chart(
        alt.Chart(g1).mark_bar().encode(
            y=alt.Y("CD_CLASMANU:N", sort=alt.SortField(field="Quantidade", order="descending"), title="CD_CLASMANU"),
            x=alt.X("Quantidade:Q", title="Quantidade"),
            tooltip=["CD_CLASMANU","Quantidade"]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =============== Gráfico 2 — Top 10 OS por Equipamento ===============
st.subheader("Gráfico 2 - Top 10 Número de OS por Equipamento (CD_EQUIPTO)")
g2 = df_filtrado["CD_EQUIPTO"].value_counts(dropna=False).reset_index(name="OS").head(10)
g2.columns = ["CD_EQUIPTO","OS"]
if g2.empty:
    st.info("Sem dados de equipamentos no período/seleção.")
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

# =============== Gráfico 3 — Tempo Total (h) por Equipamento ===============
st.subheader("Gráfico 3 - Top 10 Tempo Total de Permanência por Equipamento (h)")
g3 = (df_filtrado.dropna(subset=["Tempo de Permanência(h)"])
      .groupby("CD_EQUIPTO", as_index=False)["Tempo de Permanência(h)"].sum()
      .sort_values("Tempo de Permanência(h)", ascending=False)
      .head(10))
if g3.empty:
    st.info("Sem dados de tempo de permanência no período/seleção.")
else:
    if debug: st.write("g3 head:", g3.head())
    st.altair_chart(
        alt.Chart(g3).mark_bar().encode(
            y=alt.Y("CD_EQUIPTO:N", sort=alt.SortField(field="Tempo de Permanência(h)", order="descending"), title="Equipamento"),
            x=alt.X("Tempo de Permanência(h):Q", title="Tempo (h)"),
            tooltip=["CD_EQUIPTO", alt.Tooltip("Tempo de Permanência(h):Q", format=".2f", title="Tempo (h)")]
        ).properties(width=800, height=380),
        use_container_width=True
    )

# =============== Gráfico 4 — Ocorrências por Componente (DE_SERVICO) ===============
st.subheader("Gráfico 4 - Ocorrências por Componente (DE_SERVICO)")
g4 = df_filtrado["Componente Detectado"].value_counts(dropna=False).reset_index(name="Ocorrências")
g4.columns = ["Componente","Ocorrências"]
if g4.empty:
    st.info("Sem ocorrências por componente no período/seleção.")
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

# =============== Gráfico 5 — Tendência Diária (filtrado) ===============
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
            alt.Chart(g5).mark_bar().encode(
                x=alt.X("Data de Entrada:T", title="Data de Entrada", axis=alt.Axis(format="%d/%m")),
                y=alt.Y("Quantidade:Q", title="Quantidade de OS", scale=alt.Scale(domainMin=1)),
                tooltip=[alt.Tooltip("Data de Entrada:T", title="Data"), alt.Tooltip("Quantidade:Q", title="Qtd")]
            ).properties(width=800, height=380),
            use_container_width=True
        )
else:
    st.info("Coluna ENTRADA não encontrada.")

# =============== Gráfico 6 — Tendência Mensal (GERAL, sem filtro) ===============
st.subheader("Gráfico 6 - Tendência Mensal de Manutenções (Geral, sem filtro de período)")
g6 = df.dropna(subset=["Ano/Mes"]).groupby("Ano/Mes").size().reset_index(name="Quantidade")
if g6.empty:
    st.info("Não foi possível construir a série mensal (dados insuficientes).")
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

# =============== Triagem — “Não Classificado” (para melhorar dicionário) ===============
st.subheader("Amostras de descrições NÃO CLASSIFICADAS (para triagem)")
nao_cls = df_filtrado[df_filtrado["Componente Detectado"] == "Não Classificado"].copy()
if nao_cls.empty:
    st.success("Ótimo! Nenhuma descrição não classificada no período/seleção.")
else:
    top_descricoes = (nao_cls["DE_SERVICO"]
                      .value_counts()
                      .reset_index(name="Ocorrências")
                      .rename(columns={"index":"Descrição"})
                      .head(50))
    st.caption("Top 50 descrições idênticas não classificadas — use para alimentar o dicionário CSV.")
    st.dataframe(top_descricoes, use_container_width=True)
    csv = top_descricoes.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Baixar CSV das não classificadas (top 50)", csv, file_name="nao_classificadas_top50.csv", mime="text/csv")
