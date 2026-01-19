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
    """Extrait les infos d'un ticket"""
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
    """Charge et nettoie les données"""
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        for col in ['Date', 'Type', 'Description', 'Montant', 'Payé', 'Année']:
            if col not in data.columns:
                data[col] = "" if col != 'Montant' else 0.0
        
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        # Gestion flexible du format booléen
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v'])
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE (Scanner & Saisie) ---
st.sidebar.header("📸 Scanner un Ticket")
file = st.sidebar.file_uploader("Prendre en photo", type=['jpg', 'jpeg', 'png'])

if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser le ticket"):
        with st.spinner("Lecture en cours..."):
            s_date, s_name, s_price = simple_ocr(img)
            st.session_state['scan_date'] = s_date
            st.session_state['scan_name'] = s_name
            st.session_state['scan_price'] = s_price
            st.session_state['show_scan_info'] = True
            st.rerun()

if st.session_state.get('show_scan_info'):
    st.sidebar.info(f"🏢 {st.session_state.get('scan_name')} | 📅 {st.session_state.get('scan_date').strftime('%d/%m/%Y')} | 💶 {st.session_state.get('scan_price'):.2f} €")

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")
date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement à Julie"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01, value=float(st.session_state.get('scan_price', 0.0)))

if st.sidebar.button("Enregistrer l'opération"):
    valeur = montant if "Vente" in type_op else -montant
    # Par défaut, un remboursement est considéré comme validé, une vente est False (non payée)
    paye_bool = True if type_op == "Remboursement à Julie" else False
    
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": paye_bool
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    
    # Sauvegarde
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.cache_data.clear()
    st.sidebar.success("Enregistré !")
    st.rerun()

# --- CALCULS ---
df_all = st.session_state.data.sort_values("Date", ascending=False).reset_index(drop=True)

# 1. Calcul Dette et Remboursement
ventes_non_payees = df_all[(df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == False)]
dette_brute = ventes_non_payees["Montant"].sum()
part_due_julie = dette_brute / 2

# Remboursements saisis qui attendent la clôture des ventes
total_rembourse_en_attente = abs(df_all[(df_all["Type"] == "Remboursement à Julie") & (dette_brute > 0)]["Montant"].sum())

# 2. Historique des Lives
lives_history = []
achats_df = df_all[df_all["Type"] == "Achat Stock (Dépense)"].copy()
ventes_df = df_all[df_all["Type"] == "Vente (Gain net Whatnot)"].copy()
for k in range(max(len(achats_df), len(ventes_df))):
    res = {"Date": None, "Investissement": 0.0, "Vente": 0.0, "Bénéfice": 0.0}
    if k < len(ventes_df):
        res["Date"], res["Vente"] = ventes_df.iloc[k]["Date"], ventes_df.iloc[k]["Montant"]
    if k < len(achats_df):
        if res["Date"] is None: res["Date"] = achats_df.iloc[k]["Date"]
        res["Investissement"] = abs(achats_df.iloc[k]["Montant"])
    res["Bénéfice"] = res["Vente"] - res["Investissement"]
    if res["Date"] is not None: lives_history.append(res)
df_lives = pd.DataFrame(lives_history)

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📑 Journal & Actions")
    st.info("💡 Pour supprimer : cochez la ligne, appuyez sur 'Suppr' (clavier), puis sauvegardez.")
    
    df_display = df_all.copy()
    if 'Année' in df_display.columns:
        df_display = df_display.drop(columns=['Année'])
    
    edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True, key="journal_editor", num_rows="dynamic")
    
    if st.button("💾 Sauvegarder les modifications"):
        new_df = edited_df.copy()
        new_df['Date'] = pd.to_datetime(new_df['Date'])
        new_df['Année'] = new_df['Date'].dt.year.astype(str)
        conn.update(data=new_df)
        st.cache_data.clear()
        st.success("Synchronisé !")
        st.rerun()

with tab2:
    st.subheader("🍿 Rentabilité des Sessions")
    if not df_lives.empty:
        st.dataframe(df_lives, use_container_width=True, hide_index=True)
        st.plotly_chart(px.line(df_lives, x="Date", y="Bénéfice", markers=True), use_container_width=True)

with tab3:
    st.subheader("👩‍💻 Remboursement Julie")
    
    if part_due_julie > 0:
        progression = min(total_rembourse_en_attente / part_due_julie, 1.0)
        st.write(f"**Progression : {total_rembourse_en_attente:.2f}€ / {part_due_julie:.2f}€**")
        st.progress(progression)
        
        if progression >= 1.0:
            st.balloons()
            st.success("🎯 Objectif atteint ! Tu peux maintenant clôturer ces ventes.")
            if st.button("✅ Valider le remboursement et passer en 'Payé'"):
                temp_df = st.session_state.data.copy()
                # On passe toutes les ventes non payées à True
                temp_df.loc[(temp_df["Type"] == "Vente (Gain net Whatnot)") & (temp_df["Payé"] == False), "Payé"] = True
                st.session_state.data = temp_df
                df_save = temp_df.copy()
                df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
                conn.update(data=df_save)
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning(f"Encore { (part_due_julie - total_rembourse_en_attente):.2f}€ à rembourser.")
    else:
        st.success("Toutes les dettes sont soldées ! ✨")
        st.progress(1.0)

    st.divider()
    st.write("### 💸 Historique des Remboursements")
    st.dataframe(df_all[df_all["Type"] == "Remboursement à Julie"][["Date", "Description", "Montant"]], use_container_width=True)

with tab4:
    st.subheader("👨‍💻 Mathéo")
    score_valid = (df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum()) / 2
    st.metric("Tes gains validés (50%)", f"{score_valid:.2f} €")
    st.info("Ce montant correspond à ta part sur les lives déjà totalement remboursés à Julie.")
