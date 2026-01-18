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
    # Lit les données et force le rafraîchissement à chaque action
    return conn.read(ttl="0s")

df_all = load_data()

# --- NETTOYAGE DES DONNÉES ---
if not df_all.empty:
    df_all['Date'] = pd.to_datetime(df_all['Date'])
    df_all['Montant'] = pd.to_numeric(df_all['Montant'], errors='coerce').fillna(0)
    # Gère le format du "Payé" venant de Sheets
    df_all['Payé'] = df_all['Payé'].astype(str).str.lower().isin(['true', '1', 'yes', 'vrai', 'checked'])

# --- BARRE LATÉRALE ---
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
    # Ajout à l'existant et envoi vers Google Sheets
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Enregistré sur Google Sheets !")
    st.rerun()

# --- CALCULS HISTORIQUES ---
ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benefice_historique = ca_historique - achats_historique

# --- CALCULS DE PAIEMENT (BASÉS SUR LA COLONNE PAYÉ) ---
df_en_attente = df_all[df_all["Payé"] == False] if not df_all.empty else pd.DataFrame()
ca_en_attente = df_en_attente[df_en_attente["Montant"] > 0]["Montant"].sum() if not df_en_attente.empty else 0
achats_en_attente = abs(df_en_attente[df_en_attente["Montant"] < 0]["Montant"].sum()) if not df_en_attente.empty else 0
benefice_net_partageable = ca_en_attente - achats_en_attente

# --- ORGANISATION EN ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Statistiques & Régularisation", "👩‍💻 Compte Julie", "👨‍💻 Compte Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale (Historique)")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_historique:.2f} €")
    c2.metric("Total Achats Stock", f"-{achats_historique:.2f} €")
    c3.metric("Bénéfice Brut Total", f"{benefice_historique:.2f} €")
    
    st.divider()
    
    st.subheader("💳 Paiements en cours (Remise à zéro)")
    col_pay, col_imp = st.columns(2)
    
    with col_pay:
        st.success(f"💰 Reste à partager : **{max(0, benefice_net_partageable):.2f} €**")
        st.write(f"👉 Verser à Julie : **{(max(0, benefice_net_partageable)/2):.2f} €**")
        st.caption("Ce bloc revient à 0 quand vous cochez 'Payé' dans le tableau.")

    with col_imp:
        total_impots = ca_historique * 0.22
        st.error(f"🏦 Impôts Totaux (22% du CA) : **{total_impots:.2f} €**")

    st.divider()
    
    if not df_all.empty:
        st.subheader("📈 Courbe de croissance globale")
        df_global = df_all.sort_values("Date").copy()
        df_global['Cumul'] = df_global['Montant'].cumsum()
        fig_global = px.area(df_global, x="Date", y="Cumul", color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_global, use_container_width=True)

    st.subheader("📑 Historique des transactions")
    edited_df = st.data_editor(
        df_all,
        column_config={"Payé": st.column_config.CheckboxColumn("Payé ?"), "Année": None},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="global_editor"
    )
    if st.button("💾 Sauvegarder les changements"):
        conn.update(data=edited_df)
        st.success("Modifications synchronisées avec Google Sheets !")
        st.rerun()

with tab2:
    st.subheader("🏆 Score Julie")
    ventes_payees = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum() if not df_all.empty else 0
    argent_julie = (ventes_payees - achats_historique) / 2
    st.write(f"Bénéfice historique encaissé : **{argent_julie:.2f} €**")
    
    if not df_all.empty:
        df_j = df_all.sort_values("Date").copy()
        df_j['Gain_J'] = df_j.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or x['Payé'] == True) else 0, axis=1)
        df_j['Cumul_J'] = df_j['Gain_J'].cumsum()
        fig_j = px.line(df_j, x="Date", y="Cumul_J", title="Progression de Julie", markers=True, color_discrete_sequence=['#FF66C4'])
        st.plotly_chart(fig_j, use_container_width=True)

with tab3:
    st.subheader("🏆 Score Mathéo")
    argent_matheo = (ventes_payees - achats_historique) / 2
    st.write(f"Bénéfice historique encaissé : **{argent_matheo:.2f} €**")
    
    if not df_all.empty:
        df_m = df_all.sort_values("Date").copy()
        df_m['Gain_M'] = df_m.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or x['Payé'] == True) else 0, axis=1)
        df_m['Cumul_M'] = df_m['Gain_M'].cumsum()
        fig_m = px.line(df_m, x="Date", y="Cumul_M", title="Progression de Mathéo", markers=True, color_discrete_sequence=['#17BECF'])
        st.plotly_chart(fig_m, use_container_width=True)
