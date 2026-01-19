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
    text = pytesseract.image_to_string(image)
    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    price = float(prices[-1].replace(',', '.')) if prices else 0.0
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    date_found = pd.to_datetime(dates[0], dayfirst=True) if dates else datetime.now()
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
        # On garde la colonne Payé pour la compatibilité, mais on gère le reste par calcul
        if 'Payé' not in data.columns:
            data['Payé'] = False
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
    # Si c'est un achat ou un remboursement, on enregistre en négatif pour la balance
    valeur = montant if "Vente" in type_op else -montant
    
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": True if type_op == "Remboursement Julie" else False
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    
    for key in ['scan_date', 'scan_name', 'scan_price']:
        if key in st.session_state: del st.session_state[key]
    st.sidebar.success("Enregistré et synchronisé !")
    st.rerun()

# --- LOGIQUE DE CALCUL MJTGC ---
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# 1. Calcul de la dette Julie (50% des Ventes)
total_ventes = df_all[df_all["Type"] == "Vente (Gain net Whatnot)"]["Montant"].sum()
dette_julie_totale = total_ventes / 2

# 2. Calcul des remboursements déjà faits (on somme les valeurs négatives du type remboursement)
total_remboursements = abs(df_all[df_all["Type"] == "Remboursement Julie"]["Montant"].sum())

# 3. Solde restant
reste_a_payer = dette_julie_totale - total_remboursements
progression = min(total_remboursements / dette_julie_totale, 1.0) if dette_julie_totale > 0 else 1.0

# 4. Calcul global pour les stats
achats_historique = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["💰 Suivi Julie", "🎬 Historique Lives", "📊 Stats Globales", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("💳 Remboursement de Julie")
    
    # Métriques principales
    c1, c2, c3 = st.columns(3)
    c1.metric("Dette Totale (50% gains)", f"{dette_julie_totale:.2f} €")
    c2.metric("Déjà remboursé", f"{total_remboursements:.2f} €")
    c3.metric("Reste à payer", f"{reste_a_payer:.2f} €", delta=f"-{total_remboursements:.2f}")

    # Barre de progression
    st.write(f"**Progression du remboursement : {progression*100:.1f}%**")
    st.progress(progression)

    if reste_a_payer <= 0 and total_ventes > 0:
        st.success("✅ Julie est totalement remboursée !")

    st.divider()
    st.subheader("📑 Historique des transactions")
    edited_df = st.data_editor(df_all, use_container_width=True, hide_index=True, key="editor")
    if st.button("💾 Sauvegarder les modifications"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.rerun()

with tab2:
    st.subheader("🍿 Rentabilité par Live")
    # Logique simple de pairing achat/vente
    lives_history = []
    temp_df = df_all[df_all["Type"] != "Remboursement Julie"] # On ignore les remboursements ici
    i = 0
    while i < len(temp_df) - 1:
        curr = temp_df.iloc[i]
        nxt = temp_df.iloc[i+1]
        if (curr['Montant'] * nxt['Montant']) < 0:
            gain_net = curr['Montant'] + nxt['Montant']
            lives_history.append({
                "Date": nxt['Date'],
                "Détails": f"{curr['Description']} + {nxt['Description']}",
                "Invest": min(curr['Montant'], nxt['Montant']),
                "Vente": max(curr['Montant'], nxt['Montant']),
                "Bénéfice": gain_net
            })
            i += 2
        else: i += 1
    
    if lives_history:
        df_lives = pd.DataFrame(lives_history)
        st.dataframe(df_lives, use_container_width=True, hide_index=True)
        fig = px.bar(df_lives, x="Date", y="Bénéfice", color="Bénéfice")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Besoin d'un achat et d'une vente pour calculer un live.")

with tab3:
    st.subheader("📈 Performance MJTGC")
    col1, col2 = st.columns(2)
    col1.metric("Chiffre d'Affaire Total", f"{total_ventes:.2f} €")
    col2.metric("Total Achats Stock", f"-{achats_historique:.2f} €")
    
    st.metric("Bénéfice Brut du Duo", f"{(total_ventes - achats_historique):.2f} €")

with tab4:
    st.subheader("👨‍💻 Espace Mathéo")
    st.write("Ici s'affiche ce qu'il te reste après avoir payé Julie.")
    mon_gain = (total_ventes / 2) - achats_historique
    st.metric("Mon Bénéfice Net (Ventes/2 - Achats)", f"{mon_gain:.2f} €")
