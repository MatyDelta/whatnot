import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Mathéo & Julie", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=1 permet de rafraîchir presque instantanément
    return conn.read(ttl="1s")

df_all = load_data()

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
    st.sidebar.success("Données envoyées au Cloud !")
    st.rerun()

# --- LOGIQUE DES CALCULS ---
# 1. Performance Historique (Ne bouge jamais)
ca_h = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_h = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benefice_total = ca_h - achats_h

# 2. Reste à payer (Se réinitialise quand on coche "Payé")
# On gère les cases vides ou non cochées
if "Payé" in df_all.columns:
    df_non_paye = df_all[df_all["Payé"].astype(str).str.lower().isin(['false', '0', 'nan', 'none', ''])]
else:
    df_non_paye = df_all.copy()

ca_enc = df_non_paye[df_non_paye["Montant"] > 0]["Montant"].sum()
ach_enc = abs(df_non_paye[df_non_paye["Montant"] < 0]["Montant"].sum())
benef_net_a_partager = ca_enc - ach_enc

# --- AFFICHAGE DES ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Paiements", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale (Historique)")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_h:.2f} €")
    c2.metric("Total Achats", f"-{achats_h:.2f} €")
    c3.metric("Bénéfice Brut", f"{benefice_total:.2f} €")

    st.divider()
    
    st.subheader("💳 À Régulariser (Virements)")
    col_p, col_i = st.columns(2)
    with col_p:
        st.success(f"💰 Reste à partager : {max(0, benef_net_a_partager):.2f} €")
        st.info(f"👉 **Virement pour Julie : {(max(0, benef_net_a_partager)/2):.2f} €**")
    with col_i:
        provision_impots = ca_h * 0.22
        st.error(f"🏦 Impôts (22% du CA total) : {provision_impots:.2f} €")
        st.caption(f"Soit {provision_impots/2:.2f} € chacun à garder.")

    st.divider()
    st.subheader("📑 Historique Complet")
    edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Enregistrer les modifications"):
        conn.update(data=edited_df)
        st.success("Modifications enregistrées !")
        st.rerun()

# --- GRAPHIQUES POUR JULIE ET MATHÉO ---
def draw_chart(df, title, color):
    if not df.empty:
        df = df.sort_values("Date")
        # On calcule le gain cumulé (Montant / 2 pour chaque ligne payée ou achat)
        df['Gain_Perso'] = df.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or str(x['Payé']).lower() == 'true') else 0, axis=1)
        df['Cumul'] = df['Gain_Perso'].cumsum()
        fig = px.area(df, x="Date", y="Cumul", title=title, color_discrete_sequence=[color])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Aucune donnée disponible.")

with tab2:
    st.subheader("🏆 Progression de Julie")
    draw_chart(df_all, "Bénéfice cumulé Julie (€)", "#FF66C4")

with tab3:
    st.subheader("🏆 Progression de Mathéo")
    draw_chart(df_all, "Bénéfice cumulé Mathéo (€)", "#17BECF")
