import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Gestion Whatnot Duo", layout="wide")
st.title("💰 Suivi Business Whatnot")

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année"])

# --- BARRE LATÉRALE : SAISIE ---
st.sidebar.header("📝 Nouvelle Opération")
annee_actuelle = str(datetime.now().year)
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain après frais Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description (ex: Live du 18/01)")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer l'opération"):
    valeur = montant if type_op.startswith("Vente") else -montant
    new_row = {"Date": date, "Type": type_op, "Description": desc, "Montant": valeur, "Année": str(date.year)}
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
    st.sidebar.success("Enregistré !")

# --- FILTRE PAR ANNÉE ---
annees_dispo = sorted(st.session_state.data["Année"].unique(), reverse=True)
if not annees_dispo: annees_dispo = [annee_actuelle]
selection_annee = st.selectbox("📅 Choisir l'année à afficher", annees_dispo)

df_filtre = st.session_state.data[st.session_state.data["Année"] == selection_annee]

# --- CALCULS ---
ca_net_whatnot = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum()
total_achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum())
benefice_reel = ca_net_whatnot - total_achats
impots_estimes = ca_net_whatnot * 0.22 # Basé sur le CA encaissé
net_final = benefice_reel - impots_estimes

# --- AFFICHAGE DES MÉTRIQUES ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Chiffre d'Affaires Net Whatnot", f"{ca_net_whatnot:.2f} €")
with col2:
    st.metric("Dépenses Stocks", f"-{total_achats:.2f} €", delta_color="inverse")
with col3:
    st.metric("Bénéfice Réel (Avant impôts)", f"{benefice_reel:.2f} €")

st.divider()

col_tax, col_duo = st.columns(2)
with col_tax:
    st.subheader("🏦 Fiscalité")
    st.warning(f"Impôts estimés (22% du CA) : **{impots_estimes:.2f} €**")
    st.info(f"Reste après impôts : **{net_final:.2f} €**")

with col_duo:
    st.subheader("👯 Partage")
    st.success(f"À reverser à ta collègue (50%) : **{(net_final / 2):.2f} €**")

# --- GRAPHIQUE ---
if not df_filtre.empty:
    st.subheader(f"📈 Évolution {selection_annee}")
    fig = px.area(df_filtre.sort_values("Date"), x="Date", y="Montant", title="Flux de trésorerie")
    st.plotly_chart(fig, use_container_width=True)

# --- SCAN ---
st.divider()
st.subheader("📸 Scan de Ticket")
file = st.file_uploader("Prendre en photo un ticket", type=["jpg", "png"])
if file:
    st.image(file, width=200)
    st.info("Ticket enregistré. N'oublie pas de saisir le montant dans 'Achat Stock' pour le déduire du bénéfice.")

# --- HISTORIQUE ---
st.subheader("📑 Détails des opérations")
st.dataframe(df_filtre, use_container_width=True)
