import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Gestion Whatnot Duo", layout="wide")
st.title("💰 Suivi Business Whatnot")

# --- INITIALISATION DE LA MÉMOIRE ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année"])

# --- BARRE LATÉRALE : SAISIE ---
st.sidebar.header("📝 Nouvelle Opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description (ex: Live du 18/01)")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer l'opération"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year)
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    st.sidebar.success("Enregistré !")

# --- FILTRE PAR ANNÉE ---
df = st.session_state.data
annee_actuelle = str(datetime.now().year)

if not df.empty and "Année" in df.columns:
    annees_dispo = sorted(df["Année"].unique(), reverse=True)
else:
    annees_dispo = [annee_actuelle]

selection_annee = st.selectbox("📅 Choisir l'année à afficher", annees_dispo)
df_filtre = df[df["Année"] == selection_annee] if not df.empty else df

# --- CALCULS ET AFFICHAGE ---
ca_net = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum() if not df_filtre.empty else 0
achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum()) if not df_filtre.empty else 0
benefice = ca_net - achats
impots = ca_net * 0.22 
net_final = benefice - impots

col1, col2, col3 = st.columns(3)
col1.metric("CA Net (Whatnot)", f"{ca_net:.2f} €")
col2.metric("Achats Stock", f"-{achats:.2f} €")
col3.metric("Bénéfice (Avant impôts)", f"{benefice:.2f} €")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.warning(f"🏦 Provision Impôts (22%): **{impots:.2f} €**")
with c2:
    st.success(f"👯 Part par personne (50%): **{(net_final/2):.2f} €**")

# --- GRAPHIQUE ---
if not df_filtre.empty:
    st.subheader(f"📈 Évolution {selection_annee}")
    df_graph = df_filtre.sort_values("Date")
    fig = px.line(df_graph, x="Date", y="Montant", title="Flux de trésorerie")
    st.plotly_chart(fig, use_container_width=True)

# --- HISTORIQUE ---
st.subheader("📑 Historique")
st.dataframe(df_filtre, use_container_width=True)
