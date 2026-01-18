import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Business Tracker", layout="wide")
st.title("📊 Suivi Business Whatnot")

# Initialisation de la base de données (stockage local simple pour l'exemple)
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        "Date", "Type", "Montant Brut", "Frais Whatnot", "Impôts", "Net Final", "Part Coloc"
    ])

# --- BARRE LATÉRALE : SAISIE DES DONNÉES ---
st.sidebar.header("Ajouter une opération")
type_op = st.sidebar.selectbox("Type", ["Vente Live", "Achat Stock (Dépense)"])
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=10.0)
date = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer"):
    if type_op == "Vente Live":
        frais = montant * 0.10  # Estimation 10% frais Whatnot
        impots = montant * 0.22 # Estimation 22% Auto-entrepreneur
        net = montant - frais - impots
        part = net / 2
        new_row = [date, "Vente", montant, frais, impots, net, part]
    else:
        # Pour un achat, on le compte en négatif pour le bénéfice
        new_row = [date, "Achat", -montant, 0, 0, -montant, 0]
    
    # Ajout à la base
    st.session_state.data.loc[len(st.session_state.data)] = new_row
    st.sidebar.success("Enregistré !")

# --- DASHBOARD ---
col1, col2, col3 = st.columns(3)

# Calculs
total_ca = st.session_state.data[st.session_state.data["Type"] == "Vente"]["Montant Brut"].sum()
total_achats = abs(st.session_state.data[st.session_state.data["Type"] == "Achat"]["Montant Brut"].sum())
benefice_reel = st.session_state.data["Net Final"].sum()

col1.metric("Chiffre d'Affaires Brut", f"{total_ca:.2f} €")
col2.metric("Total Achats (Stock)", f"{total_achats:.2f} €")
col3.metric("Net à se partager (après impôts/frais)", f"{benefice_reel:.2f} €", delta=f"{(benefice_reel/2):.2f} € par personne")

# --- GRAPHIQUE ---
if not st.session_state.data.empty:
    st.subheader("Courbe de croissance")
    fig = px.line(st.session_state.data, x="Date", y="Montant Brut", title="Évolution du CA")
    st.plotly_chart(fig, use_container_width=True)

# --- SCAN / TICKETS ---
st.subheader("📸 Gestion des justificatifs")
uploaded_file = st.file_uploader("Scanner un ticket de caisse", type=["jpg", "png", "pdf"])
if uploaded_file:
    st.image(uploaded_file, caption="Ticket téléchargé", width=300)
    st.info("Le montant a été détecté (simulation). Pensez à l'ajouter dans la barre latérale en 'Achat'.")

# --- TABLEAU RÉCAPITULATIF ---
st.subheader("Historique des transactions")
st.dataframe(st.session_state.data, use_container_width=True)
