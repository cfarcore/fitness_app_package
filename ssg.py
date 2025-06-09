import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
import os
import time
import pickle
import datetime
import plotly.graph_objects as go

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
        # Open spreadsheet by title
        sh = client.open(sheet_name)
        try:
            # Try to get worksheet with the same name as the spreadsheet
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Fallback: use the first worksheet
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

# --- BLOCCO CACHE DATI ---
#@st.cache_data
def carica_utenti():
    return carica_da_google_sheets("utenti")

#@st.cache_data
def carica_esercizi():
    return carica_da_google_sheets("esercizi")

#@st.cache_data
def carica_test():
    return carica_da_google_sheets("test")

#@st.cache_data
def carica_benchmark():
    return carica_da_google_sheets("benchmark")

#@st.cache_data
def carica_wod():
    return carica_da_google_sheets("wod")

# Carica i dati dalle cache (USARE SEMPRE QUESTI!)
utenti_df = carica_utenti()
esercizi_df = carica_esercizi()
test_df = carica_test()
benchmark_df = carica_benchmark()
wod_df = carica_wod()

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
        # Open spreadsheet by title
        sh = client.open(sheet_name)
        try:
            # Try to get worksheet with the same name as the spreadsheet
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Fallback: use the first worksheet
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

# Carica i dati da Google Sheets
utenti_df = carica_utenti()
esercizi_df = carica_esercizi()
test_df = carica_test()
benchmark_df = carica_benchmark()
wod_df = carica_wod()

# Login
if not st.session_state.logged_in:
    ruolo = st.selectbox("Seleziona il tuo ruolo", ["atleta", "coach"])
    nome = st.text_input("Inserisci il tuo nome")
    pin = st.text_input("Inserisci il tuo PIN", type="password")
    if st.button("Accedi"):
        utenti_df["nome"] = utenti_df["nome"].astype(str).str.strip()
        utenti_df["pin"] = utenti_df["pin"].astype(str).str.strip()
        utenti_df["ruolo"] = utenti_df["ruolo"].astype(str).str.strip()
        nome_normalizzato = nome.strip()
        pin_normalizzato = pin.strip()

        utente_raw = utenti_df[
            (utenti_df["nome"] == nome_normalizzato) &
            (utenti_df["pin"] == pin_normalizzato) &
            (utenti_df["ruolo"] == ruolo)
        ]
        if not utente_raw.empty:
            st.session_state.logged_in = True
            st.session_state.user_pin = pin_normalizzato
            st.session_state.utente = utente_raw.squeeze().to_dict()
            st.session_state.refresh = True
            st.rerun()
 # <--- questa fa ripartire l'app SUBITO dopo il login!
        else:
            st.error("Nome, PIN o ruolo non validi. Riprova.")
        # st.stop()  # Non serve più qui!
    st.stop()  # Qui va bene: ferma solo se NON hai cliccato Accedi!

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

# --- Sidebar navigazione ---
if is_utente_valido():
    if utente['ruolo'] == 'coach':
        pagine_sidebar = [
            "🏠 Dashboard","👤 Profilo Atleta",  "📅 Calendario WOD", "➕ Inserisci nuovo test", 
            "⚙️ Gestione esercizi", "📋 Storico Dati utenti", "📊 Bilanciamento Atleti",
            "➕ Aggiungi Utente", "⚙️ Gestione benchmark", "📊 Grafici", "📈 Storico Progressi",
            "📒 WOD", "🏆 Classifiche"
        ]
    else:
        pagine_sidebar = [
            "🏠 Dashboard","➕ Inserisci nuovo test","👤 Profilo Atleta", "📅 Calendario WOD", 
            "📊 Grafici", "📜 Storico test", "📈 Storico Progressi", "📒 WOD"
        ]

if 'pagina_attiva' not in st.session_state:
    st.session_state.pagina_attiva = pagine_sidebar[0]

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
    st.title("Dashboard")
    st.write("Benvenuto nella Dashboard!")

elif pagina == "📅 Calendario WOD":
    st.title("Calendario WOD")
    st.write("Visualizza e filtra il calendario degli allenamenti.")

    # Ricerca/filtro per nome o data
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
                carica_wod.clear()
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
                        carica_wod.clear()
                        wod_df = carica_wod()
                        st.success("WOD aggiornato con successo!")


        st.markdown("---")

        # --- ELIMINA WOD ---
        st.subheader("🗑️ Elimina un WOD")
        if not wod_df.empty:
            wod_df["info"] = wod_df.apply(lambda x: f"{x['data']} - {x['nome']}", axis=1)
            wod_da_eliminare = st.selectbox("Seleziona un WOD da eliminare", wod_df["info"].unique(), key="elimina_wod_select")
            if st.button("Elimina WOD"):
                index_to_delete = wod_df[wod_df["info"] == wod_da_eliminare].index[0]
                wod_df = wod_df.drop(index=index_to_delete)
                salva_su_google_sheets(wod_df, "wod", "wod")
                carica_wod.clear()
                wod_df = carica_wod()
                st.success("WOD eliminato con successo!")

    # Divider grafico (FACOLTATIVO)
    # st.markdown("---")
    # st.subheader("📊 Statistiche rapide calendario")
    # ...qui puoi aggiungere altri grafici, se vuoi...


elif pagina == "➕ Inserisci nuovo test":
    st.title("Inserisci nuovo test")
    # ...existing code...

elif pagina == "👤 Profilo Atleta":
    st.title("Profilo Atleta")
    # ...existing code...

elif pagina == "⚙️ Gestione esercizi" and utente['ruolo'] == 'coach':
    st.title("Gestione Esercizi")
    # ...existing code...

elif pagina == "📋 Storico Dati utenti" and utente['ruolo'] == 'coach':
    st.title("Storico Dati utenti")
    # ...existing code...

elif pagina == "📊 Bilanciamento Atleti" and utente['ruolo'] == 'coach':
    st.title("Bilanciamento Atleti")
    st.write("Bilancia i carichi di lavoro degli atleti.")
    st.dataframe(test_df)  # Mostra i dati dei test per analisi del bilanciamento

elif pagina == "➕ Aggiungi Utente" and utente['ruolo'] == 'coach':
    st.title("Aggiungi Utente")
    # ...existing code...

elif pagina == "⚙️ Gestione benchmark" and utente['ruolo'] == 'coach':
    st.title("Gestione Benchmark")
    # ...existing code...

elif pagina == "📊 Grafici" and utente['ruolo'] == 'coach':
    st.subheader("📊 Grafico radar: Livello medio per categoria (tutti gli atleti)")

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
                (benchmark_df["esercizio"] == row["esercizio"]) &
                (benchmark_df["genere"] == row["genere"])
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
                        soglia = float(soglia)
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

    # AREA ATLETA: mostra solo i test dell’atleta loggato
    if utente['ruolo'] == 'atleta':
        storico = test_df[test_df['nome'] == utente['nome']].copy()
    # AREA COACH: filtro per atleta o tutti
    elif utente['ruolo'] == 'coach':
        opzioni_atleti = ["Tutti"] + list(test_df["nome"].unique())
        atleta_sel = st.selectbox("Seleziona atleta", opzioni_atleti)
        if atleta_sel == "Tutti":
            storico = test_df.copy()
        else:
            storico = test_df[test_df["nome"] == atleta_sel].copy()
    else:
        storico = test_df.copy()

    # Ordina per data discendente
    storico["data"] = pd.to_datetime(storico["data"], errors="coerce")
    storico = storico.sort_values("data", ascending=False)

    # Filtro per esercizio
    esercizi_disp = ["Tutti"] + list(storico["esercizio"].unique())
    esercizio_sel = st.selectbox("Seleziona esercizio", esercizi_disp)
    if esercizio_sel != "Tutti":
        storico = storico[storico["esercizio"] == esercizio_sel]

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
                    except Exception:
                        return None
                try:
                    return float(v.replace(",", "."))
                except Exception:
                    return None

            y = storico["valore"].apply(converti_valore)
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

elif pagina == "📒 WOD":
    st.title("WOD")
    st.write("Gestisci e visualizza i WOD.")
    st.dataframe(wod_df)  # Mostra i dati dei WOD

elif pagina == "🏆 Classifiche" and utente['ruolo'] == 'coach':
    st.title("Classifiche")
    st.write("Visualizza le classifiche degli atleti, suddivise per categoria e tipo di valore.")

    categorie = esercizi_df['categoria'].unique()
    for cat in categorie:
        st.subheader(f"Categoria: {cat.capitalize()}")
        esercizi_cat = esercizi_df[esercizi_df['categoria'] == cat]['esercizio']
        test_cat = test_df[test_df['esercizio'].isin(esercizi_cat)]

        # -- CLASSIFICHE NUMERICHE --
        num_tests = test_cat[test_cat['tipo_valore'] != 'tempo'].copy()
        num_tests['valore_num'] = pd.to_numeric(num_tests['valore'], errors='coerce')
        classifica_num = num_tests.groupby('nome').agg({'valore_num':'sum'}).reset_index()
        classifica_num = classifica_num.sort_values("valore_num", ascending=False)
        if not classifica_num.empty:
            st.write("Classifica test numerici (kg, reps, ...):")
            st.dataframe(classifica_num)
        else:
            st.info("Nessun test numerico per questa categoria.")

        # -- CLASSIFICHE TEMPO (in secondi) --
        tempo_tests = test_cat[test_cat['tipo_valore'] == 'tempo'].copy()
        def tempo_to_sec(x):
            try:
                m, s = map(int, str(x).split(":"))
                return m*60+s
            except:
                return None
        tempo_tests['valore_sec'] = tempo_tests['valore'].apply(tempo_to_sec)
        classifica_tempo = tempo_tests.groupby('nome').agg({'valore_sec':'sum'}).reset_index()
        classifica_tempo = classifica_tempo.sort_values("valore_sec")  # Più basso = meglio, solitamente
        if not classifica_tempo.empty:
            st.write("Classifica test a tempo (secondi totali, più basso è meglio):")
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

# Utility per ottenere il peso corporeo senza duplicazioni
def get_peso_corporeo(utente):
    if utente["ruolo"] == "atleta":
        return utente.get("peso", None)
    else:
        return st.number_input("Peso corporeo (kg)", min_value=30.0, max_value=200.0, step=0.1)

# Funzione per salvare i dati su Google Sheets
def salva_su_google_sheets(df, file_name, sheet_name):
    import time
    try:
        sh = client.open(file_name)
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        time.sleep(2)  # Aggiungi una piccola pausa per sicurezza
        st.success("Scrittura su Google Sheets completata!")
    except Exception as e:
        st.error(f"Errore nel salvataggio su Google Sheets: {e}")

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
        test_df = carica_test() # Ricarica i dati aggiornati
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

        # ...il resto del codice qui prosegue invariato...

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
            elif tipo == "kg_rel":
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
                        benchmark = benchmark[["base", "principiante", "intermedio", "buono", "elite"]].apply(
                            lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]) if isinstance(x, str) and ":" in x else float(x)
                            if pd.notnull(x) else x
                        )
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
            index_to_delete = atleta_test[atleta_test['info'] == test_da_eliminare].index[0]
            test_df = test_df.drop(index=index_to_delete)
            salva_su_google_sheets(test_df, "test", "test")  # Usa salva_su_google_sheets
            st.success("Test eliminato con successo!")
            st.query_params = {"refresh": "true"}  # Simula un aggiornamento della pagina

# ----- GRAFICI COACH -----
elif pagina == "📊 Grafici" and utente['ruolo'] == 'coach':
    st.subheader("📊 Stato esercizi (tutti o singolo atleta)")

    # Scegli atleta: "Tutti gli atleti" o uno specifico
    opzioni_utenti = ["Tutti gli atleti"] + list(utenti_df[utenti_df['ruolo'] == 'atleta']['nome'].unique())
    atleta_selezionato = st.selectbox("Seleziona atleta", opzioni_utenti)

    # Scegli categoria/esercizio
    categorie_disponibili = esercizi_df["categoria"].unique()
    categoria_selezionata = st.selectbox("Seleziona categoria", categorie_disponibili)
    esercizi_filtrati = esercizi_df[esercizi_df["categoria"] == categoria_selezionata]["esercizio"].unique()
    esercizio_selezionato = st.selectbox("Seleziona esercizio", esercizi_filtrati)

    # Filtro i test in base a chi voglio vedere
    if atleta_selezionato == "Tutti gli atleti":
        test_selezionati = test_df[test_df['esercizio'] == esercizio_selezionato]
    else:
        test_selezionati = test_df[(test_df['esercizio'] == esercizio_selezionato) & (test_df['nome'] == atleta_selezionato)]

    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    risultati = []
    nomi_barre = []

    for _, row in test_selezionati.iterrows():
        benchmark = benchmark_df[
            (benchmark_df['esercizio'] == row['esercizio']) &
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
                    soglia = float(soglia)
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
        import plotly.graph_objects as go
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
            xaxis=dict(range=[0.5, 5.5], tickvals=[1,2,3,4,5], ticktext=list(livello_mapping.keys()), title="Livello raggiunto"),
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
    
    st.write("DEBUG - test_df per atleta:", test_df[test_df['nome'] == atleta_radar])
    
    tutte_categorie = esercizi_df["categoria"].unique()
    radar_labels = []
    radar_values = []
    livelli_val = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    for categoria in tutte_categorie:
        esercizi_cat = esercizi_df[esercizi_df['categoria'] == categoria]['esercizio']
        test_cat = test_df[(test_df['nome'] == atleta_radar) & (test_df['esercizio'].isin(esercizi_cat))]
        livelli_cat = []
        for _, row in test_cat.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio'].astype(str).str.strip() == str(row['esercizio']).strip()) &
                (benchmark_df['genere'].astype(str).str.strip() == str(row['genere']).strip())
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
        if livelli_cat:
            radar_labels.append(categoria.capitalize())
            radar_values.append(round(sum(livelli_cat) / len(livelli_cat), 2))
    st.write("DEBUG - Radar labels:", radar_labels)
    st.write("DEBUG - Radar values:", radar_values)

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

# ----- GRAFICI ATLETA -----
elif pagina == "📊 Grafici" and utente['ruolo'] == 'atleta':
    st.subheader("📊 Risultati esercizi: Stato & Macro-Aree")

    # Seleziona macro-area e poi esercizio
    macroaree = esercizi_df["categoria"].unique()
    macroarea_sel = st.selectbox("Seleziona macro-area", macroaree)
    esercizi_macro = esercizi_df[esercizi_df["categoria"] == macroarea_sel]["esercizio"].unique()
    esercizio_sel = st.selectbox("Seleziona esercizio", esercizi_macro)

    # Estrai ultimi test di quell’esercizio per l’atleta
    test_esercizio = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'] == esercizio_sel)]
    livello_mapping = {"base": 1, "principiante": 2, "intermedio": 3, "buono": 4, "elite": 5}
    ultimo_livello = "base"
    progresso = 0

    if not test_esercizio.empty:
        row = test_esercizio.sort_values("data").iloc[-1]
        benchmark = benchmark_df[
            (benchmark_df['esercizio'] == row['esercizio']) &
            (benchmark_df['genere'] == row['genere'])
        ]
        benchmark = benchmark.squeeze() if not benchmark.empty else None
        livello = "base"
        progresso = 0
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
                    soglia = float(soglia)
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
            progresso = livello_mapping.get(livello, 1) / max(livello_mapping.values())
            ultimo_livello = livello.capitalize()
        
        st.markdown(f"<b>{esercizio_sel}:</b> {ultimo_livello}", unsafe_allow_html=True)
        st.progress(progresso, text=f"Progresso verso Elite: {int(progresso*100)}%")
    else:
        st.info("Nessun test disponibile per questo esercizio.")

    st.markdown("---")

    # Descrizione RADAR
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
    livelli_val = livello_mapping

    for categoria in macroaree:
        esercizi_cat = esercizi_df[esercizi_df['categoria'] == categoria]['esercizio']
        test_cat = test_df[(test_df['nome'] == utente['nome']) & (test_df['esercizio'].isin(esercizi_cat))]
        livelli_cat = []
        for _, row in test_cat.iterrows():
            benchmark = benchmark_df[
                (benchmark_df['esercizio'] == row['esercizio']) &
                (benchmark_df['genere'] == row['genere'])
            ]
            benchmark = benchmark.squeeze() if not benchmark.empty else None
            livello_num = 0
            if benchmark is not None:
                tipo = benchmark['tipo_valore']
                try:
                    peso_corporeo = float(row['peso_corporeo'])
                except Exception:
                    peso_corporeo = None
                if tipo == 'kg_rel' and peso_corporeo:
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
                    for livello_nome in reversed(list(livelli_val.keys())):
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
        import plotly.graph_objects as go
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
    st.title("Profilo Atleta")

    if utente is not None and isinstance(utente, dict) and 'nome' in utente:
        atleta = utenti_df[utenti_df['nome'].str.strip().str.lower() == utente['nome'].strip().lower()]
    else:
        atleta = pd.DataFrame()

    st.write("### Dati attuali:")
    if atleta.empty:
        st.warning("⚠️ Nessun atleta selezionato o dati mancanti.")
    else:
        st.write(f"**Nome:** {atleta['nome'].iloc[0]}")
        st.write(f"**Ruolo:** {atleta['ruolo'].iloc[0]}")
        st.write(f"**Data di nascita:** {atleta['data_nascita'].iloc[0]}")
        st.write(f"**Peso corporeo:** {atleta['peso'].iloc[0]} kg")
        st.write(f"**Genere:** {atleta['genere'].iloc[0]}")

    st.write("### Modifica i tuoi dati:")
    if atleta.empty:
        data_nascita_default = datetime.date(2000, 1, 1)
        peso_default = 70.0
        genere_default = "Maschio"
    else:
        data_nascita_raw = atleta['data_nascita'].iloc[0]
        data_nascita_default = pd.to_datetime(data_nascita_raw) if pd.notnull(data_nascita_raw) else datetime.date(2000, 1, 1)
        peso_raw = atleta['peso'].iloc[0]
        peso_default = float(peso_raw) if pd.notnull(peso_raw) else 70.0
        genere_raw = atleta['genere'].iloc[0]
        genere_default = genere_raw if genere_raw in ["Maschio", "Femmina", "Altro"] else "Maschio"

    nuova_data_nascita = st.date_input(
        "Data di nascita",
        value=data_nascita_default,
        min_value=datetime.date(1960, 1, 1)
    )

    nuovo_peso = st.number_input(
        "Peso corporeo (kg)",
        min_value=30.0,
        max_value=200.0,
        step=0.1,
        value=peso_default
    )

    nuovo_genere = st.selectbox(
        "Genere",
        options=["Maschio", "Femmina", "Altro"],
        index=["Maschio", "Femmina", "Altro"].index(genere_default)
    )

    if st.button("Salva modifiche"):
        utenti_df.loc[
            utenti_df['nome'].str.strip().str.lower() == utente['nome'].strip().lower(),
            'data_nascita'
        ] = nuova_data_nascita.strftime("%Y-%m-%d")
        utenti_df.loc[
            utenti_df['nome'].str.strip().str.lower() == utente['nome'].strip().lower(),
            'peso'
        ] = nuovo_peso
        utenti_df.loc[
            utenti_df['nome'].str.strip().str.lower() == utente['nome'].strip().lower(),
            'genere'
        ] = nuovo_genere

        # Salva su Google Sheets
        salva_su_google_sheets(utenti_df, "utenti", "utenti")
        st.success("✅ Modifiche salvate con successo!")


# Pagine Coach
if is_utente_valido() and utente['ruolo'] == 'coach':
    if pagina == "⚙️ Gestione esercizi":
        # Pagina: Gestione esercizi (solo per coach)
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
                carica_esercizi.clear()  # Pulisci la cache PRIMA di ricaricare
                esercizi_df = carica_esercizi()  # Carica i dati aggiornati

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

    elif pagina == "⚙️ Gestione benchmark":
        # Pagina: Gestione benchmark (solo per coach)
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
            if nuovo_esercizio and genere and base and principiante and intermedio and buono and elite:
                nuovo_record = {
                    "esercizio": nuovo_esercizio,
                                    "genere": genere,
                    "base": base,
                    "principiante": principiante,
                    "intermedio": intermedio,
                    "buono": buono,
                    "elite": elite
                }
                benchmark_df = pd.concat([benchmark_df, pd.DataFrame([nuovo_record])], ignore_index=True)
                salva_su_google_sheets(benchmark_df, "benchmark", "benchmark")  # Salva su Google Sheets
                carica_benchmark.clear()  # Svuota la cache prima di ricaricare
                benchmark_df = carica_benchmark()  # Ricarica i dati aggiornati
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

    elif pagina == "➕ Aggiungi Utente":
        # Pagina: Aggiungi Utente (solo per coach)
        st.subheader("➕ Aggiungi un nuovo utente")
        carica_utenti.clear()        # Svuota la cache utenti
        utenti_df = carica_utenti()  # Ricarica dal foglio Google
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
            salva_su_google_sheets(utenti_df, "utenti", "utenti")
            test_df = test_df[test_df["nome"] != utente_da_eliminare]
            salva_su_google_sheets(test_df, "test", "test")
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

        # --- QUI LA MODIFICA FONDAMENTALE ---
        if st.button("Aggiungi utente", key="aggiungi_utente_button"):
            if nuovo_nome and nuovo_pin:
                carica_utenti.clear()  # Pulisci la cache prima di ricaricare!
                utenti_df = carica_utenti()  # Ricarica TUTTI gli utenti dal foglio Google
                st.write("DEBUG: utenti_df dopo ricarica dal foglio:", utenti_df)

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
                    st.write("DEBUG: utenti_df che stai per salvare:", utenti_df)
                    salva_su_google_sheets(utenti_df, "utenti", "utenti")
                    st.success(f"Nuovo utente '{nuovo_nome}' aggiunto con successo come {nuovo_ruolo}!")
                    carica_utenti.clear()
                    utenti_df = carica_utenti()
                    st.write("DEBUG: utenti_df DOPO salvataggio:", utenti_df)
                    st.dataframe(utenti_df)
            else:
                st.error("Compila tutti i campi richiesti.")


    elif pagina == "📋 Storico Dati utenti":
        # Pagina: Storico Dati utenti (solo per coach)
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

    # Gestione della navigazione tra le pagine
if is_utente_valido():
    if utente['ruolo'] == 'coach':
        if pagina == "🏠 Dashboard":
            st.title("🏠 Dashboard Coach")

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

            # --- PANORAMICA RAPIDA COACH ---
            num_atleti = len(utenti_df[utenti_df['ruolo'] == 'atleta'])
            test_df["data"] = pd.to_datetime(test_df["data"])
            data_cutoff = pd.to_datetime(datetime.date.today() - datetime.timedelta(days=30))
            test_ultimo_mese = test_df[test_df["data"] > data_cutoff]
            num_test_ultimo_mese = len(test_ultimo_mese)
            ultimi_test = test_df.sort_values("data", ascending=False).head(5)
            cutoff = datetime.date.today() - datetime.timedelta(weeks=6)
            test_scaduti = test_df[pd.to_datetime(test_df["data"]) < pd.to_datetime(cutoff)]
            atleti_scaduti = test_scaduti["nome"].unique()

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Totale atleti", num_atleti)
                st.metric("Test inseriti (ultimi 30 giorni)", num_test_ultimo_mese)
                if len(atleti_scaduti) > 0:
                    st.warning(f"⚠️ Atleti con test scaduti: {', '.join(atleti_scaduti)}")
                else:
                    st.success("Tutti gli atleti sono aggiornati!")

            with col2:
                st.subheader("Ultimi test inseriti")
                st.dataframe(ultimi_test[["data", "nome", "esercizio", "valore"]])

# Pagina: Dashboard Atleta
    elif pagina == "🏠 Dashboard":
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
