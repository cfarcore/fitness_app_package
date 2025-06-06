import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
import os
import time
import pickle
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="Fitness Gauge", layout="wide")

if "refresh" not in st.session_state:
    st.session_state.refresh = False
if "utente" not in st.session_state:
    st.session_state.utente = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 🔥 Leggi le credenziali da st.secrets
SERVICE_ACCOUNT_INFO = st.secrets["SERVICE_ACCOUNT_JSON"]

# 🔥 Crea le credenziali
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=SCOPE
)

client = gspread.authorize(creds)

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
        sheet = client.open(sheet_name).worksheet(sheet_name)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        with open(cache_file, "wb") as f:
            pickle.dump(df, f)

        return df

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Il foglio '{sheet_name}' non è stato trovato. Verifica che il nome sia corretto.")
        st.stop()

# Carica i dati da Google Sheets
utenti_df = carica_da_google_sheets("utenti", cache_duration=0)
esercizi_df = carica_da_google_sheets("esercizi")
test_df = carica_da_google_sheets("test")
benchmark_df = carica_da_google_sheets("benchmark")
wod_df = carica_da_google_sheets("wod")


# Carica i dati da Google Sheets
utenti_df = carica_da_google_sheets("utenti", cache_duration=0)
esercizi_df = carica_da_google_sheets("esercizi")
test_df = carica_da_google_sheets("test")  # Corretto caricamento dei dati dei test
benchmark_df = carica_da_google_sheets("benchmark")
wod_df = carica_da_google_sheets("wod")

# Login
if not st.session_state.logged_in:
    ruolo = st.selectbox("Seleziona il tuo ruolo", ["atleta", "coach"])  # Aggiunto per scegliere il ruolo
    nome = st.text_input("Inserisci il tuo nome")
    pin = st.text_input("Inserisci il tuo PIN", type="password")
    if st.button("Accedi"):
        # Normalizza i dati per il confronto
        utenti_df["nome"] = utenti_df["nome"].astype(str).str.strip()
        utenti_df["pin"] = utenti_df["pin"].astype(str).str.strip()
        utenti_df["ruolo"] = utenti_df["ruolo"].astype(str).str.strip()
        nome_normalizzato = nome.strip()
        pin_normalizzato = pin.strip()

        # Filtra l'utente in base al ruolo selezionato
        utente_raw = utenti_df[
            (utenti_df["nome"] == nome_normalizzato) &
            (utenti_df["pin"] == pin_normalizzato) &
            (utenti_df["ruolo"] == ruolo)
        ]
        if not utente_raw.empty:
            st.session_state.logged_in = True
            st.session_state.user_pin = pin_normalizzato
            st.session_state.utente = utente_raw.squeeze().to_dict()  # Updated assignment
            st.session_state.refresh = True  # Imposta il refresh
        else:
            st.error("Nome, PIN o ruolo non validi. Riprova.")
    st.stop()

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
# Gestione del refresh della pagina
if st.session_state.refresh:
    st.session_state.refresh = False
    st.query_params = {"refresh": "true"}  # Simula un aggiornamento della pagina

# Utente loggato
utente = st.session_state.utente

if utente is not None and utente['ruolo'] == 'coach':
    st.success(f"Benvenuto, {utente['nome']} ({utente['ruolo']})")
else:
    st.warning("Nessun utente selezionato.")

# Barra laterale per navigazione con pulsanti
if is_utente_valido():
    if utente['ruolo'] == 'coach':
        pagine_sidebar = [
            "🏠 Dashboard",  # Nuova home
            "📅 Calendario WOD",
            "➕ Inserisci nuovo test",
            "👤 Profilo Atleta",
            "⚙️ Gestione esercizi",
            "📋 Storico Dati utenti",
            "📊 Bilanciamento Atleti",
            "➕ Aggiungi Utente",
            "⚙️ Gestione benchmark",
            "📊 Grafici",
            "📈 Storico Progressi",
            "📒 WOD",
            "🏆 Classifiche"
        ]
    else:
        pagine_sidebar = [
            "🏠 Dashboard",  # Nuova home
            "📅 Calendario WOD",
            "➕ Inserisci nuovo test",
            "👤 Profilo Atleta",
            "📊 Grafici",
            "📜 Storico test",
            "📈 Storico Progressi",
            "📒 WOD",
        ]


# Inizializza la pagina attiva se non esiste
if 'pagina_attiva' not in st.session_state:
    st.session_state.pagina_attiva = pagine_sidebar[0]

with st.sidebar:
    # CSS per rendere i pulsanti sidebar della stessa dimensione
    st.markdown("""
        <style>
        div.stButton > button {
            width: 100% !important;
            min-width: 120px;
            margin-bottom: 0.25rem;
        }
        </style>
    """, unsafe_allow_html=True)
    for pagina_nome in pagine_sidebar:
        if st.button(pagina_nome, key=f"btn_{pagina_nome}"):
            st.session_state.pagina_attiva = pagina_nome  # Aggiorna correttamente la pagina attiva

    # Pulsante per uscire
    if st.button("Esci", key="sidebar_logout_button"):
        logout()

# Assicurati che la pagina attiva venga caricata
pagina = st.session_state.get('pagina_attiva', pagine_sidebar[0])

# Debug: Mostra la pagina attiva per verificare (solo se in modalità debug)
import os
DEBUG = os.environ.get("DEBUG", "0") == "1"
if DEBUG:
    st.write(f"DEBUG: Pagina attiva: {pagina}")

# Definizione dei livelli di valutazione
livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}

# Inizializza punteggi per le macro aree
punteggi = {"forza": [], "ginnastica": [], "metabolico": []}

# Utility per ottenere il peso corporeo senza duplicazioni
def get_peso_corporeo(utente):
    if utente["ruolo"] == "atleta":
        return utente.get("peso", None)
    else:
        return st.number_input("Peso corporeo (kg)", min_value=30.0, max_value=200.0, step=0.1)

# Funzione per salvare i dati su Google Sheets
def salva_su_google_sheets(df, file_name, sheet_name):
    """
    Salva i dati in un foglio Google Sheets specifico.
    :param df: DataFrame da salvare.
    :param file_name: Nome del file Google Sheets.
    :param sheet_name: Nome del foglio all’interno del file.
    """
    sh = client.open(file_name)
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# Funzione per scrivere su Google Sheets
def scrivi_su_google_sheet(sheet_name, dataframe):
    credentials = Credentials.from_service_account_file(
        "service_account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_ID)
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
    st.success(f"Dati esportati correttamente sul foglio '{sheet_name}'!")

# Variabile globale per accedere facilmente all'utente
utente = st.session_state.get("utente", None)

# Pagina: Inserisci nuovo test
if pagina == "➕ Inserisci nuovo test":
    st.subheader("➕ Inserisci un nuovo test")
    # Selezione categoria prima di esercizio
    categorie_disponibili = esercizi_df["categoria"].unique()
    categoria_selezionata = st.selectbox("Seleziona categoria", categorie_disponibili)
    esercizi_filtrati = esercizi_df[esercizi_df["categoria"] == categoria_selezionata]["esercizio"].unique()
    nome_atleta = utente['nome'] if utente['ruolo'] == 'atleta' else st.selectbox("Seleziona atleta", utenti_df[utenti_df['ruolo'] == 'atleta']['nome'].unique())
    esercizio = st.selectbox("Esercizio", esercizi_filtrati)
    tipo_valore = esercizi_df[esercizi_df["esercizio"] == esercizio]["tipo_valore"].values[0]
    genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"], key="genere_test")  # Aggiunto campo per il genere

    if tipo_valore == "tempo":
        minuti = st.number_input("Minuti", min_value=0, max_value=59, step=1)
        secondi = st.number_input("Secondi", min_value=0, max_value=59, step=1)
        valore = f"{int(minuti):02d}:{int(secondi):02d}"
    else:
        valore = st.number_input("Valore", step=1.0)

    data_test = st.date_input("Data", value=datetime.date.today())
    peso_corporeo = get_peso_corporeo(utente)

    # Converte eventuali virgole in punti per gestire numeri europei
    if isinstance(peso_corporeo, str):
        peso_corporeo = peso_corporeo.replace(",", ".")
    try:
        peso_corporeo = float(peso_corporeo) if peso_corporeo is not None else None
    except (ValueError, TypeError):
        peso_corporeo = None
    if peso_corporeo is None or not isinstance(peso_corporeo, (int, float)) or peso_corporeo <= 0:
        st.error("Peso corporeo non valido. Inserisci un valore numerico maggiore di 0.")
        st.stop()

    # Verifica che peso_corporeo sia valido e numerico
    try:
        peso_corporeo = float(peso_corporeo) if peso_corporeo is not None else None
    except (ValueError, TypeError):
        peso_corporeo = None
    # Aggiungi un controllo per evitare errori
    if peso_corporeo is None or not isinstance(peso_corporeo, (int, float)) or peso_corporeo <= 0:
        st.error("Peso corporeo non valido. Inserisci un valore numerico maggiore di 0.")
        st.stop()

    # Verifica che peso_corporeo sia valido prima di usarlo
    if tipo_valore == "kg_rel" and peso_corporeo > 0:
        relativo = round(float(valore) / peso_corporeo, 2)
    else:
        relativo = None

# Salva un nuovo test
    if st.button("Salva test"):
        nuovo_test = {
            "nome": nome_atleta,
            "esercizio": esercizio,
            "valore": str(valore).replace(",", "."),
            "tipo_valore": tipo_valore,
            "peso_corporeo": peso_corporeo,
            "relativo": relativo,
            "data": data_test.strftime("%Y-%m-%d"),
            "genere": genere
        }
        test_df = pd.concat([test_df, pd.DataFrame([nuovo_test])], ignore_index=True)
        salva_su_google_sheets(test_df, "test", "test")  # Salva su Google Sheets
        test_df = carica_da_google_sheets("test")  # Ricarica i dati aggiornati
        st.success("Test salvato correttamente!")

        # Feedback intelligente
        test_utente = test_df[(test_df["nome"] == nome_atleta) & (test_df["esercizio"] == esercizio)]
        test_utente["data"] = pd.to_datetime(test_utente["data"])
        test_utente = test_utente.sort_values("data")

        # Calcolo valore attuale
        if tipo_valore == "tempo":
            val_attuale = int(minuti) * 60 + int(secondi)
        elif tipo_valore == "kg_rel":
            val_attuale = relativo
        else:
            val_attuale = float(valore)

        # Recupera benchmark
        benchmark = benchmark_df[
            (benchmark_df["esercizio"] == esercizio) &
            (benchmark_df["genere"] == genere)
        ]
        if benchmark.empty:
            st.error(f"Nessun benchmark tr_dvato per l'esercizio '{esercizio}' e il genere '{genere}'. Verifica i dati nel foglio Google Sheets 'benchmark'.")
            st.stop()
        benchmark = benchmark.squeeze()

        livello_raggiunto = "Non valutabile"
        livello_prossimo = None
        target_prossimo = None

        if benchmark is not None:
            soglie = ["base", "principiante", "intermedio", "buono", "elite"]
            valori = []
            for soglia in soglie:
                valore_raw = benchmark[soglia]
                try:
                    if tipo_valore == "tempo" and ":" in str(valore_raw):
                        m, s = map(int, valore_raw.split(":"))
                        valori.append(m * 60 + s)
                    else:
                        valori.append(float(valore_raw))
                except (ValueError, TypeError):
                    st.error(f"Valore non valido per la soglia '{soglia}' nell'esercizio '{esercizio}'. Verifica i dati nel foglio Google Sheets 'benchmark'.")
                    st.stop()

            # Determina il livello attuale
            for i, soglia in enumerate(reversed(soglie)):
                if (tipo_valore == "tempo" and val_attuale <= valori[-(i+1)]) or (tipo_valore != "tempo" and val_attuale >= valori[-(i+1)]):
                    livello_raggiunto = soglia.capitalize()
                    if i != 0:
                        livello_prossimo = soglie[-(i)]
                        target_prossimo = valori[-(i)]
                    break

        st.info(f"🎯 Hai raggiunto il livello **{livello_raggiunto}** nel test di **{esercizio}**.")
        if livello_prossimo and target_prossimo:
            st.warning(f"➡️ Obiettivo consigliato: livello **{livello_prossimo.capitalize()}** ({target_prossimo}).")
        st.caption(f"📅 Ripeti il test tra circa **6 settimane** ({(data_test + datetime.timedelta(weeks=6)).strftime('%d/%m/%Y')}).")

        # Miglioramento percentuale rispetto al test precedente
        if len(test_utente) > 1:
            penultimo = test_utente.iloc[-2]
            if tipo_valore == "tempo":
                try:
                    m, s = map(int, str(penultimo["valore"]).split(":"))
                    val_prec = m * 60 + s
                except (ValueError, TypeError):
                    val_prec = None
            elif tipo_valore == "kg_rel":
                val_prec = penultimo["relativo"]
            else:
                try:
                    val_prec = float(penultimo["valore"])
                except (ValueError, TypeError):
                    val_prec = None

            if val_prec and val_prec != 0:
                if tipo_valore == "tempo":
                    delta = val_prec - val_attuale
                    miglioramento = (delta / val_prec) * 100
                else:
                    delta = val_attuale - val_prec
                    miglioramento = (delta / val_prec) * 100
                st.success(f"📈 Miglioramento del **{miglioramento:.2f}%** rispetto al test precedente.")

                # Badge sbloccato
                if livello_raggiunto != "Non valutabile":
                    if livelli_val.get(livello_raggiunto.lower(), 0) > livelli_val.get(penultimo.get("livello", "").lower(), 0):
                        st.balloons()
                        st.success("🏅 Hai sbloccato un nuovo badge di livello!")

    # Mostra l'expander solo dopo il salvataggio
    if st.session_state.get('show_expander', False):
        with st.expander("📊 Analisi del test appena inserito", expanded=True):
            # 1. Calcola livello raggiunto
            benchmark = benchmark_df[
                (benchmark_df['esercizio'].astype(str).str.strip() == str(esercizio).strip()) &
                (benchmark_df['genere'].astype(str).str.strip() == str(genere).strip())
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
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
                        if isinstance(soglia, str):
                            soglia = float(soglia)
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
                elif tipo_valore == 'reps' or tipo_valore == 'valore':
                    val_prec = float(row_prec['valore'])
                elif tipo_valore == 'tempo':
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

# Pagina: Dashboard Atleta
elif pagina == "📈 Dashboard Atleta":
    st.subheader("📈 Dashboard Atleta")
    atleta_test = test_df[test_df['nome'] == utente['nome']]
    latest_tests = atleta_test.sort_values("data").groupby("esercizio").tail(1)

    for _, row in latest_tests.iterrows():
        benchmark = benchmark_df[
            (benchmark_df['esercizio'] == row['esercizio']) &
            (benchmark_df['genere'] == utente['genere'])
        ]
        benchmark = benchmark.squeeze() if not benchmark.empty else None
        livello = "Non valutabile"

        if benchmark is not None:
            tipo = benchmark['tipo_valore']
            if tipo == 'kg_rel' and pd.notnull(row['relativo']):
                val = float(row['relativo'])
            elif tipo == 'reps':
                val = float(row['valore'])
            elif tipo == 'tempo':
                # Converti il valore in secondi
                m, s = map(int, str(row['valore']).split(":"))
                val = m * 60 + s
                # Converti i valori del benchmark in secondi
                if isinstance(benchmark, pd.Series):
                    benchmark['base'] = float(benchmark['base']) if ":" not in str(benchmark['base']) else int(benchmark['base'].split(":")[0]) * 60 + int(benchmark['base'].split(":")[1])
                    benchmark['elite'] = float(benchmark['elite']) if ":" not in str(benchmark['elite']) else int(benchmark['elite'].split(":")[0]) * 60 + int(benchmark['elite'].split(":")[1])
            else:
                val = float(row['valore'])

            for livello_nome in reversed(list(livelli_val.keys())) if tipo == 'tempo' else livelli_val:
                soglia_min = float(benchmark['base']) if isinstance(benchmark, pd.Series) else float(benchmark['base'].iloc[0])
                soglia_max = float(benchmark['elite']) if isinstance(benchmark, pd.Series) else float(benchmark['elite'].iloc[0])
                if tipo == 'tempo':
                    if soglia_min <= val <= soglia_max:
                        livello = benchmark['tipo_valore'] if isinstance(benchmark, pd.Series) else benchmark['tipo_valore'].iloc[0]
                        break
                else:
                    if soglia_min <= val <= soglia_max:
                        livello = benchmark['tipo_valore'] if isinstance(benchmark, pd.Series) else benchmark['tipo_valore'].iloc[0]
                        break

        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric(f"{row['esercizio']}", row['valore'], help=f"Livello: {livello}")
        with col2:
            if row['tipo_valore'] == 'kg_rel':
                st.text(f"Forza relativa: {row['relativo']}")

# Pagina: Storico Dati
elif pagina == "📜 Storico Dati":
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

            if benchmark is not None:
                tipo = benchmark['tipo_valore']
                if tipo == 'kg_rel' and pd.notnull(row['peso_corporeo']):
                    val = float(row['valore']) / float(row['peso_corporeo'])
                elif tipo == 'reps' or tipo == 'valore':
                    val = float(row['valore'])
                elif tipo == 'tempo':
                    m, s = map(int, str(row['valore']).split(":"))
                    val = m * 60 + s
                    # Filtra solo le colonne pertinenti per il confronto
                    benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                        lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                        if pd.notnull(x) else x
                    )
                else:
                    val = float(row['valore'])

                for livello_nome in reversed(list(livelli_val.keys())) if tipo == 'tempo' else livelli_val:
                    soglia = benchmark[livello_nome]
                    if isinstance(soglia, str):  # Converte soglia in float se è una stringa
                        soglia = float(soglia)
                    if tipo == 'tempo':
                        if val <= soglia:
                            livello = livello_nome.capitalize()
                            break
                    else:
                        if val >= soglia:
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
            index_to_delete = atleta_test[atleta_test['info'] == test_da_eliminare].index[0]
            test_df = test_df.drop(index=index_to_delete)
            salva_su_google_sheets(test_df, "test", "test")  # Usa salva_su_google_sheets
            st.success("Test eliminato con successo!")
            st.query_params = {"refresh": "true"}  # Simula un aggiornamento della pagina

    # Genera un grafico radar per lo stato dell'atleta
    st.subheader("📊 Stato dell'Atleta")
    radar_labels = []
    radar_values = []
    for categoria in punteggi.keys():
        categoria_tests = atleta_test[atleta_test['esercizio'].isin(esercizi_df[esercizi_df['categoria'] == categoria]['esercizio'])]
        if not categoria_tests.empty:
            categoria_livelli = categoria_tests['livello'].map(lambda x: livelli_val.get(x.lower(), 0))
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(categoria_livelli.mean(), 2) if not categoria_livelli.empty else 0)

    if radar_labels:
        fig = go.Figure(data=go.Scatterpolar(
            r=radar_values,
            theta=radar_labels,
            fill='toself'
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# Pagina: Grafici (grafico a barre orizzontali per risultati esercizi)
elif pagina == "📊 Grafici":
    st.subheader("📊 Risultati esercizi (Grafico a barre orizzontali)")

    # Selezione categoria prima di esercizio
    categorie_disponibili = esercizi_df["categoria"].unique()
    categoria_selezionata = st.selectbox("Seleziona categoria", categorie_disponibili)
    esercizi_filtrati = esercizi_df[esercizi_df["categoria"] == categoria_selezionata]["esercizio"].unique()
    esercizio_selezionato = st.selectbox("Seleziona esercizio", esercizi_filtrati)

    atleta_test = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'] == esercizio_selezionato)]

    if atleta_test.empty:
        st.info(f"Non ci sono test disponibili per l'esercizio '{esercizio_selezionato}'.")
    else:
        livelli = []
        valori_barra = []
        etichette_barra = []
        for _, row in atleta_test.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio'] == row['esercizio']) &
                (benchmark_df['genere'] == utente['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello = "Non valutabile"
            progresso = 0

            if benchmark is not None:
                tipo = benchmark['tipo_valore']
                val = None
                if tipo == 'kg_rel' and row['peso_corporeo'] > 0:
                    val = float(row['valore']) / row['peso_corporeo']
                elif tipo == 'tempo':
                    try:
                        m, s = map(int, str(row['valore']).split(":"))
                        val = m * 60 + s
                    except (ValueError, TypeError):
                        val = None
                else:
                    try:
                        val = float(row['valore'])
                    except (ValueError, TypeError):
                        val = None

                if val is not None:
                    for livello_nome in reversed(list(livelli_val.keys())):
                        soglia = benchmark[livello_nome]
                        try:
                            soglia = float(soglia)
                        except (ValueError, TypeError):
                            continue
                        if tipo == 'tempo' and val <= soglia:
                            livello = livello_nome.capitalize()
                            progresso = livelli_val[livello_nome] / max(livelli_val.values())
                            break
                        elif tipo != 'tempo' and val >= soglia:
                            livello = livello_nome.capitalize()
                            progresso = livelli_val[livello_nome] / max(livelli_val.values())
                            break

            livelli.append(livello)
            valori_barra.append(progresso)
            etichette_barra.append(f"{row['valore']} ({livelli[-1]})")

        if valori_barra:
            st.write(f"**Livello raggiunto:** {livelli[-1]}")
            st.write(f"**Valore inserito:** {row['valore']}")
            st.progress(valori_barra[-1], text=f"Progresso verso Elite: {int(valori_barra[-1]*100)}%")
            # Barra orizzontale con Plotly per chiarezza
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(
                x=[valori_barra[-1]*100],
                y=[esercizio_selezionato],
                orientation='h',
                marker=dict(
                    color='rgba(0, 123, 255, 0.7)',
                    line=dict(color='rgba(0, 123, 255, 1.0)', width=8)
                ),
                text=[f"{row['valore']} ({livelli[-1]})"],
                textposition='outside'
            ))
            fig.update_layout(
                xaxis=dict(range=[0, 100], title="Progresso verso Elite (%)"),
                yaxis=dict(title="Esercizio"),
                title=f"Progresso su {esercizio_selezionato}",
                bargap=0.4,
                height=200
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Non ci sono dati sufficienti per mostrare il grafico.")

    # Grafico radar per atleta (tutte le macro-categorie)
    if utente['ruolo'] == 'atleta':
        st.subheader("📊 Profilo Radar: Tutte le Macro-Categorie")
        tutte_categorie = esercizi_df["categoria"].unique()
        radar_labels = []
        radar_values = []
        for categoria in tutte_categorie:
            esercizi_cat = esercizi_df[esercizi_df['categoria'] == categoria]['esercizio']
            test_cat = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'].isin(esercizi_cat))]
            livelli_cat = []
            for _, row in test_cat.iterrows():
                benchmark = benchmark_df[
                    (benchmark_df['esercizio'].astype(str).str.strip() == str(row['esercizio']).strip()) &
                    (benchmark_df['genere'].astype(str).str.strip() == str(row['genere']).strip())

                ]
                b_dnchmark = benchmark.squeeze() if not benchmark.empty else None
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
                                soglia = float(soglia)
                            if val is not None and val <= soglia:
                                livello_num = livelli_val[livello_nome]
                                break
                    else:
                        for livello_nome in reversed(list(livelli_val.keys())):
                            soglia = benchmark[livello_nome]
                            if isinstance(soglia, str):
                                soglia = float(soglia)
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
            # Miglioria: mostra valori numerici accanto alle etichette
            for label, value in zip(radar_labels, radar_values):
                st.write(f"**{label}**: {value}/5")
        else:
            st.info("Non ci sono dati sufficienti per generare il grafico radar.")

# Pagina: Profilo Fitness per Area
elif pagina == "📊 Profilo Fitness per Area":
    st.subheader("📊 Profilo Fitness per Area")
    
    # Seleziona esercizi da visualizzare
    esercizi_selezionati = st.multiselect(
        "Seleziona esercizi",
        options=esercizi_df["esercizio"].unique(),
        default=esercizi_df["esercizio"].unique()
    )
    
    # Filtra i test dell'atleta per gli esercizi selezionati
    atleta_test = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'].isin(esercizi_selezionati))]
    
    # Calcola il livello per ogni esercizio
    livelli = []
    for _, row in atleta_test.iterrows():
        benchmark = benchmark_df[benchmark_df['esercizio'] == row['esercizio']]
        benchmark = benchmark.squeeze() if not benchmark.empty else None

        livello = "Non valutabile"

        if benchmark is not None:
            tipo = benchmark['tipo_valore']
            if tipo == 'kg_rel' and pd.notnull(row['peso_corporeo']):
                val = float(row['valore']) / float(row['peso_corporeo'])
            elif tipo == 'reps' or tipo == 'valore':
                val = float(row['valore'])
            elif tipo == 'tempo':
                m, s = map(int, str(row['valore']).split(":"))
                val = m * 60 + s
                benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                    lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if ":" in str(x) else float(x)
                    if pd.notnull(x) else x
                )
            else:
                val = float(row['valore'])

            for livello_nome in reversed(list(livelli_val.keys())):
                soglia = benchmark[livello_nome]
                if isinstance(soglia, str):
                    soglia = float(soglia)
                if tipo == 'tempo':
                    if val <= soglia:
                        livello = livello_nome.capitalize()
                        break
                else:
                    if val >= soglia:
                        livello = livello_nome.capitalize()
                        break

        livelli.append((row['esercizio'], livello))

    # Genera il grafico a barre orizzontali
    if livelli:
        df_livelli = pd.DataFrame(livelli, columns=["Esercizio", "Livello"])
        livello_mapping = {"Base": 1, "Principiante": 2, "Intermedio": 3, "Buono": 4, "Elite": 5}
        df_livelli["Livello Numerico"] = df_livelli["Livello"].map(livello_mapping)

        fig = go.Figure(go.Bar(
            x=df_livelli["Livello Numerico"],
            y=df_livelli["Esercizio"],
            orientation='h',
            text=df_livelli["Livello"],
            textposition='auto'
        ))
        fig.update_layout(
            xaxis=dict(
                tickvals=list(livello_mapping.values()),
                ticktext=list(livello_mapping.keys()),
                title="Livello"
            ),
            yaxis=dict(title="Esercizio"),
            title="Livello per Esercizio"
        )
        st.plotly_chart(fig, use_container_width=True)

# Pagina: Profilo Atleta
elif pagina == "👤 Profilo Atleta":

    # Carica i dati dell'atleta
    atleta = utenti_df[utenti_df['nome'] == utente['nome']].squeeze()

    # Mostra i dati attuali
    st.write("### Dati attuali:")
    st.write(f"**Nome:** {atleta['nome']}")
    st.write(f"**Ruolo:** {atleta['ruolo']}")
    st.write(f"**Data di nascita:** {atleta['data_nascita']}")
    st.write(f"**Peso corporeo:** {atleta['peso']} kg")
    st.write(f"**Genere:** {atleta['genere']}")

    # Modifica i dati
    st.write("### Modifica i tuoi dati:")
    data_nascita_default = pd.to_datetime(atleta['data_nascita']) if pd.notnull(atleta['data_nascita']) else datetime.date(2000, 1, 1)
    nuova_data_nascita = st.date_input(
        "Data di nascita",
        value=data_nascita_default,
        min_value=datetime.date(1960, 1, 1)
    )
    nuovo_peso = st.number_input("Peso corporeo (kg)", min_value=30.0, max_value=200.0, step=0.1, value=float(atleta['peso']) if pd.notnull(atleta['peso']) else 70.0)
    nuovo_genere = st.selectbox(
        "Genere",
        options=["Maschio", "Femmina", "Altro"],
        index=["Maschio", "Femmina", "Altro"].index(atleta['genere']) if atleta['genere'] in ["Maschio", "Femmina", "Altro"] else 0
    )

    if st.button("Salva modifiche"):
        # Aggiorna i dati nel DataFrame
        utenti_df.loc[utenti_df['nome'] == utente['nome'], 'data_nascita'] = nuova_data_nascita.strftime("%Y-%m-%d")
        utenti_df.loc[utenti_df['nome'] == utente['nome'], 'peso'] = nuovo_peso
        utenti_df.loc[utenti_df['nome'] == utente['nome'], 'genere'] = nuovo_genere

        # Salva i dati aggiornati nel file CSV
        # salva_csv(utenti_df, "utenti.csv")
        st.success("Dati aggiornati con successo!")

# Pagina: Gestione esercizi (solo per coach)
if is_utente_valido() and utente['ruolo'] == 'coach':
    st.subheader("⚙️ Gestione esercizi")
    st.info("Sei nell'area riservata ai coach.")

    # Visualizza gli esercizi esistenti
    st.write("### esercizi esistenti:")
    st.dataframe(esercizi_df)

    # Aggiungi un nuovo esercizio
    st.write("### Aggiungi un nuovo esercizio:")
    nuovo_esercizio = st.text_input("Nome esercizio")
    categoria = st.selectbox("Categoria", ["forza", "ginnastica", "metabolico"])
    tipo_valore = st.selectbox("Tipo di valore", ["kg", "kg_rel", "reps", "tempo", "valore"])

    if st.button("Aggiungi esercizio"):
        if nuovo_esercizio and categoria and tipo_valore:
            nuovo_record = {"esercizio": nuovo_esercizio, "categoria": categoria, "tipo_valore": tipo_valore}
            esercizi_df = pd.concat([esercizi_df, pd.DataFrame([nuovo_record])], ignore_index=True)
            salva_su_google_sheets(esercizi_df, "esercizi", "esercizi")  # Salva su Google Sheets
            esercizi_df = carica_da_google_sheets("esercizi")  # Ricarica i dati aggiornati
            st.success("Esercizio aggiunto con successo!")
        else:
            st.error("Compila tutti i campi per aggiungere un esercizio.")

    # Elimina un esercizio esistente
    st.write("### Elimina un esercizio:")
    esercizio_da_eliminare = st.selectbox("Seleziona un esercizio da eliminare", esercizi_df["esercizio"])

    if st.button("Elimina esercizio"):
        esercizi_df = esercizi_df[esercizi_df["esercizio"] != esercizio_da_eliminare]
        salva_su_google_sheets(esercizi_df, "esercizi", "esercizi")  # Usa salva_su_google_sheets
        st.success("Esercizio eliminato con successo!")

# Pagina: Gestione benchmark (solo per coach)
if is_utente_valido() and utente['ruolo'] == 'coach':
    st.subheader("⚙️ Gestione benchmark")
    st.info("Sei nell'area riservata ai coach per gestire i dati di benchmark.")

    # Visualizza i benchmark esistenti
    st.write("### benchmark esistenti:")
    st.dataframe(benchmark_df)

    # Aggiungi un nuovo benchmark
    st.write("### Aggiungi un nuovo benchmark:")
    nuovo_esercizio = st.selectbox("Esercizio", esercizi_df["esercizio"].unique(), key="aggiungi_esercizio")
    genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"], key="aggiungi_genere")
    base = st.text_input("Base", key="aggiungi_base")
    principiante = st.text_input("Principiante", key="aggiungi_principiante")
    intermedio = st.text_input("Intermedio", key="aggiungi_intermedio")
    buono = st.text_input("Buono", key="aggiungi_buono")
    elite = st.text_input("Elite", key="aggiungi_elite")

    if st.button("Aggiungi benchmark", key="aggiungi_benchmark_button"):
        if nuovo_esercizio and tipo_valore and genere and base and principiante and intermedio and buono and elite:
            nuovo_record = {
                "esercizio": nuovo_esercizio,
                "tipo_valore": tipo_valore,
                "genere": genere,
                "base": base,
                "principiante": principiante,
                "intermedio": intermedio,
                "buono": buono,
                "elite": elite
            }
            benchmark_df = pd.concat([benchmark_df, pd.DataFrame([nuovo_record])], ignore_index=True)
            salva_su_google_sheets(benchmark_df, "benchmark", "benchmark")  # Salva su Google Sheets
            benchmark_df = carica_da_google_sheets("benchmark")  # Ricarica i dati aggiornati
            st.success("Nuovo benchmark aggiunto con successo!")
        else:
            st.error("Compila tutti i campi per aggiungere un benchmark.")

    # Elimina un benchmark esistente
    st.write("### Elimina un benchmark:")
    benchmark_da_eliminare = st.selectbox("Seleziona un benchmark da eliminare", benchmark_df[["esercizio", "genere"]].apply(lambda x: f"{x['esercizio']} ({x['genere']})", axis=1), key="elimina_benchmark")

    if st.button("Elimina benchmark", key="elimina_benchmark_button"):
        esercizio, genere = benchmark_da_eliminare.rsplit(" (", 1)
        genere = genere.rstrip(")")
        benchmark_df = benchmark_df[~((benchmark_df["esercizio"] == esercizio) & (benchmark_df["genere"] == genere))]
        salva_su_google_sheets(benchmark_df, "benchmark", "benchmark")  # Usa salva_su_google_sheets
        st.success("Benchmark eliminato con successo!")

    # Modifica un benchmark esistente
    st.write("### Modifica un benchmark esistente:")
    benchmark_da_modificare = st.selectbox("Seleziona un benchmark da modificare", benchmark_df[["esercizio", "genere"]].apply(lambda x: f"{x['esercizio']} ({x['genere']})", axis=1), key="modifica_benchmark")
    if benchmark_da_modificare:
        esercizio, genere = benchmark_da_modificare.rsplit(" (", 1)
        genere = genere.rstrip(")")
        benchmark_selezionato = benchmark_df[(benchmark_df["esercizio"] == esercizio) & (benchmark_df["genere"] == genere)].iloc[0]
        nuovo_tipo_valore = st.selectbox("Tipo di valore", ["kg", "kg_rel", "reps", "tempo", "valore"], index=["kg", "kg_rel", "reps", "tempo", "valore"].index(benchmark_selezionato["tipo_valore"]), key="modifica_tipo_valore")
        nuovo_genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"], index=["Maschio", "Femmina", "Altro"].index(benchmark_selezionato["genere"]), key="modifica_genere")
        nuovo_base = st.text_input("Base", value=benchmark_selezionato["base"], key="modifica_base")
        nuovo_principiante = st.text_input("Principiante", value=benchmark_selezionato["principiante"], key="modifica_principiante")
        nuovo_intermedio = st.text_input("Intermedio", value=benchmark_selezionato["intermedio"], key="modifica_intermedio")
        nuovo_buono = st.text_input("Buono", value=benchmark_selezionato["buono"], key="modifica_buono")
        nuovo_elite = st.text_input("Elite", value=benchmark_selezionato["elite"], key="modifica_elite")

        if st.button("Salva modifiche", key="salva_modifiche_benchmark"):
            benchmark_df.loc[(benchmark_df["esercizio"] == esercizio) & (benchmark_df["genere"] == genere), ["tipo_valore", "genere", "base", "principiante", "intermedio", "buono", "elite"]] = [
                nuovo_tipo_valore, nuovo_genere, nuovo_base, nuovo_principiante, nuovo_intermedio, nuovo_buono, nuovo_elite
            ]
            salva_su_google_sheets(benchmark_df, "benchmark", "benchmark")  # Usa salva_su_google_sheets
            st.success("Benchmark modificato con successo!")

# Pagina: Aggiungi Utente (solo per coach)
if is_utente_valido() and utente['ruolo'] == 'coach':
    st.subheader("➕ Aggiungi un nuovo utente")

    # Mostra tutti gli utenti esistenti
    st.write("### utenti esistenti:")
    st.dataframe(utenti_df)

    # Mostra solo i coach esistenti
    st.write("### Coach esistenti:")
    coach_df = utenti_df[utenti_df["ruolo"] == "coach"]
    st.dataframe(coach_df)

    # Seleziona un utente da eliminare
    st.write("### Elimina un utente:")
    utente_da_eliminare = st.selectbox("Seleziona un utente da eliminare", utenti_df["nome"].unique(), key="elimina_utente")

    if st.button("Elimina utente", key="elimina_utente_button"):
        utenti_df = utenti_df[utenti_df["nome"] != utente_da_eliminare]
        salva_su_google_sheets(utenti_df, "utenti", "utenti")  # Usa salva_su_google_sheets
        test_df = test_df[test_df["nome"] != utente_da_eliminare]
        salva_su_google_sheets(test_df, "test", "test")  # Usa salva_su_google_sheets
        st.success(f"Utente '{utente_da_eliminare}' e i suoi dati sono stati eliminati con successo!")

    # Input per i dettagli del nuovo utente (coach o atleta)
    st.write("### Aggiungi un nuovo utente")
    nuovo_nome = st.text_input("Nome utente")
    nuovo_pin = st.text_input("PIN utente", type="password")
    nuovo_ruolo = st.selectbox("Ruolo", ["atleta", "coach"], key="aggiungi_ruolo")
    nuovo_peso = st.number_input("Peso corporeo (kg)", min_value=30.0, max_value=200.0, step=0.1, key="aggiungi_peso")
    nuova_data_nascita = st.date_input(
        "Data di nascita",
        value=datetime.date(2000, 1, 1),
        min_value=datetime.date(1960, 1, 1),
        key="aggiungi_data_nascita"
    )
    nuovo_genere = st.selectbox("Genere", ["Maschio", "Femmina", "Altro"], key="aggiungi_genere_utente")

# Aggiungi un nuovo utente
    if st.button("Aggiungi utente", key="aggiungi_utente_button"):
        if nuovo_nome and nuovo_pin:
            nomi_esistenti = utenti_df["nome"].astype(str).str.strip().str.lower()
            if nuovo_nome.strip().lower() in nomi_esistenti.values:
                st.error(f"Esiste già un utente con il nome '{nuovo_nome}'. Scegli un nome diverso.")
            else:
                nuovo_utente = {
                    "nome": nuovo_nome,
                    "pin": nuovo_pin,
                    "ruolo": nuovo_ruolo,
                    "peso": nuovo_peso,
                    "data_nascita": nuova_data_nascita.strftime("%Y-%m-%d"),
                    "genere": nuovo_genere
                }
                utenti_df = pd.concat([utenti_df, pd.DataFrame([nuovo_utente])], ignore_index=True)
                salva_su_google_sheets(utenti_df, "utenti", "utenti")  # Salva su Google Sheets
                utenti_df = carica_da_google_sheets("utenti")  # Ricarica i dati aggiornati
                st.success(f"Nuovo utente '{nuovo_nome}' aggiunto con successo come {nuovo_ruolo}!")
        else:
            st.error("Compila tutti i campi richiesti.")

# Pagina: Storico Dati utenti (solo per coach)
if is_utente_valido() and utente['ruolo'] == 'coach':
    st.subheader("📋 Storico Dati utenti")
    st.write("### Risultati di tutti i test:")
    st.dataframe(test_df)

    # Opzione per filtrare i test per utente
    st.write("### Filtra per utente:")
    utente_selezionato = st.selectbox("Seleziona un utente", utenti_df["nome"].unique(), key="filtra_utente")
    test_filtrati = test_df[test_df["nome"] == utente_selezionato]

    if test_filtrati.empty:
        st.info(f"Non ci sono test disponibili per l'utente '{utente_selezionato}'.")
    else:
        st.write(f"### test di {utente_selezionato}:")
        st.dataframe(test_filtrati)

# Pagina: Aree di Performance
if is_utente_valido() and utente['ruolo'] == 'coach':
    st.subheader("📊 Aree di Performance")

    # Ottieni tutte le categorie presenti
    tutte_categorie = esercizi_df["categoria"].unique()

    # Funzione per calcolare i livelli medi per ogni categoria e genere
    def calcola_radar_per_genere(genere):
        radar_labels = []
        radar_values = []
        livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
        atleti = utenti_df[(utenti_df["ruolo"] == "atleta") & (utenti_df["genere"] == genere)]["nome"].unique()
        for categoria in tutte_categorie:
            esercizi_cat = esercizi_df[esercizi_df['categoria'] == categoria]['esercizio']
            test_cat = test_df[
                (test_df['nome'].isin(atleti)) &
                (test_df['esercizio'].isin(esercizi_cat))
            ]
            livelli_cat = []
            for _, row in test_cat.iterrows():
                benchmark = benchmark_df[
                    (benchmark_df['esercizio'] == row['esercizio']) &
                    (benchmark_df['genere'] == genere)
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
                                soglia = float(soglia)
                            if val is not None and val <= soglia:
                                livello_num = livelli_val[livello_nome]
                                break
                    else:
                        for livello_nome in reversed(list(livelli_val.keys())):
                            soglia = benchmark[livello_nome]
                            if isinstance(soglia, str):
                                soglia = float(soglia)
                            if val is not None and val >= soglia:
                                livello_num = livelli_val[livello_nome]
                                break
                livelli_cat.append(livello_num)
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(sum(livelli_cat) / len(livelli_cat), 2) if livelli_cat else 0)
        return radar_labels, radar_values

    # Radar per Maschi
    st.markdown("#### 👨 Uomini")
    radar_labels_m, radar_values_m = calcola_radar_per_genere("Maschio")
    if any(radar_values_m):
        fig_m = go.Figure(data=go.Scatterpolar(
            r=radar_values_m,
            theta=radar_labels_m,
            fill='toself',
            marker=dict(color='rgba(0,123,255,0.7)')
        ))
        fig_m.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title="Profilo Radar per Macro-Categoria (Uomini)",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig_m, use_container_width=True)
        for label, value in zip(radar_labels_m, radar_values_m):
            st.write(f"**{label}**: {value}/5")
    else:
        st.info("Non ci sono dati sufficienti per generare il grafico radar per gli uomini.")

    # Radar per Femmine
    st.markdown("#### 👩 Donne")
    radar_labels_f, radar_values_f = calcola_radar_per_genere("Femmina")
    if any(radar_values_f):
        fig_f = go.Figure(data=go.Scatterpolar(
            r=radar_values_f,
            theta=radar_labels_f,
            fill='toself',
            marker=dict(color='rgba(255,0,123,0.7)')
        ))
        fig_f.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title="Profilo Radar per Macro-Categoria (Donne)",
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig_f, use_container_width=True)
        for label, value in zip(radar_labels_f, radar_values_f):
            st.write(f"**{label}**: {value}/5")
    else:
        st.info("Non ci sono dati sufficienti per generare il grafico radar per le donne.")

    # Grafico a barre per il bilanciamento di genere
    st.subheader("📊 Bilanciamento di Genere")
    genere_counts = utenti_df['genere'].value_counts()
    fig_genere = go.Figure(data=go.Bar(
        x=genere_counts.index,
        y=genere_counts.values,
        text=genere_counts.values,
        textposition='auto'
    ))
    fig_genere.update_layout(
        xaxis_title="Genere",
        yaxis_title="Numero di utenti",
        title="Distribuzione degli utenti per Genere"
    )
    st.plotly_chart(fig_genere, use_container_width=True)

# Pagina: Storico test (solo atleta)
if pagina == "📜 Storico test" and utente['ruolo'] == 'atleta':
    st.subheader("📜 Storico dei test Inseriti")
    atleta_test = test_df[test_df['nome'] == utente['nome']]
    if atleta_test.empty:
        st.info("Non ci sono test disponibili per questo utente.")
    else:
        st.dataframe(atleta_test.sort_values("data", ascending=False))

# Pagina: Calendario WOD
if pagina == "📅 Calendario WOD":
    st.subheader("📅 Calendario WOD (Workout Of the Day)")

    # Seleziona una data
    data_selezionata = st.date_input("Seleziona una data", value=datetime.date.today(), key="wod_date")
    data_str = data_selezionata.strftime("%Y-%m-%d")

    # Ensure the 'data' column exists in wod_df
    if "data" not in wod_df.columns:
        st.error("La colonna 'data' non è presente nei dati del WOD. Verifica il contenuto del foglio Google Sheets.")
        st.stop()

    # Convert 'data' column to datetime format if not already
    wod_df["data"] = pd.to_datetime(wod_df["data"], errors="coerce")

    # Handle missing or invalid dates
    if wod_df["data"].isnull().any():
        st.error("Errore nel formato delle date in 'wod_df'. Assicurati che siano nel formato 'YYYY-MM-DD'.")
        st.stop()

    # Filter WOD for the selected date
    wod_oggi = wod_df[wod_df["data"] == pd.to_datetime(data_selezionata)]

    if not wod_oggi.empty:
        st.write(f"### WOD del {data_str}")
        st.write(f"**Nome:** {wod_oggi.iloc[0]['titolo']}")
        st.write(f"**Descrizione:** {wod_oggi.iloc[0]['descrizione']}")
    else:
        st.info("Nessun WOD pubblicato per questa data.")

    # Solo i coach possono aggiungere/modificare/eliminare WOD
    if utente['ruolo'] == 'coach':
        st.write("---")
        st.write("### Pubblica o modifica WOD per questa data")
        titolo_wod = st.text_input("Titolo WOD", value=wod_oggi.iloc[0]['titolo'] if not wod_oggi.empty else "")
        descrizione_wod = st.text_area("Descrizione WOD", value=wod_oggi.iloc[0]['descrizione'] if not wod_oggi.empty else "")

        if st.button("Salva/Modifica WOD", key="salva_wod"):
            # Se esiste già, aggiorna; altrimenti aggiungi
            if not wod_oggi.empty:
                wod_df.loc[wod_df["data"] == data_str, ["titolo", "descrizione"]] = [titolo_wod, descrizione_wod]
            else:
                nuovo_wod = {"data": data_str, "titolo": titolo_wod, "descrizione": descrizione_wod}
                wod_df = pd.concat([wod_df, pd.DataFrame([nuovo_wod])], ignore_index=True)
            salva_su_google_sheets(wod_df, "wod", "wod")
            st.success("WOD salvato/modificato con successo!")

        if not wod_oggi.empty:
            if st.button("Elimina WOD", key="elimina_wod"):
                wod_df = wod_df[wod_df["data"] != data_str]
                salva_su_google_sheets(wod_df, "wod", "wod")
                st.success("WOD eliminato con successo!")

    st.write("---")
    st.write("### Storico WOD pubblicati")
    # Modifica per gestire formati di data non standard
    wod_df["data"] = pd.to_datetime(wod_df["data"], format="%Y-%m-%d", errors="coerce")
    if wod_df["data"].isnull().any():
        st.error("Errore nel formato delle date in 'wod.csv'. Assicurati che siano nel formato 'YYYY-MM-DD'.")
        st.stop()

    wod_df = wod_df.sort_values("data", ascending=False)

    for idx, row in wod_df.iterrows():
        # Verifica che la colonna 'nome' esista, altrimenti usa un valore predefinito
        nome_wod = row['nome'] if 'nome' in row else "WOD"
        with st.expander(f"{row['data'].date()} - {nome_wod}"):
            st.markdown(f"**Descrizione:** {row['descrizione']}")
            esercizi_collegati = row['esercizi'].split(";") if 'esercizi' in row and pd.notnull(row['esercizi']) else []
            if esercizi_collegati:
                st.markdown(f"**esercizi collegati:** {', '.join(esercizi_collegati)}")

            # Mostra test dell’atleta legati al WOD
            test_collegati = test_df[
                (test_df["nome"] == utente["nome"]) &
                (test_df["esercizio"].isin(esercizi_collegati))
            ]
            if not test_collegati.empty:
                st.markdown("📊 **test collegati a questo WOD:**")
                st.dataframe(test_collegati[["data", "esercizio", "valore", "tipo_valore"]])
            else:
                st.info("Nessun test collegato trovato per questo WOD.")

            # Aggiungi nota personale
            st.markdown("📝 **Nota personale**")
            note_key = f"nota_{idx}_{utente['nome']}"
            nota = st.text_area("Scrivi una nota (visibile solo a te)", key=note_key)
            if st.button("Salva nota", key=f"salva_{note_key}"):
                # Salva su CSV o mostra (puoi implementare salvataggio locale più avanti)
                st.success("Nota salvata! (implementare salvataggio permanente)")

# Pagina: Storico Progressi
if pagina == "📈 Storico Progressi":
    st.subheader("📈 Storico Progressi per Esercizio")

    # Selezione esercizio
    esercizi_disponibili = test_df[test_df['nome'] == utente['nome']]['esercizio'].unique()
    if len(esercizi_disponibili) == 0:
        st.info("Non ci sono test disponibili per questo utente.")
    else:
        esercizio_sel = st.selectbox("Seleziona esercizio", esercizi_disponibili)
        dati_esercizio = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'] == esercizio_sel)].copy()

        # Assicurati che i dati siano ordinati per data
        dati_esercizio["data"] = pd.to_datetime(dati_esercizio["data"], format="%Y-%m-%d", errors="coerce")
        dati_esercizio = dati_esercizio.sort_values("data")

        # Calcola livello per ogni test
        livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
        livelli = []
        for _, row in dati_esercizio.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio'] == row['esercizio']) &
                (benchmark_df['genere'] == row.get('genere', utente.get('genere', 'Maschio')))
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None


            livello = "Non valutabile"

            val = None
            if benchmark is not None and isinstance(benchmark, pd.Series):
                tipo = benchmark['tipo_valore']
                try:
                    peso_corporeo = float(row['peso_corporeo'])
                except Exception:
                    peso_corporeo = None
                if tipo == 'kg_rel' and peso_corporeo and peso_corporeo != 0:
                    try:
                        val = float(row['valore']) / peso_corporeo
                    except Exception:
                        val = None
                elif tipo == 'reps' or tipo_valore == 'valore':
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

                livello_num = 0
                livello_nome_trovato = None
                if tipo == 'tempo':
                    livelli_ordine = list(reversed(list(livelli_val.keys())))
                    for livello_nome in livelli_ordine:
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
                        if isinstance(soglia, str):
                            soglia = float(soglia)
                        if val is not None and val >= soglia:
                            livello_nome_trovato = livello_nome.capitalize()
                            livello_num = livelli_val[livello_nome]
                            break
                livello = livello_nome_trovato if livello_nome_trovato else "Non valutabile"
            livelli.append(livello)

        dati_esercizio['livello'] = livelli

        # Prepara valori per il grafico
        x = pd.to_datetime(dati_esercizio['data'])
        y = dati_esercizio['valore']
        testo = [
            f"Valore: {v}<br>Livello: {l}" for v, l in zip(dati_esercizio['valore'], dati_esercizio['livello'])
        ]

        # Grafico a linee
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines+markers',
            marker=dict(size=10, color='rgba(0,123,255,0.8)'),
            line=dict(color='rgba(0,123,255,0.5)', width=2),
            text=testo,
            hoverinfo='text'
        ))

        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Valore",
            title=f"Andamento nel tempo: {esercizio_sel}",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

# Pagina: WOD
elif pagina == "📒 WOD":
    st.subheader("📒 Workout of the Day (WOD)")

    oggi = datetime.date.today()
    wod_oggi = wod_df[wod_df["data"] == pd.to_datetime(oggi)]

    if not wod_oggi.empty:
        wod = wod_oggi.iloc[0]
        st.subheader(f"🏋️‍♂️ WOD del giorno: {wod['nome']}")

        # Mostra i 3 livelli
        st.markdown("### Livelli disponibili:")
        st.markdown(f"**Principiante**: {wod['principiante']}")
        st.markdown(f"**Intermedio**: {wod['intermedio']}")
        st.markdown(f"**Avanzato**: {wod['avanzato']}")

        st.divider()
        st.subheader("📥 Inserisci il tuo risultato")

        livello = st.radio("Livello scelto", ["principiante", "intermedio", "avanzato"])
        tipo_valore = wod["tipo_valore"]

        if tipo_valore == "tempo":
            minuti = st.number_input("Minuti", min_value=0, max_value=59)
            secondi = st.number_input("Secondi", min_value=0, max_value=59)
            risultato = f"{int(minuti):02d}:{int(secondi):02d}"
        else:
            risultato = st.number_input("Risultato (reps o rounds)", step=1)

        if st.button("Salva risultato"):
            risultati_df = pd.read_csv("fitness_app/wod_risultati.csv") if os.path.exists("fitness_app/wod_risultati.csv") else pd.DataFrame(columns=["nome", "data_wod", "livello", "risultato", "tipo_valore"])
            nuovo_record = {
                "nome": utente["nome"],
                "data_wod": oggi.strftime("%Y-%m-%d"),
                "livello": livello,
                "risultato": risultato,
                "tipo_valore": tipo_valore
            }
            risultati_df = pd.concat([risultati_df, pd.DataFrame([nuovo_record])], ignore_index=True)
            risultati_df.to_csv("fitness_app/wod_risultati.csv", index=False)
            st.success("Risultato salvato!")

        st.divider()
        st.subheader("📊 Classifica del giorno")

        if os.path.exists("fitness_app/wod_risultati.csv"):
            risultati_df = pd.read_csv("fitness_app/wod_risultati.csv")
            classifica = risultati_df[risultati_df["data_wod"] == oggi.strftime("%Y-%m-%d")]

            if not classifica.empty:
                if tipo_valore == "tempo":
                    classifica["valore_sec"] = classifica["risultato"].apply(lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]))
                    classifica = classifica.sort_values("valore_sec")
                else:
                    classifica["valore_num"] = pd.to_numeric(classifica["risultato"], errors="coerce")
                    classifica = classifica.sort_values("valore_num", ascending=False)

                st.dataframe(classifica[["nome", "livello", "risultato"]].reset_index(drop=True))
            else:
                st.info("Nessun risultato registrato oggi.")
    else:
        st.info("Nessun WOD pubblicato per oggi.")

# Pagina: Dashboard iniziale
if pagina == "🏠 Dashboard":
    st.title("🏠 Dashboard Atleta")

    # Spinner per caricamento dati
    with st.spinner("Caricamento dati..."):
        # Box utente migliorato
        st.markdown(
            """
            <style>
            .user-card {
                background: #f7f9fa;
                border-radius: 18px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.07);
                padding: 1.2rem 1.5rem 1.2rem 1.5rem;
                margin-bottom: 1.5rem;
                display: flex;
                align-items: center;
            }
            .user-avatar {
                margin-right: 1.5rem;
            }
            .user-avatar img {
                border-radius: 50%;
                border: 2px solid #e0e0e0;
                width: 70px;
                height: 70px;
                object-fit: cover;
            }
            .user-info {
                font-size: 1.15em;
            }
            @media (max-width: 600px) {
                .user-card { flex-direction: column; align-items: flex-start; }
                .user-avatar { margin-bottom: 1rem; }
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        # Usa st.image per il logo, più compatibile con Streamlit
        col1, col2 = st.columns([1, 4])
        with col1:
            # Mostra il logo solo se esiste il file
            logo_path = "fitness_app/assets/logo.png"
            if os.path.exists(logo_path):
                st.image(logo_path, width=70)
            else:
                st.warning("Logo non trovato: fitness_app/assets/logo.png")
        with col2:
            st.markdown(
                f"""
                <div class="user-info">
                    <b>👤 Nome:</b> {utente['nome']}<br>
                    <b>🎂 Età:</b> {datetime.date.today().year - pd.to_datetime(utente['data_nascita']).year} anni<br>
                    <b>⚖️ Peso:</b> {utente['peso']} kg<br>
                    <b>🏅 Genere:</b> {utente['genere']}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()

        # test recenti
        st.subheader("📈 test recenti")
        test_utente = test_df[test_df["nome"] == utente["nome"]].copy()
        test_utente["data"] = pd.to_datetime(test_utente["data"])
        test_utente = test_utente.sort_values("data")
        test_recenti = test_utente.sort_values("data", ascending=False).head(5)
        st.dataframe(test_recenti[["data", "esercizio", "valore"]])

        # Prossimi test consigliati (oltre 6 settimane fa)
        st.subheader("⏰ test da ripetere")
        cutoff_date = datetime.date.today() - datetime.timedelta(weeks=6)
        test_scaduti = test_utente[test_utente["data"] < pd.to_datetime(cutoff_date)]
        test_scaduti = test_scaduti.groupby("esercizio").tail(1)
        if not test_scaduti.empty:
            st.warning("⚠️ Questi test andrebbero aggiornati:")
            st.dataframe(test_scaduti[["data", "esercizio", "valore"]])
        else:
            st.success("✅ Nessun test da aggiornare al momento.")

# Responsive CSS per mobile
st.markdown("""
    <style>
    html, body, .stApp {
        max-width: 100vw;
        overflow-x: hidden;
        font-size: 17px;
    }
    .block-container {
        padding-top: 3.5rem !important;  # <--- aumenta il padding-top
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    @media (max-width: 600px) {
        .block-container {
            padding-top: 1.5rem !important;  # <--- aumenta anche su mobile
            padding-bottom: 0.2rem !important;
            padding-left: 0.1rem !important;
            padding-right: 0.1rem !important;
        }
        h1, h2, h3, h4 {
            font-size: 1.2em !important;
        }
        .stImage > img {
            width: 60px !important;
            height: 60px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)
