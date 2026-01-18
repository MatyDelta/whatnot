import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURATION
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# 2. CONNEXION
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        # Supprime les lignes totalement vides (souvent en bas du Sheets)
        data = data.dropna(how='all')
        
        # Force la Date
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data = data.dropna(subset=['Date'])
        
        # Force le Montant
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0.0)
        
        # Force le Payé (Conversion ultra-sécurisée)
        def clean_bool(val):
            val = str(val).lower().strip()
            return val in ['true', '1', 'yes', 'vrai', 'checked', 'x', 'v']
        
        data['Payé'] = data['Payé'].apply(clean_bool)
    return data

# Chargement
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

# --- CALCULS ---
ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benefice_historique = ca_historique - achats_historique

df_en_attente = df_all[df_all["Payé"] == False] if not df_all.empty else pd.DataFrame()
ca_en_attente = df_en_attente[df_en_attente["Montant"] > 0]["Montant"].sum() if not df_en_attente.empty else 0
achats_en_attente = abs(df_en_attente[df_en_attente["Montant"] < 0]["Montant"].sum()) if not df_en_attente.empty else 0
benefice_net_partageable = ca_en_attente - achats_en_attente

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Stats & Régularisation", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_historique:.2f} €")
    c2.metric("Total Achats", f"-{achats_historique:.2f} €")
    c3.metric("Bénéfice Brut", f"{benefice_historique:.2f} €")
    
    st.divider()
    
    st.subheader("💳 Paiements en cours")
    col_pay, col_imp = st.columns(2)
    with col_pay:
        st.success(f"💰 Reste à partager : **{max(0, benefice_net_partageable):.2f} €**")
        st.write(f"👉 Verser à Julie : **{(max(0, benefice_net_partageable)/2):.2f} €**")

    with col_imp:
        st.error(f"🏦 Impôts (22%) : **{(ca_historique * 0.22):.2f} €**")

    st.divider()

    # --- LE TABLEAU (ZONE SENSIBLE) ---
    st.subheader("📑 Historique des transactions")
    
    # Création d'une copie propre forcée en types Python standards
    df_clean_display = df_all.copy()
    df_clean_display['Payé'] = df_clean_display['Payé'].astype(bool)

    edited_df = st.data_editor(
        df_clean_display,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?"),
            "Date": st.column_config.DateColumn("Date"),
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "Année": None,
            "Type": st.column_config.SelectboxColumn("Type", options=["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_final"
    )
    
    if st.button("💾 Sauvegarder les changements"):
        df_save = edited_df.copy()
        df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.success("Sheets mis à jour !")
        st.rerun()

# --- CODES JULIE ET MATHEO ---
# (Gardez votre code actuel pour tab2 et tab3, il fonctionne très bien)

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
