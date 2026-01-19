import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# --- CONFIGURATION ET CONSTANTES ---
st.set_page_config(page_title="MJTGC Duo Tracker v2", layout="wide", page_icon="💰")

TYPE_VENTE = "📈 Vente (Gain Net)"
TYPE_ACHAT = "📉 Achat Stock"
TYPE_REMB_J = "💸 Remboursement Julie"

# --- CONNEXION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl="0s")
    if df is not None and not df.empty:
        df = df.dropna(how='all')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Montant'] = pd.to_numeric(df['Montant'], errors='coerce').fillna(0.0)
    else:
        df = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année"])
    return df

# --- LOGIQUE OCR ---
def perform_ocr(image):
    try:
        text = pytesseract.image_to_string(image)
        prices = re.findall(r"(\d+[\.,]\d{2})", text)
        price = float(prices[-1].replace(',', '.')) if prices else 0.0
        return datetime.now(), "Nouveau Scan", price
    except:
        return datetime.now(), "Erreur Scan", 0.0

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

df = st.session_state.data

# --- SIDEBAR : SAISIE ---
with st.sidebar:
    st.header("📸 Nouveau Ticket")
    uploaded_file = st.file_uploader("Scan", type=['jpg', 'png', 'jpeg'])
    if uploaded_file and st.button("Analyser"):
        d, desc, p = perform_ocr(Image.open(uploaded_file))
        st.session_state.update({"d": d, "desc": desc, "p": p})
    
    st.divider()
    st.header("📝 Ajouter une ligne")
    with st.form("entry_form", clear_on_submit=True):
        f_date = st.date_input("Date", st.session_state.get("d", datetime.now()))
        f_type = st.selectbox("Nature", [TYPE_VENTE, TYPE_ACHAT, TYPE_REMB_J])
        f_desc = st.text_input("Description", st.session_state.get("desc", ""))
        f_mnt = st.number_input("Montant (€)", min_value=0.0, value=st.session_state.get("p", 0.0))
        
        if st.form_submit_button("Enregistrer"):
            # Vente = Positif / Achat & Remboursement = Sorties de caisse (Négatif)
            valeur = f_mnt if f_type == TYPE_VENTE else -f_mnt
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(f_date),
                "Type": f_type,
                "Description": f_desc,
                "Montant": valeur,
                "Année": str(f_date.year)
            }])
            st.session_state.data = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=st.session_state.data)
            st.rerun()

# --- CALCULS DE LA BALANCE ---
# 1. Ce que Julie doit toucher au total (50% des ventes)
total_ventes = df[df["Type"] == TYPE_VENTE]["Montant"].sum()
dette_theorique_julie = total_ventes / 2

# 2. Ce qui a déjà été soustrait (Remboursements saisis)
deja_rembourse = abs(df[df["Type"] == TYPE_REMB_J]["Montant"].sum())

# 3. Le reste à payer par soustraction simple
reste_a_payer = max(0.0, dette_theorique_julie - deja_rembourse)
progression = min(deja_rembourse / dette_theorique_julie, 1.0) if dette_theorique_julie > 0 else 1.0

# --- INTERFACE PRINCIPALE ---
st.title("🤝 MJTGC Duo Tracker")

# Widgets de résumé
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Chiffre d'Affaires", f"{total_ventes:.2f} €")
with c2:
    st.metric("Total Achats Stock", f"{df[df['Type'] == TYPE_ACHAT]['Montant'].sum():.2f} €")
with c3:
    st.metric("Part de Julie (Dû)", f"{dette_theorique_julie:.2f} €")
with c4:
    color = "off" if reste_a_payer > 0 else "normal"
    st.metric("Reste à lui verser", f"{reste_a_payer:.2f} €", delta=f"-{deja_rembourse:.2f} déjà fait")

# Barre de progression
st.subheader("📊 État du Remboursement de Julie")
st.progress(progression)
st.caption(f"Julie a reçu {deja_rembourse:.2f} € sur les {dette_theorique_julie:.2f} € prévus ({progression*100:.1f}%)")

# Onglets
tab_list, tab_viz = st.tabs(["📑 Historique & Édition", "📈 Analyses"])

with tab_list:
    st.subheader("Toutes les opérations")
    # Tri par date décroissante pour voir le plus récent en haut
    df_display = df.sort_values(by="Date", ascending=False)
    edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True)
    
    if st.button("💾 Sauvegarder les modifications"):
        st.session_state.data = edited_df
        conn.update(data=edited_df)
        st.success("Modifications enregistrées !")
        st.rerun()

with tab_viz:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.write("💰 **Répartition des flux**")
        pie_data = df.groupby("Type")["Montant"].sum().abs().reset_index()
        fig_pie = px.pie(pie_data, values="Montant", names="Type", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_right:
        st.write("📅 **Évolution des Gains**")
        line_data = df[df["Type"] == TYPE_VENTE].sort_values("Date")
        if not line_data.empty:
            line_data["Cumul"] = line_data["Montant"].cumsum()
            fig_line = px.line(line_data, x="Date", y="Cumul")
            st.plotly_chart(fig_line, use_container_width=True)

# --- FOOTER ---
if reste_a_payer == 0 and total_ventes > 0:
    st.balloons()
    st.success("Félicitations ! Julie est totalement remboursée.")
