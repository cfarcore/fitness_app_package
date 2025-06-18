import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account

# --- CREDENZIALI GOOGLE ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SERVICE_ACCOUNT_INFO = st.secrets["SERVICE_ACCOUNT_JSON"]
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=SCOPE
)
client = gspread.authorize(creds)

NOME_FILE = "esercizi"       # Cambia con il nome esatto del tuo file Google
SHEET_NAME = "esercizi"      # Cambia con il nome esatto del foglio/tabella

def carica_esercizi():
    sh = client.open(NOME_FILE)
    worksheet = sh.worksheet(SHEET_NAME)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def salva_esercizi(df):
    sh = client.open(NOME_FILE)
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

def mostra_gestione_esercizi():
    st.title("⚙️ Gestione Esercizi")
    df = carica_esercizi()

    # --- Visualizza tabella esercizi ---
    st.dataframe(df)

    # --- Aggiungi nuovo esercizio ---
    st.markdown("### ➕ Aggiungi nuovo esercizio")
    with st.form("aggiungi_esercizio"):
        categoria = st.text_input("Categoria")
        esercizio = st.text_input("Nome esercizio")
        tipo_valore = st.selectbox("Tipo valore", ["kg_rel", "reps", "tempo", "altro"])
        submitted = st.form_submit_button("Aggiungi")
        if submitted:
            nuovo = {
                "categoria": categoria,
                "esercizio": esercizio,
                "tipo_valore": tipo_valore
            }
            df = pd.concat([df, pd.DataFrame([nuovo])], ignore_index=True)
            salva_esercizi(df)
            st.success("Esercizio aggiunto con successo!")
            st.rerun()

    # --- Modifica esercizio ---
    st.markdown("### ✏️ Modifica esercizio")
    if not df.empty:
        idx = st.selectbox("Seleziona esercizio da modificare", df.index, format_func=lambda i: f"{df.loc[i, 'categoria']} - {df.loc[i, 'esercizio']}")
        with st.form("modifica_esercizio"):
            new_categoria = st.text_input("Categoria", value=df.loc[idx, "categoria"])
            new_esercizio = st.text_input("Nome esercizio", value=df.loc[idx, "esercizio"])
            new_tipo_valore = st.selectbox("Tipo valore", ["kg_rel", "reps", "tempo", "altro"], index=["kg_rel", "reps", "tempo", "altro"].index(df.loc[idx, "tipo_valore"]) if df.loc[idx, "tipo_valore"] in ["kg_rel", "reps", "tempo", "altro"] else 0)
            submit_mod = st.form_submit_button("Modifica")
            if submit_mod:
                df.loc[idx, "categoria"] = new_categoria
                df.loc[idx, "esercizio"] = new_esercizio
                df.loc[idx, "tipo_valore"] = new_tipo_valore
                salva_esercizi(df)
                st.success("Esercizio modificato!")
                st.rerun()

    # --- Elimina esercizio ---
    st.markdown("### 🗑️ Elimina esercizio")
    if not df.empty:
        idx_del = st.selectbox("Seleziona esercizio da eliminare", df.index, format_func=lambda i: f"{df.loc[i, 'categoria']} - {df.loc[i, 'esercizio']}", key="elimina")
        if st.button("Elimina", key="delete_button"):
            df = df.drop(idx_del).reset_index(drop=True)
            salva_esercizi(df)
            st.warning("Esercizio eliminato!")
            st.rerun()
