import streamlit as st
import pandas as pd

def mostra_classifica_wod(test_df, wod_selezionato, esercizi_df):
    st.header(f"Classifica: {wod_selezionato}")
    tipo_valore = esercizi_df[esercizi_df['esercizio'] == wod_selezionato]['tipo_valore'].values[0]
    classifica = test_df[test_df['esercizio'] == wod_selezionato].copy()

    if tipo_valore == 'tempo':
        def tempo_to_sec(x):
            try:
                m, s = map(int, str(x).split(":"))
                return m * 60 + s
            except:
                return None
        classifica['valore_sec'] = classifica['valore'].apply(tempo_to_sec)
        classifica = classifica.sort_values('valore_sec')
    else:
        classifica['valore_num'] = pd.to_numeric(classifica['valore'], errors='coerce')
        classifica = classifica.sort_values('valore_num', ascending=False)

    genere_selezionato = st.selectbox("Seleziona genere", ["Tutti", "Maschio", "Femmina"])
    if genere_selezionato != "Tutti":
        classifica = classifica[classifica['genere'] == genere_selezionato]

    st.dataframe(classifica[['nome', 'valore', 'data', 'genere']].reset_index(drop=True))

