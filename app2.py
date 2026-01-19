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
    text = pytesseract.image_to_string(image)
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
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
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
        s_date, s_name, s_price = simple_ocr(img)
        st.session_state['scan_date'] = s_date
        st.session_state['scan_name'] = s_name
        st.session_state['scan_price'] = s_price
        st.sidebar.success("Analyse terminée !")

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")

date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement Julie"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0, value=st.session_state.get('scan_price', 0.0))

if st.sidebar.button("Enregistrer l'opération"):
    # Logique de signe : Vente = Positif / Achat et Remboursement = Négatif
    valeur = montant if "Vente" in type_op else -montant
    
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year)
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    
    for key in ['scan_date', 'scan_name', 'scan_price']:
        if key in st.session_state: del st.session_state[key]
    st.sidebar.success("Enregistré !")
    st.rerun()

# --- LOGIQUE DE CALCUL ---
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# 1. Calcul de la dette théorique (50% des gains de ventes)
total_ventes = df_all[df_all["Type"] == "Vente (Gain net Whatnot)"]["Montant"].sum()
dette_initiale_julie = total_ventes / 2

# 2. Somme des remboursements (montants négatifs enregistrés sous "Remboursement Julie")
total_deja_paye = abs(df_all[df_all["Type"] == "Remboursement Julie"]["Montant"].sum())

# 3. Calcul par soustraction
reste_a_verser = dette_initiale_julie - total_deja_paye
progression = min(total_deja_paye / dette_initiale_julie, 1.0) if dette_initiale_julie > 0 else 1.0

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["💰 Remboursement Julie", "🎬 Historique Lives", "📊 Stats Globales"])

with tab1:
    st.subheader("💸 État du compte de Julie")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Dû total (50% Gains)", f"{dette_initiale_julie:.2f} €")
    c2.metric("Déjà envoyé", f"{total_deja_paye:.2f} €")
    c3.metric("Reste à payer", f"{reste_a_verser:.2f} €", delta=f"-{total_deja_paye:.2f}")

    st.write(f"**Progression du remboursement : {progression*100:.1f}%**")
    st.progress(progression)

    st.divider()
    st.subheader("📑 Historique complet des transactions")
    # L'utilisateur peut modifier les montants ici si besoin
    edited_df = st.data_editor(df_all, use_container_width=True, hide_index=True)
    if st.button("💾 Sauvegarder les modifications"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.rerun()

with tab2:
    st.subheader("🍿 Rentabilité par Live")
    lives_history = []
    # On filtre pour n'avoir que les achats et ventes pour le calcul de rentabilité
    temp_df = df_all[df_all["Type"].isin(["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])]
    i = 0
    while i < len(temp_df) - 1:
        curr = temp_df.iloc[i]
        nxt = temp_df.iloc[i+1]
        if (curr['Montant'] * nxt['Montant']) < 0:
            gain_net = curr['Montant'] + nxt['Montant']
            lives_history.append({
                "Date": nxt['Date'],
                "Détails": f"{curr['Description']} + {nxt['Description']}",
                "Bénéfice": gain_net
            })
            i += 2
        else: i += 1
    
    if lives_history:
        st.dataframe(pd.DataFrame(lives_history), use_container_width=True, hide_index=True)
    else:
        st.info("Ajoutez des données pour voir les calculs par live.")

with tab3:
    st.subheader("📈 Performance MJTGC")
    achats = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
    st.metric("Chiffre d'Affaire Total", f"{total_ventes:.2f} €")
    st.metric("Investissement Stock", f"-{achats:.2f} €")
    st.metric("Bénéfice Net Global", f"{(total_ventes - achats):.2f} €")
