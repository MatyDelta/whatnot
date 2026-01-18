import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="1s")

df_all = load_data()

# Nettoyage et formatage des données
if not df_all.empty:
    df_all['Montant'] = pd.to_numeric(df_all['Montant'], errors='coerce').fillna(0)
    # Transformation de la colonne Payé en vrai Booléen (Vrai/Faux)
    df_all['Payé'] = df_all['Payé'].astype(str).str.lower().isin(['true', '1', 'yes', 'vrai', 'checked'])

# --- BARRE LATÉRALE : SAISIE ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("🚀 Enregistrer l'opération"):
    # Une vente est positive, un achat est négatif
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": date_op.strftime('%Y-%m-%d'), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False # Par défaut, une nouvelle vente n'est pas payée
    }])
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Opération enregistrée !")
    st.rerun()

# --- LOGIQUE DE CALCULS ---

# 1. Calcul du virement (Ventes non encore payées)
# On ne prend que les montants positifs (ventes) qui sont à 'False' dans Payé
df_en_attente = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]
virement_julie = df_en_attente["Montant"].sum() / 2

# 2. Calcul des gains personnels (Ventes payées ET TOUS les achats)
# Chaque euro gagné ou dépensé est divisé par 2
def calculer_total_perso(df):
    if df.empty: return 0.0
    # On prend les ventes SEULEMENT SI payées + TOUS les achats (négatifs)
    masque = (df["Montant"] < 0) | ((df["Montant"] > 0) & (df["Payé"] == True))
    return df[masque]["Montant"].sum() / 2

total_perso = calculer_total_perso(df_all)

# --- AFFICHAGE ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Paiements", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("💰 État des Comptes")
    c1, c2 = st.columns(2)
    
    with c1:
        st.success(f"💶 Virement à faire pour Julie : {virement_julie:.2f} €")
        st.caption("Réinitialisé dès que la vente est cochée 'Payé'.")
    
    with c2:
        # Calcul de la provision pour impôts (22% sur le CA total des ventes)
        ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
        st.error(f"🏦 Charge URSSAF (22%) : {(ca_total * 0.22):.2f} €")

    st.divider()
    st.subheader("📑 Historique & Validation (Cochez ici)")
    # Éditeur interactif pour cocher "Payé"
    edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Sauvegarder les modifications"):
        conn.update(data=edited_df)
        st.success("Modifications synchronisées avec Google Sheets !")
        st.rerun()

# --- FONCTION GRAPHIQUE ---
def tracer_graphique(df, couleur, nom):
    if not df.empty:
        # Filtrer : Achats (tous) + Ventes (payées seulement)
        df_filtre = df[(df["Montant"] < 0) | (df["Payé"] == True)].copy()
        df_filtre = df_filtre.sort_values("Date")
        # Division par deux pour le cumul perso
        df_filtre['Montant_Perso'] = df_filtre['Montant'] / 2
        df_filtre['Cumul_Gains'] = df_filtre['Montant_Perso'].cumsum()
        
        fig = px.area(df_filtre, x="Date", y="Cumul_Gains", 
                     title=f"Evolution du compte de {nom}",
                     color_discrete_sequence=[couleur])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée encaissée.")

with tab2:
    st.header("👩‍💻 Espace Julie")
    st.metric("Total encaissé (après achats)", f"{total_perso:.2f} €")
    tracer_graphique(df_all, "#FF66C4", "Julie")

with tab3:
    st.header("👨‍💻 Espace Mathéo")
    st.metric("Total encaissé (après achats)", f"{total_perso:.2f} €")
    tracer_graphique(df_all, "#17BECF", "Mathéo")
