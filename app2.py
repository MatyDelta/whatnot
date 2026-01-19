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
        # S'assurer que les colonnes vitales existent, sinon les créer vides
        for col in ['Date', 'Type', 'Description', 'Montant', 'Payé', 'Année']:
            if col not in data.columns:
                data[col] = "" if col != 'Montant' else 0.0
        
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'x', 'v', 'vrai'])
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
        with st.spinner("Lecture du ticket..."):
            s_date, s_name, s_price = simple_ocr(img)
            st.session_state['scan_date'] = s_date
            st.session_state['scan_name'] = s_name
            st.session_state['scan_price'] = s_price
            st.session_state['show_scan_info'] = True
            st.rerun()

if st.session_state.get('show_scan_info'):
    st.sidebar.success("✅ Analyse terminée !")
    st.sidebar.info(f"🏢 {st.session_state.get('scan_name')} | 📅 {st.session_state.get('scan_date').strftime('%d/%m/%Y')} | 💶 {st.session_state.get('scan_price'):.2f} €")
    if st.sidebar.button("Masquer le résumé"):
        st.session_state['show_scan_info'] = False
        st.rerun()

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")

date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement à Julie"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01, value=float(st.session_state.get('scan_price', 0.0)))

if st.sidebar.button("Enregistrer l'opération"):
    temp_df = st.session_state.data.copy()
    paye_status = False
    
    if type_op == "Remboursement à Julie":
        valeur = -montant
        paye_status = True
        montant_a_solder = montant * 2
        idx_non_payes = temp_df[(temp_df['Montant'] > 0) & (temp_df['Payé'] == False)].index
        for i in idx_non_payes:
            if montant_a_solder > 0:
                temp_df.at[i, 'Payé'] = True
                montant_a_solder -= temp_df.at[i, 'Montant']
    else:
        valeur = montant if "Vente" in type_op else -montant

    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": paye_status
    }])
    
    st.session_state.data = pd.concat([temp_df, new_row], ignore_index=True)
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.cache_data.clear()
    st.rerun()

# --- CALCULS ---
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# Historique des Lives
lives_history = []
achats = df_all[df_all["Type"] == "Achat Stock (Dépense)"].reset_index()
ventes = df_all[df_all["Type"] == "Vente (Gain net Whatnot)"].reset_index()
for k in range(max(len(achats), len(ventes))):
    res = {"Date": None, "Investissement": 0.0, "Vente": 0.0, "Bénéfice": 0.0}
    if k < len(ventes):
        res["Date"], res["Vente"] = ventes.loc[k, "Date"], ventes.loc[k, "Montant"]
    if k < len(achats):
        if res["Date"] is None: res["Date"] = achats.loc[k, "Date"]
        res["Investissement"] = abs(achats.loc[k, "Montant"])
    res["Bénéfice"] = res["Vente"] - res["Investissement"]
    if res["Date"] is not None: lives_history.append(res)
df_lives = pd.DataFrame(lives_history)

ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
depenses_stock = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
gains_en_attente = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]["Montant"].sum()
total_paye_julie = abs(df_all[df_all["Type"] == "Remboursement à Julie"]["Montant"].sum())
score_partage = (df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum()) / 2

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_total:.2f} €")
    c2.metric("Total Achats", f"-{depenses_stock:.2f} €")
    c3.metric("Bénéfice Brut", f"{(ca_total - depenses_stock):.2f} €")
    
    st.divider()
    cp, cv = st.columns(2)
    cp.success(f"💰 Gains à solder : **{gains_en_attente:.2f} €**")
    cv.warning(f"👉 Part Julie restante : **{(gains_en_attente/2):.2f} €**")

    st.divider()
    st.subheader("📑 Journal")
    
    # --- CORRECTION ICI : Drop sécurisé ---
    df_display = df_all.copy()
    if 'Année' in df_display.columns:
        df_display = df_display.drop(columns=['Année'])
        
    edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True, key="editor", num_rows="dynamic")
    
    if st.button("💾 Sauvegarder les modifications"):
        df_save = edited_df.copy()
        # On rajoute l'année si elle a disparu pour la base de données
        if 'Date' in df_save.columns:
            df_save['Date'] = pd.to_datetime(df_save['Date'])
            df_save['Année'] = df_save['Date'].dt.year.astype(str)
            df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.cache_data.clear()
        st.session_state.data = load_data()
        st.rerun()

with tab2:
    if not df_lives.empty:
        st.dataframe(df_lives, use_container_width=True, hide_index=True)
        st.plotly_chart(px.line(df_lives, x="Date", y="Bénéfice", markers=True), use_container_width=True)

with tab3:
    st.metric("Déjà versé", f"{total_paye_julie:.2f} €")
    st.metric("Gains validés (50%)", f"{score_partage:.2f} €")

with tab4:
    st.metric("Gains validés (50%)", f"{score_partage:.2f} €")
