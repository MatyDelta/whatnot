import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Mathéo & Julie", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie (Automatique)")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="1s") # On lit les données en temps réel

df_all = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("🚀 Enregistrer et Synchroniser"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": date_op.strftime('%Y-%m-%d'), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False
    }])
    # On ajoute la ligne et on renvoie tout au Sheets immédiatement
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Données envoyées au Cloud !")
    st.rerun()

# --- CALCULS HISTORIQUES ---
ca_h = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_h = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benefice_h = ca_h - achats_h

# --- CALCULS EN ATTENTE ---
# On gère le fait que 'Payé' peut être une chaîne de caractères ou un booléen
df_en_attente = df_all[df_all["Payé"].astype(str).str.lower().isin(['false', '0', 'nan', 'none'])]
ca_enc = df_en_attente[df_en_attente["Montant"] > 0]["Montant"].sum()
ach_enc = abs(df_en_attente[df_en_attente["Montant"] < 0]["Montant"].sum())
benef_net_partageable = ca_enc - ach_enc

# --- AFFICHAGE ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Paiements", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Historique")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_h:.2f} €")
    c2.metric("Total Achats", f"-{achats_h:.2f} €")
    c3.metric("Bénéfice Brut", f"{benefice_h:.2f} €")

    st.divider()
    
    st.subheader("💳 Paiements en cours (Remise à zéro)")
    col_p, col_i = st.columns(2)
    with col_p:
        st.success(f"💰 Reste à partager : {max(0, benef_net_partageable):.2f} €")
        st.write(f"👉 Verser à Julie : **{(max(0, benef_net_partageable)/2):.2f} €**")
    with col_i:
        st.error(f"🏦 Impôts Totaux (22%) : {ca_h * 0.22:.2f} €")

    st.divider()
    st.subheader("📑 Historique (Modifiable)")
    edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Enregistrer les modifications du tableau"):
        conn.update(data=edited_df)
        st.success("Modifications enregistrées !")
        st.rerun()

# (Les graphiques Julie/Mathéo identiques aux versions précédentes)
