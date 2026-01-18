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
    st.sidebar.success("Opération ajoutée !")

# --- CALCULS GLOBAUX (DEPUIS LE DÉPART) ---
df_all = st.session_state.data
if not df_all.empty:
    ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum()
    achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())
    impots_historique = ca_historique * 0.22
    benef_total_depuis_depart = ca_historique - achats_historique - impots_historique
else:
    benef_total_depuis_depart = 0

# Affichage du score global tout en haut
st.metric("🏆 Bénéfice NET cumulé (Depuis le départ)", f"{max(0, benef_total_depuis_depart):.2f} €")
st.divider()

# --- FILTRE PAR ANNÉE ---
annee_actuelle = str(datetime.now().year)
liste_annees = sorted(df_all["Année"].unique(), reverse=True) if not df_all.empty else [annee_actuelle]
selection_annee = st.selectbox("📅 Consulter l'année :", liste_annees)
df_filtre = df_all[df_all["Année"] == selection_annee].copy() if not df_all.empty else df_all

# --- CALCULS DU RESTE À PAYER (REMISE À ZÉRO DYNAMIQUE) ---
if not df_filtre.empty:
    # On ne calcule le "Reste à payer" que sur les lignes NON PAYÉES
    df_non_paye = df_filtre[df_filtre["Payé"] == False]
    
    ca_en_attente = df_non_paye[df_non_paye["Montant"] > 0]["Montant"].sum()
    achats_en_attente = abs(df_non_paye[df_non_paye["Montant"] < 0]["Montant"].sum())
    impots_en_attente = ca_en_attente * 0.22
    
    # Le bénéfice net qui reste à diviser
    benefice_net_en_attente = ca_en_attente - achats_en_attente - impots_en_attente
    part_collegue = benefice_net_en_attente / 2
else:
    benefice_net_en_attente = 0
    part_collegue = 0

# --- AFFICHAGE DES CHIFFRES "EN COURS" ---
st.subheader(f"📊 Situation actuelle ({selection_annee})")
c1, c2 = st.columns(2)

with c1:
    st.info(f"💰 Bénéfice NET en attente de partage : **{max(0, benefice_net_en_attente):.2f} €**")
    st.caption("Ceci est le bénéfice après retrait des achats et impôts non encore régularisés.")

with c2:
    st.success(f"👯 Reste à verser à ma collègue : **{max(0, part_collegue):.2f} €**")
    st.caption("Dès que vous cochez 'Payé' dans le tableau, ce montant revient à 0.")

# --- HISTORIQUE ET VALIDATION ---
st.divider()
st.subheader("📑 Détails des transactions")
if not df_filtre.empty:
    edited_df = st.data_editor(
        df_filtre,
        column_config={
            "Payé": st.column_config.CheckboxColumn("💰 Remboursé / Payé ?"),
            "Année": None,
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f")
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("Sauvegarder et Mettre à jour les calculs"):
        autres_annees = df_all[df_all["Année"] != selection_annee]
        st.session_state.data = pd.concat([autres_annees, edited_df], ignore_index=True)
        st.rerun()
else:
    st.write("Aucune donnée pour cette année.")
