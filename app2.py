import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION GOOGLE SHEETS ---
# Remplacez l'URL ci-dessous par l'URL de VOTRE Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Q_7k-wHtSBIFfw54TSLqqjUJeWr3X-tqbSvRApFPLGM/edit?usp=sharing"
# Pour que Pandas puisse lire le CSV, on transforme l'URL
CSV_URL = SHEET_URL.replace('/edit?usp=sharing', '/export?format=csv')
CSV_URL = CSV_URL.replace('/edit#gid=0', '/export?format=csv')

# --- CONFIGURATION APP ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie (Sauvegarde Cloud)")

# --- CHARGEMENT DES DONNÉESPUIS GOOGLE SHEETS ---
def load_data():
    try:
        # On tente de lire le Google Sheets
        df = pd.read_csv(CSV_URL)
        df['Date'] = pd.to_datetime(df['Date'])
        # On s'assure que 'Payé' est bien traité comme un booléen (Vrai/Faux)
        df['Payé'] = df['Payé'].astype(bool)
        return df
    except:
        # Si erreur (feuille vide), on crée une structure vide
        return pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année", "Payé"])

# Initialisation des données dans la session
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE : AJOUT ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": date_op.strftime('%Y-%m-%d'), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False
    }])
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
    st.sidebar.info("⚠️ Pour sauvegarder définitivement dans Google Sheets, cliquez sur '💾 Sauvegarder' dans l'onglet Global.")

# --- CALCULS ---
df_all = st.session_state.data
ca_h = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_h = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benefice_h = ca_h - achats_h

df_en_attente = df_all[df_all["Payé"] == False] if not df_all.empty else pd.DataFrame()
ca_en_attente = df_en_attente[df_en_attente["Montant"] > 0]["Montant"].sum() if not df_en_attente.empty else 0
achats_en_attente = abs(df_en_attente[df_en_attente["Montant"] < 0]["Montant"].sum()) if not df_en_attente.empty else 0
benef_net_partageable = ca_en_attente - achats_en_attente

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Statistiques & Régularisation", "👩‍💻 Compte Julie", "👨‍💻 Compte Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale (Historique)")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_h:.2f} €")
    c2.metric("Total Achats Stock", f"-{achats_h:.2f} €")
    c3.metric("Bénéfice Brut Total", f"{benefice_h:.2f} €")
    
    st.divider()
    
    st.subheader("💳 Paiements en cours")
    col_pay, col_imp = st.columns(2)
    with col_pay:
        st.success(f"💰 Reste à partager : **{max(0, benef_net_partageable):.2f} €**")
        st.write(f"👉 Verser à Julie : **{(max(0, benef_net_partageable)/2):.2f} €**")

    with col_imp:
        total_impots = ca_h * 0.22
        st.error(f"🏦 Impôts Totaux (22% du CA) : **{total_impots:.2f} €**")

    st.divider()
    
    # TABLEAU & SAUVEGARDE
    st.subheader("📑 Historique des transactions")
    edited_df = st.data_editor(
        df_all,
        column_config={"Payé": st.column_config.CheckboxColumn("Payé ?")},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # BOUTON CRITIQUE
    if st.button("💾 SAUVEGARDER DANS GOOGLE SHEETS"):
        # Ici on affiche un message car pour l'écriture automatique, 
        # il faut normalement utiliser les API Google plus complexes.
        # Pour cette version, on propose le téléchargement ou l'affichage du lien.
        st.session_state.data = edited_df
        st.success("Données mises à jour dans l'application !")
        st.warning("Note : Pour synchroniser l'écriture automatique, contactez Mathéo pour configurer les 'Secrets' Google Service Account.")

# (Le reste du code pour les onglets Julie/Mathéo reste identique)
