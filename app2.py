import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# --- 2. CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        # Nettoyage des lignes fantômes
        data = data.dropna(how='all')
        
        # Sécurité Dates
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        
        # Sécurité Montants
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        
        # SÉCURITÉ BOULÉENNE (La clé du problème)
        # On s'assure que tout ce qui n'est pas explicitement "vrai" devient False
        def force_bool(val):
            s = str(val).lower().strip()
            return s in ['true', '1', 'vrai', 'checked', 'x', 'yes']
        
        data['Payé'] = data['Payé'].apply(force_bool).astype(bool)
    return data

df_all = load_data()

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
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Enregistré !")
    st.rerun()

# --- LOGIQUE DE CALCUL (PRÉCISE) ---

# 1. On sépare les dépenses (toujours partagées)
total_achats = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())

# 2. Reste à partager (Ventes avec Payé == False)
ventes_en_attente = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]["Montant"].sum()

# 3. Bénéfice Encaissé (Ventes avec Payé == True)
ventes_payees = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum()

# Formule du bénéfice partagé final
benefice_net_total = ventes_payees - total_achats

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Régularisation", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("💰 Suivi des Paiements")
    
    col_pay, col_imp = st.columns(2)
    with col_pay:
        # Affiche 400€ si une vente de 400 n'est pas cochée
        st.success(f"💰 Reste à partager : **{ventes_en_attente:.2f} €**")
        # Affiche 200€
        st.write(f"👉 Verser à Julie : **{(ventes_en_attente/2):.2f} €**")
        st.caption("Dès que vous cochez 'Payé' et sauvegardez, ce montant tombe à 0.")

    with col_imp:
        ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
        st.error(f"🏦 Impôts (22%) : **{(ca_total * 0.22):.2f} €**")

    st.divider()

    st.subheader("📑 Historique")
    edited_df = st.data_editor(
        df_all,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?"),
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "Année": None
        },
        use_container_width=True,
        hide_index=True,
        key="main_editor"
    )
    
    if st.button("💾 Sauvegarder les changements"):
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.success("Données synchronisées !")
        st.rerun()

with tab2:
    st.subheader("👩‍💻 Compte Julie")
    # Part de Julie = (Ventes validées - Achats) / 2
    part_julie = benefice_net_total / 2
    st.metric("Bénéfice Net Reçu", f"{part_julie:.2f} €")
    
    st.write("### 📜 Détails de mes gains encaissés")
    # Affiche uniquement ce qui est payé ou ce qui est une dépense
    df_julie = df_all[(df_all["Payé"] == True) | (df_all["Montant"] < 0)].copy()
    if not df_julie.empty:
        df_julie['Ma Part'] = df_julie['Montant'] / 2
        st.table(df_julie[["Date", "Description", "Ma Part"]])

with tab3:
    st.subheader("👨‍💻 Compte Mathéo")
    part_matheo = benefice_net_total / 2
    st.metric("Bénéfice Net Reçu", f"{part_matheo:.2f} €")
    
    st.write("### 📜 Détails de mes gains encaissés")
    df_matheo = df_all[(df_all["Payé"] == True) | (df_all["Montant"] < 0)].copy()
    if not df_matheo.empty:
        df_matheo['Ma Part'] = df_matheo['Montant'] / 2
        st.table(df_matheo[["Date", "Description", "Ma Part"]])
