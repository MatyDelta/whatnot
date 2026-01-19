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
        st.session_state.pop('show_scan_info', None)
        st.rerun()

st.sidebar.divider()
st.sidebar.header("📝 Saisir une opération")

date_op = st.sidebar.date_input("Date", st.session_state.get('scan_date', datetime.now()))
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement à Julie"])
desc = st.sidebar.text_input("Description", st.session_state.get('scan_name', ""))
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01, value=float(st.session_state.get('scan_price', 0.0)))

if st.sidebar.button("Enregistrer l'opération"):
    # LOGIQUE : Tout est enregistré en 'Non Payé' par défaut. On additionnera plus tard.
    valeur = montant if "Vente" in type_op else -montant
    
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False # RESTE FALSE POUR ADITIONNER PLUS TARD
    }])
    
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.cache_data.clear()
    st.rerun()

# --- CALCULS LOGIQUES ---
df_all = st.session_state.data.copy()

# 1. Dette totale actuelle (50% des ventes non payées)
mask_ventes_dues = (df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == False)
dette_totale_julie = df_all[mask_ventes_dues]["Montant"].sum() * 0.5

# 2. Cumul des remboursements déjà faits (non encore validés)
mask_remb_faits = (df_all["Type"] == "Remboursement à Julie") & (df_all["Payé"] == False)
cumul_remboursements = abs(df_all[mask_remb_faits]["Montant"].sum())

# 3. Reste à payer réel
reste_a_payer = max(0.0, dette_totale_julie - cumul_remboursements)

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance & Journal")
    # Stats rapides
    ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
    depenses_stock = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
    
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_total:.2f} €")
    c2.metric("Total Achats", f"-{depenses_stock:.2f} €")
    c3.metric("Bénéfice Brut", f"{(ca_total - depenses_stock):.2f} €")
    
    st.divider()
    
    # Editeur de journal
    edited_df = st.data_editor(df_all.sort_values("Date", ascending=False).drop(columns=['Année']), use_container_width=True, hide_index=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder les modifications"):
        new_df = edited_df.copy()
        new_df['Date'] = pd.to_datetime(new_df['Date'])
        new_df['Année'] = new_df['Date'].dt.year.astype(str)
        conn.update(data=new_df)
        st.session_state.data = new_df
        st.rerun()

with tab2:
    # Historique des Lives (Fusion Investissement / Vente par ligne)
    achats_live = df_all[df_all["Type"] == "Achat Stock (Dépense)"].copy()
    ventes_live = df_all[df_all["Type"] == "Vente (Gain net Whatnot)"].copy()
    lives_history = []
    for k in range(max(len(achats_live), len(ventes_live))):
        res = {"Date": None, "Investissement": 0.0, "Vente": 0.0, "Bénéfice": 0.0}
        if k < len(ventes_live):
            res["Date"], res["Vente"] = ventes_live.iloc[k]["Date"], ventes_live.iloc[k]["Montant"]
        if k < len(achats_live):
            if res["Date"] is None: res["Date"] = achats_live.iloc[k]["Date"]
            res["Investissement"] = abs(achats_live.iloc[k]["Montant"])
        res["Bénéfice"] = res["Vente"] - res["Investissement"]
        if res["Date"] is not None: lives_history.append(res)
    
    if lives_history:
        df_l = pd.DataFrame(lives_history)
        st.dataframe(df_l, use_container_width=True, hide_index=True)
        st.plotly_chart(px.line(df_l, x="Date", y="Bénéfice", markers=True), use_container_width=True)

with tab3:
    st.subheader("👩‍💻 Suivi de Julie")
    c_j1, c_j2, c_j3 = st.columns(3)
    c_j1.metric("Dette Totale (50%)", f"{dette_totale_julie:.2f} €")
    c_j2.metric("Tes remboursements", f"{cumul_remboursements:.2f} €")
    c_j3.metric("RESTE À PAYER", f"{reste_a_payer:.2f} €", delta_color="inverse")

    st.divider()
    if dette_totale_julie > 0:
        prog = min(cumul_remboursements / dette_totale_julie, 1.0)
        st.write(f"**Progression vers la validation :** {prog*100:.1f}%")
        st.progress(prog)

        if cumul_remboursements >= dette_totale_julie:
            st.balloons()
            st.success("🎯 Somme totale atteinte !")
            if st.button("✅ VALIDER LE REMBOURSEMENT COMPLET"):
                temp_df = st.session_state.data.copy()
                # On valide TOUT le cycle actuel (Ventes et Remboursements)
                temp_df.loc[temp_df["Payé"] == False, "Payé"] = True
                conn.update(data=temp_df)
                st.session_state.data = temp_df
                st.rerun()
        else:
            st.info(f"Verse encore **{reste_a_payer:.2f} €** pour pouvoir clôturer ce remboursement.")
    else:
        st.success("Aucune dette. Julie est remboursée ! ✨")

with tab4:
    st.subheader("👨‍💻 Suivi de Mathéo")
    # Tes gains ne sont validés que sur les lignes déjà "Payées" (archivées)
    score_partage = (df_all[(df_all["Type"] == "Vente (Gain net Whatnot)") & (df_all["Payé"] == True)]["Montant"].sum()) / 2
    st.metric("Tes gains sécurisés (Julie payée)", f"{score_partage:.2f} €")
