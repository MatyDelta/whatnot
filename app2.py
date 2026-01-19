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
    # Lecture sans cache pour garantir la persistence des données
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        for col in ['Date', 'Type', 'Description', 'Montant', 'Payé', 'Année']:
            if col not in data.columns:
                data[col] = "" if col != 'Montant' else 0.0
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        # Conversion stricte pour Google Sheets (évite les bugs d'actualisation)
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v', 'vrai'])
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("📸 Scanner / Saisir")
file = st.sidebar.file_uploader("Scanner un ticket", type=['jpg', 'jpeg', 'png'])
if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser"):
        with st.spinner("Lecture..."):
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
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, "Description": desc, "Montant": valeur, 
        "Année": str(date_op.year), "Payé": False 
    }])
    updated_df = pd.concat([st.session_state.data, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.session_state.data = updated_df
    st.cache_data.clear()
    st.rerun()

# --- LOGIQUE DE CALCUL ---
df_all = st.session_state.data.copy()

# 1. Ce que Julie doit recevoir (50% des ventes non payées)
ventes_dues = df_all[(df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == False)]
total_du_julie = ventes_dues["Montant"].sum() * 0.5

# 2. Cumul des remboursements Mathéo (non encore validés)
remb_faits = abs(df_all[(df_all["Type"] == "Remboursement à Julie") & (df_all["Payé"] == False)]["Montant"].sum())

# 3. Reste à payer réel
reste_a_payer = max(0.0, total_du_julie - remb_faits)

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Journal", "🎬 Historique", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📑 Journal des Transactions")
    edited_df = st.data_editor(df_all.sort_values("Date", ascending=False).drop(columns=['Année']), use_container_width=True, hide_index=True)
    if st.button("💾 Sauvegarder les modifications du Journal"):
        edited_df['Date'] = pd.to_datetime(edited_df['Date'])
        edited_df['Année'] = edited_df['Date'].dt.year.astype(str)
        conn.update(data=edited_df)
        st.session_state.data = edited_df
        st.success("Données mémorisées !")
        st.rerun()

with tab3:
    st.subheader("Espace Julie")
    col_j1, col_j2, col_j3 = st.columns(3)
    col_j1.metric("Total dû (50%)", f"{total_du_julie:.2f} €")
    col_j2.metric("Déjà versé", f"{remb_faits:.2f} €")
    col_j3.metric("RESTE À PERCEVOIR", f"{reste_a_payer:.2f} €", delta=f"-{remb_faits:.2f}", delta_color="inverse")

    st.divider()
    st.write("### 🎯 Progression du remboursement")
    if total_du_julie > 0:
        prog = min(remb_faits / total_du_julie, 1.0)
        st.progress(prog)
        st.write(f"Julie a reçu **{prog*100:.1f}%** de sa part.")
        
        if reste_a_payer <= 0:
            st.balloons()
            st.success("✅ La somme due est atteinte !")
            if st.button("🌟 Valider le remboursement complet (Reset)"):
                temp_df = st.session_state.data.copy()
                # On valide TOUT ce qui était en attente
                temp_df.loc[temp_df["Payé"] == False, "Payé"] = True
                conn.update(data=temp_df)
                st.session_state.data = temp_df
                st.rerun()
    else:
        st.info("Aucune dette en cours. Julie est à jour !")

with tab4:
    st.subheader("Espace Mathéo")
    # Gains validés = 50% des ventes marquées "Payé"
    score_m = (df_all[(df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == True)]["Montant"].sum()) * 0.5
    st.metric("Tes gains validés mémorisés", f"{score_m:.2f} €")
