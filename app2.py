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

# --- FONCTIONS TECHNIQUES (GARDÉES) ---
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
        # Gestion propre des booléens pour éviter les sauts d'actualisation
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v'])
    return data

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE (SAISIE) ---
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
    # LOGIQUE CORRIGÉE : Rien n'est marqué comme payé à la saisie
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, "Description": desc, "Montant": valeur, 
        "Année": str(date_op.year), "Payé": False 
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.rerun()

# --- LOGIQUE DE CALCUL GLOBALE ---
df_all = st.session_state.data.copy()

# 1. Total que Julie doit recevoir (50% des ventes non payées)
mask_ventes = (df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == False)
total_du_julie = df_all[mask_ventes]["Montant"].sum() * 0.5

# 2. Cumul de tes remboursements (non encore validés)
mask_remb = (df_all["Type"] == "Remboursement à Julie") & (df_all["Payé"] == False)
total_verse_julie = abs(df_all[mask_remb]["Montant"].sum())

# 3. Reste à payer réel
reste_a_payer = max(0.0, total_du_julie - total_verse_julie)

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Journal", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📑 Journal des Transactions")
    edited_df = st.data_editor(df_all.sort_values("Date", ascending=False).drop(columns=['Année']), use_container_width=True, hide_index=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder modifications"):
        new_df = edited_df.copy()
        new_df['Date'] = pd.to_datetime(new_df['Date'])
        new_df['Année'] = new_df['Date'].dt.year.astype(str)
        conn.update(data=new_df)
        st.session_state.data = new_df
        st.rerun()

with tab3:
    st.subheader("👩‍💻 Suivi Julie")
    col1, col2, col3 = st.columns(3)
    col1.metric("Dette Totale (50%)", f"{total_du_julie:.2f} €")
    col2.metric("Déjà versé (Cumul)", f"{total_verse_julie:.2f} €")
    col3.metric("RESTE À PAYER", f"{reste_a_payer:.2f} €", delta_color="inverse")

    st.divider()
    if total_du_julie > 0:
        prog = min(total_verse_julie / total_du_julie, 1.0)
        st.progress(prog)
        st.write(f"Avancement : **{prog*100:.1f}%**")

        if total_verse_julie >= total_du_julie:
            st.success("✅ Somme atteinte ! Tu peux valider.")
            if st.button("🌟 Valider le remboursement complet"):
                temp_df = st.session_state.data.copy()
                # On valide uniquement les lignes en attente
                temp_df.loc[temp_df["Payé"] == False, "Payé"] = True
                conn.update(data=temp_df)
                st.session_state.data = temp_df
                st.rerun()
        else:
            st.warning(f"Il manque encore **{reste_a_payer:.2f} €** pour solder la dette.")
    else:
        st.success("Aucune dette en cours ! ✨")

with tab4:
    st.subheader("👨‍💻 Suivi Mathéo")
    # Gains validés = 50% des ventes cochées "Payé"
    mask_valide = (df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == True)
    gains_valides = df_all[mask_valide]["Montant"].sum() * 0.5
    st.metric("Tes gains validés mémorisés", f"{gains_valides:.2f} €")
