import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker MJTGC", layout="wide")
st.title("🤝 MJTGC - Whatnot Duo Tracker")

# --- LIAISON GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTIONS TECHNIQUES ---
def simple_ocr(image):
    image = image.convert('L')
    text = pytesseract.image_to_string(image, lang='fra')
    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    price = float(prices[-1].replace(',', '.')) if prices else 0.0
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    date_found = pd.to_datetime(dates[0], dayfirst=True) if dates else datetime.now()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0][:20] if lines else "Ticket Scan"
    return date_found, name, price

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        for col in ['Date', 'Type', 'Description', 'Montant', 'Payé', 'Année']:
            if col not in data.columns:
                data[col] = "" if col != 'Montant' else 0.0
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        # Nettoyage strict des booléens pour éviter les erreurs de lecture
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v', 'vrai'])
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("📸 Scanner / Saisir")
file = st.sidebar.file_uploader("Prendre en photo", type=['jpg', 'jpeg', 'png'])

if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser le ticket"):
        with st.spinner("Analyse..."):
            s_date, s_name, s_price = simple_ocr(img)
            st.session_state['scan_date'], st.session_state['scan_name'], st.session_state['scan_price'] = s_date, s_name, s_price
            st.session_state['show_scan_info'] = True
            st.rerun()

st.sidebar.divider()
date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement à Julie"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01, value=float(st.session_state.get('scan_price', 0.0)))

if st.sidebar.button("Enregistrer l'opération"):
    # ICI : On enregistre l'opération, mais on ne valide RIEN (Payé reste False)
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
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.rerun()

# --- LOGIQUE DE CALCUL STRICT ---
df_calc = st.session_state.data.copy()

# 1. Dette totale : 50% de TOUTES les ventes non payées
mask_ventes = (df_calc["Type"] == "Vente (Gain net Whatnot)") & (df_calc["Payé"] == False)
dette_a_rembourser = df_calc[mask_ventes]["Montant"].sum() * 0.5

# 2. Cagnotte : Somme de TOUS les remboursements non encore validés
mask_remb = (df_calc["Type"] == "Remboursement à Julie") & (df_calc["Payé"] == False)
cagnotte_remboursements = abs(df_calc[mask_remb]["Montant"].sum())

# 3. Ce qu'il manque encore
reste_a_donner = max(0.0, dette_a_rembourser - cagnotte_remboursements)

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Journal", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📑 Journal des Transactions")
    edited_df = st.data_editor(df_calc.sort_values("Date", ascending=False).drop(columns=['Année']), use_container_width=True, hide_index=True)
    if st.button("💾 Sauvegarder modifications"):
        new_df = edited_df.copy()
        new_df['Date'] = pd.to_datetime(new_df['Date'])
        new_df['Année'] = new_df['Date'].dt.year.astype(str)
        conn.update(data=new_df)
        st.session_state.data = new_df
        st.rerun()

with tab3:
    st.subheader("👩‍💻 Suivi du Remboursement Julie")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Somme due (1/2)", f"{dette_a_rembourser:.2f} €")
    col2.metric("Cumul déjà versé", f"{cagnotte_remboursements:.2f} €")
    col3.metric("RESTE À DONNER", f"{reste_a_donner:.2f} €", delta_color="inverse")

    if dette_a_rembourser > 0:
        prog = min(cagnotte_remboursements / dette_a_rembourser, 1.0)
        st.write(f"**Progression : {cagnotte_remboursements:.2f}€ / {dette_a_rembourser:.2f}€**")
        st.progress(prog)

        if cagnotte_remboursements >= dette_a_rembourser:
            st.balloons()
            st.success("✅ C'est bon ! Tu as fini de rembourser Julie.")
            if st.button("🌟 VALIDER : Tout cocher et remettre à zéro"):
                temp_df = st.session_state.data.copy()
                # On coche toutes les lignes du cycle actuel
                temp_df.loc[temp_df["Payé"] == False, "Payé"] = True
                conn.update(data=temp_df)
                st.session_state.data = temp_df
                st.rerun()
        else:
            st.warning(f"Continue ! Il manque encore **{reste_a_donner:.2f}€** pour que je valide.")
    else:
        st.success("Julie est à jour. Aucune dette ! ✨")

with tab4:
    st.subheader("👨‍💻 Suivi Mathéo")
    # Tes gains validés = 50% des ventes dont le statut est ENFIN "Payé"
    score = (df_calc[(df_calc["Type"] == "Vente (Gain net Whatnot)") & (df_calc["Payé"] == True)]["Montant"].sum()) * 0.5
    st.metric("Gains personnels sécurisés", f"{score:.2f} €")
