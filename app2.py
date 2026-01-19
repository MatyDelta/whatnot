import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# --- CONFIGURATION STYLE ---
st.set_page_config(page_title="MJTGC Duo Finance", layout="wide", page_icon="🤝")

# Personnalisation CSS pour une interface plus moderne
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stProgress > div > div > div > div { background-color: #2ecc71; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION & DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(ttl="0s")
    if df is not None and not df.empty:
        df = df.dropna(how='all')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Montant'] = pd.to_numeric(df['Montant'], errors='coerce').fillna(0.0)
    else:
        df = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année"])
    return df

# --- LOGIQUE MÉTIER ---
def save_entry(date, n_type, desc, montant):
    # Logique : Les ventes sont des entrées (+), les achats et remboursements sont des sorties (-)
    valeur = montant if "Vente" in n_type else -montant
    new_data = pd.DataFrame([{
        "Date": pd.to_datetime(date),
        "Type": n_type,
        "Description": desc,
        "Montant": valeur,
        "Année": str(date.year)
    }])
    updated_df = pd.concat([st.session_state.data, new_data], ignore_index=True)
    conn.update(data=updated_df)
    st.session_state.data = updated_df
    st.rerun()

# Initialisation
if 'data' not in st.session_state:
    st.session_state.data = get_data()

df = st.session_state.data

# --- CALCULS CLÉS (Soustraction dynamique) ---
ventes_totale = df[df["Type"].str.contains("Vente", na=False)]["Montant"].sum()
remboursements_totaux = abs(df[df["Type"].str.contains("Remboursement", na=False)]["Montant"].sum())
achats_totaux = abs(df[df["Type"].str.contains("Achat", na=False)]["Montant"].sum())

dû_julie = ventes_totale / 2
reste_a_payer = max(0.0, dû_julie - remboursements_totaux)
progression = min(remboursements_totaux / dû_julie, 1.0) if dû_julie > 0 else 1.0

# --- INTERFACE ---
st.title("🤝 MJTGC Duo Finance")
st.subheader("Suivi de rentabilité et remboursements en temps réel")

# ZONE 1 : LE COCKPIT (Remboursement Julie)
with st.container():
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        st.metric("Total dû à Julie", f"{dû_julie:.2f} €")
    with col2:
        st.metric("Reste à verser", f"{reste_a_payer:.2f} €", delta=f"-{remboursements_totaux:.2f} payés", delta_color="normal")
    
    with col3:
        st.write(f"**Niveau de remboursement : {progression*100:.1f}%**")
        st.progress(progression)
        if reste_a_payer <= 0 and dû_julie > 0:
            st.success("✅ Julie est à jour !")
        else:
            st.info(f"👉 Julie possède déjà **{remboursements_totaux:.2f} €** de sa part.")

st.divider()

# ZONE 2 : ACTIONS & ANALYSES
tab_add, tab_stats, tab_history = st.tabs(["➕ Ajouter une Opération", "📊 Performance Duo", "📖 Registre Complet"])

with tab_add:
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.markdown("#### 📝 Saisie Manuelle")
        with st.form("quick_add", clear_on_submit=True):
            f_date = st.date_input("Date", datetime.now())
            f_type = st.selectbox("Type", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement Julie"])
            f_desc = st.text_input("Description (ex: Live Pokémon, Virement Lydia...)")
            f_mnt = st.number_input("Montant (€)", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Valider l'opération"):
                if f_desc and f_mnt > 0:
                    save_entry(f_date, f_type, f_desc, f_mnt)
                else:
                    st.error("Remplis la description et le montant !")

    with c_right:
        st.markdown("#### 📸 Scan de Ticket")
        uploaded_file = st.file_uploader("Prendre une photo", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.warning("OCR activé. Vérifiez bien les données avant de valider.")
            # Ici on pourrait appeler la fonction simple_ocr définie précédemment
            st.image(uploaded_file, width=200)

with tab_stats:
    st.markdown("#### 📉 Bilan Financier")
    s1, s2, s3 = st.columns(3)
    s1.metric("Chiffre d'Affaires (CA)", f"{ventes_totale:.2f} €")
    s2.metric("Investissement Stock", f"-{achats_totaux:.2f} €")
    s3.metric("Bénéfice Net Global", f"{(ventes_totale - achats_totaux):.2f} €")
    
    # Petit graphique d'évolution
    df_ventes = df[df["Type"].str.contains("Vente")].sort_values("Date")
    if not df_ventes.empty:
        fig = px.area(df_ventes, x="Date", y="Montant", title="Historique des Gains Whatnot")
        st.plotly_chart(fig, use_container_width=True)

with tab_history:
    st.markdown("#### 🗄️ Journal des transactions")
    # On affiche les données triées par date récente
    df_recent = df.sort_values("Date", ascending=False)
    
    # Éditeur de données pour modifications rapides
    edited_df = st.data_editor(
        df_recent, 
        use_container_width=True, 
        num_rows="dynamic",
        column_config={
            "Montant": st.column_config.NumberColumn(format="%.2f €"),
            "Type": st.column_config.SelectboxColumn(options=["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement Julie"])
        }
    )
    
    if st.button("💾 Appliquer les modifications du registre"):
        conn.update(data=edited_df)
        st.session_state.data = edited_df
        st.success("Base de données mise à jour !")
        st.rerun()

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.write(f"📅 **Dernière mise à jour :** {datetime.now().strftime('%d/%m/%Y')}")
