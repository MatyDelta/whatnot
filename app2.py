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

# Nettoyage des données pour éviter les bugs de calcul
if not df_all.empty:
    df_all['Montant'] = pd.to_numeric(df_all['Montant'], errors='coerce').fillna(0)
    # On s'assure que la colonne Payé est bien traitée comme un Vrai/Faux
    df_all['Payé'] = df_all['Payé'].astype(str).str.lower().isin(['true', '1', 'yes', 'vrai', 'checked'])

# --- SAISIE RAPIDE ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("🚀 Enregistrer et Synchroniser"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": date_op.strftime('%Y-%m-%d'), 
        "Type": type_op, 
        "Description": desc, 
        "Montant": valeur, 
        "Année": str(date_op.year),
        "Payé": False
    }])
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Données envoyées !")
    st.rerun()

# --- LOGIQUE DES CALCULS ---

# 1. Chiffres Globaux (Historique)
ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
achats_total = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())

# 2. Calcul du virement (Uniquement les ventes NON PAYÉES)
df_non_paye = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]
reste_a_partager = df_non_paye["Montant"].sum()

# 3. Calcul pour les graphiques (Uniquement les ventes PAYÉES et on déduit les achats)
# On divise les gains par 2 pour chacun
df_ventes_payees = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]
gain_paye_chacun = (df_ventes_payees["Montant"].sum() / 2)

# --- AFFICHAGE ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Paiements", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("💰 État des Comptes")
    c1, c2, c3 = st.columns(3)
    c1.metric("Chiffre d'Affaires Total", f"{ca_total:.2f} €")
    c2.metric("Total Achats Stock", f"-{achats_total:.2f} €")
    c3.metric("Bénéfice Brut", f"{(ca_total - achats_total):.2f} €")

    st.divider()
    
    col_v, col_i = st.columns(2)
    with col_v:
        st.success(f"💶 Virement en attente pour Julie : {(reste_a_partager/2):.2f} €")
        st.caption("Dès que tu coches 'Payé' dans le tableau, ce montant revient à zéro.")
    with col_i:
        st.error(f"🏦 Charge URSSAF (22%) : {(ca_total * 0.22):.2f} €")

    st.divider()
    st.subheader("📑 Tableau de gestion (Cochez 'Payé' ici)")
    # Le data_editor permet de cocher directement les cases
    edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Sauvegarder les modifications"):
        conn.update(data=edited_df)
        st.success("C'est enregistré dans Google Sheets !")
        st.rerun()

# --- GRAPHIQUES ---
def tracer_gain(df, couleur, nom):
    if not df.empty:
        # On ne prend que les lignes payées pour le gain réel ou les achats pour le stock
        df_graph = df.copy()
        # Calcul du gain perso : + (Montant/2) si payé, - (Montant/2) si achat
        df_graph['Gain_Perso'] = df_graph.apply(
            lambda x: (x['Montant']/2) if (x['Payé'] == True or x['Montant'] < 0) else 0, axis=1
        )
        df_graph = df_graph.sort_values("Date")
        df_graph['Cumul'] = df_graph['Gain_Perso'].cumsum()
        
        fig = px.area(df_graph, x="Date", y="Cumul", title=f"Progression Gains : {nom}", color_discrete_sequence=[couleur])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée à afficher")

with tab2:
    st.subheader(f"Julie : {gain_paye_chacun:.2f} € encaissés")
    tracer_gain(df_all, "#FF66C4", "Julie")

with tab3:
    st.subheader(f"Mathéo : {gain_paye_chacun:.2f} € encaissés")
    tracer_gain(df_all, "#17BECF", "Mathéo")
