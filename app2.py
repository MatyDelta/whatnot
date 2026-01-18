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
    df_save = st.session_state.data.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.sidebar.success("Enregistré et synchronisé !")
    st.rerun()

# --- LOGIQUE DE CALCUL MJTGC ---
df_all = st.session_state.data.sort_values("Date").reset_index(drop=True)

# 1. Calcul des Lives (Groupement par 2)
lives_history = []
i = 0
while i < len(df_all) - 1:
    curr = df_all.iloc[i]
    nxt = df_all.iloc[i+1]
    
    # Si on a une paire Achat/Vente ou Vente/Achat sur la même période/description proche
    if (curr['Montant'] * nxt['Montant']) < 0: # L'un est positif, l'autre négatif
        gain_net = curr['Montant'] + nxt['Montant']
        lives_history.append({
            "Date": nxt['Date'],
            "Détails": f"{curr['Description']} + {nxt['Description']}",
            "Investissement": min(curr['Montant'], nxt['Montant']),
            "Vente": max(curr['Montant'], nxt['Montant']),
            "Bénéfice Net": gain_net
        })
        i += 2 # On saute la paire
    else:
        i += 1

df_lives = pd.DataFrame(lives_history)

# 2. Variables de performance
ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum()
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())
gains_non_payes = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]["Montant"].sum()
gains_valides = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == True)]["Montant"].sum()

# --- ONGLETS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stats & Régul", "🎬 Historique Lives", "👩‍💻 Julie", "👨‍💻 Mathéo"])

with tab1:
    st.subheader("📈 Performance Totale")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_historique:.2f} €")
    c2.metric("Total Achats", f"-{achats_historique:.2f} €")
    c3.metric("Bénéfice Brut", f"{(ca_historique - achats_historique):.2f} €")
    
    st.divider()
    st.subheader("💳 Paiements en cours")
    col_pay, col_ver = st.columns(2)
    with col_pay:
        st.success(f"💰 Gains à partager : **{gains_non_payes:.2f} €**")
    with col_ver:
        st.info(f"👉 Verser à Julie (50%) : **{(gains_non_payes/2):.2f} €**")

    st.divider()
    st.subheader("📑 Toutes les transactions")
    edited_df = st.data_editor(df_all, use_container_width=True, hide_index=True, key="editor")
    if st.button("💾 Sauvegarder"):
        st.session_state.data = edited_df
        df_save = edited_df.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.rerun()

with tab2:
    st.subheader("🍿 Rentabilité par Live (Paires Achat/Vente)")
    if not df_lives.empty:
        st.dataframe(df_lives, use_container_width=True, hide_index=True)
        fig = px.bar(df_lives, x="Date", y="Bénéfice Net", title="Gains réels par session", color="Bénéfice Net")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ajoutez un achat et une vente pour voir le calcul du live s'afficher ici.")

# (Onglets Julie et Mathéo restent identiques à votre version précédente)
with tab3:
    st.subheader("🏆 Score Julie")
    st.metric("Total encaissé (Validé)", f"{(gains_valides / 2):.2f} €")

with tab4:
    st.subheader("🏆 Score Mathéo")
    st.metric("Total encaissé (Validé)", f"{(gains_valides / 2):.2f} €")
