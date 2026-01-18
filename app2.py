import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Gestion Whatnot Duo", layout="wide")
st.title("💰 Suivi Business Whatnot")

# --- INITIALISATION ---
if 'data' not in st.session_state:
    # On ajoute la colonne 'Payé' (booléen)
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
        "Payé": False # Par défaut, ce n'est pas encore payé
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    st.sidebar.success("Enregistré !")

# --- FILTRE PAR ANNÉE ---
df = st.session_state.data
annee_actuelle = str(datetime.now().year)
liste_annees = sorted(df["Année"].unique(), reverse=True) if not df.empty else [annee_actuelle]
selection_annee = st.selectbox("📅 Année :", liste_annees)
df_filtre = df[df["Année"] == selection_annee].copy() if not df.empty else df

# --- CALCULS ---
if not df_filtre.empty:
    ca_net = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum()
    achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum())
    benefice = ca_net - achats
    
    # Calcul de la part due (Uniquement sur les ventes NON COCHÉES)
    # Formule : (Montant Vente * 0.78 (après impôts) / 2)
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
st.info("💡 Cochez 'Payé' dans le tableau ci-dessous pour déduire un montant déjà versé.")

# --- HISTORIQUE INTERACTIF ---
st.subheader("📑 Détails et Validation des paiements")
if not df_filtre.empty:
    # On utilise st.data_editor pour pouvoir cocher les cases directement
    edited_df = st.data_editor(
        df_filtre,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?", help="Cocher une fois le virement fait"),
            "Année": None, # On cache l'année pour gagner de la place
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
        },
        disabled=["Date", "Type", "Description", "Montant"], # On ne peut modifier QUE la case Payé
        use_container_width=True,
        hide_index=True
    )
    
    # Mise à jour de la mémoire si une case est cochée
    if st.button("Sauvegarder les validations de paiement"):
        st.session_state.data.update(edited_df)
        st.rerun()
else:
    st.write("Aucune donnée.")
