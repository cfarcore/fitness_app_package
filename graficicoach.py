import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def normalize(s):
    """
    Normalizza una stringa: lowercase, rimuove spazi e caratteri speciali.
    """
    if pd.isnull(s): return ""
    return str(s).strip().lower().replace(" ", "").replace("-", "").replace("_", "")

def mostra_grafico_radar_coach(test_df, esercizi_df, benchmark_df, utenti_df):
    # --- Normalizza colonne necessarie ---
    esercizi_df['categoria_norm'] = esercizi_df['categoria'].apply(normalize)
    esercizi_df['esercizio_norm'] = esercizi_df['esercizio'].apply(normalize)
    test_df['esercizio_norm'] = test_df['esercizio'].apply(normalize)
    benchmark_df['esercizio_norm'] = benchmark_df['esercizio'].apply(normalize)
    utenti_df['nome_norm'] = utenti_df['nome'].apply(normalize)
    test_df['nome_norm'] = test_df['nome'].apply(normalize)

    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    livelli_val = livello_mapping

    st.subheader("📊 Profilo Radar (per atleta)")
    nomi_atleti = utenti_df[utenti_df['ruolo'] == 'atleta']['nome'].unique()
    nomi_atleti_norm = [normalize(n) for n in nomi_atleti]
    atleta_radar_vis = st.selectbox("Seleziona atleta per Radar", nomi_atleti)
    atleta_radar = normalize(atleta_radar_vis)

    # Debug: controllo presenza nome!
    test_atleta = test_df[test_df['nome_norm'] == atleta_radar]
    st.write(f"Dati trovati per {atleta_radar_vis}: {len(test_atleta)} righe in test_df")
    if len(test_atleta) == 0:
        st.warning(f"Nessun dato trovato per '{atleta_radar_vis}' (nome normalizzato: '{atleta_radar}') in test_df.")
        st.write("Nomi unici in test_df:", list(test_df['nome'].unique()))

    tutte_categorie = esercizi_df["categoria"].unique()
    radar_labels = []
    radar_values = []

    for categoria in tutte_categorie:
        cat_norm = normalize(categoria)
        esercizi_cat = esercizi_df[esercizi_df['categoria_norm'] == cat_norm]['esercizio_norm']
        test_cat = test_df[(test_df['nome_norm'] == atleta_radar) & (test_df['esercizio_norm'].isin(esercizi_cat))]
        livelli_cat = []
        for _, row in test_cat.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
                (benchmark_df['genere'] == row['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello_num = 0
            if benchmark is not None and isinstance(benchmark, pd.Series):
                tipo = benchmark['tipo_valore']
                try:
                    peso_corporeo = float(row.get('peso_corporeo', 0) or row.get('peso', 0))
                except Exception:
                    peso_corporeo = None
                if tipo == 'kg_rel' and peso_corporeo and peso_corporeo != 0:
                    try:
                        val = float(row['valore']) / peso_corporeo
                    except Exception:
                        val = None
                elif tipo == 'reps' or tipo == 'valore':
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None
                elif tipo == 'tempo':
                    try:
                        m, s = map(int, str(row['valore']).split(":"))
                        val = m * 60 + s
                        benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                            lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                        )
                    except Exception:
                        val = None
                else:
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None

                if tipo == 'tempo':
                    livelli_ordine = list(reversed(livelli_val.keys()))
                    for livello_nome in livelli_ordine:
                        soglia = benchmark[livello_nome]
                        if isinstance(soglia, str) and ":" in soglia:
                            m, s = map(int, soglia.split(":"))
                            soglia = m * 60 + s
                        else:
                            try:
                                soglia = float(soglia)
                            except Exception:
                                continue
                        if val is not None and val <= soglia:
                            livello_num = livelli_val[livello_nome]
                            break
                else:
                    for livello_nome in reversed(list(livelli_val.keys())):
                        soglia = benchmark[livello_nome]
                        try:
                            soglia = float(soglia)
                        except Exception:
                            continue
                        if val is not None and val >= soglia:
                            livello_num = livelli_val[livello_nome]
                            break
            livelli_cat.append(livello_num)
        if livelli_cat:
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(sum(livelli_cat) / len(livelli_cat), 2))
    if radar_labels:
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_values,
            theta=radar_labels,
            fill='toself',
            marker=dict(color='rgba(0,123,255,0.7)')
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title=f"Profilo Radar: {atleta_radar_vis}",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
        for label, value in zip(radar_labels, radar_values):
            st.write(f"**{label}**: {value}/5")
    else:
        st.info("Non ci sono dati sufficienti per generare il grafico radar.")

def mostra_grafico_radar_generale(test_df, esercizi_df, benchmark_df, utenti_df):
    esercizi_df['categoria_norm'] = esercizi_df['categoria'].apply(normalize)
    esercizi_df['esercizio_norm'] = esercizi_df['esercizio'].apply(normalize)
    test_df['esercizio_norm'] = test_df['esercizio'].apply(normalize)
    benchmark_df['esercizio_norm'] = benchmark_df['esercizio'].apply(normalize)

    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    livelli_val = livello_mapping

    st.subheader("📊 Radar Stato Generale Atleti (per categoria)")
    tutte_categorie = esercizi_df["categoria"].unique()
    radar_labels = []
    radar_values = []

    for categoria in tutte_categorie:
        cat_norm = normalize(categoria)
        esercizi_cat = esercizi_df[esercizi_df['categoria_norm'] == cat_norm]['esercizio_norm']
        test_cat = test_df[test_df['esercizio_norm'].isin(esercizi_cat)]
        livelli_cat = []
        for _, row in test_cat.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
                (benchmark_df['genere'] == row['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello_num = 0
            if benchmark is not None and isinstance(benchmark, pd.Series):
                tipo = benchmark['tipo_valore']
                try:
                    peso_corporeo = float(row.get('peso_corporeo', 0) or row.get('peso', 0))
                except Exception:
                    peso_corporeo = None
                if tipo == 'kg_rel' and peso_corporeo and peso_corporeo != 0:
                    try:
                        val = float(row['valore']) / peso_corporeo
                    except Exception:
                        val = None
                elif tipo == 'reps' or tipo == 'valore':
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None
                elif tipo == 'tempo':
                    try:
                        m, s = map(int, str(row['valore']).split(":"))
                        val = m * 60 + s
                        benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                            lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                        )
                    except Exception:
                        val = None
                else:
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None

                if tipo == 'tempo':
                    livelli_ordine = list(reversed(livelli_val.keys()))
                    for livello_nome in livelli_ordine:
                        soglia = benchmark[livello_nome]
                        if isinstance(soglia, str) and ":" in soglia:
                            m, s = map(int, soglia.split(":"))
                            soglia = m * 60 + s
                        else:
                            try:
                                soglia = float(soglia)
                            except Exception:
                                continue
                        if val is not None and val <= soglia:
                            livello_num = livelli_val[livello_nome]
                            break
                else:
                    for livello_nome in reversed(list(livelli_val.keys())):
                        soglia = benchmark[livello_nome]
                        try:
                            soglia = float(soglia)
                        except Exception:
                            continue
                        if val is not None and val >= soglia:
                            livello_num = livelli_val[livello_nome]
                            break
            livelli_cat.append(livello_num)
        if livelli_cat:
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(sum(livelli_cat) / len(livelli_cat), 2))
    if radar_labels:
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_values,
            theta=radar_labels,
            fill='toself',
            marker=dict(color='rgba(40,167,69,0.7)')
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title="Stato Generale Atleti per Categoria",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
        for label, value in zip(radar_labels, radar_values):
            st.write(f"**{label}**: {value}/5")
    else:
        st.info("Non ci sono dati sufficienti per generare il grafico radar generale.")

def mostra_grafici_coach(test_df, esercizi_df, benchmark_df, utenti_df):
    """
    Wrapper per mostrare entrambi i grafici radar (individuale e generale).
    """
    mostra_grafico_radar_coach(test_df, esercizi_df, benchmark_df, utenti_df)
    if st.button("Mostra Radar Stato Generale Atleti"):
        mostra_grafico_radar_generale(test_df, esercizi_df, benchmark_df, utenti_df)
