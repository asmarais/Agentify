import streamlit as st
import requests
import re
import uuid
import math
import logging
import urllib.parse
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go




# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page to wide mode for full-width layout
st.set_page_config(layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Card-like containers */
    div[data-testid="stExpander"] {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric containers */
    div[data-testid="stMetric"] {
        background-color: #2C2C2C;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #FF4B4B !important;
        font-weight: 600;
    }
    
    /* Buttons */
    div.stButton > button {
        background-color: #FF4B4B;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background-color: #E63E3E;
        box-shadow: 0 2px 4px rgba(255, 75, 75, 0.2);
    }
    
    /* Chat messages */
    div.stChatMessage {
        background-color: #2C2C2C;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
    
    /* Sidebar */
    div[data-testid="stSidebar"] {
        background-color: #1E1E1E;
        padding: 2rem 1rem;
    }
    
    /* Tables */
    div[data-testid="stTable"] {
        background-color: #2C2C2C;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Scrollable container for products */
    .scrollable-products {
        max-height: 200px;
        overflow-y: auto;
        padding: 15px;
        border: 1px solid #444;
        border-radius: 8px;
        background-color: #2C2C2C;
        margin: 10px 0;
    }
    
    .product-item {
        background-color: #3C3C3C;
        border-radius: 6px;
        padding: 10px;
        margin: 8px 0;
        border-left: 3px solid #FF4B4B;
    }
    
    .product-name {
        font-weight: 600;
        color: #FF4B4B;
        margin-bottom: 5px;
    }
    
    .product-score {
        color: #A0A0A0;
        font-size: 0.9em;
    }
    
    /* Pitch display container */
    .pitch-container {
        background-color: #2C2C2C;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #FF4B4B;
        margin: 15px 0;
        line-height: 1.6;
    }
    
    .pitch-title {
        color: #FF4B4B;
        font-weight: 600;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# API endpoints
API_URL = "http://localhost:8000/api/workflow/run_workflow"
REFINE_API_URL = "http://localhost:8000/api/workflow/run_refinement"
SMS_API_URL = "http://localhost:8000/api/notify/send-sms"
WHATSAPP_API_URL = "http://localhost:8000/api/notify/send-whatsapp"
EMAIL_API_URL = "http://localhost:8000/api/notify/send-email"

# Dashboard API endpoints
DASHBOARD_API_URL = "http://localhost:8000/api/dashboard"
INTERACTIONS_API_URL = "http://localhost:8000/api/dashboard/interactions"
STATS_API_URL = f"{DASHBOARD_API_URL}/stats"
# Profile endpoints
CLIENT_API_URL = "http://localhost:8000/api/client"
PROFILE_API_URL = CLIENT_API_URL+"/profile"
# Data endpoints
DATA_CONTRATS_SINISTRES =CLIENT_API_URL+ "/dataFrames"
# Pagination constants - removed MAX_PAGES limit to use backend total_pages

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone):
    # Basic E.164 format validation (e.g., +1234567890)
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))

def fetch_data(page=1, page_size=5, type_personne="Physique"):
    with st.spinner("Fetching client recommendations..."):
        try:
            response = requests.get(API_URL, params={"page": page, "page_size": page_size, "type_personne": type_personne})
            if response.status_code == 200:
                data = response.json()
                return data
         
            else:
                 st.error(f"Failed to fetch data: {response.status_code} - {response.text}")
                 return None
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return None

     
def fetch_profile_stat(client_ref):
    with st.spinner("Fetching client recommendations..."):
        try:
            response = requests.get(PROFILE_API_URL, params={"client_ref":client_ref})
            if response.status_code == 200:
                data = response.json()
                return data
         
            else:
                 st.error(f"Failed to fetch data: {response.status_code} - {response.text}")
                 return None
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return None
def send_sms(phone_number, message):
    if not message:
        st.error("Message cannot be empty.")
        return
    try:
        payload = {"to": phone_number, "body": message}
        logger.info(f"Sending SMS to {phone_number} with payload: {payload}")
        response = requests.post(SMS_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {phone_number} via SMS!")
        else:
            st.error(f"Failed to send SMS: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending SMS: {str(e)}")

def send_whatsapp(phone_number, message):
    if not message:
        st.error("Message cannot be empty.")
        return
    try:
        payload = {"to": phone_number, "body": message}
        logger.info(f"Sending WhatsApp to {phone_number} with payload: {payload}")
        response = requests.post(WHATSAPP_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {phone_number} via WhatsApp!")
        else:
            st.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending WhatsApp message: {str(e)}")

def send_email(email, subject, message):
    if not is_valid_email(email):
        st.error("Invalid email format.")
        return
    if not subject or not message:
        st.error("Subject and message cannot be empty.")
        return
    try:
        payload = {"to": email, "subject": subject, "body": message}
        logger.info(f"Sending email to {email} with payload: {payload}")
        response = requests.post(EMAIL_API_URL, json=payload)
        if response.status_code == 200:
            st.success(f"Pitch sent to {email} via email!")
        else:
            st.error(f"Failed to send email: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")

def refine_pitch(client_name, products, user_input, max_words=150):
    """Send refinement request as POST with JSON body"""
    try:
        # Handle products properly - extract first product or concatenate all
        if isinstance(products, list) and len(products) > 0:
            product = products[0].get("product", "Insurance Product") if isinstance(products[0], dict) else str(products[0])
        else:
            product = str(products)
            
        payload = {
            "client_name": client_name,
            "product": product,
            "user_input": user_input,
            "max_words": max_words
        }
        logger.info(f"Sending POST request to {REFINE_API_URL} with payload: {payload}")
        response = requests.post(REFINE_API_URL, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get("pitch", "No pitch returned")
        else:
            logger.error(f"Refinement API error: {response.status_code} - {response.text}")
            return f"Failed to refine pitch: {response.status_code} - {response.text}"
    except Exception as e:
        logger.error(f"Error calling refinement API: {str(e)}")
        return f"Error calling refinement API: {str(e)}"

# Dashboard functions
def fetch_interactions(page=1, page_size=20, **filters):
    """Récupère les interactions avec pagination et filtres"""
    try:
        params = {
            "page": page,
            "page_size": page_size
        }
        response = requests.get(INTERACTIONS_API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            # Use actual total_pages from backend
            return data
        else:
            st.error(f"Erreur lors de la récupération des données: {response}")
            return None
    except Exception as e:
        st.error(f"Erreur de connexion: {str(e)}")
        return None

def fetch_stats():
    """Récupère les statistiques du tableau de bord"""
    try:
        response = requests.get(STATS_API_URL)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur lors de la récupération des statistiques: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erreur de connexion: {str(e)}")
        return None

def display_stats_cards(stats):
    """Affiche les cartes de statistiques"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📧 Total des Interactions",
            value=stats.get("total_interactions", 0)
        )
    
    with col2:
        st.metric(
            label="📈 Interactions Récentes (7j)",
            value=stats.get("recent_interactions", 0)
        )
    
    with col3:
        interested_count = stats.get("status_distribution", {}).get("interesse", 0)
        st.metric(
            label="✅ Clients Intéressés",
            value=interested_count
        )
    
    with col4:
        quote_requests = stats.get("type_distribution", {}).get("demande_devis", 0)
        st.metric(
            label="💰 Demandes de Devis",
            value=quote_requests
        )

def display_detailed_stats(stats):
    """Affiche des statistiques détaillées avec graphiques"""
    
    st.subheader("📊 Répartition par Type de Réponse")
    type_distribution = stats.get("type_distribution", {})
    if type_distribution:
        # Create a more readable display for types
        type_labels = {
            "interesse": "✅ Intéressé",
            "non_interesse": "❌ Non Intéressé", 
            "demande_devis": "💰 Demande Devis",
            "besoin_info": "ℹ️ Besoin d'Info",
            "inconnu": "❓ Inconnu",
            "en_cours": "⏳ En Cours"
        }
        
        for type_key, count in type_distribution.items():
            label = type_labels.get(type_key, type_key.title())
            st.metric(label, count)
    else:
        st.info("Aucune donnée de type disponible")
    
    # Top senders section
    st.subheader("👥 Top 5 des Expéditeurs les Plus Actifs")
    top_senders = stats.get("top_senders", [])
    if top_senders:
        for i, sender in enumerate(top_senders, 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{i}.** {sender.get('email', 'Email inconnu')}")
            with col2:
                st.write(f"**{sender.get('count', 0)}** interactions")
    else:
        st.info("Aucune donnée d'expéditeur disponible")
    
    # Additional metrics
    st.subheader("📋 Métriques Supplémentaires")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Calculate conversion rate (interested / total)
        total = stats.get("total_interactions", 0)
        interested = stats.get("status_distribution", {}).get("interesse", 0)
        conversion_rate = (interested / total * 100) if total > 0 else 0
        st.metric("📈 Taux de Conversion", f"{conversion_rate:.1f}%")
    
    with col2:
        # Calculate recent activity rate
        recent = stats.get("recent_interactions", 0)
        activity_rate = (recent / total * 100) if total > 0 else 0
        st.metric("⚡ Activité Récente", f"{activity_rate:.1f}%")
    
    with col3:
        # Average interactions per sender
        unique_senders = len(stats.get("top_senders", []))
        avg_interactions = (total / unique_senders) if unique_senders > 0 else 0
        st.metric("📊 Moy. par Expéditeur", f"{avg_interactions:.1f}")

def display_interactions_table(data):
    """Affiche le tableau des interactions"""
    if not data or not data.get("interactions"):
        st.info("Aucune interaction trouvée")
        return
    
    interactions = data["interactions"]
    
    # Convertir en DataFrame
    df = pd.DataFrame(interactions)
    
    # Formater les colonnes
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Traduire les statuts et types
        type_translation = {
            "interesse": "✅ Intéressé",
            "non_interesse": "❌ Non Intéressé",
            "demande_devis": "💰 Demande Devis",
            "besoin_info": "ℹ️ Besoin d'Info",
            "inconnu": "❓ Inconnu",
            "en_cours": "⏳ En Cours"
        }
        
        df['type_reponse'] = df['type_reponse'].map(type_translation).fillna(df['type_reponse'])
        
        # Configuration des colonnes
        column_config = {
            "expediteur_email": st.column_config.TextColumn("📧 Email", width="medium"),
            "sujet": st.column_config.TextColumn("📝 Sujet", width="medium"),
            "corps": st.column_config.TextColumn("✉️ Corps", width="large"),
            "type_reponse": st.column_config.TextColumn("📋 Type", width="small"),
            "timestamp": st.column_config.TextColumn("🕒 Date", width="small"),
        }
        
        # Sélectionner les colonnes à afficher
        display_columns = ["expediteur_email", "sujet","corps", "type_reponse", "timestamp"]
        df_display = df[display_columns]
        
        # Afficher le tableau
        st.dataframe(
            df_display,
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )

def show_dashboard():
    """Affiche le tableau de bord des interactions"""
    st.title("Tableau de Bord des Interactions")
    
    # Fetch and display statistics
    stats = fetch_stats()
    if stats:
        st.subheader("📊 Statistiques Générales")
        display_stats_cards(stats)
        
        # Additional stats visualizations
        display_detailed_stats(stats)
        
        st.divider()
    
    # Pagination
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📋 Liste des Interactions")
    with col2:
        page_size = st.selectbox("Éléments par page:", [10, 20, 50], index=1)
    
    # État de session pour la pagination du dashboard
    if 'dashboard_page' not in st.session_state:
        st.session_state.dashboard_page = 1
    
    # Récupérer les interactions
    data = fetch_interactions(
        page=st.session_state.dashboard_page,
        page_size=page_size,
    )
    
    if data:
        pagination = data.get("pagination", {})
        total_pages = pagination.get("total_pages", 1)
        current_page = pagination.get("page", st.session_state.dashboard_page)
        
        # Ensure current page doesn't exceed total pages
        st.session_state.dashboard_page = max(1, min(st.session_state.dashboard_page, total_pages))
        
        # Display pagination info
        st.info(f"📄 Page {current_page} sur {total_pages}")
        
        # Boutons de navigation
        col1, col2, col3 = st.columns([1, 5, 1])
        
        with col1:
            if st.button("⬅️ Précédent", disabled=st.session_state.dashboard_page <= 1, key="dash_prev"):
                st.session_state.dashboard_page -= 1
                st.rerun()
        
        with col3:
            # Disable next button if at total pages
            disable_next = (st.session_state.dashboard_page >= total_pages)
            if st.button("➡️ Suivant", disabled=disable_next, key="dash_next"):
                st.session_state.dashboard_page += 1
                st.rerun()
        
        # Afficher le tableau
        display_interactions_table(data)
    
    if st.button("🔄 Rafraîchir les données",key='refresh_data'):
        st.rerun()

def display_scrollable_products(products):
    """Display products in a scrollable container"""
    st.subheader("📦 Produits Recommandés")
    
    # Create a container with fixed height for scrolling
    with st.container(height=250, border=True):
        if isinstance(products, list):
            for i, product in enumerate(products):
                if isinstance(product, dict):
                    product_name = product.get("product", "N/A")
                    product_score = product.get("final_score", "N/A")
                    
                    # Create a styled container for each product
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{product_name}**")
                        with col2:
                            st.markdown(f"`{product_score:.3f}`")
                else:
                    st.markdown(f"**{product}**")
                
                # Add separator between products (except for the last one)
                if i < len(products) - 1:
                    st.divider()
        else:
            st.markdown(f"**{products}**")

def display_pitch(pitch_text, title="💬 Pitch Commercial"):
    """Display pitch in a styled container"""
    st.subheader(title)
    st.info(pitch_text)

def get_top_product(products):
    """Extract the top product from products list/dict"""
    if isinstance(products, list) and len(products) > 0:
        if isinstance(products[0], dict):
            return products[0].get("product", "N/A")
        else:
            return str(products[0])
    elif isinstance(products, dict):
        return products.get("product", "N/A")
    else:
        return str(products) if products != "N/A" else "N/A"

def show_recommendations():
    """Affiche la page des recommandations clients"""
    st.title("BH Assurance")
    
    st.divider()
    


    # Add tabs for Moral and Physique person types
    tab1, tab2 = st.tabs(["👤 Particuliers (Physique)", "🏢 Entreprises (Moral)"])
    
    with tab1:
        show_recommendations_for_type("Physique")
    
    with tab2:
        show_recommendations_for_type("Moral")

def show_recommendations_for_type(type_personne):
    """Affiche les recommandations pour un type de personne spécifique"""
    
    # Create unique session state keys for each type
    current_page_key = f'current_page_{type_personne}'
    last_page_size_key = f'last_page_size_{type_personne}'
    cached_data_key = f'cached_data_{type_personne}'
    last_fetched_page_key = f'last_fetched_page_{type_personne}'
    last_fetched_page_size_key = f'last_fetched_page_size_{type_personne}'

    # Session state initialization for this type
    if current_page_key not in st.session_state:
        st.session_state[current_page_key] = 1
    if last_page_size_key not in st.session_state:
        st.session_state[last_page_size_key] = 5
    if cached_data_key not in st.session_state:
        st.session_state[cached_data_key] = None
    if last_fetched_page_key not in st.session_state:
        st.session_state[last_fetched_page_key] = None
    if last_fetched_page_size_key not in st.session_state:
        st.session_state[last_fetched_page_size_key] = None

    # Page size from sidebar
    page_size = st.session_state.get('page_size', 5)

    # Fetch data only when necessary
    should_fetch = (
        st.session_state[cached_data_key] is None or
        st.session_state[last_fetched_page_key] != st.session_state[current_page_key] or
        st.session_state[last_fetched_page_size_key] != page_size
    )

    st.session_state[cached_data_key] = fetch_data(st.session_state[current_page_key], page_size, type_personne)
    st.session_state[last_fetched_page_key] = st.session_state[current_page_key]
    st.session_state[last_fetched_page_size_key] = page_size

   

    if st.session_state[last_page_size_key] != page_size:
        st.session_state[current_page_key] = 1
        st.session_state[last_page_size_key] = page_size
        st.session_state[cached_data_key] = None
        st.rerun()
    data = st.session_state[cached_data_key]
    if data and data.get('pitchs'):
        # Get total pages from data or use 1 as fallback
        total_pages = data.get('total_pages', 1)
        current_page = data.get('page', st.session_state[current_page_key])
        
        # Ensure current page doesn't exceed total pages
        max_allowed_page = total_pages
        st.session_state[current_page_key] = min(max(1, st.session_state[current_page_key]), max_allowed_page)

        # Display navigation info
        print(f"📄 Page {current_page} sur {total_pages} - {type_personne}")

        col1, col2 = st.columns([1, 1])
       
        with col1:
            if st.button("⬅️ Précédent", disabled=(st.session_state[current_page_key] <= 1), key=f"prev_button_{type_personne}"):
                st.session_state[current_page_key] = st.session_state[current_page_key] - 1
                st.session_state[cached_data_key] = None
                st.rerun()
        with col2:
            # Disable next button if at max allowed page
            disable_next = (st.session_state[current_page_key] >= max_allowed_page)
            if st.button("➡️ Suivant", disabled=disable_next, key=f"next_button_{type_personne}"):
                st.session_state[current_page_key] = st.session_state[current_page_key] + 1
                logger.info(f"Next button clicked: Navigating to page {st.session_state[current_page_key]} for {type_personne}")
                st.session_state[cached_data_key] = None
                st.rerun()

        # Display cards in full-width layout
        for idx, item in enumerate(data.get('pitchs', [])):
            client_ref = item.get('ref_personne', f'client_{idx}')
            client = item.get('client_name', 'N/A')
            products = item.get('recommendations', 'N/A')
            original_pitch = item.get('pitch', 'N/A')
            
            # Handle different fields based on type_personne
            if type_personne == "Moral":
                profession = item.get('LIB_SECTEUR_ACTIVITE')
                secteur = item.get('LIB_ACTIVITE')
                title_info = f"💼 {profession} | 🏢 {secteur}"
            else:
                profession = item.get('profession')
                age = item.get('age')
                sexe = item.get('sexe')
                title_info = f"💼 {profession} | 🎂 {age} ans | {'👨' if sexe in ['M', 'Homme', 'Male'] else '👩' if sexe in ['F', 'Femme', 'Female'] else '👤'} {sexe}"
                situation_fam=item.get('situation_familiale','N/A')
            
            # Get top product for display
            top_product = get_top_product(products)
            
            # Create unique key for this item
            unique_key = f"{type_personne}_{client_ref}_{idx}"
            
            with st.expander(f"👤 {client} | {title_info} | 📦 {top_product}", expanded=False):
                # Client Information Section
                st.subheader("📋 Informations Client")
                
                if type_personne == "Moral":
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🔍 Référence", client_ref)
                        st.metric("🏢 Raison Sociale", client)

                    with col2:
                        st.metric("💼 Libellé Secteur", profession)
                        st.metric("🏢 Secteur d'Activité", secteur)

                    with col3:
                        st.metric("📦 Top produit Recommandé", top_product)
                else:
                    # Extract age and gender for particuliers
                    age = item.get('age', item.get('AGE', 'N/A'))
                    sexe = item.get('sexe', item.get('SEXE', 'N/A'))
                    
                    col1, col2, col3, col4= st.columns(4)
                    
                    with col1:
                        st.metric("🔍 Référence", client_ref)
                        st.metric("👤 Nom", client)

                    with col2:
                        st.metric("💼 Profession", profession)
                        st.metric("🎂 Âge", f"{age} ans" if age != 'N/A' else 'N/A')

                    with col3:
                        # Display gender with appropriate icon
                        gender_display = "👨 Homme" if sexe in ['M', 'Homme', 'Male'] else "👩 Femme" if sexe in ['F', 'Femme', 'Female'] else f"👤 {sexe}"
                        st.metric("⚤ Sexe", gender_display)
                        st.metric("👫 Situation familiale", situation_fam)

                    with col4:
                        st.metric("📦 Top produit Recommandé", top_product)
                        
                
                st.divider()
                show_details=False
                # Bouton pour toggle les détails supplémentaires
                if st.button("📊 Voir plus de détails", key=f"btn_voir_client_stat{client_ref}"):
                      show_details = True
                #with st.form(key=f"client_form_{client_ref}"):

                if show_details:
                        st.subheader("📈 Détails supplémentaires")

                        # Appel de votre fonction pour récupérer les données
                        dashboard_data = fetch_profile_stat(client_ref)
                        print('dahboard_dataaa',dashboard_data)
                        person_info = dashboard_data['person_info']
                        graphs = dashboard_data['graphs']

                        # Header avec style CSS inline


                        # Statistiques principales
                        st.header("📊 STATISTIQUES GLOBALES")

                        # Grid de statistiques
                        col1, col2, col3, col4, col5, col6 = st.columns(6)

                        with col1:
                            st.metric("Total Contrats", person_info['total_contrats'], "Tous contrats confondus")

                        with col2:
                            st.metric("En Cours", person_info['stats_contrats'].get('EN COURS', 0), "Contrats actifs")

                        with col3:
                            st.metric("Expirés", person_info['stats_contrats'].get('EXPIRE', 0), "Contrats terminés")

                        with col4:
                            st.metric("Payés", person_info['paiement_stats'].get('payé', 0), "Contrats payés")

                        with col5:
                            st.metric("Non Payés", person_info['paiement_stats'].get('Non payé', 0), "Contrats en attente")

                        with col6:
                            st.metric("Valeur Totale", f"{person_info['valeur_totale']:,.0f} TND", "Somme des quittances")

                        # Informations sur les montants
                        col7, col8 = st.columns(2)

                        with col7:
                            st.success(f"**Total payé: {person_info['total_paye']:,.0f} TND**")
                            st.caption("Montant total des contrats réglés")

                        with col8:
                            st.error(f"**Total non payé: {person_info['total_non_paye']:,.0f} TND**")
                            st.caption("Montant total des contrats en attente de paiement")

                        # Visualisations
                        st.header("📈 ANALYSE VISUELLE DES CONTRATS")

                        # Graphiques en 2 colonnes
                        col_graph1, col_graph2 = st.columns(2)

                        with col_graph1:
                            st.subheader("Évolution des sousscriptions")
                            st.image(f"data:image/png;base64,{graphs['evolution_contrats']}", use_column_width=True)
                            st.caption("Évolution du nombre de contrats par année")

                        with col_graph2:
                            st.subheader("Répartition par branche")
                            st.image(f"data:image/png;base64,{graphs['repartition_branche']}", use_column_width=True)

                        col_graph3, col_graph4 = st.columns(2)

                        with col_graph3:
                            st.subheader("Capital assuré (TND)")
                            st.image(f"data:image/png;base64,{graphs['capital_assure']}", use_column_width=True)

                        with col_graph4:
                            st.subheader("Souscriptions récentes")
                            st.image(f"data:image/png;base64,{graphs['souscriptions_mensuelles']}", use_column_width=True)

                        col_graph5, col_graph6 = st.columns(2)

                        with col_graph5:
                            st.subheader("Montants payés vs non payés (TND)")
                            st.image(f"data:image/png;base64,{graphs['total_paye_non_paye']}", use_column_width=True)



                        # Produits
                        st.header("📋 PRODUITS")

                        col_prod1, col_prod2 = st.columns(2)

                        with col_prod1:
                            st.subheader("✅ PRODUITS EN COURS")
                            if person_info['produits_en_cours']:
                                for product, count in person_info['produits_en_cours'].items():
                                    st.info(f"**{product}** - {count} contrats")
                            else:
                                st.warning("Aucun contrat en cours")

                        with col_prod2:
                            st.subheader("❌ PRODUITS EXPIRÉS")
                            if person_info['produits_expires']:
                                for product, count in person_info['produits_expires'].items():
                                    st.error(f"**{product}** - {count} contrats")
                            else:
                                st.info("Aucun contrat expiré")

                        # Insights analytiques
                        st.header("💡 INSIGHTS ANALYTIQUES")

                        col_insight1, col_insight2, col_insight3 = st.columns(3)

                        with col_insight1:
                            st.markdown("""
                            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                                <h4>Comportement de souscription</h4>
                                <p>Analyse des habitudes de souscription du client</p>
                            </div>
                            """, unsafe_allow_html=True)

                        with col_insight2:
                            st.markdown(f"""
                            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                                <h4>Analyse de fidélité</h4>
                                <p>Taux de renouvellement estimé: <strong>{person_info['taux_renouvellement']:.1f}%</strong></p>
                                <p>Produits uniques: <strong>{len(set(list(person_info['produits_en_cours'].keys()) + list(person_info['produits_expires'].keys())))}</strong></p>
                            </div>
                            """, unsafe_allow_html=True)

                        with col_insight3:
                            taux_paiement = (person_info['total_paye']/person_info['valeur_totale']*100 if person_info['valeur_totale'] > 0 else 0)
                            st.markdown(f"""
                            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;">
                                <h4>Analyse financière</h4>
                                <p>Taux de paiement: <strong>{taux_paiement:.1f}%</strong></p>
                                <p>Encours à recouvrer: <strong>{person_info['total_non_paye']:,.0f} TND</strong></p>
                            </div>
                            """, unsafe_allow_html=True)

                        # Section Sinistres
                        if person_info['total_sinistres'] > 0:
                            st.header("⚠️ HISTORIQUE DES SINISTRES")

                            col_sin1, col_sin2, col_sin3 = st.columns(3)

                            with col_sin1:
                                st.metric("Total Sinistres", person_info['total_sinistres'])

                            with col_sin2:
                                st.metric("Montant Total", f"{person_info['montant_total_sinistres']:,.0f} TND")

                            with col_sin3:
                                st.metric("Taux Sinistralité", f"{person_info['taux_sinistralite']:.1f}%")

                            # Graphiques Sinistres
                            col_sin_graph1, col_sin_graph2 = st.columns(2)

                            with col_sin_graph1:
                                st.subheader("Répartition par état")
                                st.image(f"data:image/png;base64,{graphs['sinistres_etat']}", use_column_width=True)

                            with col_sin_graph2:
                                st.subheader("Évolution temporelle")
                                st.image(f"data:image/png;base64,{graphs['evolution_sinistres']}", use_column_width=True)

                            col_sin_graph3, col_sin_graph4 = st.columns(2)

                            with col_sin_graph3:
                                st.subheader("Répartition par branche")
                                st.image(f"data:image/png;base64,{graphs['sinistres_branche']}", use_column_width=True)

                            with col_sin_graph4:
                                st.subheader("Montants des sinistres")
                                st.image(f"data:image/png;base64,{graphs['montants_sinistres']}", use_column_width=True)

                            # Insights sinistres
                            col_sin_insight1, col_sin_insight2 = st.columns(2)

                            with col_sin_insight1:
                                freq_moyenne = person_info['total_sinistres'] / person_info['total_contrats'] if person_info['total_contrats'] > 0 else 0
                                st.markdown(f"""
                                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #dc3545;">
                                    <h4>Fréquence des sinistres</h4>
                                    <p>Ce client a déclaré en moyenne <strong>{freq_moyenne:.2f}</strong> sinistres par contrat</p>
                                </div>
                                """, unsafe_allow_html=True)

                            with col_sin_insight2:
                                cout_moyen = person_info['montant_total_sinistres'] / person_info['total_sinistres'] if person_info['total_sinistres'] > 0 else 0
                                st.markdown(f"""
                                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #dc3545;">
                                    <h4>Analyse de gravité</h4>
                                    <p>Coût moyen par sinistre: <strong>{cout_moyen:,.0f} TND</strong></p>
                                    <p>Montant encaissé: <strong>{person_info['montant_encaisse']:,.0f} TND</strong></p>
                                </div>
                                """, unsafe_allow_html=True)

                            # Détails des sinistres par type
                            if person_info['sinistres_par_type']:
                                st.subheader("Détail par type de sinistre")
                                for sin_type, count in person_info['sinistres_par_type'].items():
                                    st.write(f"**{sin_type}**: {count} sinistres")

                        else:
                            st.info("ℹ️ Aucun sinistre déclaré pour ce client")

                        # Bouton pour réduire les détails
                        if st.button("👆 Voir moins", key=f"btn_voir_moins{client_ref}"):
                            show_details = False
                            st.experimental_rerun()

                st.divider()
                # Use scrollable container for products
                display_scrollable_products(products)

                # Initialize chat history and current pitch for this client
                chat_key = f"chat_history_{unique_key}"
                current_pitch_key = f"current_pitch_{unique_key}"
                
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []
                if current_pitch_key not in st.session_state:
                    st.session_state[current_pitch_key] = original_pitch

                # Display current pitch
                display_pitch(st.session_state[current_pitch_key])

                # Refine pitch section (chat-like interface)
                st.subheader("🤖 Discuter et Affiner le Pitch avec l'IA")
                
                # Display chat history
                chat_container = st.container(border=True)
                with chat_container:
                    if st.session_state[chat_key]:
                        for msg in st.session_state[chat_key]:
                            if msg.startswith("User:"):
                                st.chat_message("user").write(msg.replace("User: ", ""))
                            else:
                                # Extract only the pitch content from the response
                                pitch_content = msg.replace("LLM: ", "")
                                st.chat_message("assistant").write(pitch_content)
                    else:
                        st.info("💡 Commencez une conversation pour affiner le pitch selon vos besoins.")

                # Input for refinement
                user_input = st.chat_input("Tapez votre message pour affiner le pitch...", key=f"chat_input_{unique_key}")
                if user_input:
                    # Add user message to chat history
                    st.session_state[chat_key].append(f"User: {user_input}")
                    
                    # Show the current pitch first if it's the first interaction
                    if len(st.session_state[chat_key]) == 1:
                        st.session_state[chat_key].insert(0, f"LLM: {st.session_state[current_pitch_key]}")

                    # Show loading spinner while refining
                    with st.spinner("🔄 Affinage du pitch en cours..."):
                        refined_pitch_response = refine_pitch(client, products, user_input, 150)

                    print("call refinement api", refined_pitch_response)
                    
                    if refined_pitch_response.startswith(("Error", "Failed")):
                        st.error(refined_pitch_response)
                        st.session_state[chat_key].append(f"LLM: ❌ {refined_pitch_response}")
                    else:
                        # Store just the pitch content in chat history
                        st.session_state[chat_key].append(f"LLM: {refined_pitch_response}")
                        
                        # Update the current pitch
                        st.session_state[current_pitch_key] = refined_pitch_response

                    st.rerun()

                # Send options
                st.subheader("📤 Envoyer le Pitch")
                st.markdown("Entrez les coordonnées de contact pour envoyer:")
                
                # Get the current pitch to send
                current_pitch_to_send = st.session_state[current_pitch_key].lstrip()
                
                with st.container():
                    email = st.text_input("📧 Email du destinataire:", key=f"email_{unique_key}")
                    if st.button("📧 Envoyer par Email", key=f"email_btn_{unique_key}") and email:
                        subject = f"Proposition d'Assurance pour {client} - {top_product}"
                        logger.info(f"Email button clicked for {unique_key}")
                        send_email(email, subject, current_pitch_to_send)
                
                    whatsapp_num = st.text_input("📱 Numéro WhatsApp (ex: +1234567890):", key=f"whatsapp_{unique_key}")
                    if st.button("📱 Envoyer via WhatsApp", key=f"whatsapp_btn_{unique_key}") and whatsapp_num:
                        logger.info(f"WhatsApp button clicked for {unique_key}")
                        send_whatsapp(whatsapp_num, current_pitch_to_send)
                
                    sms_num = st.text_input("💬 Numéro SMS (ex: +1234567890):", key=f"sms_{unique_key}")
                    if st.button("💬 Envoyer via SMS", key=f"sms_btn_{unique_key}") and sms_num:
                        logger.info(f"SMS button clicked for {unique_key}")
                        send_sms(sms_num, current_pitch_to_send)
    else:
        st.warning(f"Aucune recommandation client disponible pour les {type_personne.lower()} ou échec du chargement des données.")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.button("⬅️ Précédent", disabled=True, key=f"prev_button_no_data_{type_personne}")
        with col2:
            st.button("➡️ Suivant", disabled=True, key=f"next_button_no_data_{type_personne}")

# Main application logic
def main():
    # Sidebar pour la navigation
    st.sidebar.title("Navigation")
    
    # Radio button pour choisir la page
    page = st.sidebar.radio(
        "Choisir une section:",
        ["Recommandations Clients", "Tableau de Bord"]
    )
    
    # Sidebar settings (seulement pour la page recommandations)
    if page == "Recommandations Clients":
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Paramètres")
        page_size_options = [5, 10, 20]
        page_size = st.sidebar.selectbox("Taille de page:", page_size_options, index=0, key="page_size_select")
        st.session_state.page_size = page_size
    
    # Afficher la page sélectionnée
    if page == "Recommandations Clients":
        show_recommendations()
    elif page == "Tableau de Bord":
        show_dashboard()

if __name__ == "__main__":
    main()