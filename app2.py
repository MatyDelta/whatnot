import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# --- INITIALISATION ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Année", "Payé"])

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
    st.sidebar.success("Enregistré !")

# --- CALCULS ---
df_all = st.session_state.data
ca_h = df_all[df_all["Montant"] > 0]["Montant"].sum() if not df_all.empty else 0
achats_h = abs(df_all[df_all["Montant"] < 0]["Montant"].sum()) if not df_all.empty else 0
benef_h = ca_h - achats_h

# Argent perso historique (Ventes payées - tous les achats) / 2
ventes_payees = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum() if not df_all.empty else 0
argent_perso_historique = (ventes_payees - achats_h) / 2

# --- CALCULS "EN COURS" (Ce qu'il reste à régulariser) ---
df_non_paye = df_all[df_all["Payé"] == False] if not df_all.empty else pd.DataFrame()
ca_en_cours = df_non_paye[df_non_paye["Montant"] > 0]["Montant"].sum() if not df_non_paye.empty else 0
achats_en_cours = abs(df_non_paye[df_non_paye["Montant"] < 0]["Montant"].sum()) if not df_non_paye.empty else 0
benef_brut_en_cours = ca_en_cours - achats_en_cours

# --- ORGANISATION EN ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📊 Vue Globale & Régularisation", "👩‍💻 Compte Julie", "👨‍💻 Compte Mathéo"])

with tab1:
    # --- COMPTEURS DE RÉGULARISATION ---
    st.subheader("⚠️ À régulariser (Ventes non encore payées)")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA en attente", f"{ca_en_cours:.2f} €")
    c2.metric("Achats à déduire", f"-{achats_en_cours:.2f} €")
    c3.metric("Bénéfice à partager", f"{benef_brut_en_cours:.2f} €")
    
    st.divider()
    
    # --- SECTION IMPOTS ET DUO ---
    col_impots, col_duo = st.columns(2)
    with col_impots:
        st.subheader("🏦 Section Impôts")
        total_impots = ca_en_cours * 0.22
        st.error(f"Provision Impôts (22% du CA) : **{total_impots:.2f} €**")
        st.caption(f"Soit {total_impots/2:.2f} € chacune à mettre de côté.")

    with col_duo:
        st.subheader("👯 Reste à payer à Julie")
        st.success(f"Montant du virement à faire : **{max(0, benef_brut_en_cours/2):.2f} €**")
        st.caption("Calculé sur le bénéfice brut (Ventes - Achats) / 2.")

    st.divider()
    
    # --- GRAPHIQUE GLOBAL ---
    if not df_all.empty:
        st.subheader("📈 Évolution du Bénéfice Global (Historique)")
        df_all['Date'] = pd.to_datetime(df_all['Date'])
        df_global = df_all.sort_values("Date").copy()
        df_global['Cumul'] = df_global['Montant'].cumsum()
        fig_global = px.area(df_global, x="Date", y="Cumul", color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig_global, use_container_width=True)

    # --- TABLEAU ET MODIFS ---
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
        st.session_state.data = edited_df
        st.rerun()

with tab2:
    st.subheader("🏆 Score Julie")
    st.write(f"Bénéfice total historique encaissé : **{argent_perso_historique:.2f} €**")
    
    if not df_all.empty:
        df_j = df_all.sort_values("Date").copy()
        df_j['Gain_J'] = df_j.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or x['Payé'] == True) else 0, axis=1)
        df_j['Cumul_J'] = df_j['Gain_J'].cumsum()
        fig_j = px.line(df_j, x="Date", y="Cumul_J", title="Progression de Julie", markers=True, color_discrete_sequence=['#FF66C4'])
        st.plotly_chart(fig_j, use_container_width=True)

with tab3:
    st.subheader("🏆 Score Mathéo")
    st.write(f"Bénéfice total historique encaissé : **{argent_perso_historique:.2f} €**")
    
    if not df_all.empty:
        df_m = df_all.sort_values("Date").copy()
        df_m['Gain_M'] = df_m.apply(lambda x: (x['Montant']/2) if (x['Montant'] < 0 or x['Payé'] == True) else 0, axis=1)
        df_m['Cumul_M'] = df_m['Gain_M'].cumsum()
        fig_m = px.line(df_m, x="Date", y="Cumul_M", title="Progression de Mathéo", markers=True, color_discrete_sequence=['#17BECF'])
        st.plotly_chart(fig_m, use_container_width=True)
