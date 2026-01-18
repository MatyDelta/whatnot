import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
st.set_page_config(page_title="Whatnot Duo Tracker", layout="wide")
st.title("🤝 Gestion Duo Mathéo & Julie")

# --- CONNEXION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how="all")
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data = data.dropna(subset=["Date"])
        data["Montant"] = pd.to_numeric(data["Montant"], errors="coerce").fillna(0)
        data["Payé"] = (
            data["Payé"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "vrai", "checked", "x"])
        )
    return data

df_all = load_data()

# --- SIDEBAR ---
st.sidebar.header("📝 Saisir une opération")
type_op = st.sidebar.selectbox("Nature", ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)"])
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=1.0)
date_op = st.sidebar.date_input("Date", datetime.now())

if st.sidebar.button("Enregistrer"):
    valeur = montant if "Vente" in type_op else -montant
    new_row = pd.DataFrame([{
        "Date": date_op.strftime("%Y-%m-%d"),
        "Type": type_op,
        "Description": desc,
        "Montant": valeur,
        "Année": str(date_op.year),
        "Payé": False
    }])
    df_all = pd.concat([df_all, new_row], ignore_index=True)
    conn.update(data=df_all)
    st.sidebar.success("Enregistré !")
    st.rerun()

# =======================
# 🔢 CALCULS CORRECTS
# =======================

# Historique total
ca_historique = df_all[df_all["Montant"] > 0]["Montant"].sum()
achats_historique = abs(df_all[df_all["Montant"] < 0]["Montant"].sum())
benefice_total = ca_historique - achats_historique

# Bénéfice NON PAYÉ
df_non_paye = df_all[df_all["Payé"] == False]
benefice_a_partager = df_non_paye["Montant"].sum()

# Bénéfice DÉJÀ PAYÉ
df_paye = df_all[df_all["Payé"] == True]
benefice_deja_paye = df_paye["Montant"].sum()

# Part individuelle
part_julie = benefice_deja_paye / 2
part_matheo = benefice_deja_paye / 2

# --- TABS ---
tab1, tab2, tab3 = st.tabs([
    "📊 Statistiques & Régularisation",
    "👩‍💻 Compte Julie",
    "👨‍💻 Compte Mathéo"
])

# =======================
# 📊 TAB 1
# =======================
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_historique:.2f} €")
    c2.metric("Achats", f"-{achats_historique:.2f} €")
    c3.metric("Bénéfice Total", f"{benefice_total:.2f} €")

    st.divider()

    st.success(f"💰 Reste à partager : **{max(0, benefice_a_partager):.2f} €**")
    st.write(f"👉 Verser à Julie : **{max(0, benefice_a_partager)/2:.2f} €**")

    st.divider()

    edited_df = st.data_editor(
        df_all,
        column_config={
            "Payé": st.column_config.CheckboxColumn("Payé ?"),
            "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "Année": None
        },
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 Sauvegarder"):
        edited_df["Date"] = edited_df["Date"].dt.strftime("%Y-%m-%d")
        conn.update(data=edited_df)
        st.success("Mis à jour")
        st.rerun()

# =======================
# 👩‍💻 JULIE
# =======================
with tab2:
    st.metric("💰 Bénéfice encaissé (Julie)", f"{part_julie:.2f} €")

    df_j = df_paye.copy()
    df_j["Part Julie"] = df_j["Montant"] / 2

    st.dataframe(
        df_j[["Date", "Description", "Montant", "Part Julie"]],
        use_container_width=True,
        hide_index=True
    )

# =======================
# 👨‍💻 MATHEO
# =======================
with tab3:
    st.metric("💰 Bénéfice encaissé (Mathéo)", f"{part_matheo:.2f} €")

    df_m = df_paye.copy()
    df_m["Part Mathéo"] = df_m["Montant"] / 2

    st.dataframe(
        df_m[["Date", "Description", "Montant", "Part Mathéo"]],
        use_container_width=True,
        hide_index=True
    )
