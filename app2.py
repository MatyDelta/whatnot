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
    """Analyse l'image pour extraire Date, Magasin et Prix"""
    # Conversion en niveaux de gris pour améliorer l'OCR
    image = image.convert('L')
    text = pytesseract.image_to_string(image, lang='fra')
    
    # Cherche un montant (ex: 12.34 ou 12,34)
    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    price = float(prices[-1].replace(',', '.')) if prices else 0.0
    
    # Cherche une date (JJ/MM/AAAA)
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    date_found = pd.to_datetime(dates[0], dayfirst=True) if dates else datetime.now()
    
    # Nom du magasin (prend la 1ère ligne non vide)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0][:20] if lines else "Ticket Scan"
    
    return date_found, name, price

def load_data():
    """Charge les données depuis Google Sheets"""
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        data['Payé'] = data['Payé'].astype(str).str.lower().isin(['true', '1', 'vrai', 'x', 'v']).astype(bool)
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE (Scanner + Saisie) ---
st.sidebar.header("📸 Scanner un Ticket")
file = st.sidebar.file_uploader("Prendre en photo", type=['jpg', 'jpeg', 'png'])

if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser le ticket"):
        with st.spinner("Lecture du ticket en cours..."):
            s_date, s_name, s_price = simple_ocr(img)
            
            # Stockage en mémoire
            st.session_state['scan_date'] = s_date
            st.session_state['scan_name'] = s_name
            st.session_state['scan_price'] = s_price
            st.session_state['show_scan_info'] = True # Flag pour afficher le résumé
            st.rerun()

# Affichage du résumé du scan (Persistant grâce au session_state)
if st.session_state.get('show_scan_info'):
    st.sidebar.success("✅ Analyse terminée !")
    st.sidebar.info(f"""
    **Données détectées :**
    - 🏢 **Magasin :** {st.session_state.get('scan_name')}
    - 📅 **Date :** {st.session_state.get('scan_date').strftime('%d/%m/%Y')}
    - 💶 **Prix :** {st.session_state.get('scan_price'):.2f} €
    """)
    if st.sidebar.button("Masquer le résumé"):
        st.session_state['show_scan_info'] = False
        st.rerun()

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")

# Utilisation des données scannées si elles existent
date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
# Step 0.01 pour autoriser les centimes
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01, value=float(st.session_state.get('scan_price', 0.0)))

if st.sidebar.button("Enregistrer l'opération"):
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
    
    # Sauvegarde vers Google Sheets
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    
    # Nettoyage de la mémoire du scan après enregistrement
    for key in ['scan_date', 'scan_name', 'scan_price', 'show_scan_info']:
        if key in st.session_state: del st.session_state[key]
        
    st.sidebar.success("Enregistré et synchronisé !")
    st.rerun()

# --- LOGIQUE DE CALCUL MJTGC ---
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# 1. Calcul des Lives (Groupement par 2)
lives_history = []
i = 0
while i < len(df_all) - 1:
    curr = df_all.iloc[i]
    nxt = df_all.iloc[i+1]
    if (curr['Montant'] * nxt['Montant']) < 0:
        gain_net = curr['Montant'] + nxt['Montant']
        lives_history.append({
            "Date": nxt['Date'],
            "Détails": f"{curr['Description']} + {nxt['Description']}",
            "Investissement": min(curr['Montant'], nxt['Montant']),
            "Vente": max(curr['Montant'], nxt['Montant']),
            "Bénéfice Net": gain_net
        })
        i += 2
    else:
        i += 1
df_lives = pd.DataFrame(lives_history)

# 2. Variables de performance
ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum()
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())
gains_non_payes = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]["Montant"].sum()
gains_valides = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum()

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_historique:.2f} €")
    c2.metric("Total Achats", f"-{achats_historique:.2f} €")
    c3.metric("Bénéfice Brut", f"{(ca_historique - achats_historique):.2f} €")
    
    st.divider()
    st.subheader("💳 Paiements en cours")
    col_pay, col_ver = st.columns(2)
    with col_pay:
        st.success(f"💰 Gains à partager : **{gains_non_payes:.2f} €**")
    with col_ver:
        st.info(f"👉 Verser à Julie (50%) : **{(gains_non_payes/2):.2f} €**")

    st.divider()
    st.subheader("📑 Toutes les transactions")
    edited_df = st.data_editor(df_all, use_container_width=True, hide_index=True, key="editor", num_rows="dynamic")
    if st.button("💾 Sauvegarder les modifications"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.rerun()

with tab2:
    st.subheader("🍿 Rentabilité par Live")
    if not df_lives.empty:
        st.dataframe(df_lives, use_container_width=True, hide_index=True)
        fig = px.bar(df_lives, x="Date", y="Bénéfice Net", color="Bénéfice Net")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ajoutez un achat et une vente pour voir le calcul.")

with tab3:
    st.subheader("🏆 Score Julie")
    st.metric("Total encaissé (Validé)", f"{(gains_valides / 2):.2f} €")

with tab4:
    st.subheader("🏆 Score Mathéo")
    st.metric("Total encaissé (Validé)", f"{(gains_valides / 2):.2f} €")
