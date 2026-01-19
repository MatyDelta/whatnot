import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(page_title="Whatnot Duo Tracker MJTGC", layout="wide")
st.title("🤝 MJTGC - Whatnot Duo Tracker")

conn = st.connection("gsheets", type=GSheetsConnection)

# ==================================================
# DATA
# ==================================================
def load_data():
    df = conn.read(ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Date", "Type", "Description", "Montant", "Payé", "Année"]
        )

    df = df.dropna(how="all")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Montant"] = pd.to_numeric(df["Montant"], errors="coerce").fillna(0)
    df["Payé"] = df["Payé"].astype(bool)
    df["Année"] = df["Date"].dt.year.astype(str)
    return df

if "data" not in st.session_state:
    st.session_state.data = load_data()

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.header("➕ Nouvelle opération")

date_op = st.sidebar.date_input("Date", datetime.now())
type_op = st.sidebar.selectbox(
    "Type",
    [
        "Vente (Gain net Whatnot)",
        "Achat Stock (Dépense)",
        "Remboursement à Julie",
    ],
)
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01)

# ==================================================
# SAVE OPERATION
# ==================================================
if st.sidebar.button("💾 Enregistrer"):
    df = st.session_state.data.copy()

    # ----------- VENTE / ACHAT -----------
    if type_op != "Remboursement à Julie":
        valeur = montant if "Vente" in type_op else -montant

        df = pd.concat([df, pd.DataFrame([{
            "Date": pd.to_datetime(date_op),
            "Type": type_op,
            "Description": desc,
            "Montant": valeur,
            "Payé": False,
            "Année": str(date_op.year)
        }])], ignore_index=True)

    # ----------- REMBOURSEMENT JULIE -----------
    else:
        # 1️⃣ Ajouter le remboursement
        df = pd.concat([df, pd.DataFrame([{
            "Date": pd.to_datetime(date_op),
            "Type": type_op,
            "Description": desc,
            "Montant": -montant,
            "Payé": True,
            "Année": str(date_op.year)
        }])], ignore_index=True)

    # ==================================================
    # 🔒 LOGIQUE DE PAIEMENT (CENTRALE, UNIQUE)
    # ==================================================

    # Bénéfice TOTAL (indépendant de Payé)
    total_ventes = df[df["Montant"] > 0]["Montant"].sum()
    total_achats = abs(df[df["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
    benefice_total = max(0, total_ventes - total_achats)

    # Part Julie
    part_julie = benefice_total / 2

    # Total réellement remboursé
    total_rembourse = abs(
        df[df["Type"] == "Remboursement à Julie"]["Montant"].sum()
    )

    # 👉 SEULE CONDITION AUTORISÉE
    if total_rembourse >= part_julie and part_julie > 0:
        df.loc[df["Montant"] > 0, "Payé"] = True
    else:
        df.loc[df["Montant"] > 0, "Payé"] = False

    # SAVE
    st.session_state.data = df
    df_save = df.copy()
    df_save["Date"] = df_save["Date"].dt.strftime("%Y-%m-%d")
    conn.update(data=df_save)
    st.rerun()

# ==================================================
# CALCULS
# ==================================================
df_all = st.session_state.data.sort_values("Date", ascending=False)

ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
depenses = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
benefice = ca_total - depenses

part_julie = max(0, benefice / 2)
julie_paye = abs(df_all[df_all["Type"] == "Remboursement à Julie"]["Montant"].sum())
julie_reste = max(0, part_julie - julie_paye)

# ==================================================
# UI
# ==================================================
tab1, tab2, tab3 = st.tabs(["📊 Stats", "📑 Journal", "👩‍💻 Julie"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_total:.2f} €")
    c2.metric("Achats", f"-{depenses:.2f} €")
    c3.metric("Bénéfice Brut", f"{benefice:.2f} €")

    st.divider()
    st.warning(f"💰 Part Julie totale : {part_julie:.2f} €")
    st.info(f"👉 Reste à payer Julie : {julie_reste:.2f} €")

with tab2:
    st.dataframe(
        df_all.drop(columns=["Année"]),
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.metric("Déjà payé", f"{julie_paye:.2f} €")
    st.metric("Reste à recevoir", f"{julie_reste:.2f} €")
