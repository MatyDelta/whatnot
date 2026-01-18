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

# S'assurer que les types de données sont corrects
if not df_all.empty:
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all['Montant'] = pd.to_numeric(df_all['Montant'], errors='coerce').fillna(0)
    # On normalise la colonne Payé pour qu'elle soit toujours lisible
    df_all['Payé'] = df_all['Payé'].astype(str).str.lower().isin(['true', '1', 'yes', 'vrai'])

# --- BARRE LATÉRALE ---
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
    st.sidebar.success("Données envoyées au Sheets !")
    st.rerun()

# --- LOGIQUE DES CALCULS ---

# 1. Performance Historique (Ne se réinitialise JAMAIS)
ca_total_historique = df_all[df_all["Montant"] > 0]["Montant"].sum()
achats_total_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())
benefice_brut_total = ca_total_historique - achats_total_historique

# 2. Gains déjà encaissés (Tout ce qui est marqué "Payé")
df_paye = df_all[df_all["Payé"] == True]
# On calcule ce que chacun a déjà reçu (Ventes payées - TOUS les achats) / 2
gain_encaisse_chacun = (df_paye[df_paye["Montant"] > 0]["Montant"].sum() - achats_total_historique) / 2
gain_encaisse_chacun = max(0, gain_encaisse_chacun)

# 3. Reste à payer (Ventes non cochées)
df_non_paye = df_all[df_all["Payé"] == False]
ca_en_attente = df_non_paye[df_non_paye["Montant"] > 0]["Montant"].sum()
# Le bénéfice net à partager (qui se remet à 0 une fois payé)
benef_net_partageable = ca_en_attente 

# --- AFFICHAGE DES ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Paiements", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Historique (Total)")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Cumulé", f"{ca_total_historique:.2f} €")
    c2.metric("Total Stocks Achetés", f"-{achats_total_historique:.2f} €")
    c3.metric("Bénéfice Brut", f"{benefice_brut_total:.2f} €")

    st.divider()
    
    st.subheader("💳 Gestion des Virements (En cours)")
    col_p, col_i = st.columns(2)
    with col_p:
        st.success(f"💰 Reste à partager : {benef_net_partageable:.2f} €")
        st.info(f"👉 **Virement pour Julie : {(benef_net_partageable/2):.2f} €**")
        st.caption("Une fois le virement fait, coche 'Payé' ci-dessous et enregistre.")
    with col_i:
        provision_impots = ca_total_historique * 0.22
        st.error(f"🏦 Provision Impôts (22% CA) : {provision_impots:.2f} €")
        st.caption("Calculé sur le CA total depuis le début.")

    st.divider()
    st.subheader("📑 Historique & Validation")
    edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Valider les changements (Payé / Modifs)"):
        conn.update(data=edited_df)
        st.success("Synchronisation réussie !")
        st.rerun()

# --- GRAPHIQUES ---
def draw_chart(df, color, title):
    if not df.empty:
        df_sorted = df.sort_values("Date")
        # Gain cumulé simplifié pour le graphique
        df_sorted['Gain_Perso'] = df_sorted.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or x['Payé']) else 0, axis=1)
        df_sorted['Cumul'] = df_sorted['Gain_Perso'].cumsum()
        fig = px.area(df_sorted, x="Date", y="Cumul", title=title, color_discrete_sequence=[color])
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("👩‍💻 Espace Julie")
    st.write(f"Argent total déjà encaissé : **{gain_encaisse_chacun:.2f} €**")
    draw_chart(df_all, "#FF66C4", "Progression des gains - Julie")

with tab3:
    st.subheader("👨‍💻 Espace Mathéo")
    st.write(f"Argent total déjà encaissé : **{gain_encaisse_chacun:.2f} €**")
    draw_chart(df_all, "#17BECF", "Progression des gains - Mathéo")
