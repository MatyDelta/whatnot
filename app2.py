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
        # Nettoyage pour éviter les erreurs
        data = data.dropna(how='all')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        # Conversion stricte du booléen pour les cases à cocher
        data['Payé'] = data['Payé'].astype(str).str.lower().str.strip().isin(['true', '1', 'vrai', 'checked', 'x', 'true.0'])
        data['Payé'] = data['Payé'].astype(bool)
    return data

df_all = load_data()

# --- BARRE LATÉRALE : SAISIE ---
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
        "Payé": False # Par défaut, une nouvelle vente n'est pas payée
    }])
    updated_df = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=updated_df)
    st.sidebar.success("Enregistré !")
    st.rerun()

# --- CALCULS DE LOGIQUE ---

# 1. Total des achats (Stock) - Toujours déduit
total_achats = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0

# 2. Reste à partager (Ventes NON COCHÉES)
df_non_paye = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]
reste_a_partager = df_non_paye["Montant"].sum()

# 3. Bénéfice déjà encaissé (Ventes COCHÉES - Achats)
df_paye = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]
ventes_payees_total = df_paye["Montant"].sum()
benefice_deja_distribue = ventes_payees_total - total_achats

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Régularisation", "👩‍💻 Compte Julie", "👨‍💻 Compte Mathéo"])

with tab1:
    st.subheader("📈 Performance & Paiements")
    
    # Section "Reste à partager"
    col_pay, col_imp = st.columns(2)
    with col_pay:
        st.success(f"💰 Reste à partager : **{reste_a_partager:.2f} €**")
        st.write(f"👉 Verser à Julie : **{(reste_a_partager/2):.2f} €**")
        st.caption("Une fois le virement fait, cochez 'Payé' ci-dessous et sauvegardez.")

    with col_imp:
        ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
        st.error(f"🏦 Impôts prévisionnels (22%) : **{(ca_total * 0.22):.2f} €**")

    st.divider()

    # Le Tableau Éditable
    st.subheader("📑 Historique & Validation des paiements")
    edited_df = st.data_editor(
        df_all,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?"),
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "Année": None
        },
        use_container_width=True,
        hide_index=True,
        key="editor_main"
    )
    
    if st.button("💾 Sauvegarder les changements"):
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.success("Données mises à jour !")
        st.rerun()

with tab2:
    st.subheader("👩‍💻 Compte Julie")
    # Julie reçoit 50% du bénéfice encaissé (Ventes payées - Achats)
    part_julie = benefice_deja_distribue / 2
    st.metric("Bénéfice Net Reçu", f"{part_julie:.2f} €")
    
    st.write("### 📜 Historique de mes gains encaissés")
    df_j = df_all[(df_all["Payé"] == True) | (df_all["Montant"] < 0)].copy()
    if not df_j.empty:
        df_j['Ma Part (50%)'] = df_j['Montant'] / 2
        st.dataframe(df_j[["Date", "Description", "Ma Part (50%)"]], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("👨‍💻 Compte Mathéo")
    # Mathéo reçoit la même chose
    part_matheo = benefice_deja_distribue / 2
    st.metric("Bénéfice Net Reçu", f"{part_matheo:.2f} €")
    
    st.write("### 📜 Historique de mes gains encaissés")
    df_m = df_all[(df_all["Payé"] == True) | (df_all["Montant"] < 0)].copy()
    if not df_m.empty:
        df_m['Ma Part (50%)'] = df_m['Montant'] / 2
        st.dataframe(df_m[["Date", "Description", "Ma Part (50%)"]], use_container_width=True, hide_index=True)
