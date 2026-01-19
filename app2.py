import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="MJTGC Whatnot Tracker Pro", layout="wide", initial_sidebar_state="expanded")

# --- STYLES CSS ---
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .positive {color: #10b981; font-weight: bold;}
    .negative {color: #ef4444; font-weight: bold;}
    .pending {color: #f59e0b; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.title("🤝 MJTGC - Whatnot Duo Tracker Pro")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTIONS OCR ---
def simple_ocr(image):
    """Extraction intelligente de données depuis un ticket"""
    text = pytesseract.image_to_string(image)
    
    prices = re.findall(r"(\d+[\.,]\d{2})", text)
    price = float(prices[-1].replace(',', '.')) if prices else 0.0
    
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    date_found = pd.to_datetime(dates[0], dayfirst=True) if dates else datetime.now()
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0][:30] if lines else "Scan Ticket"
    
    return date_found, name, price

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=5)
def load_data():
    """Charge et nettoie les données depuis Google Sheets"""
    data = conn.read(ttl="0s")
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        
        # Nouvelles colonnes de remboursement
        if 'Statut_Julie' not in data.columns:
            data['Statut_Julie'] = 'En attente'
        if 'Statut_Matheo' not in data.columns:
            data['Statut_Matheo'] = 'En attente'
        if 'Date_Remb_Julie' not in data.columns:
            data['Date_Remb_Julie'] = None
        if 'Date_Remb_Matheo' not in data.columns:
            data['Date_Remb_Matheo'] = None
        if 'Montant_Part' not in data.columns:
            data['Montant_Part'] = data['Montant'] / 2
            
        data['Date_Remb_Julie'] = pd.to_datetime(data['Date_Remb_Julie'], errors='coerce')
        data['Date_Remb_Matheo'] = pd.to_datetime(data['Date_Remb_Matheo'], errors='coerce')
        
    return data

# --- INITIALISATION ---
if 'data' not in st.session_state or st.button("🔄 Rafraîchir", key="refresh_top"):
    st.session_state.data = load_data()

df = st.session_state.data

# --- SIDEBAR : SAISIE ---
with st.sidebar:
    st.header("📸 Scanner un Ticket")
    file = st.file_uploader("Prendre en photo", type=['jpg', 'jpeg', 'png'])
    
    if file:
        img = Image.open(file)
        st.image(img, width=250)
        if st.button("🔍 Analyser"):
            s_date, s_name, s_price = simple_ocr(img)
            st.session_state['scan_date'] = s_date
            st.session_state['scan_name'] = s_name
            st.session_state['scan_price'] = s_price
            st.success("✅ Ticket analysé !")
    
    st.divider()
    st.header("➕ Nouvelle Opération")
    
    date_op = st.date_input("📅 Date", st.session_state.get('scan_date', datetime.now()))
    type_op = st.selectbox("🏷️ Type", ["💰 Vente Whatnot", "🛒 Achat Stock", "💸 Frais", "🔄 Remboursement"])
    desc = st.text_input("📝 Description", st.session_state.get('scan_name', ""))
    montant = st.number_input("💵 Montant (€)", min_value=0.0, step=0.01, value=st.session_state.get('scan_price', 0.0))
    
    if st.button("💾 Enregistrer", type="primary", use_container_width=True):
        # Calcul du montant avec signe
        if "Vente" in type_op:
            valeur = montant
        else:
            valeur = -montant
        
        new_row = pd.DataFrame([{
            "Date": pd.to_datetime(date_op),
            "Type": type_op,
            "Description": desc,
            "Montant": valeur,
            "Montant_Part": valeur / 2,
            "Statut_Julie": "En attente",
            "Statut_Matheo": "En attente",
            "Date_Remb_Julie": None,
            "Date_Remb_Matheo": None,
            "Année": str(date_op.year)
        }])
        
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        
        # Sauvegarde
        df_save = st.session_state.data.copy()
        df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
        df_save['Date_Remb_Julie'] = pd.to_datetime(df_save['Date_Remb_Julie']).dt.strftime('%Y-%m-%d')
        df_save['Date_Remb_Matheo'] = pd.to_datetime(df_save['Date_Remb_Matheo']).dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        
        # Reset scan
        for key in ['scan_date', 'scan_name', 'scan_price']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("✅ Enregistré !")
        st.rerun()

# --- CALCULS GLOBAUX ---
ventes = df[df['Montant'] > 0]['Montant'].sum()
achats = abs(df[df['Montant'] < 0]['Montant'].sum())
benefice = ventes - achats

# Calcul par personne
julie_en_attente = df[df['Statut_Julie'] == 'En attente']['Montant_Part'].sum()
julie_paye = df[df['Statut_Julie'] == 'Payé']['Montant_Part'].sum()
matheo_en_attente = df[df['Statut_Matheo'] == 'En attente']['Montant_Part'].sum()
matheo_paye = df[df['Statut_Matheo'] == 'Payé']['Montant_Part'].sum()

# --- ONGLETS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Tableau de Bord", "💰 Remboursements", "👩‍💻 Julie", "👨‍💻 Mathéo", "📋 Données"])

# --- TAB 1 : DASHBOARD ---
with tab1:
    st.subheader("📈 Vue d'Ensemble")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 CA Total", f"{ventes:.2f} €", delta=f"+{ventes/100:.0f}%" if ventes > 0 else None)
    with col2:
        st.metric("🛒 Achats", f"{achats:.2f} €", delta=f"-{achats/100:.0f}%" if achats > 0 else None)
    with col3:
        st.metric("💎 Bénéfice Net", f"{benefice:.2f} €", delta="Positif" if benefice > 0 else "Négatif")
    with col4:
        marge = (benefice / ventes * 100) if ventes > 0 else 0
        st.metric("📊 Marge", f"{marge:.1f}%", delta="Excellent" if marge > 30 else "Normal")
    
    st.divider()
    
    # Graphiques côte à côte
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📅 Évolution du CA")
        df_month = df[df['Montant'] > 0].copy()
        df_month['Mois'] = df_month['Date'].dt.to_period('M').astype(str)
        monthly = df_month.groupby('Mois')['Montant'].sum().reset_index()
        fig1 = px.line(monthly, x='Mois', y='Montant', markers=True, title="CA Mensuel")
        fig1.update_traces(line_color='#10b981', line_width=3)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_g2:
        st.subheader("🎯 Répartition des Opérations")
        type_counts = df['Type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Nombre']
        fig2 = px.pie(type_counts, values='Nombre', names='Type', hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)
    
    st.divider()
    
    # Dernières opérations
    st.subheader("🕒 5 Dernières Opérations")
    recent = df.sort_values('Date', ascending=False).head(5)
    st.dataframe(recent[['Date', 'Type', 'Description', 'Montant', 'Statut_Julie', 'Statut_Matheo']], 
                 use_container_width=True, hide_index=True)

# --- TAB 2 : REMBOURSEMENTS ---
with tab2:
    st.subheader("💳 Gestion des Remboursements")
    
    col_j, col_m = st.columns(2)
    
    with col_j:
        st.markdown("### 👩‍💻 Julie")
        st.metric("En attente", f"{julie_en_attente:.2f} €", delta=None)
        st.metric("Déjà payé", f"{julie_paye:.2f} €", delta=None)
        st.progress(julie_paye / (julie_paye + julie_en_attente) if (julie_paye + julie_en_attente) > 0 else 0)
        
        st.divider()
        st.markdown("#### Transactions en attente :")
        julie_pending = df[df['Statut_Julie'] == 'En attente'].copy()
        if not julie_pending.empty:
            for idx, row in julie_pending.iterrows():
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.write(f"**{row['Description']}** - {row['Date'].strftime('%d/%m/%Y')}")
                        st.write(f"<span class='pending'>💰 {row['Montant_Part']:.2f} €</span>", unsafe_allow_html=True)
                    with col_btn:
                        if st.button("✅ Payé", key=f"julie_{idx}"):
                            st.session_state.data.at[idx, 'Statut_Julie'] = 'Payé'
                            st.session_state.data.at[idx, 'Date_Remb_Julie'] = datetime.now()
                            
                            df_save = st.session_state.data.copy()
                            df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
                            df_save['Date_Remb_Julie'] = pd.to_datetime(df_save['Date_Remb_Julie']).dt.strftime('%Y-%m-%d')
                            df_save['Date_Remb_Matheo'] = pd.to_datetime(df_save['Date_Remb_Matheo']).dt.strftime('%Y-%m-%d')
                            conn.update(data=df_save)
                            st.rerun()
        else:
            st.success("🎉 Tout est payé !")
    
    with col_m:
        st.markdown("### 👨‍💻 Mathéo")
        st.metric("En attente", f"{matheo_en_attente:.2f} €", delta=None)
        st.metric("Déjà payé", f"{matheo_paye:.2f} €", delta=None)
        st.progress(matheo_paye / (matheo_paye + matheo_en_attente) if (matheo_paye + matheo_en_attente) > 0 else 0)
        
        st.divider()
        st.markdown("#### Transactions en attente :")
        matheo_pending = df[df['Statut_Matheo'] == 'En attente'].copy()
        if not matheo_pending.empty:
            for idx, row in matheo_pending.iterrows():
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.write(f"**{row['Description']}** - {row['Date'].strftime('%d/%m/%Y')}")
                        st.write(f"<span class='pending'>💰 {row['Montant_Part']:.2f} €</span>", unsafe_allow_html=True)
                    with col_btn:
                        if st.button("✅ Payé", key=f"matheo_{idx}"):
                            st.session_state.data.at[idx, 'Statut_Matheo'] = 'Payé'
                            st.session_state.data.at[idx, 'Date_Remb_Matheo'] = datetime.now()
                            
                            df_save = st.session_state.data.copy()
                            df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
                            df_save['Date_Remb_Julie'] = pd.to_datetime(df_save['Date_Remb_Julie']).dt.strftime('%Y-%m-%d')
                            df_save['Date_Remb_Matheo'] = pd.to_datetime(df_save['Date_Remb_Matheo']).dt.strftime('%Y-%m-%d')
                            conn.update(data=df_save)
                            st.rerun()
        else:
            st.success("🎉 Tout est payé !")

# --- TAB 3 : JULIE ---
with tab3:
    st.subheader("👩‍💻 Statistiques Julie")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Encaissé", f"{julie_paye:.2f} €")
    col2.metric("⏳ En Attente", f"{julie_en_attente:.2f} €")
    col3.metric("📊 Total Dû", f"{(julie_paye + julie_en_attente):.2f} €")
    
    st.divider()
    
    # Historique des paiements Julie
    st.subheader("📜 Historique des Paiements")
    julie_hist = df[df['Statut_Julie'] == 'Payé'].sort_values('Date_Remb_Julie', ascending=False)
    if not julie_hist.empty:
        st.dataframe(julie_hist[['Date', 'Description', 'Montant_Part', 'Date_Remb_Julie']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Aucun paiement enregistré pour l'instant")

# --- TAB 4 : MATHÉO ---
with tab4:
    st.subheader("👨‍💻 Statistiques Mathéo")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Encaissé", f"{matheo_paye:.2f} €")
    col2.metric("⏳ En Attente", f"{matheo_en_attente:.2f} €")
    col3.metric("📊 Total Dû", f"{(matheo_paye + matheo_en_attente):.2f} €")
    
    st.divider()
    
    # Historique des paiements Mathéo
    st.subheader("📜 Historique des Paiements")
    matheo_hist = df[df['Statut_Matheo'] == 'Payé'].sort_values('Date_Remb_Matheo', ascending=False)
    if not matheo_hist.empty:
        st.dataframe(matheo_hist[['Date', 'Description', 'Montant_Part', 'Date_Remb_Matheo']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Aucun paiement enregistré pour l'instant")

# --- TAB 5 : DONNÉES BRUTES ---
with tab5:
    st.subheader("📋 Gestion des Données")
    
    edited_df = st.data_editor(
        st.session_state.data,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
            "Montant_Part": st.column_config.NumberColumn("Part (50%)", format="%.2f €"),
            "Statut_Julie": st.column_config.SelectboxColumn("Statut Julie", options=["En attente", "Payé"]),
            "Statut_Matheo": st.column_config.SelectboxColumn("Statut Mathéo", options=["En attente", "Payé"]),
        }
    )
    
    col_save, col_export = st.columns(2)
    
    with col_save:
        if st.button("💾 Sauvegarder les Modifications", type="primary", use_container_width=True):
            st.session_state.data = edited_df
            df_save = edited_df.copy()
            df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
            df_save['Date_Remb_Julie'] = pd.to_datetime(df_save['Date_Remb_Julie']).dt.strftime('%Y-%m-%d')
            df_save['Date_Remb_Matheo'] = pd.to_datetime(df_save['Date_Remb_Matheo']).dt.strftime('%Y-%m-%d')
            conn.update(data=df_save)
            st.success("✅ Données sauvegardées !")
            st.rerun()
    
    with col_export:
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Exporter en CSV",
            csv,
            "mjtgc_export.csv",
            "text/csv",
            use_container_width=True
        )

# --- FOOTER ---
st.divider()
st.caption(f"🔄 Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
