import streamlit as st
import pandas as pd
from datetime import datetime

# ================= CONFIG =================
st.set_page_config("MJTGC – Live Tracker", layout="wide")

TAUX_IMPOT = 0.22
PALIERS = [1000, 5000, 10000, 20000]

# ================= DATA =================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data.csv")
    except:
        df = pd.DataFrame(columns=[
            "DATE", "LIVE_ID", "TYPE", "DESCRIPTION",
            "MONTANT", "JULIE_PAYE"
        ])
    return df

def save_data(df):
    df.to_csv("data.csv", index=False)

df = load_data()

# ================= CALCULS =================
def calcul_par_live(df):
    lives = []

    for live_id, d in df.groupby("LIVE_ID"):
        ventes = d[d["TYPE"] == "vente"]["MONTANT"].sum()
        depenses = d[d["TYPE"] == "depense"]["MONTANT"].sum()
        benefice = ventes - depenses

        julie_due = benefice / 2
        julie_paye = d["JULIE_PAYE"].sum()

        if julie_paye >= julie_due:
            statut = "Payé"
        elif julie_paye > 0:
            statut = "Partiel"
        else:
            statut = "En attente"

        matheo = julie_due if statut == "Payé" else 0

        lives.append({
            "LIVE_ID": live_id,
            "CA_BRUT": ventes,
            "DEPENSES": depenses,
            "BENEFICE": benefice,
            "JULIE_DUE": julie_due,
            "JULIE_PAYE": julie_paye,
            "STATUT_JULIE": statut,
            "MATHEO": matheo
        })

    return pd.DataFrame(lives)

df_live = calcul_par_live(df)

CA_BRUT = df[df["TYPE"] == "vente"]["MONTANT"].sum()
DEPENSES = df[df["TYPE"] == "depense"]["MONTANT"].sum()
BENEFICE_NET = CA_BRUT - DEPENSES
IMPOTS = CA_BRUT * TAUX_IMPOT

# ================= UI =================
st.title("💎 MJTGC – Whatnot Live Tracker")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🎥 Historique Lives",
    "👩 Julie",
    "👨 Mathéo"
])

# ================= DASHBOARD =================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 CA Brut", f"{CA_BRUT:.2f} €")
    c2.metric("💸 Dépenses", f"{DEPENSES:.2f} €")
    c3.metric("💎 Bénéfice Net", f"{BENEFICE_NET:.2f} €")
    c4.metric("🧾 Impôts estimés", f"{IMPOTS:.2f} €")

    for p in PALIERS:
        st.progress(min(CA_BRUT / p, 1.0))
        st.write(f"🎯 Objectif {p} €")

# ================= HISTORIQUE LIVES =================
with tab2:
    st.subheader("🎥 Résumé par Live")
    st.dataframe(df_live, use_container_width=True)

# ================= JULIE =================
with tab3:
    total_due = df_live["JULIE_DUE"].sum()
    total_paye = df_live["JULIE_PAYE"].sum()

    st.metric("💰 Total dû", f"{total_due:.2f} €")
    st.metric("✅ Total payé", f"{total_paye:.2f} €")
    st.progress(total_paye / total_due if total_due else 0)

    st.subheader("💳 Remboursements")
    for i, row in df_live.iterrows():
        if row["STATUT_JULIE"] != "Payé":
            with st.expander(f"Live {row['LIVE_ID']} – {row['STATUT_JULIE']}"):
                montant = st.number_input(
                    "Montant remboursé",
                    min_value=0.0,
                    step=1.0,
                    key=f"julie_{i}"
                )
                if st.button("💸 Rembourser", key=f"btn_{i}"):
                    df.loc[len(df)] = [
                        datetime.now().date(),
                        row["LIVE_ID"],
                        "remboursement",
                        "Remboursement Julie",
                        0,
                        montant
                    ]
                    save_data(df)
                    st.experimental_rerun()

# ================= MATHEO =================
with tab4:
    matheo_total = df_live["MATHEO"].sum()
    st.metric("💰 Disponible", f"{matheo_total:.2f} €")

    st.dataframe(
        df_live[df_live["STATUT_JULIE"] == "Payé"]
        [["LIVE_ID", "MATHEO"]],
        use_container_width=True
    )

# ================= AJOUT OPERATION =================
st.sidebar.subheader("➕ Nouvelle opération")

with st.sidebar.form("add"):
    live = st.text_input("Live ID")
    type_op = st.selectbox("Type", ["vente", "depense"])
    desc = st.text_input("Description")
    montant = st.number_input("Montant", min_value=0.0)
    submit = st.form_submit_button("Ajouter")

    if submit:
        df.loc[len(df)] = [
            datetime.now().date(),
            live,
            type_op,
            desc,
            montant,
            0
        ]
        save_data(df)
        st.experimental_rerun()
