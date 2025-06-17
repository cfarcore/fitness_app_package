import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
import os
import time
import pickle
import datetime
import plotly.graph_objects as go

# --- UTILITY: NORMALIZE FUNCTION ---
def normalize(s):
    """Normalizza una stringa per confronto: lowercase, strip, senza spazi/trattini."""
    return str(s).strip().lower().replace(" ", "").replace("-", "") if pd.notnull(s) else ""

from classifica_workout import mostra_classifica_wod
# --- INIZIALIZZAZIONE DATAFRAME VUOTI ---
utenti_df = pd.DataFrame()
esercizi_df = pd.DataFrame()
test_df = pd.DataFrame()
benchmark_df = pd.DataFrame()
wod_df = pd.DataFrame()

# --- INIZIALIZZAZIONE SESSION STATE ---
if "refresh" not in st.session_state:
    st.session_state.refresh = False
if "utente" not in st.session_state:
    st.session_state.utente = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- FUNZIONI DI UTILITÀ ---
def is_utente_valido():
    return (
        "utente" in st.session_state and
        st.session_state.utente is not None and
        isinstance(st.session_state.utente, dict) and
        "ruolo" in st.session_state.utente
    )

def logout():
    st.session_state.logged_in = False
    st.session_state.utente = None
    st.session_state.refresh = False
    st.success("Logout effettuato con successo!")
    st.rerun()

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

def salva_su_google_sheets(df, file_name, sheet_name, append=False):
    import numpy as np

    # Converte tutto in stringhe e sostituisce NaN o None con ""
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(lambda x: "" if pd.isna(x) or x is None or (isinstance(x, float) and np.isnan(x)) else str(x))

    df = df.fillna("").reset_index(drop=True)

    sh = client.open(file_name)
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
    if append:
        last_row = df.iloc[-1].values.tolist()
        worksheet.append_row(last_row)
    else:
        if len(df) == 0:
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()])
            st.warning("Foglio aggiornato solo con intestazioni (nessun dato da salvare).")
            return
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())




# --- CACHE LOCALE ---
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def carica_da_google_sheets(sheet_name, cache_duration=300):
    cache_file = os.path.join(CACHE_DIR, f"{sheet_name}.pkl")
    if os.path.exists(cache_file):
        last_modified = os.path.getmtime(cache_file)
        if time.time() - last_modified < cache_duration:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
    try:
        sh = client.open(sheet_name)
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.get_worksheet(0)
            st.warning(f"Worksheet '{sheet_name}' non trovato, caricata la prima worksheet '{worksheet.title}' dal file '{sheet_name}'.")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        with open(cache_file, "wb") as f:
            pickle.dump(df, f)
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Il file Google Sheets '{sheet_name}' non è stato trovato. Verifica che il nome sia corretto.")
        st.stop()
    except Exception as e:
        st.error(f"Errore durante il caricamento di '{sheet_name}': {e}")
        st.stop()

# --- CACHE DATI ---
@st.cache_data(ttl=60)
def carica_utenti():
    return carica_da_google_sheets("utenti", cache_duration=0)

@st.cache_data(ttl=60)
def carica_esercizi():
    return carica_da_google_sheets("esercizi", cache_duration=0)

@st.cache_data(ttl=60)
def carica_test():
    return carica_da_google_sheets("test", cache_duration=0)

@st.cache_data(ttl=60)
def carica_benchmark():
    return carica_da_google_sheets("benchmark", cache_duration=0)

@st.cache_data(ttl=60)
def carica_wod():
    return carica_da_google_sheets("wod", cache_duration=0)

# --- REFRESH DATI ---
def aggiorna_tutti_i_dati():
    global utenti_df, esercizi_df, test_df, benchmark_df, wod_df
    utenti_df = carica_utenti()
    esercizi_df = carica_esercizi()
    esercizi_df["categoria_norm"] = esercizi_df["categoria"].astype(str).str.strip().str.lower().str.replace(" ", "")
    esercizi_df["esercizio_norm"] = esercizi_df["esercizio"].astype(str).str.strip().str.lower().str.replace(" ", "")
    test_df = carica_test()
    test_df["esercizio_norm"] = test_df["esercizio"].astype(str).str.strip().str.lower().str.replace(" ", "")
    benchmark_df = carica_benchmark()
    benchmark_df["esercizio_norm"] = benchmark_df["esercizio"].astype(str).str.strip().str.lower().str.replace(" ", "")
    benchmark_df["categoria_norm"] = benchmark_df["esercizio"].map(
        lambda e: esercizi_df.set_index("esercizio")["categoria"].get(e, "") if e in esercizi_df["esercizio"].values else ""
    ).astype(str).str.strip().str.lower().str.replace(" ", "")
    wod_df = carica_wod()



    # Normalizzazione colonne e valori
    test_df.columns = [str(col).strip().lower() for col in test_df.columns]
    esercizi_df.columns = [str(col).strip().lower() for col in esercizi_df.columns]
    benchmark_df.columns = [str(col).strip().lower() for col in benchmark_df.columns]
    # --- AGGIUNGI colonne normalizzate ---
    if "esercizio" in benchmark_df.columns:
        benchmark_df["esercizio_norm"] = benchmark_df["esercizio"].apply(normalize)
    if "categoria" in benchmark_df.columns:
        benchmark_df["categoria_norm"] = benchmark_df["categoria"].apply(normalize)
    if "esercizio" in test_df.columns:
        test_df["esercizio_norm"] = test_df["esercizio"].apply(normalize)
    if "categoria" in test_df.columns:
        test_df["categoria_norm"] = test_df["categoria"].apply(normalize)
    if "esercizio" in esercizi_df.columns:
        esercizi_df["esercizio_norm"] = esercizi_df["esercizio"].apply(normalize)
    if "categoria" in esercizi_df.columns:
        esercizi_df["categoria_norm"] = esercizi_df["categoria"].apply(normalize)
    # --- merge su colonne normalizzate ---
    if 'esercizio' in test_df.columns and 'esercizio' in esercizi_df.columns and 'categoria' in esercizi_df.columns:
        test_df = test_df.merge(
            esercizi_df[['esercizio_norm', 'categoria', 'categoria_norm']],
            how='left',
            left_on='esercizio_norm',
            right_on='esercizio_norm'
        )
    else:
        st.error("⚠️ Errore: manca la colonna 'esercizio' o 'categoria' nei dati esercizi.")
        st.stop()

# (Qui continua tutta la tua logica: login, sidebar, pagine ecc… come negli esempi sopra)


    # 🔒 Salva nei session_state per uso cross-pagina
    st.session_state.test_df = test_df
    st.session_state.benchmark_df = benchmark_df
    st.session_state.esercizi_df = esercizi_df
    st.session_state.wod_df = wod_df
    st.session_state.utenti_df = utenti_df

#
# 🔥 Crea le credenziali
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=SCOPE
)

client = gspread.authorize(creds)

CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)
# --- PULSANTE REFRESH MANUALE (sidebar) ---
with st.sidebar:
    if st.button("🔄 Refresh Dati"):
        aggiorna_tutti_i_dati()
        st.success("✅ Dati aggiornati con successo!")

# --- BLOCCO LOGIN ---

if not st.session_state.logged_in:
    ruolo = st.selectbox("Seleziona il tuo ruolo", ["atleta", "coach"])
    nome = st.text_input("Inserisci il tuo nome")
    pin = st.text_input("Inserisci il tuo PIN", type="password")

    if st.button("Accedi"):
        nome_normalizzato = nome.strip().lower()
        pin_normalizzato = pin.strip()
        ruolo_normalizzato = ruolo.strip().lower()

        # 🔄 Carica utenti per il login
        utenti_df = carica_utenti()
        utenti_df["nome"] = utenti_df["nome"].astype(str).str.strip().str.lower()
        utenti_df["pin"] = utenti_df["pin"].astype(str).str.strip()
        utenti_df["ruolo"] = utenti_df["ruolo"].astype(str).str.strip().str.lower()

        utente_raw = utenti_df[
            (utenti_df["nome"] == nome_normalizzato) &
            (utenti_df["pin"] == pin_normalizzato) &
            (utenti_df["ruolo"] == ruolo_normalizzato)
        ]

        if not utente_raw.empty:
            st.session_state.logged_in = True
            st.session_state.user_pin = pin_normalizzato
            st.session_state.utente = utente_raw.squeeze().to_dict()
            st.session_state.utente["nome"] = st.session_state.utente["nome"].strip().title()

            # 🔄 Dopo il login: aggiorna tutti i dati
            aggiorna_tutti_i_dati()
            st.rerun()
        else:
            st.error("Nome, PIN o ruolo non validi. Riprova.")

    st.stop()

# --- Sidebar pagine SEMPRE visibile ---
utente = st.session_state.get("utente", None)
if utente is not None:
    if utente["ruolo"] == "coach":
        st.session_state["pagine_sidebar"] = [
            "🏠 Dashboard", "👤 Profilo Atleta", "📅 Calendario WOD", "➕ Inserisci nuovo test",
            "⚙️ Gestione esercizi", "📋 Storico Dati utenti", "📊 Bilanciamento Atleti",
            "➕ Aggiungi Utente", "⚙️ Gestione benchmark", "📊 Grafici", "📈 Storico Progressi",
            "📒 WOD", "🏆 Classifiche", "🏅 Classifica Workout" 
        ]
    else:
        st.session_state["pagine_sidebar"] = [
            "🏠 Dashboard", "➕ Inserisci nuovo test", "👤 Profilo Atleta", "📅 Calendario WOD",
            "📊 Grafici", "📜 Storico test", "📈 Storico Progressi", "📒 WOD"
        ]
else:
    st.session_state["pagine_sidebar"] = []
pagine_sidebar = st.session_state.get("pagine_sidebar", [])
if 'pagina_attiva' not in st.session_state or \
   (st.session_state.pagina_attiva not in pagine_sidebar and pagine_sidebar):
    if pagine_sidebar:
        st.session_state.pagina_attiva = pagine_sidebar[0]
    else:
        st.session_state.pagina_attiva = None

# ✅ Recupera i dati dal session_state (serve dopo ogni rerun o cambio pagina)
utenti_df = st.session_state.get("utenti_df", pd.DataFrame())
esercizi_df = st.session_state.get("esercizi_df", pd.DataFrame())
test_df = st.session_state.get("test_df", pd.DataFrame())
benchmark_df = st.session_state.get("benchmark_df", pd.DataFrame())
wod_df = st.session_state.get("wod_df", pd.DataFrame())

# ✅ Se l'utente è loggato ma i dati non sono ancora caricati
if st.session_state.logged_in:
    if utenti_df.empty or esercizi_df.empty or test_df.empty:
        aggiorna_tutti_i_dati()

# Tema chiaro/scuro
tema = st.sidebar.radio("🎨 Tema", ["Chiaro", "Scuro"])
if tema == "Scuro":
    st.markdown(
        """
        <style>
        body {
            background-color: #1e1e1e;
            color: #f0f0f0;
        }
        .stApp {
            background-color: #1e1e1e;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        body {
            background-color: #ffffff;
            color: #000000;
        }
        .stApp {
            background-color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

if st.session_state.refresh:
    st.session_state.refresh = False  # Reset the refresh flag
    st.query_params.update({"refresh": "true"})  # Simula un aggiornamento della pagina
if st.session_state.refresh:
    st.session_state.refresh = False
    st.query_params = {"refresh": "true"}

# Utente loggato
utente = st.session_state.get('utente', None)

if utente is not None and utente['ruolo'] == 'coach':
    st.success(f"Benvenuto, {utente['nome']} ({utente['ruolo']})")

# --- Sidebar navigazione ---
if 'pagina_attiva' not in st.session_state or \
   (st.session_state.pagina_attiva not in pagine_sidebar and pagine_sidebar):
    if pagine_sidebar:
        st.session_state.pagina_attiva = pagine_sidebar[0]
    else:
        st.session_state.pagina_attiva = None

with st.sidebar:
    st.markdown("""
        <style>
        div.stButton > button {
            width: 100% !important;
            margin-bottom: 0.25rem;
        }
        </style>
    """, unsafe_allow_html=True)
    for pagina_nome in pagine_sidebar:
        if st.button(pagina_nome, key=f"btn_{pagina_nome}"):
            st.session_state.pagina_attiva = pagina_nome
            st.rerun()

    if st.button("Esci", key="sidebar_logout_button"):
        logout()

pagina = st.session_state.pagina_attiva
# --- Rendering pagine ---
if pagina == "🏠 Dashboard":
    from PIL import Image
    import streamlit as st

    try:
        logo = Image.open("assets/logo.png")
        st.image(logo, width=120)
    except Exception as e:
        st.warning(f"Logo non caricato: {e}")


    st.markdown("<h1 style='color:#263959;'>Dashboard</h1>", unsafe_allow_html=True)
    st.write("Benvenuto nella Dashboard! Qui puoi visualizzare i tuoi progressi e accedere alle funzionalità principali.")
        # --- Ultimi test per esercizio, con livello e progress bar ---
    if utente and 'nome' in utente:
        atleta_test = test_df[test_df['nome'] == utente['nome']]
        latest_tests = atleta_test.sort_values("data").groupby("esercizio").tail(1)
        st.markdown("### 🏋️‍♂️ Ultimi test per esercizio")

        livello_mapping = {"Base": 1, "Principiante": 2, "Intermedio": 3, "Buono": 4, "Elite": 5}
        livello_colore = {
            "Base": "gray",
            "Principiante": "orange",
            "Intermedio": "dodgerblue",
            "Buono": "seagreen",
            "Elite": "gold"
        }

        if not latest_tests.empty:
            for _, row in latest_tests.iterrows():
                # Calcolo livello (devi adattare questo blocco al tuo schema benchmark!)
                benchmark = benchmark_df[
                    (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
                    (benchmark_df['genere'] == row['genere'])
                ]
                benchmark = benchmark.squeeze() if not benchmark.empty else None
                livello = "Non valutabile"

                if benchmark is not None:
                    tipo = benchmark.get('tipo_valore', None)
                    val = None
                    try:
                        if tipo == 'kg_rel' and pd.notnull(row.get('relativo', None)):
                            val = float(row['relativo'])
                        elif tipo == 'reps':
                            val = float(row['valore'])
                        elif tipo == 'tempo':
                            m, s = map(int, str(row['valore']).split(":"))
                            val = m * 60 + s
                            for key in ["base", "elite"]:
                                if ":" in str(benchmark[key]):
                                    m_b, s_b = map(int, str(benchmark[key]).split(":"))
                                    benchmark[key] = m_b * 60 + s_b
                                else:
                                    benchmark[key] = float(benchmark[key])
                        else:
                            val = float(row['valore'])

                        for livello_nome in reversed(['base', 'principiante', 'intermedio', 'buono', 'elite']):
                            soglia = benchmark.get(livello_nome, None)
                            if soglia is not None:
                                try:
                                    soglia = float(soglia)
                                except:
                                    pass
                                if tipo == 'tempo':
                                    if val is not None and val <= soglia:
                                        livello = livello_nome.capitalize()
                                        break
                                else:
                                    if val is not None and val >= soglia:
                                        livello = livello_nome.capitalize()
                                        break
                    except Exception:
                        livello = "Non valutabile"

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.metric(f"{row['esercizio']}", row['valore'])
                    st.markdown(
                        f"<span style='font-size:0.95em; color:{livello_colore.get(livello, 'black')};'>Livello: <b>{livello}</b></span>",
                        unsafe_allow_html=True
                    )
                    # Progress bar visiva
                    prog = livello_mapping.get(livello, 1) / 5 if livello in livello_mapping else 0.1
                    st.progress(prog)
                with col2:
                    if row['tipo_valore'] == 'kg_rel':
                        st.text(f"Forza relativa: {row.get('relativo', '-')}")
        else:
            st.info("Non ci sono ancora test inseriti per questo atleta.")
    else:
        st.warning("Devi essere loggato come atleta per visualizzare i tuoi progressi.")

if pagina == "📅 Calendario WOD":
    st.title("Calendario WOD")
    st.write("Visualizza e filtra il calendario degli allenamenti.")

    col1, col2 = st.columns([2, 1])
    with col1:
        filtro_nome = st.text_input("🔍 Cerca WOD per nome", "")
    with col2:
        data_filtro = st.date_input("📆 Filtra per data (facoltativo)")

    # Filtra il DataFrame
    filtered_df = wod_df.copy()
    if filtro_nome:
        filtered_df = filtered_df[filtered_df["nome"].str.contains(filtro_nome, case=False, na=False)]
    if data_filtro:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["data"]) == pd.to_datetime(data_filtro)]

    st.dataframe(filtered_df)

    # SOLO COACH: funzioni avanzate (export, aggiungi, modifica, elimina)
    if utente['ruolo'] == 'coach':

        # --- ESPORTA IN CSV ---
        st.markdown("#### Esporta calendario")
        if st.button("Esporta in CSV"):
            filtered_df.to_csv("Calendario_WOD.csv", index=False)
            st.success("File CSV esportato (scarica dalla sidebar a sinistra se sei su Streamlit Cloud)!")

        st.markdown("---")

        # --- AGGIUNGI NUOVO WOD ---
        st.subheader("➕ Aggiungi un nuovo WOD")
        with st.form("aggiungi_wod"):
            nome = st.text_input("Nome del WOD", key="wod_nome")
            descrizione = st.text_area("Descrizione", key="wod_descrizione")
            data_wod = st.date_input("Data", value=datetime.date.today(), key="wod_data")
            principiante = st.text_input("Versione Principiante", key="wod_principiante")
            intermedio = st.text_input("Versione Intermedio", key="wod_intermedio")
            avanzato = st.text_input("Versione Avanzato", key="wod_avanzato")
            esercizi = st.text_area("Esercizi (separati da virgola)", key="wod_esercizi")
            tipo_valore = st.selectbox("Tipo Valore", ["kg", "reps", "tempo", "calorie", "metri", "round", "altro"], key="wod_tipo_valore")
            titolo = st.text_input("Titolo/Obiettivo del WOD", key="wod_titolo")
            submit_wod = st.form_submit_button("Salva nuovo WOD")
            if submit_wod:
                nuovo_wod = {
                    "nome": nome,
                    "descrizione": descrizione,
                    "data": data_wod.strftime("%Y-%m-%d"),
                    "principiante": principiante,
                    "intermedio": intermedio,
                    "avanzato": avanzato,
                    "esercizi": esercizi,
                    "tipo_valore": tipo_valore,
                    "titolo": titolo
                }
                wod_df = pd.concat([wod_df, pd.DataFrame([nuovo_wod])], ignore_index=True)
                salva_su_google_sheets(wod_df, "wod", "wod")
                wod_df = carica_wod()
                st.success("Nuovo WOD aggiunto!")

        st.markdown("---")

        # --- MODIFICA WOD ---
        st.subheader("✏️ Modifica un WOD esistente")
        if not wod_df.empty:
            wod_df["info"] = wod_df.apply(lambda x: f"{x['data']} - {x['nome']}", axis=1)
            wod_da_modificare = st.selectbox("Seleziona un WOD da modificare", wod_df["info"].unique(), key="modifica_wod_select")
            if wod_da_modificare:
                idx = wod_df[wod_df["info"] == wod_da_modificare].index[0]
                row = wod_df.loc[idx]
                tipo_valori_possibili = ["kg", "reps", "tempo", "calorie", "metri", "round", "altro"]
                valore_attuale = str(row["tipo_valore"]) if str(row["tipo_valore"]) in tipo_valori_possibili else tipo_valori_possibili[0]
                with st.form("modifica_wod_form"):
                    nome_mod = st.text_input("Nome del WOD", value=row["nome"], key="mod_nome")
                    descrizione_mod = st.text_area("Descrizione", value=row["descrizione"], key="mod_descrizione")
                    data_mod = st.date_input("Data", value=pd.to_datetime(row["data"]), key="mod_data")
                    principiante_mod = st.text_input("Versione Principiante", value=row["principiante"], key="mod_principiante")
                    intermedio_mod = st.text_input("Versione Intermedio", value=row["intermedio"], key="mod_intermedio")
                    avanzato_mod = st.text_input("Versione Avanzato", value=row["avanzato"], key="mod_avanzato")
                    esercizi_mod = st.text_area("Esercizi (separati da virgola)", value=row["esercizi"], key="mod_esercizi")
                    tipo_valore_mod = st.selectbox(
                        "Tipo Valore", 
                        tipo_valori_possibili, 
                        index=tipo_valori_possibili.index(valore_attuale),
                        key="mod_tipo_valore"
                    )
                    titolo_mod = st.text_input("Titolo/Obiettivo del WOD", value=row["titolo"], key="mod_titolo")
                    submit_mod = st.form_submit_button("Salva modifiche")
                    if submit_mod:
                        wod_df.loc[idx, ["nome", "descrizione", "data", "principiante", "intermedio", "avanzato", "esercizi", "tipo_valore", "titolo"]] = [
                            nome_mod, descrizione_mod, data_mod.strftime("%Y-%m-%d"), principiante_mod, intermedio_mod, avanzato_mod, esercizi_mod, tipo_valore_mod, titolo_mod
                        ]
                        salva_su_google_sheets(wod_df, "wod", "wod")
                        wod_df = carica_wod()
                        st.success("WOD aggiornato con successo!")

        st.markdown("---")

        # --- ELIMINA WOD ---
        st.subheader("🗑️ Elimina un WOD")
        if not wod_df.empty:
            wod_df["info"] = wod_df.apply(lambda x: f"{x['data']} - {x['nome']}", axis=1)
            wod_da_eliminare = st.selectbox(
                "Seleziona un WOD da eliminare", wod_df["info"].unique(), key="elimina_wod_select"
            )
            if st.button("Elimina WOD"):
                # Trova indice da eliminare
                index_to_delete = wod_df[wod_df["info"] == wod_da_eliminare].index[0]
                # Elimina, resetta indice e riempi NaN
                wod_df = wod_df.drop(index=index_to_delete).reset_index(drop=True).fillna("")
                salva_su_google_sheets(wod_df, "wod", "wod")
                wod_df = carica_wod()
                st.success("WOD eliminato con successo!")
        else:
            st.info("Non ci sono WOD da eliminare.")

elif pagina == "➕ Inserisci nuovo test":
    st.subheader("➕ Inserisci un nuovo test")
    import datetime

    # --- Reset form se richiesto ---
    if st.session_state.get("reset_test_form", False):
        if "categoria" in esercizi_df.columns:
            st.session_state["categoria_input"] = esercizi_df["categoria"].unique()[0]
        st.session_state["esercizio_input"] = ""
        st.session_state["genere_input"] = "Maschio"
        st.session_state["valore_input"] = 0.0
        st.session_state["minuti_input"] = 0
        st.session_state["secondi_input"] = 0
        st.session_state["data_input"] = datetime.date.today()
        if utente and utente.get("ruolo") == "coach":
            st.session_state["nome_atleta_input"] = utenti_df[utenti_df["ruolo"] == "atleta"]["nome"].unique()[0]
        st.session_state["reset_test_form"] = False

    if "categoria_input" not in st.session_state:
        if "categoria" in esercizi_df.columns:
            st.session_state["categoria_input"] = esercizi_df["categoria"].unique()[0]
        else:
            st.error("❌ La colonna 'categoria' non è presente nel foglio esercizi.")
            st.stop()

    categorie_disponibili = esercizi_df["categoria"].unique()
    categoria_selezionata = st.selectbox("Seleziona categoria", categorie_disponibili, key="categoria_input")
    categoria_sel_norm = normalize(categoria_selezionata)
    esercizi_filtrati = esercizi_df[esercizi_df["categoria_norm"] == categoria_sel_norm]["esercizio"].unique()

    if "esercizio_input" not in st.session_state or st.session_state["esercizio_input"] not in esercizi_filtrati:
        st.session_state["esercizio_input"] = esercizi_filtrati[0] if len(esercizi_filtrati) > 0 else ""

    esercizio = st.selectbox("Esercizio", esercizi_filtrati, key="esercizio_input")
    esercizio_sel_norm = normalize(esercizio)

    if esercizio in esercizi_df["esercizio"].values:
        tipo_valore = esercizi_df[esercizi_df["esercizio"] == esercizio]["tipo_valore"].values[0]
    else:
        st.error("❌ Errore: esercizio non valido. Controlla il database esercizi.")
        st.stop()

    # Nome Atleta
    if utente and utente.get("ruolo") == "atleta":
        nome_atleta = utente["nome"]
        st.markdown(f"👤 **Atleta:** {nome_atleta}")
    else:
        if "nome_atleta_input" not in st.session_state:
            st.session_state["nome_atleta_input"] = utenti_df[utenti_df["ruolo"] == "atleta"]["nome"].unique()[0]
        nome_atleta = st.selectbox("Seleziona atleta", utenti_df[utenti_df["ruolo"] == "atleta"]["nome"].unique(), key="nome_atleta_input")

    # Genere
    genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"], key="genere_input")

    # Recupera il peso corporeo dal profilo atleta selezionato o chiedi di inserirlo
    default_peso = None
    if utente and utente.get("ruolo") == "atleta":
        try:
            default_peso = float(str(utente["peso_corporeo"]).replace(",", "."))
        except Exception:
            default_peso = 70.0
    else:
        riga_atleta = utenti_df[utenti_df["nome"] == nome_atleta]
        if not riga_atleta.empty:
            try:
                default_peso = float(str(riga_atleta.iloc[0]["peso_corporeo"]).replace(",", "."))
            except Exception:
                default_peso = 70.0
        else:
            default_peso = 70.0

    peso_corporeo = st.number_input(
        "Peso corporeo (kg)",
        min_value=20.0, max_value=250.0,
        value=float(default_peso) if default_peso else 70.0,
        step=0.1
    )

    # Valore inserito
    if tipo_valore == "tempo":
        minuti = st.number_input("Minuti", min_value=0, step=1, key="minuti_input")
        secondi = st.number_input("Secondi", min_value=0, max_value=59, step=1, key="secondi_input")
        valore = f"{int(minuti):02d}:{int(secondi):02d}"
    else:
        valore = st.number_input("Valore", step=1.0, key="valore_input")

    # Data test
    data_test = st.date_input("Data", key="data_input")

    # Calcolo valore relativo
    relativo = None
    if tipo_valore == "kg_rel" and peso_corporeo is not None and peso_corporeo > 0:
        try:
            relativo = round(float(valore) / peso_corporeo, 2)
        except:
            relativo = None

    if st.button("Salva test"):
        try:
            nuovo_test = {
                "nome": nome_atleta.strip().title(),
                "esercizio": esercizio,
                "valore": str(valore).replace(",", "."),
                "tipo_valore": tipo_valore,
                "peso_corporeo": peso_corporeo,
                "relativo": relativo,
                "data": data_test.strftime("%Y-%m-%d"),
                "genere": genere
            }
            test_df = carica_test()
            test_df = pd.concat([test_df, pd.DataFrame([nuovo_test])], ignore_index=True)
            salva_su_google_sheets(test_df, "test", "test")
            test_df = carica_test()
            test_df["nome"] = test_df["nome"].astype(str).str.strip().str.title()
            st.session_state["pagina_attiva"] = "➕ Inserisci nuovo test"
            st.success("✅ Test salvato correttamente!")
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Errore durante il salvataggio del test: {e}")

        st.session_state["pagina_attiva"] = "➕ Inserisci nuovo test"
        st.session_state["last_nome"] = nuovo_test["nome"]
        st.session_state["last_esercizio"] = nuovo_test["esercizio"]
        st.session_state["last_valore"] = nuovo_test["valore"]
        st.session_state["last_tipo_valore"] = nuovo_test["tipo_valore"]
        st.session_state["last_relativo"] = nuovo_test["relativo"]
        if tipo_valore == "tempo":
            st.session_state["last_minuti"] = int(minuti)
            st.session_state["last_secondi"] = int(secondi)
        st.session_state["reset_test_form"] = True
        st.rerun()


elif pagina == "👤 Profilo Atleta":
    st.title("Profilo Atleta")
    if utente is None:
        st.warning("Nessun utente loggato.")
        st.stop()

    # Trova la riga dell’utente nel DataFrame
    utente_row = utenti_df[utenti_df["nome"] == utente["nome"]].iloc[0] if utente["nome"] in utenti_df["nome"].values else None

    if utente_row is None:
        st.error("Dati atleta non trovati.")
        st.stop()

    st.markdown(f"## 👤 {utente_row['nome'].title()} ({utente_row['ruolo'].capitalize()})")

    import datetime
    eta = "-"
    if "data_nascita" in utente_row and pd.notnull(utente_row["data_nascita"]):
        try:
            data_nascita = pd.to_datetime(str(utente_row["data_nascita"]))
            oggi = datetime.datetime.now()
            eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
        except Exception:
            pass

    info_fields = [
        ("Data di nascita", "data_nascita"),
        ("Età", None),  # calcolata
        ("Genere", "genere"),
        ("Peso corporeo (kg)", "peso"),
        ("Altezza (cm)", "altezza"),
        ("Telefono", "telefono"),
        ("Email", "email"),
        ("Note", "note"),
        ("Obiettivi", "obiettivi"),
        ("Patologie", "patologie"),
        ("Scadenza certificato", "certificato_scadenza"),
        ("Ultima visita medica", "certificato_data"),
        ("Tag", "tag")
    ]

    # Questi può modificarli solo l'atleta (tutto il resto solo COACH)
    campi_modificabili_atleta = ["peso", "altezza", "note", "obiettivi"]

    if utente["ruolo"] == "coach":
        st.info("Come coach puoi modificare tutti i campi.")
    else:
        st.info("Puoi aggiornare solo alcuni dati del tuo profilo (peso, altezza, note, obiettivi).")

    with st.form("modifica_profilo"):
        nuovi_valori = {}
        for label, col in info_fields:
            if col is None:
                st.write(f"**{label}:** {eta}")
                continue
            valore_corrente = utente_row.get(col, "")
            # Coach: modifica tutto, atleta solo alcuni
            if utente["ruolo"] == "coach" or (utente["ruolo"] == "atleta" and col in campi_modificabili_atleta):
                nuovi_valori[col] = st.text_input(label, value=str(valore_corrente) if pd.notnull(valore_corrente) else "")
            else:
                st.write(f"**{label}:** {valore_corrente if pd.notnull(valore_corrente) else '-'}")
        salva = st.form_submit_button("💾 Salva modifiche")

    if salva:
        # Aggiorna solo i campi modificabili
        for col, nuovo in nuovi_valori.items():
            utenti_df.loc[utenti_df["nome"] == utente["nome"], col] = nuovo
        utenti_df = utenti_df.fillna("")  # ⚠️ Importantissimo per evitare errori Google Sheets con NaN/None!
        salva_su_google_sheets(utenti_df, "utenti", "utenti")
        st.success("Profilo aggiornato correttamente! 🚀")
        st.session_state["utenti_df"] = utenti_df
        st.rerun()

elif pagina == "⚙️ Gestione esercizi" and utente['ruolo'] == 'coach':
    st.title("Gestione Esercizi")
    # ...existing code...

elif pagina == "📋 Storico Dati utenti" and utente['ruolo'] == 'coach':
    st.title("Storico Dati utenti")
    # ...existing code...

if pagina == "📊 Bilanciamento Atleti" and utente['ruolo'] == 'coach':
    st.title("Bilanciamento Atleti")
    st.write("Bilancia i carichi di lavoro degli atleti.")

    # --- Funzione per il conteggio dei test per macro-area ---
    def conta_test_per_macroarea(test_df, esercizi_df):
        esercizio2cat = esercizi_df.set_index('esercizio')['categoria'].to_dict()
        test_df['macroarea'] = test_df['esercizio'].map(esercizio2cat)
        pivot = pd.pivot_table(
            test_df,
            index='nome',
            columns='macroarea',
            values='esercizio',
            aggfunc='count',
            fill_value=0
        )
        pivot['Totale test'] = pivot.sum(axis=1)
        return pivot

    # --- Calcola la tabella bilanciamento e mostra ---
    tabella_bilanciamento = conta_test_per_macroarea(test_df, esercizi_df)
    st.dataframe(tabella_bilanciamento, use_container_width=True)

    # Funzione per colorare la tabella in base al numero di test fatti
    def highlight_cells(val):
        if val == 0:
            color = '#ffcccc'  # rosso chiaro se zero test
        elif val < 3:
            color = '#fff5ba'  # giallo se pochi test
        else:
            color = '#ccffcc'  # verde se OK
        return f'background-color: {color}'

    pivot = conta_test_per_macroarea(test_df, esercizi_df)

    # Usa st.dataframe per l'interattività, st.write(pivot.style) per i colori
    st.write("### Tabella Bilanciamento Atleti (colorata):")
    st.dataframe(
        pivot.style.applymap(highlight_cells, subset=pivot.columns[:-1])  # solo le macroaree, non il totale
    )
    import io

    csv = pivot.to_csv().encode()
    st.download_button(
        label="📥 Scarica Tabella (CSV)",
        data=csv,
        file_name='bilanciamento_atleti.csv',
        mime='text/csv',
    )


elif pagina == "➕ Aggiungi Utente" and utente['ruolo'] == 'coach':
    st.title("Aggiungi Utente")

    with st.form("form_nuovo_utente"):
        nome = st.text_input("Nome e Cognome")
        pin = st.text_input("PIN (numerico o stringa)", max_chars=6)
        ruolo = st.selectbox("Ruolo", ["atleta", "coach"])
        data_nascita = st.date_input("Data di nascita")
        peso = st.number_input("Peso (kg)", min_value=20.0, max_value=250.0, step=0.1)
        altezza = st.number_input("Altezza (cm)", min_value=100.0, max_value=230.0, step=0.1)
        genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"])
        email = st.text_input("Email")
        telefono = st.text_input("Telefono")
        obiettivi = st.text_area("Obiettivi")
        note_mediche = st.text_area("Note mediche")
        data_iscrizione = st.date_input("Data iscrizione", value=pd.to_datetime("today"))
        scadenza_certificato = st.date_input("Scadenza certificato")
        foto_profilo = st.text_input("Link foto profilo (opzionale)")

        submitted = st.form_submit_button("Aggiungi utente")

        if submitted:
            try:
                utenti_df = carica_utenti()

                nuovo_utente = {
                    "nome": nome.strip().title(),
                    "pin": pin,
                    "ruolo": ruolo,
                    "data_nascita": data_nascita.strftime("%Y-%m-%d"),
                    "peso": peso,
                    "altezza": altezza,
                    "genere": genere,
                    "email": email,
                    "telefono": telefono,
                    "obiettivi": obiettivi,
                    "note_mediche": note_mediche,
                    "data_iscrizione": data_iscrizione.strftime("%Y-%m-%d"),
                    "scadenza_certificato": scadenza_certificato.strftime("%Y-%m-%d"),
                    "foto_profilo": foto_profilo
                }

                utenti_df = pd.concat([utenti_df, pd.DataFrame([nuovo_utente])], ignore_index=True)
                salva_su_google_sheets(utenti_df, "utenti", "utenti", append=False)  # append=False per riscrivere il foglio solo con il nuovo utente
                st.success(f"Utente '{nome}' aggiunto con successo!")
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {e}")


elif pagina == "⚙️ Gestione benchmark" and utente['ruolo'] == 'coach':
    st.title("Gestione Benchmark")
    # ...existing code...

    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    radar_labels = []
    radar_values = []

    # Prendi tutte le categorie uniche
    for categoria in esercizi_df["categoria"].unique():
        esercizi_categoria = esercizi_df[esercizi_df["categoria"] == categoria]["esercizio"].unique()
        test_categoria = test_df[test_df["esercizio"].isin(esercizi_categoria)].copy()
        livelli = []

        # Calcola il livello per OGNI test inserito da tutti
        for idx, row in test_categoria.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
                (benchmark_df['genere'] == row['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello = "base"  # default: base

            if benchmark is not None:
                tipo = benchmark['tipo_valore']
                val = None
                try:
                    if tipo == "kg_rel" and float(row["peso_corporeo"]) > 0:
                        val = float(row["valore"]) / float(row["peso_corporeo"])
                    elif tipo == "tempo":
                        m, s = map(int, str(row["valore"]).split(":"))
                        val = m * 60 + s
                        # Conversione anche dei benchmark in secondi
                        benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                            lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                        )
                    else:
                        val = float(row["valore"])
                except Exception:
                    val = None
                # Calcolo livello (tempo: <= soglia, altrimenti >= soglia)
                for livello_nome in reversed(list(livello_mapping.keys())):
                    soglia = benchmark[livello_nome]
                    try:
                        soglia = float(soglia) if tipo != "tempo" else int(soglia.split(":")[0]) * 60 + int(soglia.split(":")[1])
                    except Exception:
                        pass
                    if tipo == "tempo":
                        if val is not None and val <= soglia:
                            livello = livello_nome
                            break
                    else:
                        if val is not None and val >= soglia:
                            livello = livello_nome
                            break
            livelli.append(livello_mapping.get(livello, 1))  # se non trova, "base"=1

        # Media livelli per categoria
        if livelli:
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(sum(livelli)/len(livelli), 2))

    if radar_labels:
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_values,
            theta=radar_labels,
            fill='toself'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title="Livelli medi per categoria (tutti gli atleti)"
        )
        st.plotly_chart(fig, use_container_width=True)
        # Visualizza i valori numerici
        st.write("**Media livelli per categoria:**")
        for cat, val in zip(radar_labels, radar_values):
            st.write(f"- {cat}: {val}/5")
    else:
        st.info("Nessun dato disponibile per il grafico radar.")

elif pagina == "📈 Storico Progressi":
    st.title("📈 Storico Progressi")
    st.write("Qui puoi visualizzare lo storico dettagliato dei test inseriti, esportare i dati e vedere l’andamento nel tempo di ogni esercizio.")

    # Inizializza 'storico' come DataFrame vuoto per evitare errori
    storico = pd.DataFrame(columns=test_df.columns)

    # AREA ATLETA: mostra solo i test dell’atleta loggato
    if utente.get('ruolo') == 'atleta':
        storico = test_df[test_df['nome'] == utente.get('nome')].copy()
    
    # AREA COACH: filtro per atleta o tutti
    elif utente.get('ruolo') == 'coach':
        opzioni_atleti = ["Tutti"] + list(test_df["nome"].unique())
        atleta_sel = st.selectbox("Seleziona atleta", opzioni_atleti)
        if atleta_sel == "Tutti":
            storico = test_df.copy()
        else:
            storico = test_df[test_df["nome"] == atleta_sel].copy()
    else:
        st.warning("Ruolo utente non riconosciuto. Controlla la configurazione.")

    # Ordina per data discendente
    storico["data"] = pd.to_datetime(storico["data"], errors="coerce")
    storico = storico.sort_values("data", ascending=False)

    # Filtro per esercizio
    esercizi_disp = ["Tutti"] + list(storico["esercizio"].unique())
    esercizio_sel = st.selectbox("Seleziona esercizio", esercizi_disp)
    esercizio_sel_norm = normalize(esercizio_sel)
    if esercizio_sel != "Tutti":
        storico = storico[storico["esercizio_norm"] == esercizio_sel_norm]

    # --- Se la colonna 'livello' non esiste la aggiunge
    if "livello" not in storico.columns:
        storico["livello"] = "Non assegnato"

    # Visualizza la tabella solo se c’è almeno un dato
    if not storico.empty:
        st.dataframe(
            storico[["data", "nome", "esercizio", "valore", "livello"]].sort_values("data", ascending=False),
            hide_index=True,
            use_container_width=True
        )
        # Esporta CSV
        st.download_button(
            label="📥 Esporta storico in CSV",
            data=storico.to_csv(index=False).encode('utf-8'),
            file_name="storico_test.csv",
            mime="text/csv"
        )

        # GRAFICO ANDAMENTO nel tempo per l’esercizio selezionato
        if esercizio_sel != "Tutti":
            st.subheader(f"Andamento nel tempo su {esercizio_sel}")
            import plotly.graph_objects as go
            y_label = "Valore"
            x = storico["data"]

            # --- Conversione automatica valori (numeri o tempi mm:ss) ---
            def converti_valore(v):
                v = str(v).strip()
                if ":" in v:
                    try:
                        m, s = map(int, v.split(":"))
                        return m * 60 + s
                    except Exception as e:
                        st.warning(f"Errore conversione tempo '{v}': {e}")
                        return None
                try:
                    return float(v.replace(",", "."))
                except Exception as e:
                    st.warning(f"Errore conversione valore '{v}': {e}")
                    return None

            y = storico["valore"].apply(converti_valore)

            # DEBUG: mostra i valori convertiti (opzionale)
            # st.write("DEBUG - Valori convertiti:", y.tolist())

            # Controlla se ci sono valori validi
            if y.dropna().empty:
                st.info("Nessun dato valido per generare il grafico.")
            else:
                fig = go.Figure(go.Scatter(x=x, y=y, mode='lines+markers'))
                fig.update_layout(
                    xaxis_title="Data",
                    yaxis_title=y_label,
                    height=350,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun test disponibile per i filtri selezionati.")
elif pagina == "🏅 Classifica Workout":
    st.title("Classifica Workout")
    wod_list = esercizi_df[esercizi_df['tipo_valore'].isin(['tempo', 'reps', 'kg_rel'])]['esercizio'].unique()
    wod_selezionato = st.selectbox("Seleziona un WOD", wod_list)
    mostra_classifica_wod(test_df, wod_selezionato, esercizi_df)

if pagina == "📒 WOD":
    st.title("WOD")
    st.write("Gestisci e visualizza i WOD.")
    st.dataframe(wod_df)  # Mostra i dati dei WOD

elif pagina == "🏆 Classifiche" and utente['ruolo'] == 'coach':
    st.title("Classifiche")
    st.write("Visualizza le classifiche degli atleti, suddivise per categoria e tipo di valore.")

    categorie = esercizi_df['categoria'].unique()
    for cat in categorie:
        st.subheader(f"Categoria: {cat.capitalize()}")
        cat_norm = normalize(cat)
        esercizi_cat = esercizi_df[esercizi_df['categoria_norm'] == cat_norm]['esercizio_norm'].tolist()
        test_cat = test_df[test_df['esercizio_norm'].isin(esercizi_cat)]

        # --- CLASSIFICHE NUMERICHE (kg, reps, ecc) - best value ---
        num_tests = test_cat[test_cat['tipo_valore'] != 'tempo'].copy()
        num_tests['valore_num'] = pd.to_numeric(num_tests['valore'], errors='coerce')
        # Miglior valore per atleta per ogni esercizio
        best_num = num_tests.groupby(['nome', 'esercizio']).agg({'valore_num':'max'}).reset_index()
        # Somma o media dei migliori PR di ogni esercizio (qui somma)
        classifica_num = best_num.groupby('nome').agg({'valore_num':'sum'}).reset_index()
        classifica_num = classifica_num.sort_values("valore_num", ascending=False)
        if not classifica_num.empty and classifica_num['valore_num'].notna().any():
            st.write("Classifica test numerici (somma PR di tutti gli esercizi):")
            st.dataframe(classifica_num)
        else:
            st.info("Nessun test numerico per questa categoria.")

        # --- CLASSIFICHE TEMPO (minuti:secondi) - best time ---
        tempo_tests = test_cat[test_cat['tipo_valore'] == 'tempo'].copy()
        def tempo_to_sec(x):
            try:
                if pd.isna(x) or x == "":
                    return None
                m, s = map(int, str(x).split(":"))
                return m * 60 + s
            except Exception:
                return None
        tempo_tests['valore_sec'] = tempo_tests['valore'].apply(tempo_to_sec)
        # Best time (minimo) per ogni atleta/esercizio
        best_time = tempo_tests.groupby(['nome', 'esercizio']).agg({'valore_sec':'min'}).reset_index()
        # Somma i migliori tempi su tutti gli esercizi (qui più basso = meglio)
        classifica_tempo = best_time.groupby('nome').agg({'valore_sec':'sum'}).reset_index()
        classifica_tempo = classifica_tempo.sort_values("valore_sec")  # Più basso è meglio
        if not classifica_tempo.empty and classifica_tempo['valore_sec'].notna().any():
            st.write("Classifica test a tempo (somma best time di tutti gli esercizi, più basso è meglio):")
            st.dataframe(classifica_tempo)
        else:
            st.info("Nessun test a tempo per questa categoria.")

# --- Debug (facoltativo) ---
DEBUG = os.environ.get("DEBUG", "0") == "1"
if DEBUG:
    st.write(f"DEBUG: Pagina attiva: {pagina}")

# Definizione dei livelli di valutazione
livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}

# Inizializza punteggi per le macro aree
punteggi = {"forza": [], "ginnastica": [], "metabolico": []}

# ✅ Utility per ottenere il peso corporeo senza duplicazioni
def get_peso_corporeo(utente):
    if utente["ruolo"] == "atleta":
        return utente.get("peso", None)
    else:
        return st.number_input("Peso corporeo (kg)", min_value=30.0, max_value=200.0, step=0.1)

# ✅ Variabile globale per accedere facilmente all'utente
utente = st.session_state.get("utente", None)

if "last_nome" in st.session_state and "last_esercizio" in st.session_state:
    test_utente = test_df[
        (test_df["nome"] == st.session_state["last_nome"]) &
        (test_df["esercizio"] == st.session_state["last_esercizio"])
    ]

    if not test_utente.empty:
        test_utente["data"] = pd.to_datetime(test_utente["data"])
        test_utente = test_utente.sort_values("data")

        tipo_valore = st.session_state["last_tipo_valore"]
        esercizio = st.session_state["last_esercizio"]
        genere = st.session_state.get("genere_input", "Maschio")  # fallback

        if tipo_valore == "tempo":
            val_attuale = st.session_state["last_minuti"] * 60 + st.session_state["last_secondi"]
        elif tipo_valore == "kg_rel":
            val_attuale = st.session_state["last_relativo"]
        else:
            val_attuale = float(st.session_state["last_valore"])

        # Recupera benchmark
        benchmark = benchmark_df[
            (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
            (benchmark_df['genere'] == row['genere'])
        ]

        if benchmark.empty:
            st.warning("⚠️ Nessun benchmark trovato per l'esercizio o il genere specificato. Verifica i dati del benchmark.")
            livello_raggiunto = "Non valutabile"
        else:
            livello_raggiunto = "Non valutabile"
            for livello_nome in reversed(list(livelli_val.keys())):
                soglia = benchmark[livello_nome]
                try:
                    soglia = float(soglia) if tipo_valore != "tempo" else int(soglia.split(":")[0]) * 60 + int(soglia.split(":")[1])
                except Exception:
                    continue
                if tipo_valore == "tempo":
                    if val_attuale is not None and val_attuale <= soglia:
                        livello_raggiunto = livello_nome.capitalize()
                        break
                else:
                    if val_attuale is not None and val_attuale >= soglia:
                        livello_raggiunto = livello_nome.capitalize()
                        break

            if livello_raggiunto == "Non valutabile":
                st.warning("⚠️ I dati del benchmark sono incompleti o il valore attuale non rientra nelle soglie definite.")

        st.success(f"✅ Hai raggiunto il livello: **{livello_raggiunto.upper()}** 💪")

        # 🔁 Confronto con test precedente
        if len(test_utente) > 1:
            test_prec = test_utente.iloc[-2]  # penultimo test
            if tipo_valore == "tempo":
                try:
                    m, s = map(int, str(test_prec["valore"]).split(":"))
                    val_prec = m * 60 + s
                    diff = val_prec - val_attuale
                    verso = "migliorato" if diff > 0 else "peggiorato"
                    st.info(f"⏱️ Hai {verso} di **{abs(diff)} secondi** rispetto al test del {test_prec['data'].date()}.")
                except Exception:
                    st.warning("⚠️ Errore nel confronto con il test precedente.")
            else:
                try:
                    val_prec = float(test_prec["relativo"]) if tipo_valore == "kg_rel" else float(test_prec["valore"])
                    diff = round(val_attuale - val_prec, 2)
                    verso = "migliorato" if diff > 0 else "peggiorato"
                    st.info(f"📊 Hai {verso} di **{abs(diff)}** rispetto al test del {test_prec['data'].date()}.")
                except Exception:
                    st.warning("⚠️ Errore nel confronto con il test precedente.")

    # Mostra l'expander solo dopo il salvataggio
    if st.session_state.get('show_expander', False):
        with st.expander("📊 Analisi del test appena inserito", expanded=True):
            # 1. Calcola livello raggiunto
            benchmark = benchmark_df[
                (benchmark_df['esercizio'].astype(str).str.strip() == str(esercizio).strip()) &
                (benchmark_df['genere'].astype(str).str.strip() == str(genere).strip())
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None  # Corretto il SyntaxError
            livello_raggiunto = "Non valutabile"
            livello_num = 0
            prossimo_livello = None
            valore_target = None
            livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
            livelli_ordine = list(livelli_val.keys())
            val = None
            if benchmark is not None and isinstance(benchmark, pd.Series):
                tipo = benchmark['tipo_valore']
                try:
                    peso_corporeo = float(peso_corporeo)
                except Exception:
                    peso_corporeo = None
                if tipo == 'kg_rel' and peso_corporeo is not None and peso_corporeo != 0:
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

                # Trova livello raggiunto
                livello_nome_trovato = None
                if tipo == 'tempo':
                    for livello_nome in reversed(livelli_ordine):
                        soglia = benchmark[livello_nome]
                        if isinstance(soglia, str) and ":" in soglia:
                            m, s = map(int, soglia.split(":"))
                            soglia = m * 60 + s
                        else:
                            soglia = float(soglia)
                        if val is not None and val <= soglia:
                            livello_nome_trovato = livello_nome.capitalize()
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
                            livello_nome_trovato = livello_nome.capitalize()
                            livello_num = livelli_val[livello_nome]
                            break
                livello_raggiunto = livello_nome_trovato if livello_nome_trovato else "Non valutabile"

                # 2. Consiglia prossimo livello e valore target
                if livello_nome_trovato and livello_nome_trovato.lower() != "elite":
                    idx = livelli_ordine.index(livello_nome_trovato.lower())
                    if idx < len(livelli_ordine) - 1:
                        prossimo_livello = livelli_ordine[idx + 1].capitalize()
                        valore_target = benchmark[livelli_ordine[idx + 1]]
                        if tipo == 'tempo' and isinstance(valore_target, (int, float)):
                            minuti = int(valore_target) // 60
                            secondi = int(valore_target) % 60
                            valore_target = f"{minuti:02d}:{secondi:02d}"
                elif livello_nome_trovato and livello_nome_trovato.lower() == "elite":
                    prossimo_livello = None
                    valore_target = None

            # Mostra risultati analisi post-salvataggio
            st.info(f"**Livello raggiunto:** {livello_raggiunto}")
            if prossimo_livello and valore_target is not None:
                st.info(f"🎯 Obiettivo prossimo livello: **{prossimo_livello}** (target: {valore_target})")
            elif livello_raggiunto == "Elite":
                st.success("🏆 Complimenti! Hai raggiunto il livello massimo (Elite).")

            # 3. Suggerisci quando ripetere il test (6 settimane)
            data_prossimo_test = data_test + datetime.timedelta(weeks=6)
            st.info(f"🔁 Ripeti questo test il: **{data_prossimo_test.strftime('%Y-%m-%d')}**")

            # 4. Calcola miglioramento percentuale rispetto al test precedente
            storico = test_df[
                (test_df['nome'] == nome_atleta) &
                (test_df['esercizio'] == esercizio) &
                (test_df['data'] < data_test.strftime("%Y-%m-%d"))
            ].sort_values("data", ascending=False)
            miglioramento = None
            badge = False
            if not storico.empty:
                row_prec = storico.iloc[0]
                # Calcola valore precedente
                val_prec = None
                if tipo_valore == 'kg_rel' and float(row_prec['peso_corporeo']) > 0:
                    val_prec = float(row_prec['valore']) / float(row_prec['peso_corporeo'])
                elif tipo == 'reps' or tipo == 'valore':
                    val_prec = float(row_prec['valore'])
                elif tipo == 'tempo':
                    m, s = map(int, str(row_prec['valore']).split(":"))
                    val_prec = m * 60 + s
                else:
                    val_prec = float(row_prec['valore'])

                # Calcola miglioramento percentuale (attenzione: per il tempo, meno è meglio)
                if val is not None and val_prec is not None:
                    if tipo_valore == 'tempo':
                        miglioramento = (val_prec - val) / val_prec * 100 if val_prec > 0 else None
                    else:
                        miglioramento = (val - val_prec) / val_prec * 100 if val_prec > 0 else None
                    if miglioramento is not None:
                        st.info(f"📈 Miglioramento rispetto al test precedente: **{miglioramento:+.2f}%**")

                # 5. Badge se migliora di livello
                livello_prec = None
                if benchmark is not None and isinstance(benchmark, pd.Series):
                    # ...existing code for livello_prec_nome...
                    if livello_nome_trovato and livello_prec_nome:
                        if livelli_val[livello_nome_trovato.lower()] > livelli_val[livello_prec_nome]:
                            badge = True
                if badge:
                    st.success("🎉 **Complimenti! Hai sbloccato un nuovo livello!**")

            # Alla fine, resetta il flag per non mostrare l'expander al prossimo caricamento
            st.session_state['show_expander'] = False

    # Extra: Tabella riassuntiva e mini-grafico
    st.markdown("### 📊 Storico recente")
    recenti = atleta_test.sort_values("data", ascending=False).head(5)
    st.dataframe(recenti[["data", "esercizio", "valore"]], hide_index=True, use_container_width=True)

    # Mini-grafico andamento ultimi test (solo valori numerici)
    import plotly.graph_objects as go
    def conv_num(x):
        try: return float(str(x).replace(",", "."))
        except: return None
    recenti["valore_num"] = recenti["valore"].apply(conv_num)
    valori_plot = recenti[recenti["valore_num"].notnull()]
    if not valori_plot.empty:
        fig = go.Figure(go.Scatter(
            x=valori_plot["data"].astype(str),
            y=valori_plot["valore_num"],
            mode='lines+markers',
            text=valori_plot["esercizio"]
        ))
        fig.update_layout(
            title="Andamento ultimi test (valore numerico)",
            xaxis_title="Data",
            yaxis_title="Valore",
            height=250,
            margin=dict(l=30, r=30, t=40, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)

# Pagina: Storico Dati
elif pagina == "📜 Storico test":
    st.subheader("📜 Storico Dati")
    atleta_test = test_df[test_df['nome'] == utente['nome']]

    if atleta_test.empty:
        st.info("Non ci sono test disponibili per questo utente.")
    else:
                # Calcola dinamicamente il livello per ogni esercizio
        livelli = []
        for _, row in atleta_test.iterrows():
            benchmark = benchmark_df[benchmark_df['esercizio'] == row['esercizio']]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello = "Non valutabile"

            if benchmark is not None and isinstance(benchmark, pd.Series):
                tipo = benchmark['tipo_valore']
                try:
                    peso_corp = float(row['peso_corporeo'])
                except Exception:
                    peso_corp = None

                val = None
                if tipo == 'kg_rel':
                    if peso_corp is not None and not pd.isna(peso_corp) and peso_corp != 0:
                        val = float(row['valore']) / peso_corp
                elif tipo in ['reps', 'valore']:
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None
                elif tipo == 'tempo':
                    try:
                        m, s = map(int, str(row['valore']).split(":"))
                        val = m * 60 + s
                    except Exception:
                        val = None
                else:
                    try:
                        val = float(row['valore'])
                    except Exception:
                        val = None

                # Valuta il livello
                if tipo == 'tempo':
                    for livello_nome in reversed(list(livelli_val.keys())):
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
                            livello = livello_nome.capitalize()
                            break
                else:
                    for livello_nome in reversed(list(livelli_val.keys())):
                        soglia = benchmark[livello_nome]
                        try:
                            soglia = float(soglia)
                        except Exception:
                            continue
                        if val is not None and val >= soglia:
                            livello = livello_nome.capitalize()
                            break

            livelli.append(livello)

        # Aggiungi i livelli calcolati allo storico
        atleta_test['livello'] = livelli
        st.dataframe(atleta_test)

        # Pulsante per eliminare un test
        atleta_test['info'] = atleta_test.apply(
            lambda row: f"Esercizio: {row['esercizio']} | Data: {row['data']} | Valore: {row['valore']} | Tipo: {row['tipo_valore']}", axis=1
        )
        test_da_eliminare = st.selectbox("Seleziona un test da eliminare", atleta_test['info'])

        if st.button("Elimina test"):
            # Ottieni indice nel test_df originale
            index_to_delete = test_df[
                (test_df["nome"] == utente["nome"]) &
                (test_df["esercizio"] == atleta_test[atleta_test['info'] == test_da_eliminare]["esercizio"].values[0]) &
                (test_df["data"] == atleta_test[atleta_test['info'] == test_da_eliminare]["data"].values[0])
            ].index

            if not index_to_delete.empty:
                test_df = test_df.drop(index=index_to_delete)
                salva_su_google_sheets(test_df, "test", "test")  # 🔥 Salva davvero online
                st.success("✅ Test eliminato con successo!")
                st.rerun()  # 🔁 Ricarica subito la pagina
            else:
                st.error("⚠️ Errore: test non trovato.")

elif pagina == "📊 Grafici":
    import plotly.graph_objects as go
    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    livelli_val = livello_mapping

    if utente['ruolo'] == 'coach':
        # ----- GRAFICI COACH -----
        st.subheader("📊 Stato esercizi (tutti o singolo atleta)")

        # Scegli atleta: "Tutti gli atleti" o uno specifico
        opzioni_utenti = ["Tutti gli atleti"] + list(utenti_df[utenti_df['ruolo'] == 'atleta']['nome'].unique())
        atleta_selezionato = st.selectbox("Seleziona atleta", opzioni_utenti)

        # Scegli categoria/esercizio
        categorie_disponibili = esercizi_df["categoria"].unique()
        categoria_selezionata = st.selectbox("Seleziona categoria", categorie_disponibili)
        categoria_sel_norm = normalize(categoria_selezionata)
        esercizi_filtrati = esercizi_df[esercizi_df["categoria_norm"] == categoria_sel_norm]["esercizio"].unique()
        esercizio_selezionato = st.selectbox("Seleziona esercizio", esercizi_filtrati)
        esercizio_sel_norm = normalize(esercizio_selezionato)   # <--- QUESTA RIGA!

        # Filtro i test in base a chi voglio vedere
        if atleta_selezionato == "Tutti gli atleti":
            test_selezionati = test_df[test_df['esercizio_norm'] == esercizio_sel_norm]
        else:
            test_selezionati = test_df[
                (test_df['esercizio_norm'] == esercizio_sel_norm) &
                (test_df['nome'] == atleta_selezionato)
            ]


        risultati = []
        nomi_barre = []

        for _, row in test_selezionati.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio_norm'] == row['esercizio_norm']) &
                (benchmark_df['genere'] == row['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello = "base"
            if benchmark is not None:
                tipo = benchmark['tipo_valore']
                val = None
                try:
                    if tipo == "kg_rel" and float(row["peso_corporeo"]) > 0:
                        val = float(row["valore"]) / float(row["peso_corporeo"])
                    elif tipo == "tempo":
                        m, s = map(int, str(row["valore"]).split(":"))
                        val = m * 60 + s
                        benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                            lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                        )
                    else:
                        val = float(row["valore"])
                except Exception:
                    val = None

                for livello_nome in reversed(list(livello_mapping.keys())):
                    soglia = benchmark[livello_nome]
                    try:
                        soglia = float(soglia) if tipo != "tempo" else int(soglia.split(":")[0]) * 60 + int(soglia.split(":")[1]) if ":" in str(soglia) else float(soglia)
                    except Exception:
                        pass
                    if tipo == "tempo":
                        if val is not None and val <= soglia:
                            livello = livello_nome
                            break
                    else:
                        if val is not None and val >= soglia:
                            livello = livello_nome
                            break
            risultati.append(livello_mapping.get(livello, 1))
            nomi_barre.append(row["nome"] if atleta_selezionato == "Tutti gli atleti" else str(row["data"]))

        if risultati:
            fig = go.Figure(go.Bar(
                x=risultati,
                y=nomi_barre,
                orientation='h',
                marker=dict(
                    color='rgba(40, 167, 69, 0.85)',
                    line=dict(color='rgba(40, 167, 69, 1.0)', width=3)
                ),
                text=[list(livello_mapping.keys())[r-1].capitalize() for r in risultati],
                textposition='outside'
            ))
            fig.update_layout(
                xaxis=dict(range=[0.5, 5.5], tickvals=[1,2,3,4,5], ticktext=list(livello_mapping.keys()), title="Livello"),
                yaxis=dict(title="Atleta" if atleta_selezionato == "Tutti gli atleti" else "Data"),
                title=f"Livello raggiunto - {esercizio_selezionato}",
                bargap=0.5,
                height=60 + 38 * len(nomi_barre)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Non ci sono dati sufficienti per mostrare il grafico.")

        # ------- Grafico Radar COACH: scegli un atleta --------
        st.markdown("---")
        st.subheader("📊 Profilo Radar (per atleta)")
        atleta_radar = st.selectbox("Seleziona atleta per Radar", utenti_df[utenti_df['ruolo'] == 'atleta']['nome'].unique(), key="coach_radar_atleta")
        
        tutte_categorie = esercizi_df["categoria"].unique()
        radar_labels = []
        radar_values = []
        for categoria in tutte_categorie:
            cat_norm = normalize(categoria)
            esercizi_cat = esercizi_df[esercizi_df['categoria_norm'] == cat_norm]['esercizio_norm']
            test_cat = test_df[(test_df['nome'] == atleta_radar) & (test_df['esercizio_norm'].isin(esercizi_cat))]
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
                        peso_corporeo = float(row['peso_corporeo'])
                    except Exception:
                        peso_corporeo = None
                    if tipo == 'kg_rel' and peso_corporeo is not None and peso_corporeo != 0:
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
                title=f"Profilo Radar: {atleta_radar}",
                margin=dict(l=40, r=40, t=60, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
            for label, value in zip(radar_labels, radar_values):
                st.write(f"**{label}**: {value}/5")
        else:
            st.info("Non ci sono dati sufficienti per generare il grafico radar.")

    else:
        # ----- GRAFICI ATLETA -----
        st.subheader("📊 Risultati esercizi: Stato & Macro-Aree")

        macroaree = esercizi_df["categoria"].unique()
        macroarea_sel = st.selectbox("Seleziona macro-area", macroaree)
        esercizi_macro = esercizi_df[esercizi_df["categoria"] == macroarea_sel]["esercizio"].unique()
        esercizio_sel = st.selectbox("Seleziona esercizio", esercizi_macro)

        # --- Funzione normalizzazione esercizio ---
        def normalize(s):
            return str(s).strip().lower().replace(" ", "").replace("-", "")

        # Assicurati di avere colonne normalizzate
        if "esercizio_norm" not in test_df.columns:
            test_df['esercizio_norm'] = test_df['esercizio'].apply(normalize)
        if "esercizio_norm" not in benchmark_df.columns:
            benchmark_df['esercizio_norm'] = benchmark_df['esercizio'].apply(normalize)
        if "categoria_norm" not in esercizi_df.columns:
            esercizi_df['categoria_norm'] = esercizi_df['categoria'].apply(normalize)

        # Dopo aver scelto macroarea e esercizio_sel...
        esercizio_sel_norm = esercizio_sel.strip().lower().replace(" ", "")
        test_esercizio = test_df[
            (test_df['nome'] == utente['nome']) &
            (test_df['esercizio_norm'] == esercizio_sel_norm)
        ]

        livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
        livello = "Non valutabile"    # <--- qui inizializzo
        livello_num = 1               # Default base

        if not test_esercizio.empty:
            row = test_esercizio.sort_values("data").iloc[-1]
            benchmark = benchmark_df[
                (benchmark_df['esercizio_norm'] == esercizio_sel_norm) &
                (benchmark_df['genere'] == utente['genere'])
            ]
            if not benchmark.empty:
                benchmark = benchmark.iloc[0]
                tipo = benchmark['tipo_valore']
                val = None
                try:
                    if tipo == "kg_rel" and float(row["peso_corporeo"]) > 0:
                        val = float(row["valore"]) / float(row["peso_corporeo"])
                    elif tipo == "tempo":
                        m, s = map(int, str(row["valore"]).split(":"))
                        val = m * 60 + s
                        for key in ["base", "principiante", "intermedio", "buono", "elite"]:
                            if ":" in str(benchmark[key]):
                                m_b, s_b = map(int, str(benchmark[key]).split(":"))
                                benchmark[key] = m_b * 60 + s_b
                            else:
                                benchmark[key] = float(benchmark[key])
                    else:
                        val = float(row["valore"])
                except Exception:
                    val = None

                for livello_nome in reversed(list(livello_mapping.keys())):
                    soglia = benchmark[livello_nome]
                    try:
                        soglia = float(soglia)
                    except Exception:
                        pass
                    if tipo == "tempo":
                        if val is not None and val <= soglia:
                            livello = livello_nome.capitalize()
                            livello_num = livello_mapping[livello_nome]
                            break
                    else:
                        if val is not None and val >= soglia:
                            livello = livello_nome.capitalize()
                            livello_num = livello_mapping[livello_nome]
                            break

        # --- GRAFICO NEON (barra crescente, spessa e colorata in base al livello) ---
        import plotly.graph_objects as go
        colori_gradiente = [
            "#ff3333",   # base
            "#ff9900",   # principiante
            "#ffee00",   # intermedio
            "#99ff33",   # buono
            "#33cc33"    # elite
        ]
        colore_barra = colori_gradiente[livello_num - 1]

        fig = go.Figure(go.Bar(
            x=[livello_num],
            y=[""],  # o ["Livello"]
            orientation='h',
            marker=dict(
                color=colore_barra,
                line=dict(color="black", width=6)
            ),
            width=[0.7],  # più spessa!
            text=[livello],
            textposition="outside"
        ))
        fig.update_layout(
            xaxis=dict(
                range=[1, 5],
                tickvals=[1, 2, 3, 4, 5],
                ticktext=["Base", "Principiante", "Intermedio", "Buono", "Elite"],
                showgrid=False
            ),
            yaxis=dict(showticklabels=False, showgrid=False),
            plot_bgcolor='rgba(0,0,0,0)',
            height=150,
            margin=dict(l=30, r=30, t=20, b=20),
            showlegend=False,
            bargap=0.18
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<div style='text-align:center;font-size:1.3em;'><b>Livello attuale:</b> {livello}</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="padding:0.7em 1em 0.7em 1em; background:#f7fafc; border-radius:10px; font-size:1.05em;">
            <b>Cos'è questo grafico radar?</b><br>
            Questo grafico mostra il tuo livello medio raggiunto in ciascuna macro-area (Forza, Ginnastica, Metabolico, Mobilità, ecc.) sulla base degli esercizi che hai testato.<br>
            Ogni area va da 1 (Principiante/Base) a 5 (Elite). Più il riempimento si avvicina al bordo, più sei vicino al massimo livello per quella categoria!
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 📊 Profilo Radar: Macro-Aree (Forza, Ginnastica, Metabolico, Mobilità)")

        radar_labels = []
        radar_values = []
        macroaree = esercizi_df["categoria"].unique()
        for categoria in macroaree:
            cat_norm = normalize(categoria)
            esercizi_cat = esercizi_df[esercizi_df['categoria_norm'] == cat_norm]['esercizio_norm']
            test_cat = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio_norm'].isin(esercizi_cat))]
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
                        peso_corporeo = float(row['peso_corporeo'])
                    except Exception:
                        peso_corporeo = None
                    if tipo == 'kg_rel' and peso_corporeo is not None and peso_corporeo != 0:
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
                title="Profilo Radar per Macro-Categoria",
                margin=dict(l=40, r=40, t=60, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
            # Mostra valori numerici accanto alle etichette
            for label, value in zip(radar_labels, radar_values):
                st.write(f"**{label}**: {value}/5")
        else:
            st.info("Non ci sono dati sufficienti per generare il grafico radar.")
