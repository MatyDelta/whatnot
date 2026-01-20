import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    try:
        from st_gsheets_connection import GSheetsConnection
    except ImportError:
        st.error("❌ Erreur : Package Google Sheets non trouvé. Installez avec : pip install streamlit-gsheets")
        st.stop()
from PIL import Image
import pytesseract
import re
import hashlib

# --- CONFIGURATION ---
"""
Module d'authentification pour Whatnot Tracker Pro V2
À intégrer au début de whatnot_tracker_v2.py
"""

import streamlit as st
import hashlib
from datetime import datetime

# --- CONFIGURATION DE L'AUTHENTIFICATION ---

def hash_password(password):
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_users():
    """Récupère les utilisateurs depuis les secrets ou utilise les valeurs par défaut"""
    try:
        # Essayer de charger depuis secrets.toml
        return {
            "Julie": hash_password(st.secrets.get("passwords", {}).get("julie", "julie2025")),
            "Matheo": hash_password(st.secrets.get("passwords", {}).get("matheo", "matheo2025")),
            "Admin": hash_password(st.secrets.get("passwords", {}).get("admin", "admin2025"))
        }
    except:
        # Valeurs par défaut si secrets.toml n'est pas configuré
        return {
            "Julie": hash_password("julie2025"),
            "Matheo": hash_password("matheo2025"),
            "Admin": hash_password("admin2025")
        }

def check_password():
    """Vérifie le mot de passe et retourne True si correct"""
    
    USERS = get_users()
    
    # Si déjà connecté, vérifier la session
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return True
    
    # CSS pour la page de connexion
    st.markdown("""
    <style>
        .login-container {
            max-width: 450px;
            margin: 80px auto;
            padding: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 15px;
        }
        .login-title {
            text-align: center;
            color: #667eea;
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .login-subtitle {
            text-align: center;
            color: #6b7280;
            font-size: 16px;
            margin-bottom: 30px;
        }
        .stTextInput > div > div > input {
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Interface de connexion
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    
    st.markdown("<div class='login-title'>💎 MJTGC</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtitle'>Whatnot Tracker Pro</div>", unsafe_allow_html=True)
    
    # Formulaire de connexion
    with st.form("login_form"):
        username = st.text_input("👤 Nom d'utilisateur", placeholder="Julie, Matheo ou Admin")
        password = st.text_input("🔑 Mot de passe", type="password", placeholder="Entrez votre mot de passe")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("🚀 Se Connecter", use_container_width=True, type="primary")
        with col2:
            reset = st.form_submit_button("🔄 Réinitialiser", use_container_width=True)
        
        if reset:
            st.session_state.clear()
            st.rerun()
        
        if submit:
            if username in USERS and hash_password(password) == USERS[username]:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.login_time = datetime.now()
                st.success(f"✅ Bienvenue {username} !")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Nom d'utilisateur ou mot de passe incorrect")
    
    # Aide pour les utilisateurs
    with st.expander("❓ Aide à la connexion"):
        st.info("""
        **Comptes disponibles par défaut:**
        - Julie / julie2025
        - Matheo / matheo2025
        - Admin / admin2025
        
        **Pour changer les mots de passe:**
        
        Créez un fichier `.streamlit/secrets.toml` :
        ```toml
        [passwords]
        julie = "votre_nouveau_mdp"
        matheo = "votre_nouveau_mdp"
        admin = "votre_nouveau_mdp"
        ```
        
        ⚠️ **Sécurité:** Changez impérativement ces mots de passe par défaut !
        """)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style='text-align: center; color: #6b7280; margin-top: 30px; padding: 20px;'>
        <p style='font-size: 12px;'>🔐 Connexion sécurisée - Vos données restent privées</p>
    </div>
    """, unsafe_allow_html=True)
    
    return False

def show_user_info():
    """Affiche les informations de l'utilisateur connecté dans la sidebar"""
    with st.sidebar:
        st.markdown("---")
        
        # Badge utilisateur
        user_emoji = {"Julie": "👩", "Matheo": "👨", "Admin": "👑"}.get(st.session_state.username, "👤")
        st.markdown(f"### {user_emoji} **{st.session_state.username}**")
        
        # Temps de connexion
        if "login_time" in st.session_state:
            duration = datetime.now() - st.session_state.login_time
            hours = int(duration.total_seconds() / 3600)
            minutes = int((duration.total_seconds() % 3600) / 60)
            
            if hours > 0:
                time_str = f"{hours}h {minutes}min"
            else:
                time_str = f"{minutes} min"
            
            st.caption(f"⏱️ Connecté depuis {time_str}")
        
        # Bouton de déconnexion
        if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
            # Sauvegarder avant de se déconnecter
            if 'data' in st.session_state and not st.session_state.data.empty:
                try:
                    # Importer la fonction save_data si elle existe
                    from __main__ import save_data
                    save_data(st.session_state.data)
                except:
                    pass
            
            st.session_state.clear()
            st.success("✅ Déconnexion réussie")
            st.rerun()
        
        st.markdown("---")

def get_username_badge():
    """Retourne un badge HTML avec le nom de l'utilisateur"""
    user_colors = {
        "Julie": "#ec4899",
        "Matheo": "#3b82f6",
        "Admin": "#10b981"
    }
    color = user_colors.get(st.session_state.username, "#6b7280")
    
    return f"""
    <div style='
        background: {color};
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        display: inline-block;
        font-weight: 600;
        font-size: 14px;
    '>
        👤 {st.session_state.username}
    </div>
    """

# --- EXEMPLE D'UTILISATION ---
"""
Pour intégrer l'authentification dans whatnot_tracker_v2.py :

1. Ajoutez cet import au début du fichier :
   import hashlib

2. Après st.set_page_config(...), ajoutez :
   
   # Vérifier l'authentification
   if not check_password():
       st.stop()

3. Après le titre de l'app, ajoutez :
   
   show_user_info()

4. Optionnel - Afficher le badge utilisateur dans le header :
   
   st.markdown(get_username_badge(), unsafe_allow_html=True)

5. Dans le formulaire de nouvelle opération, ajoutez le champ Saisi_Par :
   
   "Saisi_Par": st.session_state.username

6. Ajoutez la colonne 'Saisi_Par' dans la structure de données :
   
   Dans load_data(), ajoutez :
   if 'Saisi_Par' not in data.columns:
       data['Saisi_Par'] = ''
"""
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
    .live-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- TITRE ---
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title("💎 MJTGC - Whatnot Tracker Pro V2")
    # Afficher les informations de l'utilisateur connecté
show_user_info()
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
                'Date', 'Type', 'Description', 'Montant_Gain', 'Montant_Depense',
                'Live_ID', 'Montant_Rembourse_Julie', 'Statut_Remb_Julie',
                'Date_Remb_Complete_Julie', 'Année', 'Notes'
            ])
        
        # Nettoyage des lignes vides
        data = data.dropna(how='all')
        
        # Conversion des types
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        # MIGRATION AUTOMATIQUE V1 → V2
        # Si les anciennes colonnes existent (Montant), convertir vers la nouvelle structure
        if 'Montant' in data.columns and 'Montant_Gain' not in data.columns:
            st.info("🔄 Migration automatique des données V1 → V2 en cours...")
            
            # Convertir Montant en Montant_Gain et Montant_Depense
            data['Montant'] = pd.to_numeric(data['Montant'], errors='coerce').fillna(0)
            data['Montant_Gain'] = data['Montant'].apply(lambda x: x if x > 0 else 0)
            data['Montant_Depense'] = data['Montant'].apply(lambda x: abs(x) if x < 0 else 0)
            
            # Renommer les anciennes colonnes de statut
            if 'Statut_Julie' in data.columns:
                data['Statut_Remb_Julie'] = data['Statut_Julie']
            if 'Date_Remb_Julie' in data.columns:
                data['Date_Remb_Complete_Julie'] = data['Date_Remb_Julie']
            
            # Calculer les montants remboursés pour Julie
            def calc_remb_julie(row):
                if row['Montant_Gain'] > 0:
                    if 'Statut_Remb_Julie' in row and row['Statut_Remb_Julie'] == 'Payé':
                        return row['Montant_Gain'] / 2
                return 0
            
            data['Montant_Rembourse_Julie'] = data.apply(calc_remb_julie, axis=1)
            
            st.success("✅ Migration terminée ! Vos données ont été converties.")
        else:
            # Structure V2 déjà présente
            data['Montant_Gain'] = pd.to_numeric(data['Montant_Gain'], errors='coerce').fillna(0)
            data['Montant_Depense'] = pd.to_numeric(data['Montant_Depense'], errors='coerce').fillna(0)
            data['Montant_Rembourse_Julie'] = pd.to_numeric(data['Montant_Rembourse_Julie'], errors='coerce').fillna(0)
        
        # Ajout des colonnes manquantes
        if 'Live_ID' not in data.columns:
            data['Live_ID'] = None
        if 'Statut_Remb_Julie' not in data.columns:
            data['Statut_Remb_Julie'] = data.apply(
                lambda row: 'En attente' if row['Montant_Gain'] > 0 else 'N/A', axis=1
            )
        if 'Date_Remb_Complete_Julie' not in data.columns:
            data['Date_Remb_Complete_Julie'] = None
        if 'Année' not in data.columns:
            data['Année'] = data['Date'].dt.year.astype(str)
        if 'Notes' not in data.columns:
            data['Notes'] = ''
        
        # Conversion des dates de remboursement
        data['Date_Remb_Complete_Julie'] = pd.to_datetime(data['Date_Remb_Complete_Julie'], errors='coerce')
        
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
        df_save['Date_Remb_Complete_Julie'] = pd.to_datetime(df_save['Date_Remb_Complete_Julie'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        conn.update(data=df_save)
        return True
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde : {e}")
        return False

# --- INITIALISATION SESSION STATE ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()

if 'delete_mode' not in st.session_state:
    st.session_state.delete_mode = False

if 'rows_to_delete' not in st.session_state:
    st.session_state.rows_to_delete = []

if 'migration_done' not in st.session_state:
    st.session_state.migration_done = False

df = st.session_state.data

# Si migration détectée et pas encore sauvegardée
if not df.empty and not st.session_state.migration_done:
    # Vérifier si c'était une migration (présence de Montant_Gain mais pas de Live_ID rempli)
    if 'Montant_Gain' in df.columns and df['Live_ID'].isna().all():
        with st.sidebar:
            st.warning("⚠️ Migration V1→V2 détectée")
            if st.button("💾 Sauvegarder les données migrées", use_container_width=True):
                if save_data(df):
                    st.success("✅ Données migrées sauvegardées !")
                    st.session_state.migration_done = True
                    st.balloons()
                    st.rerun()

# --- CALCULS FINANCIERS ---
def calculer_metriques(df):
    """Calcule toutes les métriques financières"""
    if df.empty:
        return {
            'ca_brut': 0, 'total_depenses_live': 0, 'benefice_net': 0,
            'part_julie': 0, 'part_matheo': 0, 'impots': 0,
            'julie_a_recevoir': 0, 'julie_recue': 0, 'julie_restant': 0,
            'matheo_disponible': 0
        }
    
    # Chiffre d'affaires brut (uniquement les gains)
    ca_brut = df['Montant_Gain'].sum()
    
    # Total des dépenses de live
    total_depenses_live = df['Montant_Depense'].sum()
    
    # Bénéfice net = CA brut - dépenses
    benefice_net = ca_brut - total_depenses_live
    
    # Parts individuelles (50/50 sur les GAINS uniquement)
    part_julie = ca_brut / 2
    part_matheo = ca_brut / 2
    
    # Calcul des impôts (23% sur le CA brut)
    impots = ca_brut * 0.23
    
    # Remboursements Julie
    julie_recue = df['Montant_Rembourse_Julie'].sum()
    julie_restant = part_julie - julie_recue
    
    # Mathéo : récupère sa part uniquement après avoir remboursé Julie
    matheo_disponible = julie_recue  # Il récupère au fur et à mesure qu'il rembourse Julie
    
    return {
        'ca_brut': ca_brut,
        'total_depenses_live': total_depenses_live,
        'benefice_net': benefice_net,
        'part_julie': part_julie,
        'part_matheo': part_matheo,
        'impots': impots,
        'julie_a_recevoir': part_julie,
        'julie_recue': julie_recue,
        'julie_restant': julie_restant,
        'matheo_disponible': matheo_disponible
    }

# --- CALCUL DES MÉTRIQUES PAR LIVE ---
def calculer_metriques_live(df, live_id):
    """Calcule les métriques d'un live spécifique"""
    live_data = df[df['Live_ID'] == live_id]
    
    if live_data.empty:
        return None
    
    gain_brut = live_data['Montant_Gain'].sum()
    depense_stock = live_data['Montant_Depense'].sum()
    benefice = gain_brut - depense_stock
    
    return {
        'gain_brut': gain_brut,
        'depense_stock': depense_stock,
        'benefice': benefice,
        'date': live_data['Date'].max()
    }

# Calcul des métriques globales
metriques = calculer_metriques(df)

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
            ["💰 Gain Live", "🛒 Dépense Stock Live", "💸 Frais Divers"]
        )
        
        # Si c'est un gain ou dépense de live, demander le Live ID
        live_id_input = None
        if "Live" in type_input:
            live_id_input = st.text_input(
                "🎬 ID du Live",
                placeholder="Ex: LIVE_20250119",
                help="Identifiant unique du live (sera généré automatiquement si vide)"
            )
        
        desc_input = st.text_input(
            "📝 Description",
            value=st.session_state.get('scan_name', ""),
            placeholder="Ex: Live Pokémon, Achat cartes chez Carrefour..."
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
                # Génération automatique du Live ID si nécessaire
                if "Live" in type_input and not live_id_input:
                    live_id_input = f"LIVE_{date_input.strftime('%Y%m%d_%H%M%S')}"
                
                # Détermination du type de montant
                montant_gain = montant_input if "Gain" in type_input else 0
                montant_depense = montant_input if "Dépense" in type_input or "Frais" in type_input else 0
                
                # Création de la nouvelle ligne
                new_entry = pd.DataFrame([{
                    "Date": pd.to_datetime(date_input),
                    "Type": type_input,
                    "Description": desc_input,
                    "Montant_Gain": montant_gain,
                    "Montant_Depense": montant_depense,
                    "Live_ID": live_id_input,
                    "Montant_Rembourse_Julie": 0,
                    "Statut_Remb_Julie": "En attente" if montant_gain > 0 else "N/A",
                    "Date_Remb_Complete_Julie": None,
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

# --- ONGLETS PRINCIPAUX ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard", 
    "🎬 Historique Lives",
    "💰 Remboursements Julie", 
    "👨‍💻 Mathéo", 
    "🎯 Objectifs",
    "📋 Données"
])

# ========== TAB 1 : DASHBOARD ==========
with tab1:
    st.markdown("### 📈 Performance Globale")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💵 CA Brut (sans dépenses)",
            f"{metriques['ca_brut']:.2f} €",
            help="Chiffre d'affaires total sans déduire les dépenses"
        )
    
    with col2:
        st.metric(
            "🛒 Dépenses Lives",
            f"{metriques['total_depenses_live']:.2f} €",
            delta=f"-{(metriques['total_depenses_live']/metriques['ca_brut']*100):.0f}%" if metriques['ca_brut'] > 0 else None,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💎 Bénéfice Net",
            f"{metriques['benefice_net']:.2f} €",
            delta="Positif ✅" if metriques['benefice_net'] > 0 else "Négatif ❌",
            delta_color="normal" if metriques['benefice_net'] > 0 else "inverse"
        )
    
    with col4:
        marge = (metriques['benefice_net'] / metriques['ca_brut'] * 100) if metriques['ca_brut'] > 0 else 0
        st.metric(
            "📊 Marge Nette",
            f"{marge:.1f}%",
            delta="Excellent" if marge > 30 else "Correct" if marge > 15 else "Faible"
        )
    
    st.divider()
    
    # Calcul des impôts et répartition
    st.markdown("### 💰 Répartition Financière")
    col_imp, col_julie, col_matheo = st.columns(3)
    
    with col_imp:
        st.metric(
            "🏦 Impôts (23% du CA brut)",
            f"{metriques['impots']:.2f} €",
            help="23% du chiffre d'affaires brut"
        )
    
    with col_julie:
        progression_julie = (metriques['julie_recue'] / metriques['part_julie'] * 100) if metriques['part_julie'] > 0 else 0
        st.metric(
            "👩 Part Julie (50% des gains)",
            f"{metriques['part_julie']:.2f} €",
            delta=f"{progression_julie:.0f}% remboursé"
        )
    
    with col_matheo:
        st.metric(
            "👨 Part Mathéo (50% des gains)",
            f"{metriques['part_matheo']:.2f} €",
            delta=f"{metriques['matheo_disponible']:.2f} € disponible",
            help="Vous récupérez votre part au fur et à mesure que vous remboursez Julie"
        )
    
    st.divider()
    
    # Graphiques
    if not df.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### 📅 Évolution Mensuelle du CA Brut")
            df_gains = df[df['Montant_Gain'] > 0].copy()
            df_gains['Mois'] = df_gains['Date'].dt.to_period('M').astype(str)
            monthly_ca = df_gains.groupby('Mois')['Montant_Gain'].sum().reset_index()
            
            fig_ca = px.area(
                monthly_ca, 
                x='Mois', 
                y='Montant_Gain',
                title="",
                labels={'Montant_Gain': 'CA (€)', 'Mois': ''}
            )
            fig_ca.update_traces(line_color='#10b981', fillcolor='rgba(16, 185, 129, 0.3)')
            fig_ca.update_layout(hovermode='x unified')
            st.plotly_chart(fig_ca, use_container_width=True)
        
        with col_g2:
            st.markdown("#### 💰 Gains vs Dépenses")
            totaux = pd.DataFrame({
                'Catégorie': ['Gains', 'Dépenses', 'Bénéfice Net'],
                'Montant': [
                    metriques['ca_brut'],
                    metriques['total_depenses_live'],
                    metriques['benefice_net']
                ]
            })
            
            fig_bar = px.bar(
                totaux,
                x='Catégorie',
                y='Montant',
                color='Catégorie',
                color_discrete_map={
                    'Gains': '#10b981',
                    'Dépenses': '#ef4444',
                    'Bénéfice Net': '#3b82f6'
                }
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    
    # Dernières opérations
    st.markdown("#### 🕒 Dernières Opérations")
    if not df.empty:
        recent_ops = df.sort_values('Date', ascending=False).head(10)
        
        for idx, row in recent_ops.iterrows():
            with st.container():
                col_date, col_desc, col_gain, col_depense = st.columns([2, 4, 2, 2])
                
                with col_date:
                    st.write(f"**{row['Date'].strftime('%d/%m/%Y')}**")
                
                with col_desc:
                    desc_display = str(row['Description']) if pd.notna(row['Description']) else 'Sans description'
                    st.write(f"{row['Type']} - {desc_display}")
                    if pd.notna(row['Live_ID']):
                        st.caption(f"🎬 {row['Live_ID']}")
                
                with col_gain:
                    if row['Montant_Gain'] > 0:
                        st.markdown(f"<span class='metric-positive'>+{row['Montant_Gain']:.2f} €</span>", unsafe_allow_html=True)
                
                with col_depense:
                    if row['Montant_Depense'] > 0:
                        st.markdown(f"<span class='metric-negative'>-{row['Montant_Depense']:.2f} €</span>", unsafe_allow_html=True)
    else:
        st.info("Aucune opération enregistrée pour le moment")

# ========== TAB 2 : HISTORIQUE LIVES ==========
with tab2:
    st.markdown("### 🎬 Historique des Lives")
    
    if not df.empty:
        # Récupération de tous les lives uniques
        lives_ids = df[df['Live_ID'].notna()]['Live_ID'].unique()
        
        if len(lives_ids) > 0:
            st.info(f"📊 {len(lives_ids)} live(s) enregistré(s)")
            
            # Affichage de chaque live
            for live_id in sorted(lives_ids, reverse=True):
                metriques_live = calculer_metriques_live(df, live_id)
                
                if metriques_live:
                    with st.expander(f"🎬 {live_id} - {metriques_live['date'].strftime('%d/%m/%Y')}", expanded=False):
                        col_l1, col_l2, col_l3 = st.columns(3)
                        
                        with col_l1:
                            st.metric("💰 Gain Brut", f"{metriques_live['gain_brut']:.2f} €")
                        
                        with col_l2:
                            st.metric("🛒 Dépense Stock", f"{metriques_live['depense_stock']:.2f} €")
                        
                        with col_l3:
                            delta_color = "normal" if metriques_live['benefice'] > 0 else "inverse"
                            st.metric(
                                "💎 Bénéfice", 
                                f"{metriques_live['benefice']:.2f} €",
                                delta="Positif" if metriques_live['benefice'] > 0 else "Négatif",
                                delta_color=delta_color
                            )
                        
                        # Détail des opérations du live
                        st.markdown("**📋 Détails des opérations :**")
                        live_operations = df[df['Live_ID'] == live_id].sort_values('Date')
                        
                        for _, op in live_operations.iterrows():
                            if op['Montant_Gain'] > 0:
                                st.success(f"✅ +{op['Montant_Gain']:.2f} € - {op['Description']}")
                            elif op['Montant_Depense'] > 0:
                                st.error(f"❌ -{op['Montant_Depense']:.2f} € - {op['Description']}")
        else:
            st.info("Aucun live enregistré pour le moment")
    else:
        st.info("Aucune donnée disponible")

# ========== TAB 3 : REMBOURSEMENTS JULIE ==========
with tab3:
    st.markdown("### 💰 Gestion des Remboursements - Julie")
    
    # Métriques Julie
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Total à Recevoir", f"{metriques['julie_a_recevoir']:.2f} €")
    
    with col2:
        st.metric("✅ Déjà Reçu", f"{metriques['julie_recue']:.2f} €")
    
    with col3:
        st.metric("⏳ Reste à Recevoir", f"{metriques['julie_restant']:.2f} €")
    
    # Barre de progression
    progression = (metriques['julie_recue'] / metriques['julie_a_recevoir'] * 100) if metriques['julie_a_recevoir'] > 0 else 0
    st.progress(progression / 100)
    st.caption(f"**{progression:.1f}%** remboursé")
    
    st.divider()
    
    # Liste des gains à rembourser
    gains_a_rembourser = df[(df['Montant_Gain'] > 0) & (df['Statut_Remb_Julie'] != 'Payé')].copy()
    
    if not gains_a_rembourser.empty:
        st.markdown(f"### 💸 Gains à Rembourser ({len(gains_a_rembourser)})")
        
        for idx, row in gains_a_rembourser.iterrows():
            part_julie = row['Montant_Gain'] / 2
            deja_rembourse = row['Montant_Rembourse_Julie']
            reste_a_rembourser = part_julie - deja_rembourse
            progression_gain = (deja_rembourse / part_julie * 100) if part_julie > 0 else 0
            
            with st.expander(
                f"💰 {part_julie:.2f} € - {row['Description']} (Reste: {reste_a_rembourser:.2f} €)",
                expanded=False
            ):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write(f"📅 **Date:** {row['Date'].strftime('%d/%m/%Y')}")
                    st.write(f"🏷️ **Type:** {row['Type']}")
                    st.write(f"💵 **Gain total:** {row['Montant_Gain']:.2f} €")
                    if pd.notna(row['Live_ID']):
                        st.write(f"🎬 **Live:** {row['Live_ID']}")
                
                with col_info2:
                    st.write(f"👤 **Part Julie (50%):** {part_julie:.2f} €")
                    st.write(f"✅ **Déjà remboursé:** {deja_rembourse:.2f} €")
                    st.write(f"⏳ **Reste:** {reste_a_rembourser:.2f} €")
                    st.progress(progression_gain / 100)
                
                if pd.notna(row['Notes']) and row['Notes']:
                    st.info(f"📌 {row['Notes']}")
                
                # Formulaire de remboursement partiel
                st.markdown("#### 💳 Rembourser")
                
                col_form1, col_form2 = st.columns([3, 1])
                
                with col_form1:
                    montant_remb = st.number_input(
                        "Montant à rembourser (€)",
                        min_value=0.01,
                        max_value=float(reste_a_rembourser),
                        value=float(reste_a_rembourser),
                        step=0.01,
                        key=f"remb_{idx}"
                    )
                
                with col_form2:
                    if st.button("💸 Rembourser", key=f"btn_remb_{idx}", use_container_width=True):
                        # Mise à jour du montant remboursé
                        nouveau_total_remb = deja_rembourse + montant_remb
                        st.session_state.data.at[idx, 'Montant_Rembourse_Julie'] = nouveau_total_remb
                        
                        # Si le remboursement est complet
                        if nouveau_total_remb >= part_julie:
                            st.session_state.data.at[idx, 'Statut_Remb_Julie'] = 'Payé'
                            st.session_state.data.at[idx, 'Date_Remb_Complete_Julie'] = datetime.now()
                        
                        if save_data(st.session_state.data):
                            st.success(f"✅ {montant_remb:.2f} € remboursé à Julie !")
                            st.rerun()
    else:
        st.success("🎉 Tous les gains ont été remboursés à Julie !")
    
    st.divider()
    
    # Historique des remboursements complets
    st.markdown("### 📜 Historique des Gains Remboursés")
    gains_rembourses = df[(df['Montant_Gain'] > 0) & (df['Statut_Remb_Julie'] == 'Payé')].sort_values('Date_Remb_Complete_Julie', ascending=False)
    
    if not gains_rembourses.empty:
        for _, row in gains_rembourses.iterrows():
            part_julie = row['Montant_Gain'] / 2
            col_h1, col_h2, col_h3, col_h4 = st.columns([2, 3, 2, 2])
            
            with col_h1:
                st.write(f"**{row['Date'].strftime('%d/%m/%Y')}**")
            
            with col_h2:
                st.write(f"{row['Description']}")
            
            with col_h3:
                st.write(f"💰 {part_julie:.2f} €")
            
            with col_h4:
                if pd.notna(row['Date_Remb_Complete_Julie']):
                    st.success(f"✅ {row['Date_Remb_Complete_Julie'].strftime('%d/%m/%Y')}")
    else:
        st.info("Aucun remboursement complet pour le moment")

# ========== TAB 4 : MATHÉO ==========
with tab4:
    st.markdown("### 👨‍💻 Tableau de Bord Mathéo")
    
    # Métriques Mathéo
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💎 Part Totale (50%)", f"{metriques['part_matheo']:.2f} €")
    
    with col2:
        st.metric(
            "💰 Disponible", 
            f"{metriques['matheo_disponible']:.2f} €",
            help="Montant que vous pouvez récupérer (= ce que vous avez déjà remboursé à Julie)"
        )
    
    with col3:
        reste_a_rembourser_julie = metriques['julie_restant']
        st.metric(
            "🔒 Bloqué", 
            f"{reste_a_rembourser_julie:.2f} €",
            help="Montant bloqué tant que Julie n'est pas remboursée"
        )
    
    # Explication du système
    st.info("""
    💡 **Comment ça marche ?**
    
    Vous récupérez votre part (50%) **au fur et à mesure** que vous remboursez Julie.
    
    - Chaque euro remboursé à Julie = un euro disponible pour vous
    - Une fois Julie 100% remboursée, vous récupérez l'intégralité de votre part
    """)
    
    st.divider()
    
    # Graphique de l'évolution de l'argent disponible
    if not df.empty:
        st.markdown("### 📈 Évolution de Votre Argent Disponible")
        
        gains_payes = df[(df['Montant_Gain'] > 0) & (df['Statut_Remb_Julie'] == 'Payé')].copy()
        
        if not gains_payes.empty:
            gains_payes = gains_payes.sort_values('Date_Remb_Complete_Julie')
            gains_payes['Part_Matheo_Cumulative'] = (gains_payes['Montant_Gain'] / 2).cumsum()
            
            fig_matheo = px.line(
                gains_payes,
                x='Date_Remb_Complete_Julie',
                y='Part_Matheo_Cumulative',
                title="",
                labels={
                    'Date_Remb_Complete_Julie': 'Date',
                    'Part_Matheo_Cumulative': 'Argent Disponible (€)'
                }
            )
            fig_matheo.update_traces(line_color='#3b82f6', line_width=3)
            fig_matheo.update_layout(hovermode='x unified')
            st.plotly_chart(fig_matheo, use_container_width=True)
        else:
            st.info("Pas encore de remboursements complets")
    
    st.divider()
    
    # Détail des gains disponibles
    st.markdown("### 💰 Détail de Votre Argent Disponible")
    
    gains_disponibles = df[(df['Montant_Gain'] > 0) & (df['Statut_Remb_Julie'] == 'Payé')].sort_values('Date_Remb_Complete_Julie', ascending=False)
    
    if not gains_disponibles.empty:
        for _, row in gains_disponibles.iterrows():
            part_matheo = row['Montant_Gain'] / 2
            
            col_d1, col_d2, col_d3, col_d4 = st.columns([2, 3, 2, 2])
            
            with col_d1:
                st.write(f"**{row['Date'].strftime('%d/%m/%Y')}**")
            
            with col_d2:
                st.write(f"{row['Description']}")
                if pd.notna(row['Live_ID']):
                    st.caption(f"🎬 {row['Live_ID']}")
            
            with col_d3:
                st.markdown(f"<span class='metric-positive'>+{part_matheo:.2f} €</span>", unsafe_allow_html=True)
            
            with col_d4:
                st.success("✅ Disponible")
    else:
        st.info("Remboursez Julie pour débloquer votre argent !")

# ========== TAB 5 : OBJECTIFS ==========
with tab5:
    st.markdown("### 🎯 Objectifs de Chiffre d'Affaires")
    
    # Définition des paliers
    paliers = [
        {"nom": "🥉 Bronze", "montant": 1000, "color": "#cd7f32"},
        {"nom": "🥈 Argent", "montant": 2500, "color": "#c0c0c0"},
        {"nom": "🥇 Or", "montant": 5000, "color": "#ffd700"},
        {"nom": "💎 Platine", "montant": 10000, "color": "#e5e4e2"},
        {"nom": "👑 Diamant", "montant": 25000, "color": "#b9f2ff"},
        {"nom": "🔥 Légende", "montant": 50000, "color": "#ff6b6b"}
    ]
    
    ca_actuel = metriques['ca_brut']
    
    # Trouvercle palier actuel et le suivant
    palier_actuel = None
    palier_suivant = None
    
    for i, palier in enumerate(paliers):
        if ca_actuel >= palier['montant']:
            palier_actuel = palier
        elif palier_suivant is None and ca_actuel < palier['montant']:
            palier_suivant = palier
            break
    
    # Affichage du statut
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        if palier_actuel:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, {palier_actuel['color']}, {palier_actuel['color']}88); 
                        padding: 30px; border-radius: 15px; text-align: center; color: white;'>
                <h2 style='margin: 0;'>{palier_actuel['nom']}</h2>
                <p style='font-size: 24px; margin: 10px 0;'>Palier Actuel</p>
                <p style='font-size: 32px; font-weight: bold; margin: 0;'>{ca_actuel:.2f} €</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #6b7280, #4b5563); 
                        padding: 30px; border-radius: 15px; text-align: center; color: white;'>
                <h2 style='margin: 0;'>🚀 Débutant</h2>
                <p style='font-size: 24px; margin: 10px 0;'>En route vers le premier palier !</p>
                <p style='font-size: 32px; font-weight: bold; margin: 0;'>{ca_actuel:.2f} €</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col_stat2:
        if palier_suivant:
            reste = palier_suivant['montant'] - ca_actuel
            progression = (ca_actuel / palier_suivant['montant'] * 100)
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, {palier_suivant['color']}, {palier_suivant['color']}88); 
                        padding: 30px; border-radius: 15px; text-align: center; color: white;'>
                <h2 style='margin: 0;'>{palier_suivant['nom']}</h2>
                <p style='font-size: 24px; margin: 10px 0;'>Prochain Objectif</p>
                <p style='font-size: 32px; font-weight: bold; margin: 0;'>{palier_suivant['montant']:.2f} €</p>
                <p style='font-size: 18px; margin-top: 10px;'>Plus que {reste:.2f} € !</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(progression / 100)
            st.caption(f"**{progression:.1f}%** vers {palier_suivant['nom']}")
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #10b981, #059669); 
                        padding: 30px; border-radius: 15px; text-align: center; color: white;'>
                <h2 style='margin: 0;'>🏆 MAXIMUM ATTEINT</h2>
                <p style='font-size: 24px; margin: 10px 0;'>Félicitations !</p>
                <p style='font-size: 18px; margin: 0;'>Vous avez atteint le niveau maximum !</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Tous les paliers
    st.markdown("### 📊 Tous les Paliers")
    
    for palier in paliers:
        col_p1, col_p2, col_p3 = st.columns([1, 3, 1])
        
        with col_p1:
            if ca_actuel >= palier['montant']:
                st.success("✅")
            else:
                st.info("⏳")
        
        with col_p2:
            progression_palier = min((ca_actuel / palier['montant'] * 100), 100)
            st.markdown(f"**{palier['nom']}** - {palier['montant']:.0f} €")
            st.progress(progression_palier / 100)
        
        with col_p3:
            if ca_actuel >= palier['montant']:
                st.write("🎉 Atteint")
            else:
                reste_palier = palier['montant'] - ca_actuel
                st.write(f"{reste_palier:.0f} €")

# ========== TAB 6 : DONNÉES ==========
with tab6:
    st.markdown("### 📋 Gestion des Données")
    
    # Mode suppression
    col_del1, col_del2 = st.columns([3, 1])
    
    with col_del1:
        if st.session_state.delete_mode:
            st.warning("⚠️ Mode suppression activé - Sélectionnez les lignes à supprimer")
    
    with col_del2:
        if st.button(
            "🗑️ Mode Suppression" if not st.session_state.delete_mode else "❌ Annuler",
            use_container_width=True
        ):
            st.session_state.delete_mode = not st.session_state.delete_mode
            st.session_state.rows_to_delete = []
            st.rerun()
    
    # Affichage du DataFrame
    if not df.empty:
        if st.session_state.delete_mode:
            # Sélection des lignes à supprimer
            selected_rows = st.multiselect(
                "Sélectionnez les opérations à supprimer",
                options=df.index.tolist(),
                format_func=lambda x: f"{df.loc[x, 'Date'].strftime('%d/%m/%Y')} - {df.loc[x, 'Description']} - {df.loc[x, 'Montant_Gain'] if df.loc[x, 'Montant_Gain'] > 0 else -df.loc[x, 'Montant_Depense']:.2f} €"
            )
            
            if selected_rows:
                if st.button("🗑️ Supprimer les lignes sélectionnées", type="primary"):
                    st.session_state.data = st.session_state.data.drop(selected_rows).reset_index(drop=True)
                    
                    if save_data(st.session_state.data):
                        st.success(f"✅ {len(selected_rows)} ligne(s) supprimée(s)")
                        st.session_state.delete_mode = False
                        st.rerun()
        
        # Affichage complet
        st.dataframe(
            df,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Montant_Gain": st.column_config.NumberColumn("Gain", format="%.2f €"),
                "Montant_Depense": st.column_config.NumberColumn("Dépense", format="%.2f €"),
                "Montant_Rembourse_Julie": st.column_config.NumberColumn("Remb. Julie", format="%.2f €"),
                "Date_Remb_Complete_Julie": st.column_config.DateColumn("Date Remb.", format="DD/MM/YYYY"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Télécharger les données (CSV)",
            csv,
            "whatnot_data.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("Aucune donnée à afficher")

# --- FOOTER ---
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 20px;'>
    <p>💎 MJTGC Whatnot Tracker Pro V2 - Gestion Professionnelle de Vos Lives</p>
    <p style='font-size: 12px;'>Dernière mise à jour : {}</p>
</div>
""".format(datetime.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)
