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
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v'])
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("📸 Scanner un Ticket")
file = st.sidebar.file_uploader("Prendre en photo", type=['jpg', 'jpeg', 'png'])
if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser le ticket"):
        with st.spinner("Lecture..."):
            s_date, s_name, s_price = simple_ocr(img)
            st.session_state['scan_date'], st.session_state['scan_name'], st.session_state['scan_price'] = s_date, s_name, s_price
            st.session_state['show_scan_info'] = True
            st.rerun()

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")
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
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.cache_data.clear()
    st.rerun()

# --- CALCULS LOGIQUE GLOBALE ---
df_all = st.session_state.data.copy()

# 1. Dette réelle : 50% des ventes NON COCHÉES
mask_ventes_dues = (df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == False)
part_due_julie = df_all[mask_ventes_dues]["Montant"].sum() * 0.5

# 2. Crédit accumulé : Somme des remboursements NON COCHÉS
mask_remb_encours = (df_all["Type"] == "Remboursement à Julie") & (df_all["Payé"] == False)
remboursements_non_utilises = abs(df_all[mask_remb_encours]["Montant"].sum())

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Journal", "🎬 Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📑 Journal des Transactions")
    edited_df = st.data_editor(df_all.sort_values("Date", ascending=False).drop(columns=['Année']), use_container_width=True, hide_index=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder modifications"):
        new_df = edited_df.copy()
        new_df['Date'] = pd.to_datetime(new_df['Date'])
        new_df['Année'] = new_df['Date'].dt.year.astype(str)
        conn.update(data=new_df)
        st.session_state.data = new_df
        st.cache_data.clear()
        st.rerun()

with tab3:
    st.subheader("👩‍💻 Suivi du Remboursement (Julie)")
    
    if part_due_julie > 0:
        progression = min(remboursements_non_utilises / part_due_julie, 1.0)
        
        c1, c2 = st.columns(2)
        c1.metric("Dû à Julie (50%)", f"{part_due_julie:.2f} €")
        c2.metric("Versé (En attente)", f"{remboursements_non_utilises:.2f} €")
        
        st.write(f"**Progression :** {remboursements_non_utilises:.2f}€ / {part_due_julie:.2f}€")
        st.progress(progression)
        
        if progression >= 1.0:
            st.balloons()
            st.success("✅ Montant total atteint ! Tu peux maintenant valider.")
            if st.button("🌟 Valider et clôturer cette période"):
                temp_df = st.session_state.data.copy()
                # On ne coche que les lignes qui n'étaient pas encore payées
                temp_df.loc[temp_df["Type"] == "Vente (Gain net Whatnot)", "Payé"] = True
                temp_df.loc[temp_df["Type"] == "Remboursement à Julie", "Payé"] = True
                
                st.session_state.data = temp_df
                df_save = temp_df.copy()
                df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
                conn.update(data=df_save)
                st.cache_data.clear()
                st.rerun()
        else:
            st.info(f"Reste à verser : **{(part_due_julie - remboursements_non_utilises):.2f} €**")
            
        st.divider()
        st.write("### 🕒 Remboursements en attente de validation")
        st.dataframe(df_all[mask_remb_encours][["Date", "Description", "Montant"]], use_container_width=True)
    else:
        st.success("Toutes les dettes sont réglées ! ✨")
        st.progress(1.0)

with tab4:
    # Mathéo voit sa part sur les ventes dont le statut est "Payé"
    mask_paye = (df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == True)
    score_matheo = df_all[mask_paye]["Montant"].sum() * 0.5
    st.metric("Tes gains personnels validés (50%)", f"{score_matheo:.2f} €")
