import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Gestion Whatnot Duo", layout="wide")
st.title("💰 Suivi Business Whatnot")

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année", "Payé"])

# --- BARRE LATÉRALE ---
st.sidebar.header("📝 Nouvelle Opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer l'opération"):
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

# --- FILTRE PAR ANNÉE ---
df = st.session_state.data
annee_actuelle = str(datetime.now().year)
liste_annees = sorted(df["Année"].unique(), reverse=True) if not df.empty else [annee_actuelle]
selection_annee = st.selectbox("📅 Année :", liste_annees)

# Filtrage
df_filtre = df[df["Année"] == selection_annee].copy() if not df.empty else df

# --- CALCULS ---
if not df_filtre.empty:
    ca_net = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum()
    achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum())
    benefice = ca_net - achats
    
    # Reste à payer (Ventes non payées après impôts)
    part_due_totale = 0
    for index, row in df_filtre.iterrows():
        if row["Montant"] > 0 and row["Payé"] == False:
            part_due_totale += (row["Montant"] * 0.78) / 2
else:
    ca_net = achats = benefice = part_due_totale = 0

# --- AFFICHAGE ---
c1, c2, c3 = st.columns(3)
c1.metric("CA Net", f"{ca_net:.2f} €")
c2.metric("Achats", f"-{achats:.2f} €")
c3.metric("Bénéfice", f"{benefice:.2f} €")

st.divider()
st.success(f"🔴 Reste à payer à ma collègue : **{part_due_totale:.2f} €**")

# --- HISTORIQUE INTERACTIF (MODIF / SUPPR) ---
st.subheader("📑 Gestion des données (Modifications et Suppressions)")
if not df_filtre.empty:
    st.info("💡 Double-cliquez sur une case pour modifier. Sélectionnez une ligne et appuyez sur 'Suppr' pour effacer.")
    
    # Le data_editor permet la modification et la suppression (num_rows="dynamic")
    edited_df = st.data_editor(
        df_filtre,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?", help="Cocher une fois payé"),
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "Année": None, # Masqué
        },
        num_rows="dynamic", # Permet d'ajouter/supprimer des lignes
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("💾 Enregistrer les changements"):
        # On met à jour la base de données globale
        # On garde les données des autres années et on remplace l'année en cours par l'éditée
        autres_annees = df[df["Année"] != selection_annee]
        st.session_state.data = pd.concat([autres_annees, edited_df], ignore_index=True)
        st.success("Données sauvegardées !")
        st.rerun()
else:
    st.write("Aucune donnée.")
