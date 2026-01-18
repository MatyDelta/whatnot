import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Gestion Whatnot Duo", layout="wide")
st.title("💰 Suivi Business Whatnot")

# --- INITIALISATION DE LA MÉMOIRE ---
# On s'assure que la structure existe dès le début
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année"])

# --- BARRE LATÉRALE : SAISIE ---
st.sidebar.header("📝 Nouvelle Opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description (ex: Live Cartes Pokémon)")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer l'opération"):
    # On détermine l'année de l'opération choisie
    annee_op = str(date_op.year)
    valeur = montant if "Vente" in type_op else -montant
    
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": annee_op
    }])
    
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    st.sidebar.success(f"Enregistré pour l'année {annee_op} !")

# --- SYSTÈME D'ARCHIVES / FILTRE PAR ANNÉE ---
df = st.session_state.data
annee_en_cours = str(datetime.now().year)

# On récupère toutes les années présentes dans les données + l'année actuelle
if not df.empty:
    liste_annees = sorted(df["Année"].unique(), reverse=True)
    if annee_en_cours not in liste_annees:
        liste_annees.append(annee_en_cours)
else:
    liste_annees = [annee_en_cours, "2025"] # Par défaut on affiche 2025 et l'actuelle

st.subheader("📅 Archives et Sélection")
selection_annee = st.selectbox("Afficher les chiffres de l'année :", sorted(list(set(liste_annees)), reverse=True))

# Filtrage des données selon l'année choisie
df_filtre = df[df["Année"] == selection_annee] if not df.empty else pd.DataFrame()

# --- CALCULS ---
ca_net = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum() if not df_filtre.empty else 0
achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum()) if not df_filtre.empty else 0
benefice_avant_impot = ca_net - achats
impots_estimes = ca_net * 0.22 
net_final = benefice_avant_impot - impots_estimes

# --- AFFICHAGE ---
st.markdown(f"### Résumé de l'année {selection_annee}")
c1, c2, c3 = st.columns(3)
c1.metric("CA Net (Whatnot)", f"{ca_net:.2f} €")
c2.metric("Achats Stock", f"-{achats:.2f} €")
c3.metric("Bénéfice (Avant impôts)", f"{benefice_avant_impot:.2f} €")

st.divider()

col_tax, col_duo = st.columns(2)
with col_tax:
    st.info(f"🏦 Impôts à prévoir (22% du CA) : **{impots_estimes:.2f} €**")
with col_duo:
    st.success(f"👯 Part par personne (50% du net) : **{(max(0, net_final)/2):.2f} €**")

# --- GRAPHIQUE ---
if not df_filtre.empty:
    st.subheader(f"📈 Courbe de l'année {selection_annee}")
    df_graph = df_filtre.sort_values("Date")
    # On calcule le cumulatif pour voir la courbe monter
    df_graph["Cumul"] = df_graph["Montant"].cumsum()
    fig = px.area(df_graph, x="Date", y="Cumul", title="Évolution du bénéfice cumulé")
    st.plotly_chart(fig, use_container_width=True)

# --- HISTORIQUE ---
st.subheader("📑 Détails des transactions")
if not df_filtre.empty:
    st.dataframe(df_filtre[["Date", "Type", "Description", "Montant"]], use_container_width=True)
else:
    st.write("Aucune donnée pour cette année.")
