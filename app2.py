import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker MJTGC", layout="wide")
st.title("🤝 MJTGC - Whatnot Duo Tracker")

# --- LIAISON GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        # Nettoyage strict pour les cases à cocher
        data['Payé'] = data['Payé'].astype(str).str.lower().isin(['true', '1', 'vrai', 'x', 'v']).astype(bool)
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- BARRE LATÉRALE ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
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
    
    # SAUVEGARDE AUTOMATIQUE
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    
    st.sidebar.success("Enregistré et synchronisé !")
    st.rerun()

# --- LOGIQUE DE CALCUL MJTGC ---
df_all = st.session_state.data

# 1. On isole uniquement les gains (ventes)
df_ventes = df_all[df_all["Montant"] > 0]

# 2. Gains en attente (Non cochés)
gains_non_payes = df_ventes[df_ventes["Payé"] == False]["Montant"].sum()

# 3. Gains validés (Cochés)
gains_valides = df_ventes[df_ventes["Payé"] == True]["Montant"].sum()

# 4. Historique global (CA et Stock) pour info
ca_historique = df_ventes["Montant"].sum()
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())

# --- ORGANISATION EN ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Paiements & Historique", "👩‍💻 Compte Julie", "👨‍💻 Compte Mathéo"])

with tab1:
    st.subheader("💳 Paiements en cours (Gains nets)")
    col_pay, col_imp = st.columns(2)
    
    with col_pay:
        st.success(f"💰 Somme des gains à partager : **{gains_non_payes:.2f} €**")
        st.write(f"👉 Verser à Julie (50%) : **{(gains_non_payes/2):.2f} €**")
        st.caption("Ce montant additionne tous vos gains non validés.")

    with col_imp:
        st.error(f"🏦 Impôts prévisionnels (22% CA) : **{(ca_historique * 0.22):.2f} €**")
        st.caption("Calculé sur la totalité des ventes historiques.")

    st.divider()

    st.subheader("📑 Historique des transactions")
    edited_df = st.data_editor(
        df_all,
        column_config={"Payé": st.column_config.CheckboxColumn("Valider le paiement ?"), "Année": None},
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="global_editor"
    )
    
    if st.button("💾 Sauvegarder les changements"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.success("Synchronisation Sheets terminée !")
        st.rerun()

with tab2:
    st.subheader("🏆 Score Julie")
    part_julie = gains_valides / 2
    st.metric("Total encaissé (Validé)", f"{part_julie:.2f} €")
    
    st.write("### 📜 Détail des gains reçus")
    df_j = df_ventes[df_ventes["Payé"] == True].copy()
    if not df_j.empty:
        df_j['Ma Part (50%)'] = df_j['Montant'] / 2
        st.dataframe(df_j[["Date", "Description", "Ma Part (50%)"]], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🏆 Score Mathéo")
    part_matheo = gains_valides / 2
    st.metric("Total encaissé (Validé)", f"{part_matheo:.2f} €")
    
    st.write("### 📜 Détail des gains reçus")
    df_m = df_ventes[df_ventes["Payé"] == True].copy()
    if not df_m.empty:
        df_m['Ma Part (50%)'] = df_m['Montant'] / 2
        st.dataframe(df_m[["Date", "Description", "Ma Part (50%)"]], use_container_width=True, hide_index=True)
