import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from PIL import Image
import pytesseract
import re

# --- CONFIGURATION ---
st.set_page_config(
    page_title="MJTGC Whatnot Pro", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="💎"
)

# --- STYLES PERSONNALISÉS ---
st.markdown("""
<style>
    .big-font {font-size: 24px !important; font-weight: bold;}
    .metric-positive {color: #10b981; font-size: 28px; font-weight: bold;}
    .metric-negative {color: #ef4444; font-size: 28px; font-weight: bold;}
    .metric-pending {color: #f59e0b; font-size: 28px; font-weight: bold;}
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- TITRE ---
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("💎 MJTGC - Whatnot Tracker Pro")
with col_refresh:
    if st.button("🔄", help="Rafraîchir les données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- CONNEXION GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"❌ Erreur de connexion Google Sheets : {e}")
    st.stop()

# --- FONCTION OCR AMÉLIORÉE ---
def extract_ticket_data(image):
    """Extraction intelligente des données d'un ticket de caisse"""
    try:
        text = pytesseract.image_to_string(image, lang='fra')
        
        # Extraction du prix (dernier montant trouvé = souvent le total)
        prices = re.findall(r"(\d+[,\.]\d{2})", text)
        price = float(prices[-1].replace(',', '.')) if prices else 0.0
        
        # Extraction de la date
        date_patterns = [
            r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",  # JJ/MM/AAAA
            r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{2})"    # JJ/MM/AA
        ]
        date_found = datetime.now()
        for pattern in date_patterns:
            dates = re.findall(pattern, text)
            if dates:
                try:
                    date_found = pd.to_datetime(dates[0], dayfirst=True)
                    break
                except:
                    continue
        
        # Extraction du nom du magasin (première ligne non vide)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]
        store_name = lines[0][:40] if lines else "Ticket scanné"
        
        return date_found, store_name, price
    except Exception as e:
        st.error(f"Erreur OCR : {e}")
        return datetime.now(), "Ticket scanné", 0.0

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=10)
def load_data():
    """Charge et prépare les données depuis Google Sheets"""
    try:
        data = conn.read(ttl="0s")
        
        if data is None or data.empty:
            # Création d'un DataFrame vide avec la structure correcte
            return pd.DataFrame(columns=[
                'Date', 'Type', 'Description', 'Montant', 'Montant_Part',
                'Statut_Julie', 'Statut_Matheo', 'Date_Remb_Julie', 
                'Date_Remb_Matheo', 'Année', 'Notes'
            ])
        
        # Nettoyage des lignes vides
        data = data.dropna(how='all')
        
        # Conversion des types
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
        
        # Ajout des colonnes manquantes
        required_cols = {
            'Montant_Part': lambda: data['Montant'] / 2,
            'Statut_Julie': 'En attente',
            'Statut_Matheo': 'En attente',
            'Date_Remb_Julie': None,
            'Date_Remb_Matheo': None,
            'Année': lambda: data['Date'].dt.year.astype(str),
            'Notes': ''
        }
        
        for col, default in required_cols.items():
            if col not in data.columns:
                data[col] = default() if callable(default) else default
        
        # Conversion des dates de remboursement
        data['Date_Remb_Julie'] = pd.to_datetime(data['Date_Remb_Julie'], errors='coerce')
        data['Date_Remb_Matheo'] = pd.to_datetime(data['Date_Remb_Matheo'], errors='coerce')
        
        return data
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement : {e}")
        return pd.DataFrame()

# --- SAUVEGARDE DES DONNÉES ---
def save_data(dataframe):
    """Sauvegarde les données vers Google Sheets"""
    try:
        df_save = dataframe.copy()
        df_save['Date'] = pd.to_datetime(df_save['Date']).dt.strftime('%Y-%m-%d')
        df_save['Date_Remb_Julie'] = pd.to_datetime(df_save['Date_Remb_Julie'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_save['Date_Remb_Matheo'] = pd.to_datetime(df_save['Date_Remb_Matheo'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        conn.update(data=df_save)
        return True
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde : {e}")
        return False

# --- INITIALISATION SESSION STATE ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

df = st.session_state.data

# --- SIDEBAR : SAISIE ET SCAN ---
with st.sidebar:
    st.markdown("## 📸 Scanner un Ticket")
    
    uploaded_file = st.file_uploader(
        "Prendre une photo du ticket", 
        type=['jpg', 'jpeg', 'png'],
        help="Prenez une photo claire du ticket"
    )
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Aperçu", use_container_width=True)
        
        if st.button("🔍 Analyser le ticket", use_container_width=True):
            with st.spinner("Analyse en cours..."):
                scan_date, scan_name, scan_price = extract_ticket_data(img)
                st.session_state['scan_date'] = scan_date
                st.session_state['scan_name'] = scan_name
                st.session_state['scan_price'] = scan_price
                st.success("✅ Analyse terminée !")
                st.balloons()
    
    st.divider()
    st.markdown("## ➕ Nouvelle Opération")
    
    # Formulaire de saisie
    with st.form("new_operation", clear_on_submit=True):
        date_input = st.date_input(
            "📅 Date",
            value=st.session_state.get('scan_date', datetime.now()),
            max_value=datetime.now()
        )
        
        type_input = st.selectbox(
            "🏷️ Type d'opération",
            ["💰 Vente Whatnot", "🛒 Achat Stock", "💸 Frais Divers", "🎁 Remboursement"]
        )
        
        desc_input = st.text_input(
            "📝 Description",
            value=st.session_state.get('scan_name', ""),
            placeholder="Ex: Live Pokémon, Achat chez Carrefour..."
        )
        
        montant_input = st.number_input(
            "💵 Montant (€)",
            min_value=0.0,
            step=0.01,
            value=float(st.session_state.get('scan_price', 0.0)),
            format="%.2f"
        )
        
        notes_input = st.text_area(
            "📌 Notes (optionnel)",
            placeholder="Informations supplémentaires..."
        )
        
        submit_btn = st.form_submit_button("💾 Enregistrer", use_container_width=True, type="primary")
        
        if submit_btn:
            if desc_input and montant_input > 0:
                # Détermination du signe du montant
                if "Vente" in type_input or "Remboursement" in type_input:
                    final_amount = montant_input
                else:
                    final_amount = -montant_input
                
                # Création de la nouvelle ligne
                new_entry = pd.DataFrame([{
                    "Date": pd.to_datetime(date_input),
                    "Type": type_input,
                    "Description": desc_input,
                    "Montant": final_amount,
                    "Montant_Part": final_amount / 2,
                    "Statut_Julie": "En attente",
                    "Statut_Matheo": "En attente",
                    "Date_Remb_Julie": None,
                    "Date_Remb_Matheo": None,
                    "Année": str(date_input.year),
                    "Notes": notes_input
                }])
                
                # Ajout et sauvegarde
                st.session_state.data = pd.concat([st.session_state.data, new_entry], ignore_index=True)
                
                if save_data(st.session_state.data):
                    st.success("✅ Opération enregistrée avec succès !")
                    
                    # Reset des valeurs scannées
                    for key in ['scan_date', 'scan_name', 'scan_price']:
                        st.session_state.pop(key, None)
                    
                    st.rerun()
            else:
                st.error("⚠️ Veuillez remplir tous les champs obligatoires")

# --- CALCULS PRINCIPAUX ---
if not df.empty:
    # Calculs globaux
    total_ventes = df[df['Montant'] > 0]['Montant'].sum()
    total_achats = abs(df[df['Montant'] < 0]['Montant'].sum())
    benefice_net = total_ventes - total_achats
    marge = (benefice_net / total_ventes * 100) if total_ventes > 0 else 0
    
    # Calculs Julie
    julie_en_attente = df[df['Statut_Julie'] == 'En attente']['Montant_Part'].sum()
    julie_paye = df[df['Statut_Julie'] == 'Payé']['Montant_Part'].sum()
    julie_total = julie_en_attente + julie_paye
    julie_progress = (julie_paye / julie_total * 100) if julie_total > 0 else 0
    
    # Calculs Mathéo
    matheo_en_attente = df[df['Statut_Matheo'] == 'En attente']['Montant_Part'].sum()
    matheo_paye = df[df['Statut_Matheo'] == 'Payé']['Montant_Part'].sum()
    matheo_total = matheo_en_attente + matheo_paye
    matheo_progress = (matheo_paye / matheo_total * 100) if matheo_total > 0 else 0
else:
    total_ventes = total_achats = benefice_net = marge = 0
    julie_en_attente = julie_paye = julie_total = julie_progress = 0
    matheo_en_attente = matheo_paye = matheo_total = matheo_progress = 0

# --- ONGLETS PRINCIPAUX ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", 
    "💰 Remboursements", 
    "👩‍💻 Julie", 
    "👨‍💻 Mathéo", 
    "📋 Données"
])

# ========== TAB 1 : DASHBOARD ==========
with tab1:
    st.markdown("### 📈 Performance Globale")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💵 Chiffre d'Affaires",
            f"{total_ventes:.2f} €",
            delta=f"+{(total_ventes/len(df)*100):.0f}% moy." if len(df) > 0 else None
        )
    
    with col2:
        st.metric(
            "🛒 Total Achats",
            f"{total_achats:.2f} €",
            delta=f"-{(total_achats/total_ventes*100):.0f}%" if total_ventes > 0 else None,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💎 Bénéfice Net",
            f"{benefice_net:.2f} €",
            delta="Positif ✅" if benefice_net > 0 else "Négatif ❌",
            delta_color="normal" if benefice_net > 0 else "inverse"
        )
    
    with col4:
        st.metric(
            "📊 Marge Nette",
            f"{marge:.1f}%",
            delta="Excellent" if marge > 30 else "Correct" if marge > 15 else "Faible"
        )
    
    st.divider()
    
    # Graphiques
    if not df.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### 📅 Évolution Mensuelle du CA")
            df_ventes = df[df['Montant'] > 0].copy()
            df_ventes['Mois'] = df_ventes['Date'].dt.to_period('M').astype(str)
            monthly_ca = df_ventes.groupby('Mois')['Montant'].sum().reset_index()
            
            fig_ca = px.area(
                monthly_ca, 
                x='Mois', 
                y='Montant',
                title="",
                labels={'Montant': 'CA (€)', 'Mois': ''}
            )
            fig_ca.update_traces(line_color='#10b981', fillcolor='rgba(16, 185, 129, 0.3)')
            fig_ca.update_layout(hovermode='x unified')
            st.plotly_chart(fig_ca, use_container_width=True)
        
        with col_g2:
            st.markdown("#### 🎯 Répartition par Type")
            type_counts = df.groupby('Type').agg({
                'Montant': 'sum'
            }).reset_index()
            type_counts['Montant_Abs'] = type_counts['Montant'].abs()
            
            fig_pie = px.pie(
                type_counts, 
                values='Montant_Abs', 
                names='Type',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    st.divider()
    
    # Dernières opérations
    st.markdown("#### 🕒 Dernières Opérations")
    if not df.empty:
        recent_ops = df.sort_values('Date', ascending=False).head(10)
        
        for idx, row in recent_ops.iterrows():
            with st.container():
                col_date, col_desc, col_amount, col_status = st.columns([2, 4, 2, 3])
                
                with col_date:
                    st.write(f"**{row['Date'].strftime('%d/%m/%Y')}**")
                
                with col_desc:
                    desc_display = str(row['Description']) if pd.notna(row['Description']) else 'Sans description'
                    st.write(f"{row['Type']} - {desc_display}")
                
                with col_amount:
                    if row['Montant'] > 0:
                        st.markdown(f"<span class='metric-positive'>+{row['Montant']:.2f} €</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='metric-negative'>{row['Montant']:.2f} €</span>", unsafe_allow_html=True)
                
                with col_status:
                    if row['Statut_Julie'] == 'Payé' and row['Statut_Matheo'] == 'Payé':
                        st.success("✅ Soldé")
                    else:
                        st.warning("⏳ En attente")
    else:
        st.info("Aucune opération enregistrée pour le moment")

# ========== TAB 2 : REMBOURSEMENTS ==========
with tab2:
    st.markdown("### 💳 Gestion des Remboursements")
    
    col_julie, col_matheo = st.columns(2)
    
    # SECTION JULIE
    with col_julie:
        st.markdown("#### 👩‍💻 Julie")
        
        # Métriques Julie
        met_col1, met_col2 = st.columns(2)
        with met_col1:
            st.metric("💰 Total Dû", f"{julie_total:.2f} €")
        with met_col2:
            st.metric("✅ Payé", f"{julie_paye:.2f} €")
        
        st.metric("⏳ En Attente", f"{julie_en_attente:.2f} €", delta=f"{julie_progress:.0f}% payé")
        st.progress(julie_progress / 100)
        
        st.divider()
        
        # Liste des paiements en attente
        julie_pending = df[df['Statut_Julie'] == 'En attente'].copy()
        
        if not julie_pending.empty:
            st.markdown(f"**{len(julie_pending)} transaction(s) en attente**")
            
            for idx, row in julie_pending.iterrows():
                desc = str(row['Description'])[:30] if pd.notna(row['Description']) else 'Sans description'
                
                with st.expander(f"💰 {row['Montant_Part']:.2f} € - {desc}"):
                    st.write(f"📅 Date: {row['Date'].strftime('%d/%m/%Y')}")
                    st.write(f"🏷️ Type: {row['Type']}")
                    st.write(f"💵 Montant total: {row['Montant']:.2f} €")
                    st.write(f"👤 Part Julie: {row['Montant_Part']:.2f} €")
                    
                    if pd.notna(row['Notes']) and row['Notes']:
                        st.info(f"📌 {row['Notes']}")
                    
                    if st.button("✅ Marquer comme Payé", key=f"julie_pay_{idx}", use_container_width=True):
                        st.session_state.data.at[idx, 'Statut_Julie'] = 'Payé'
                        st.session_state.data.at[idx, 'Date_Remb_Julie'] = datetime.now()
                        
                        if save_data(st.session_state.data):
                            st.success("✅ Paiement enregistré !")
                            st.rerun()
        else:
            st.success("🎉 Tous les paiements sont à jour !")
    
    # SECTION MATHÉO
    with col_matheo:
        st.markdown("#### 👨‍💻 Mathéo")
        
        # Métriques Mathéo
        met_col1, met_col2 = st.columns(2)
        with met_col1:
            st.metric("💰 Total Dû", f"{matheo_total:.2f} €")
        with met_col2:
            st.metric("✅ Payé", f"{matheo_paye:.2f} €")
        
        st.metric("⏳ En Attente", f"{matheo_en_attente:.2f} €", delta=f"{matheo_progress:.0f}% payé")
        st.progress(matheo_progress / 100)
        
        st.divider()
        
        # Liste des paiements en attente
        matheo_pending = df[df['Statut_Matheo'] == 'En attente'].copy()
        
        if not matheo_pending.empty:
            st.markdown(f"**{len(matheo_pending)} transaction(s) en attente**")
            
            for idx, row in matheo_pending.iterrows():
                desc = str(row['Description'])[:30] if pd.notna(row['Description']) else 'Sans description'
                
                with st.expander(f"💰 {row['Montant_Part']:.2f} € - {desc}"):
                    st.write(f"📅 Date: {row['Date'].strftime('%d/%m/%Y')}")
                    st.write(f"🏷️ Type: {row['Type']}")
                    st.write(f"💵 Montant total: {row['Montant']:.2f} €")
                    st.write(f"👤 Part Mathéo: {row['Montant_Part']:.2f} €")
                    
                    if pd.notna(row['Notes']) and row['Notes']:
                        st.info(f"📌 {row['Notes']}")
                    
                    if st.button("✅ Marquer comme Payé", key=f"matheo_pay_{idx}", use_container_width=True):
                        st.session_state.data.at[idx, 'Statut_Matheo'] = 'Payé'
                        st.session_state.data.at[idx, 'Date_Remb_Matheo'] = datetime.now()
                        
                        if save_data(st.session_state.data):
                            st.success("✅ Paiement enregistré !")
                            st.rerun()
        else:
            st.success("🎉 Tous les paiements sont à jour !")

# ========== TAB 3 : JULIE ==========
with tab3:
    st.markdown("### 👩‍💻 Tableau de Bord Julie")
    
    # Statistiques
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Encaissé", f"{julie_paye:.2f} €")
    col2.metric("⏳ En Attente", f"{julie_en_attente:.2f} €")
    col3.metric("📊 Total", f"{julie_total:.2f} €")
    col4.metric("📈 Taux", f"{julie_progress:.0f}%")
    
    st.divider()
    
    # Historique des paiements
    st.markdown("#### 📜 Historique des Paiements")
    julie_paid = df[df['Statut_Julie'] == 'Payé'].sort_values('Date_Remb_Julie', ascending=False)
    
    if not julie_paid.empty:
        display_cols = ['Date', 'Type', 'Description', 'Montant_Part', 'Date_Remb_Julie']
        st.dataframe(
            julie_paid[display_cols],
            column_config={
                "Date": st.column_config.DateColumn("Date Opération", format="DD/MM/YYYY"),
                "Montant_Part": st.column_config.NumberColumn("Montant", format="%.2f €"),
                "Date_Remb_Julie": st.column_config.DateColumn("Date Remboursement", format="DD/MM/YYYY"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Graphique des paiements mensuels
        if len(julie_paid) > 1:
            julie_paid_copy = julie_paid.copy()
            julie_paid_copy['Mois'] = julie_paid_copy['Date_Remb_Julie'].dt.to_period('M').astype(str)
            monthly_julie = julie_paid_copy.groupby('Mois')['Montant_Part'].sum().reset_index()
            
            fig_julie = px.bar(
                monthly_julie,
                x='Mois',
                y='Montant_Part',
                title="Remboursements Mensuels",
                labels={'Montant_Part': 'Montant (€)', 'Mois': ''}
            )
            fig_julie.update_traces(marker_color='#ec4899')
            st.plotly_chart(fig_julie, use_container_width=True)
    else:
        st.info("Aucun paiement enregistré")

# ========== TAB 4 : MATHÉO ==========
with tab4:
    st.markdown("### 👨‍💻 Tableau de Bord Mathéo")
    
    # Statistiques
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Encaissé", f"{matheo_paye:.2f} €")
    col2.metric("⏳ En Attente", f"{matheo_en_attente:.2f} €")
    col3.metric("📊 Total", f"{matheo_total:.2f} €")
    col4.metric("📈 Taux", f"{matheo_progress:.0f}%")
    
    st.divider()
    
    # Historique des paiements
    st.markdown("#### 📜 Historique des Paiements")
    matheo_paid = df[df['Statut_Matheo'] == 'Payé'].sort_values('Date_Remb_Matheo', ascending=False)
    
    if not matheo_paid.empty:
        display_cols = ['Date', 'Type', 'Description', 'Montant_Part', 'Date_Remb_Matheo']
        st.dataframe(
            matheo_paid[display_cols],
            column_config={
                "Date": st.column_config.DateColumn("Date Opération", format="DD/MM/YYYY"),
                "Montant_Part": st.column_config.NumberColumn("Montant", format="%.2f €"),
                "Date_Remb_Matheo": st.column_config.DateColumn("Date Remboursement", format="DD/MM/YYYY"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Graphique des paiements mensuels
        if len(matheo_paid) > 1:
            matheo_paid_copy = matheo_paid.copy()
            matheo_paid_copy['Mois'] = matheo_paid_copy['Date_Remb_Matheo'].dt.to_period('M').astype(str)
            monthly_matheo = matheo_paid_copy.groupby('Mois')['Montant_Part'].sum().reset_index()
            
            fig_matheo = px.bar(
                monthly_matheo,
                x='Mois',
                y='Montant_Part',
                title="Remboursements Mensuels",
                labels={'Montant_Part': 'Montant (€)', 'Mois': ''}
            )
            fig_matheo.update_traces(marker_color='#3b82f6')
            st.plotly_chart(fig_matheo, use_container_width=True)
    else:
        st.info("Aucun paiement enregistré")

# ========== TAB 5 : DONNÉES ==========
with tab5:
    st.markdown("### 📋 Gestion des Données")
    
    # Filtres
    with st.expander("🔍 Filtres", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            filter_type = st.multiselect(
                "Type d'opération",
                options=df['Type'].unique() if not df.empty else [],
                default=[]
            )
        
        with filter_col2:
            filter_year = st.multiselect(
                "Année",
                options=sorted(df['Année'].unique()) if not df.empty else [],
                default=[]
            )
        
        with filter_col3:
            filter_status = st.selectbox(
                "Statut",
                ["Tous", "En attente", "Payé (Julie)", "Payé (Mathéo)", "Soldé"]
            )
    
    # Application des filtres
    df_filtered = df.copy()
