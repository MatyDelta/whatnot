import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Whatnot")

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année", "Payé"])

# --- BARRE LATÉRALE ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": pd.to_datetime(date_op), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    st.sidebar.success("Enregistré !")

# --- CALCULS GLOBAUX ---
df_all = st.session_state.data
ca_h = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_h = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
impots_h = ca_h * 0.22
benef_historique = ca_h - achats_h - impots_h

# --- FILTRE PAR ANNÉE ---
annee_actuelle = str(datetime.now().year)
liste_annees = sorted(df_all["Année"].unique(), reverse=True) if not df_all.empty else [annee_actuelle]
selection_annee = st.selectbox("📅 Consulter l'année :", liste_annees)
df_filtre = df_all[df_all["Année"] == selection_annee].copy() if not df_all.empty else df_all

# --- CALCULS "EN COURS" (REMISE À ZÉRO) ---
df_non_paye = df_filtre[df_filtre["Payé"] == False] if not df_filtre.empty else pd.DataFrame()
ca_en_cours = df_non_paye[df_non_paye["Montant"] > 0]["Montant"].sum() if not df_non_paye.empty else 0
achats_en_cours = abs(df_non_paye[df_non_paye["Montant"] < 0]["Montant"].sum()) if not df_non_paye.empty else 0
impots_en_cours = ca_en_cours * 0.22
benef_net_en_cours = ca_en_cours - achats_en_cours - impots_en_cours

# --- AFFICHAGE DES COMPTEURS ---
c1, c2, c3 = st.columns(3)
c1.metric("CA Net (Ventes en cours)", f"{ca_en_cours:.2f} €")
c2.metric("Achats Stock (en cours)", f"-{achats_en_cours:.2f} €")
c3.metric("Bénéfice NET (en cours)", f"{max(0, benef_net_en_cours):.2f} €")

# --- GRAPHIQUE D'ÉVOLUTION ---
st.divider()
if not df_filtre.empty:
    st.subheader(f"📈 Évolution du bénéfice en {selection_annee}")
    # Préparation des données pour le graphique
    df_graph = df_filtre.sort_values("Date").copy()
    # On calcule le bénéfice net par ligne (Montant - 22% d'impôts si c'est une vente)
    df_graph['Net_Ligne'] = df_graph.apply(lambda x: x['Montant'] * 0.78 if x['Montant'] > 0 else x['Montant'], axis=1)
    df_graph['Cumul_Net'] = df_graph['Net_Ligne'].cumsum()
    
    fig = px.area(df_graph, x="Date", y="Cumul_Net", 
                  labels={"Cumul_Net": "Bénéfice NET Cumulé (€)"},
                  color_discrete_sequence=['#00CC96'])
    st.plotly_chart(fig, use_container_width=True)

# --- HISTORIQUE ET PARTAGE ---
st.divider()
col_hist, col_paye = st.columns(2)
with col_hist:
    st.subheader("🏆 Score Global")
    st.write(f"Bénéfice NET cumulé (Depuis le départ) : **{max(0, benef_historique):.2f} €**")

with col_paye:
    st.subheader("👯 Partage")
    st.success(f"Reste à verser à ma collègue : **{(max(0, benef_net_en_cours)/2):.2f} €**")

# --- TABLEAU DE DÉTAILS ---
st.divider()
st.subheader("📑 Détails des transactions")
if not df_filtre.empty:
    edited_df = st.data_editor(
        df_filtre,
        column_config={"Payé": st.column_config.CheckboxColumn("Remboursé / Payé ?"), "Année": None},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    if st.button("Sauvegarder les changements"):
        autres_annees = df_all[df_all["Année"] != selection_annee]
        st.session_state.data = pd.concat([autres_annees, edited_df], ignore_index=True)
        st.rerun()
