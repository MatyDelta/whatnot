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
df_filtre = df[df["Année"] == selection_annee].copy() if not df.empty else df

# --- CALCULS PRÉCIS ---
if not df_filtre.empty:
    ca_net_whatnot = df_filtre[df_filtre["Montant"] > 0]["Montant"].sum()
    total_achats = abs(df_filtre[df_filtre["Montant"] < 0]["Montant"].sum())
    
    # 1. Le bénéfice avant impôts (Ventes - Achats)
    benefice_brut = ca_net_whatnot - total_achats
    
    # 2. Les impôts (toujours calculés sur le CA encaissé)
    impots = ca_net_whatnot * 0.22
    
    # 3. Ce qu'il reste réellement à partager (Bénéfice - Impôts)
    reste_a_partager_total = benefice_brut - impots
    
    # Calcul du reste à payer à la collègue (uniquement sur les lignes non cochées 'Payé')
    # On calcule au prorata du bénéfice net global
    if reste_a_partager_total > 0:
        part_collegue_theorique = reste_a_partager_total / 2
        # Pour l'affichage dynamique, on regarde le ratio de ventes non payées
        ventes_non_payees = df_filtre[(df_filtre["Montant"] > 0) & (df_filtre["Payé"] == False)]["Montant"].sum()
        total_ventes = max(ca_net_whatnot, 1)
        reste_a_payer_collegue = (ventes_non_payees / total_ventes) * part_collegue_theorique
    else:
        reste_a_payer_collegue = 0
else:
    ca_net_whatnot = total_achats = benefice_brut = impots = reste_a_partager_total = reste_a_payer_collegue = 0

# --- AFFICHAGE ---
c1, c2, c3 = st.columns(3)
c1.metric("CA Net (Whatnot)", f"{ca_net_whatnot:.2f} €")
c2.metric("Achats Stock", f"-{total_achats:.2f} €")
c3.metric("Bénéfice Brut", f"{benefice_brut:.2f} €")

st.divider()

col_tax, col_duo = st.columns(2)
with col_tax:
    st.info(f"🏦 Provision Impôts (22% du CA) : **{impots:.2f} €**")
    st.write(f"Bénéfice Net final : {reste_a_partager_total:.2f} €")

with col_duo:
    st.success(f"👯 Reste à payer à ma collègue : **{max(0, reste_a_payer_collegue):.2f} €**")
    st.caption("Le calcul déduit les achats de stock et les impôts avant de diviser par deux.")

# --- HISTORIQUE ---
st.subheader("📑 Détails et Modifs")
if not df_filtre.empty:
    edited_df = st.data_editor(
        df_filtre,
        column_config={"Payé": st.column_config.CheckboxColumn("Payé ?"), "Année": None},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )
    if st.button("Enregistrer les changements"):
        autres_annees = df[df["Année"] != selection_annee]
        st.session_state.data = pd.concat([autres_annees, edited_df], ignore_index=True)
        st.rerun()
