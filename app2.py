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
desc = st.sidebar.text_input("Description (ex: Live Pokémon)")
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

# --- FILTRE PAR ANNÉE ---
df = st.session_state.data
annee_actuelle = str(datetime.now().year)
liste_annees = sorted(df["Année"].unique(), reverse=True) if not df.empty else [annee_actuelle]
selection_annee = st.selectbox("📅 Année :", liste_annees)
df_filtre = df[df["Année"] == selection_annee].copy() if not df.empty else df

# --- CALCULS 50/50 ---
if not df_filtre.empty:
    ca_net = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum()
    achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum())
    
    # 1. On calcule les impôts totaux (22% du CA)
    impots_totaux = ca_net * 0.22
    
    # 2. Le bénéfice réel après avoir retiré les achats et les impôts
    # (Puisque vous divisez tout par deux, on calcule le reste global d'abord)
    benefice_a_se_partager = ca_net - achats - impots_totaux
    
    # 3. Calcul de la part due à la collègue (uniquement sur ce qui n'est pas coché 'Payé')
    # On calcule le ratio de ce qui reste à verser
    ventes_non_payees = df_filtre[(df_filtre["Montant"] > 0) & (df_filtre["Payé"] == False)]["Montant"].sum()
    total_ventes = max(ca_net, 1)
    reste_a_payer = (ventes_non_payees / total_ventes) * (benefice_a_se_partager / 2)
else:
    ca_net = achats = impots_totaux = benefice_a_se_partager = reste_a_payer = 0

# --- AFFICHAGE ---
c1, c2, c3 = st.columns(3)
c1.metric("CA Net (Ventes)", f"{ca_net:.2f} €")
c2.metric("Achats (Investi)", f"-{achats:.2f} €")
c3.metric("Impôts (22%)", f"-{impots_totaux:.2f} €")

st.divider()

col_fin, col_pay = st.columns(2)
with col_fin:
    st.info(f"💰 Bénéfice Total à se partager : **{max(0, benefice_a_se_partager):.2f} €**")
    st.write(f"Soit **{(max(0, benefice_a_se_partager)/2):.2f} €** chacune.")

with col_pay:
    st.success(f"👯 Reste à verser à ma collègue : **{max(0, reste_a_payer):.2f} €**")
    st.caption("Ce montant baisse automatiquement quand vous cochez 'Payé' dans le tableau.")

# --- HISTORIQUE ---
st.subheader("📑 Historique, Modifications et Suppressions")
if not df_filtre.empty:
    edited_df = st.data_editor(
        df_filtre,
        column_config={"Payé": st.column_config.CheckboxColumn("Payé ?"), "Année": None},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    if st.button("Sauvegarder les modifications"):
        autres_annees = df[df["Année"] != selection_annee]
        st.session_state.data = pd.concat([autres_annees, edited_df], ignore_index=True)
        st.rerun()
