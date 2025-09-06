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

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone):
    # Basic E.164 format validation (e.g., +1234567890)
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))

def fetch_data(page=1, page_size=5):
    with st.spinner("Fetching client recommendations..."):
        try:
            page = max(1, int(page))
            #logger.info(f"Sending request to {API_URL}?page={page}&page_size={page_size}")
            response = requests.get(API_URL, params={"page": page, "page_size": page_size})
            if response.status_code == 200:
                data = response.json()
                #logger.info(f"Received response: {data}")
                data['client'] = max(1, int(data.get('client', page)))
                data['page_size'] = max(1, int(data.get('page_size', page_size)))
                data['total_clients'] = max(0, int(data.get('total_clients', 0)))
                data['total_pages'] = max(1, int(data.get('total_pages', math.ceil(data['total_clients'] / data['page_size']))))
                if data['client'] != page:
                    st.warning(f"Warning: Requested page {page}, but received page {data['client']} from backend.")
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

def refine_pitch(client_name, product, user_input, max_words=150):
    """Send refinement request as POST with JSON body"""
    try:
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
            return response.json()
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
            "id": st.column_config.NumberColumn("ID", width="small"),
            "expediteur_email": st.column_config.TextColumn("📧 Email", width="medium"),
            "sujet": st.column_config.TextColumn("📝 Sujet", width="medium"),
            "type_reponse": st.column_config.TextColumn("📋 Type", width="small"),
            "timestamp": st.column_config.TextColumn("🕒 Date", width="small"),
        }
        
        # Sélectionner les colonnes à afficher
        display_columns = ["id", "expediteur_email", "sujet", "type_reponse", "timestamp"]
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

    print("intr", data)
    
    if data:
        pagination = data.get("pagination", {})
        
        # Afficher les informations de pagination
        st.info(f"Page {pagination.get('page', 1)} sur {pagination.get('total_pages', 1)} "
                f"({pagination.get('total_items', 0)} interactions au total)")
        
        # Boutons de navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Précédent", disabled=st.session_state.dashboard_page <= 1, key="dash_prev"):
                st.session_state.dashboard_page -= 1
                st.rerun()
        
        with col3:
            if st.button("➡️ Suivant", disabled=st.session_state.dashboard_page >= pagination.get('total_pages', 1), key="dash_next"):
                st.session_state.dashboard_page += 1
                st.rerun()
        
        # Afficher le tableau
        display_interactions_table(data)
    
    if st.button("🔄 Rafraîchir les données"):
        st.rerun()


def show_recommendations():
    """Affiche la page des recommandations clients"""
    st.title("BH Assurance")

    # Session state initialization
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'last_page_size' not in st.session_state:
        st.session_state.last_page_size = 5
    if 'cached_data' not in st.session_state:
        st.session_state.cached_data = None
    if 'last_fetched_page' not in st.session_state:
        st.session_state.last_fetched_page = None
    if 'last_fetched_page_size' not in st.session_state:
        st.session_state.last_fetched_page_size = None

    # Page size from sidebar
    page_size = st.session_state.get('page_size', 5)

    # Fetch data only when necessary
    should_fetch = (
        st.session_state.cached_data is None or
        st.session_state.last_fetched_page != st.session_state.current_page or
        st.session_state.last_fetched_page_size != page_size
    )

    if should_fetch:
        st.session_state.cached_data = fetch_data(st.session_state.current_page, page_size)
        st.session_state.last_fetched_page = st.session_state.current_page
        st.session_state.last_fetched_page_size = page_size

    data = st.session_state.cached_data

    # Reset current_page to 1 when page_size changes
    if st.session_state.last_page_size != page_size:
        st.session_state.current_page = 1
        st.session_state.last_page_size = page_size
        st.session_state.cached_data = None  # Clear cache to force refetch
        st.rerun()

    if data and data.get('pitchs'):
        st.session_state.current_page = min(max(1, st.session_state.current_page), 50)

        col1, col2 = st.columns([1, 1])
       
        with col1:
            if st.button("Previous", disabled=(st.session_state.current_page <= 1), key="prev_button"):
                st.session_state.current_page = st.session_state.current_page - 1
                st.session_state.cached_data = None  # Clear cache to force refetch
                st.rerun()
        with col2:
            if st.button("Next", disabled=(st.session_state.current_page >= 50), key="next_button"):
                st.session_state.current_page = st.session_state.current_page + 1
                logger.info(f"Next button clicked: Navigating to page {st.session_state.current_page}")
                st.session_state.cached_data = None  # Clear cache to force refetch
                st.rerun()

        # Display cards in full-width layout
        for idx, item in enumerate(data.get('pitchs', [])):
            client_ref = item.get('ref_personne', f'client_{idx}')
            client = item.get('client_name', 'N/A')
            product = item.get('recommendations', 'N/A')
            profession = item.get('LIB_SECTEUR_ACTIVITE', 'N/A')
            secteur = item.get('LIB_ACTIVITE', 'N/A')
            pitch_text = item.get('pitch', 'N/A')
            
            # Create unique key for this item
            unique_key = f"{client_ref}_{idx}"
            
            with st.expander(f"👤 {client} | 💼 {profession} | 🏢 {secteur} | 📦 {product}", expanded=False):
                # Client Information Section
                st.subheader("📋 Informations Client")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("🔍 Référence", client_ref)
                    st.metric("👤 Raison Sociale", client)

                with col2:
                    st.metric("💼 Libellé Secteur", profession)
                    st.metric("🏢 Secteur d'Activité", secteur)

                with col3:
                    st.metric("📦 Top produit Recommandé", product)
                
                st.divider()
                
                st.markdown("**🎯 Recommandations:**")
                st.write(product)
                
                st.markdown("**💬 Pitch Commercial:**")
                st.write(pitch_text)

                # Refine pitch section (chat-like interface)
                st.subheader("🤖 Discuss and Refine Pitch with LLM")
                chat_key = f"chat_history_{unique_key}"
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []

                # Display chat history
                chat_container = st.container(border=True)
                with chat_container:
                    for msg in st.session_state[chat_key]:
                        if msg.startswith("User:"):
                            st.chat_message("user").write(msg.replace("User: ", ""))
                        else:
                            # Extract only the pitch content from the response
                            pitch_content = msg.replace("LLM: ", "")
                            st.chat_message("assistant").write(pitch_content)

                # Input for refinement
                user_input = st.chat_input("Type your message to refine the pitch...", key=f"chat_input_{unique_key}")
                if user_input:
                    st.session_state[chat_key].append(f"User: {user_input}")

                    refined_pitch_response = refine_pitch(client, product, user_input, 150)

                    print("call refinment api", refined_pitch_response)
                    
                    if refined_pitch_response.startswith(("Error", "Failed")):
                        st.error(refined_pitch_response)
                        st.session_state[chat_key].append(f"LLM: {refined_pitch_response}")
                    else:
                        # Store just the pitch content in chat history
                        st.session_state[chat_key].append(f"LLM: {refined_pitch_response}")
                        
                        # Update the displayed pitch in the data
                        item['pitch'] = refined_pitch_response

                    st.rerun()

                # Send options
                st.subheader("📤 Send Pitch")
                st.markdown("Enter contact details to send:")
                
                with st.container():
                    email = st.text_input("📧 Recipient Email:", key=f"email_{unique_key}")
                    if st.button("📧 Send via Email", key=f"email_btn_{unique_key}") and email:
                        subject = f"Insurance Pitch for {client} - {product}"
                        logger.info(f"Email button clicked for {unique_key}")
                        send_email(email, subject, pitch_text)
                
                    whatsapp_num = st.text_input("📱 Recipient WhatsApp Number (e.g., +1234567890):", key=f"whatsapp_{unique_key}")
                    if st.button("📱 Send via WhatsApp", key=f"whatsapp_btn_{unique_key}") and whatsapp_num:
                        logger.info(f"WhatsApp button clicked for {unique_key}")
                        send_whatsapp(whatsapp_num, pitch_text)
                
                    sms_num = st.text_input("💬 Recipient SMS Number (e.g., +1234567890):", key=f"sms_{unique_key}")
                    sms_num = "+21620089888"
                    if st.button("💬 Send via SMS", key=f"sms_btn_{unique_key}") and sms_num:
                        logger.info(f"SMS button clicked for {unique_key}")
                        send_sms(sms_num, pitch_text)
    else:
        st.warning("No client recommendations available or failed to load data.")
        st.session_state.current_page = 1
        col1, col2 = st.columns([1, 1])
        with col1:
            st.button("Previous", disabled=True, key="prev_button_no_data")
        with col2:
            st.button("Next", disabled=True, key="next_button_no_data")
        

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