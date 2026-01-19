import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# ================= CONFIG =================
st.set_page_config(page_title="Whatnot Duo Tracker MJTGC", layout="wide")
st.title("🤝 MJTGC - Whatnot Duo Tracker")

conn = st.connection("gsheets", type=GSheetsConnection)

# ================= OCR =================
def simple_ocr(image):
    image = image.convert('L')
    text = pytesseract.image_to_string(image, lang='fra')

    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    price = float(prices[-1].replace(',', '.')) if prices else 0.0

    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    date_found = pd.to_datetime(dates[0], dayfirst=True) if dates else datetime.now()

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0][:20] if lines else "Ticket Scan"

    return date_found, name, price

# ================= DATA =================
def load_data():
    df = conn.read(ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Type", "Description", "Montant", "Payé", "Année"])

    df = df.dropna(how="all")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Montant"] = pd.to_numeric(df["Montant"], errors="coerce").fillna(0)
    df["Payé"] = df["Payé"].astype(str).str.lower().isin(["true", "1", "vrai", "x", "v"])
    df["Année"] = df["Date"].dt.year.astype(str)

    return df

if "data" not in st.session_state:
    st.session_state.data = load_data()

# ================= SIDEBAR =================
st.sidebar.header("📸 Scanner un ticket")
file = st.sidebar.file_uploader("Photo", type=["jpg", "png", "jpeg"])

if file:
    img = Image.open(file)
    if st.sidebar.button("Analyser"):
        d, n, p = simple_ocr(img)
        st.session_state.scan = (d, n, p)
        st.sidebar.success(f"{n} | {p:.2f} €")

st.sidebar.divider()
st.sidebar.header("➕ Nouvelle opération")

date_op = st.sidebar.date_input("Date", datetime.now())
type_op = st.sidebar.selectbox(
    "Type",
    ["Vente (Gain net Whatnot)", "Achat Stock (Dépense)", "Remboursement à Julie"]
)
desc = st.sidebar.text_input("Description")
montant = st.sidebar.number_input("Montant (€)", min_value=0.0, step=0.01)

# ================= SAVE OPERATION =================
if st.sidebar.button("💾 Enregistrer"):
    df = st.session_state.data.copy()

    # ---- VENTE / ACHAT ----
    if type_op != "Remboursement à Julie":
        valeur = montant if "Vente" in type_op else -montant
        new_row = {
            "Date": pd.to_datetime(date_op),
            "Type": type_op,
            "Description": desc,
            "Montant": valeur,
            "Payé": False,
            "Année": str(date_op.year)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # ---- REMBOURSEMENT JULIE ----
    else:
        # Gains non payés
        gains_non_payes = df[
            (df["Montant"] > 0) & (df["Payé"] == False)
        ]["Montant"].sum()

        part_julie = gains_non_payes / 2

        deja_paye = abs(
            df[df["Type"] == "Remboursement à Julie"]["Montant"].sum()
        )

        reste_a_payer = max(0, part_julie - deja_paye)

        # Enregistrer le remboursement (même partiel)
        new_row = {
            "Date": pd.to_datetime(date_op),
            "Type": type_op,
            "Description": desc,
            "Montant": -montant,
            "Payé": True,
            "Année": str(date_op.year)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Si seuil atteint → on solde les gains correspondants
        if montant >= reste_a_payer and reste_a_payer > 0:
            a_solder = part_julie * 2  # gains totaux liés

            idx = df[
                (df["Montant"] > 0) & (df["Payé"] == False)
            ].index

            for i in idx:
                if a_solder > 0:
                    df.at[i, "Payé"] = True
                    a_solder -= df.at[i, "Montant"]

    st.session_state.data = df
    df_save = df.copy()
    df_save["Date"] = df_save["Date"].dt.strftime("%Y-%m-%d")
    conn.update(data=df_save)
    st.rerun()

# ================= CALCULS =================
df_all = st.session_state.data.sort_values("Date", ascending=False)

ca_total = df_all[df_all["Montant"] > 0]["Montant"].sum()
depenses = abs(df_all[df_all["Type"] == "Achat Stock (Dépense)"]["Montant"].sum())
gains_attente = df_all[(df_all["Montant"] > 0) & (df_all["Payé"] == False)]["Montant"].sum()
julie_reste = gains_attente / 2
julie_paye = abs(df_all[df_all["Type"] == "Remboursement à Julie"]["Montant"].sum())

# ================= UI =================
tab1, tab2, tab3 = st.tabs(["📊 Stats", "📑 Journal", "👩‍💻 Julie"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", f"{ca_total:.2f} €")
    c2.metric("Achats", f"-{depenses:.2f} €")
    c3.metric("Bénéfice brut", f"{(ca_total - depenses):.2f} €")

    st.divider()
    st.warning(f"💰 Gains à solder : {gains_attente:.2f} €")
    st.info(f"👩 Julie – reste à payer : {julie_reste:.2f} €")

with tab2:
    edited = st.data_editor(
        df_all.drop(columns=["Année"]),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )

    if st.button("💾 Sauvegarder modifications"):
        edited["Date"] = pd.to_datetime(edited["Date"])
        edited["Année"] = edited["Date"].dt.year.astype(str)
        st.session_state.data = edited
        edited["Date"] = edited["Date"].dt.strftime("%Y-%m-%d")
        conn.update(data=edited)
        st.rerun()

with tab3:
    st.metric("Déjà payé", f"{julie_paye:.2f} €")
    st.metric("Reste à recevoir", f"{julie_reste:.2f} €")
