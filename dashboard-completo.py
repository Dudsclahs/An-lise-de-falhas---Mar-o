import altair as alt

# Gráfico - Tipos de Falha
tipo_falha = df_filtrado["Causa manutenção"].value_counts().head(15)
df_falha = tipo_falha.reset_index()
df_falha.columns = ["Tipo de Falha", "Quantidade"]

chart_falha = alt.Chart(df_falha).mark_bar().encode(
    x=alt.X("Tipo de Falha:N", sort="-y"),
    y="Quantidade:Q"
).properties(width=700)

st.subheader("Top 15 - Tipos de Falha")
st.altair_chart(chart_falha, use_container_width=True)

# Gráfico - Número de OS por Frota
os_por_frota = df_filtrado["Número de frota"].value_counts().head(15)
df_os = os_por_frota.reset_index()
df_os.columns = ["Frota", "OS"]

chart_os = alt.Chart(df_os).mark_bar().encode(
    x=alt.X("Frota:N", sort="-y"),
    y="OS:Q"
).properties(width=700)

st.subheader("Top 15 - Número de OS por Frota")
st.altair_chart(chart_os, use_container_width=True)

# Gráfico - Tempo de Permanência por Frota
tempo_por_frota = df_filtrado.groupby("Número de frota")["Tempo de Permanência(h)"].sum().sort_values(ascending=False).head(15)
df_tempo = tempo_por_frota.reset_index()
df_tempo.columns = ["Frota", "Tempo (h)"]

chart_tempo = alt.Chart(df_tempo).mark_bar().encode(
    x=alt.X("Frota:N", sort="-y"),
    y="Tempo (h):Q"
).properties(width=700)

st.subheader("Top 15 - Tempo Total de Permanência por Frota (h)")
st.altair_chart(chart_tempo, use_container_width=True)

# Gráfico de Pareto - Tempo por Tipo de Falha
df_pareto = df_filtrado.groupby("Causa manutenção")["Tempo de Permanência(h)"].sum().sort_values(ascending=False)
df_pareto = df_pareto[df_pareto > 0].reset_index()
df_pareto.columns = ["Tipo de Falha", "Tempo"]
df_pareto["Acumulado (%)"] = df_pareto["Tempo"].cumsum() / df_pareto["Tempo"].sum()

chart_pareto = alt.Chart(df_pareto).mark_bar(color="green").encode(
    x=alt.X("Tipo de Falha:N", sort="-y"),
    y="Tempo:Q"
)

linha_pareto = alt.Chart(df_pareto).mark_line(point=True, color="orange").encode(
    x="Tipo de Falha:N",
    y=alt.Y("Acumulado (%):Q", axis=alt.Axis(format='%'))
)

st.subheader("Gráfico de Pareto - Tempo por Tipo de Falha")
st.altair_chart(chart_pareto + linha_pareto, use_container_width=True)

# Gráfico - Tendência Mensal
tendencia = df_filtrado.groupby("Ano/Mes")["Boletim"].count().reset_index()
tendencia.columns = ["Ano/Mês", "Quantidade"]

chart_tendencia = alt.Chart(tendencia).mark_line(point=True).encode(
    x="Ano/Mês:T",
    y="Quantidade:Q"
).properties(width=700)

st.subheader("Tendência Mensal de Manutenções")
st.altair_chart(chart_tendencia, use_container_width=True)

