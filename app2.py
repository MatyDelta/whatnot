import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import pytesseract
from PIL import Image
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker MJTGC", layout="wide", page_icon="🤝")
st.title("🤝 MJTGC - Whatnot Duo Tracker & Scanner")

# --- LIAISON GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        data['Payé'] = data['Payé'].astype(str).str.lower().isin(['true', '1', 'vrai', 'x', 'v']).astype(bool)
    return data

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- FONCTION SCANNER OCR ---
def scan_receipt(image):
    # Transformation de l'image en texte
    text = pytesseract.image_to_string(image)
    
    # Extraction du montant (cherche le dernier chiffre avec une virgule ou un point)
    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    total_price = float(prices[-1].replace(',', '.')) if prices else 0.0
    
    # Extraction de la date (format DD/MM/YYYY)
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    receipt_date = datetime.strptime(dates[0], "%d/%m/%y") if dates else datetime.now()
    
    # Extraction du nom du magasin (première ligne non vide)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    store_name = lines[0] if lines else "Magasin Inconnu"
    
    return receipt_date, store_name, total_price

# --- BARRE LATÉRALE : ENTRÉES ---
st.sidebar.header("📸 Scanner un Ticket")
uploaded_file = st.sidebar.file_uploader("Prendre une photo", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Ticket chargé", use_container_width=True)
    if st.sidebar.button("Analyser le ticket"):
        r_date, r_name, r_price = scan_receipt(img)
        # On injecte les résultats dans les champs manuels ci-dessous
        st.session_state.r_date = r_date
        st.session_state.r_name = r_name
        st.session_state.r_price = r_price
        st.sidebar.success("Analyse terminée ! Vérifiez les champs ci-dessous.")

st.sidebar.divider()

st.sidebar.header("📝 Saisie Manuelle / Correction")
# Utilisation de valeurs par défaut venant du scan si elles existent
date_op = st.sidebar.date_input("Date", st.session_state.get('r_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description", st.session_state.get('r_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0, value=st.session_state.get('r_price', 0.0))

if st.sidebar.button("Valider l'entrée dans l'historique"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    # Sauvegarde Google Sheets
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.sidebar.success("Entrée enregistrée !")
    st.rerun()

# --- RESTE DU CODE (LOGIQUE DE CALCUL ET ONGLETS) ---
# [Ici on garde la même logique de calcul et les 4 onglets précédents]
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# ... (Calculs CA, Achats, Reste à partager identiques) ...

tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale")
    # Affichage des métriques...
    
    st.divider()
    st.subheader("📑 Historique Complet des Transactions")
    # Le data_editor permet de modifier/renseigner des entrées directement dans le tableau
    edited_df = st.data_editor(
        df_all, 
        use_container_width=True, 
        hide_index=True, 
        key="editor_global",
        num_rows="dynamic" # Permet d'ajouter des lignes directement dans le tableau
    )
    if st.button("💾 Sauvegarder toutes les modifications"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.success("Toutes les modifications ont été enregistrées !")
        st.rerun()
