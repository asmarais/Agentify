import streamlit as st
import pandas as pd
import random
from faker import Faker
import os
import json
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Recherche Client et Génération Pitch", layout="wide")

# Initialisation de la session state
if 'clients_df' not in st.session_state:
    # Vérifier si le fichier de données existe déjà
    if os.path.exists('clients_data.csv'):
        st.session_state.clients_df = pd.read_csv('clients_data.csv')
    else:
        # Importer le générateur de données fictives
        from data_generator import generate_fake_clients
        # Générer des données fictives
        clients_df = generate_fake_clients(50)  # 50 clients fictifs
        # Sauvegarder les données
        clients_df.to_csv('clients_data.csv', index=False)
        st.session_state.clients_df = clients_df

if 'selected_client' not in st.session_state:
    st.session_state.selected_client = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'final_pitch' not in st.session_state:
    st.session_state.final_pitch = ""

# Fonction pour vérifier si les champs essentiels sont remplis et correctement formatés
def check_essential_fields(client):
    essential_fields = ['metier', 'age', 'situation_familiale', 'email', 'telephone']
    missing_fields = []
    invalid_formats = {}
    
    for field in essential_fields:
        # Vérifier si le champ est vide ou NaN
        if pd.isna(client[field]) or client[field] == "":
            missing_fields.append(field)
        # Vérifier le format de l'email
        elif field == 'email' and '@' not in str(client[field]):
            invalid_formats[field] = "Format d'email invalide"
        # Vérifier le format du téléphone (au moins 10 chiffres)
        elif field == 'telephone':
            phone = ''.join(filter(str.isdigit, str(client[field])))
            if len(phone) < 10:
                invalid_formats[field] = "Format de téléphone invalide"
    
    return missing_fields, invalid_formats

# Fonction pour générer des recommandations
def generate_recommendations(client):
    recommendations = []
    
    # Logique simple basée sur l'âge et la situation familiale
    if client['age'] < 30:
        if 'Auto' not in client['contrats_souscrits']:
            recommendations.append("Assurance Auto - Idéal pour les jeunes conducteurs avec des tarifs adaptés")
    
    if client['situation_familiale'] in ['Marié(e)', 'En couple'] and 'Habitation' not in client['contrats_souscrits']:
        recommendations.append("Assurance Habitation - Protection optimale pour votre foyer")
    
    if client['age'] > 40 and 'Santé' not in client['contrats_souscrits']:
        recommendations.append("Assurance Santé - Couverture complète adaptée à votre âge")
    
    if client['situation_familiale'] in ['Marié(e)', 'Divorcé(e)'] and client['age'] > 35 and 'Prévoyance' not in client['contrats_souscrits']:
        recommendations.append("Assurance Prévoyance - Sécurité financière pour vous et vos proches")
    
    # Si aucune recommandation n'a été générée, proposer un produit par défaut
    if not recommendations:
        available_products = ['Auto', 'Habitation', 'Santé', 'Prévoyance', 'Épargne']
        current_products = client['contrats_souscrits'].split(', ') if isinstance(client['contrats_souscrits'], str) else []
        
        for product in available_products:
            if product not in current_products:
                recommendations.append(f"Assurance {product} - Complétez votre protection avec notre offre adaptée")
                break
        
        if not recommendations:
            recommendations.append("Révision de contrats - Optimisez vos contrats actuels avec notre audit personnalisé")
    
    return recommendations

# Fonction pour générer un pitch commercial
def generate_pitch(client, recommendations):
    if not recommendations:
        return "Aucune recommandation disponible pour ce client."
    
    nom_complet = f"{client['prenom']} {client['nom']}"
    
    pitch = f"Bonjour {client['prenom']},\n\n"
    pitch += f"Suite à notre analyse de votre profil, nous avons identifié des opportunités pour optimiser votre protection.\n\n"
    
    for i, rec in enumerate(recommendations, 1):
        product = rec.split(' - ')[0]
        justification = rec.split(' - ')[1]
        pitch += f"{i}. {product}: {justification}\n"
    
    pitch += "\nSeriez-vous disponible pour un échange rapide afin de discuter de ces solutions adaptées à votre situation ?\n\n"
    pitch += "Cordialement,\nVotre conseiller"
    
    return pitch

# Fonction pour simuler l'envoi d'un message
def send_message(channel, client, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Message envoyé via {channel} à {client['prenom']} {client['nom']} le {timestamp}"

# Interface utilisateur
st.title("Recherche Client et Génération Pitch")

# Barre latérale pour la recherche client
with st.sidebar:
    st.header("Recherche Client")
    client_ref = st.text_input("Référence client", placeholder="Entrez la référence client")
    search_button = st.button("Rechercher")
    
    # Suppression de l'affichage des références clients
    # with st.expander("Références clients disponibles"):
    #     st.dataframe(st.session_state.clients_df[['ref_client', 'nom', 'prenom']], hide_index=True)

# Recherche du client
if search_button and client_ref:
    client_data = st.session_state.clients_df[st.session_state.clients_df['ref_client'] == client_ref]
    
    if not client_data.empty:
        st.session_state.selected_client = client_data.iloc[0].to_dict()
        st.session_state.chat_history = []
        st.session_state.final_pitch = ""
    else:
        st.error("Client non trouvé. Veuillez vérifier la référence client.")

# Affichage des informations client et traitement
if st.session_state.selected_client:
    client = st.session_state.selected_client
    
    # Affichage du résumé de la fiche client avec possibilité d'édition
    st.subheader(f"Fiche client: {client['prenom']} {client['nom']}")
    
    # Création d'un formulaire pour éditer toutes les informations
    with st.form("edit_client_form"):
        updated_client = client.copy()
        form_valid = True
        col1, col2 = st.columns(2)
        
        with col1:
            prenom = st.text_input("Prénom", value=client['prenom'])
            if not prenom:
                st.error("Le prénom est requis")
                form_valid = False
            updated_client['prenom'] = prenom
            
            nom = st.text_input("Nom", value=client['nom'])
            if not nom:
                st.error("Le nom est requis")
                form_valid = False
            updated_client['nom'] = nom
            
            updated_client['age'] = st.number_input("Âge", min_value=18, max_value=100, value=int(client['age']) if not pd.isna(client['age']) else 30)
            
            metier = st.text_input("Métier", value=client['metier'] if client['metier'] else "")
            if not metier:
                st.error("Le métier est requis")
                form_valid = False
            updated_client['metier'] = metier
            
            situations = ["Célibataire", "En couple", "Marié(e)", "Divorcé(e)", "Veuf/Veuve"]
            updated_client['situation_familiale'] = st.selectbox("Situation familiale", situations, 
                                                                index=situations.index(client['situation_familiale']) if client['situation_familiale'] in situations else 0)
        
        with col2:
            email = st.text_input("Email", value=client['email'] if client['email'] else "")
            if not email:
                st.error("L'email est requis")
                form_valid = False
            elif '@' not in email:
                st.error("Format d'email invalide")
                form_valid = False
            updated_client['email'] = email
            
            telephone = st.text_input("Téléphone", value=client['telephone'] if client['telephone'] else "")
            if not telephone:
                st.error("Le téléphone est requis")
                form_valid = False
            elif len(''.join(filter(str.isdigit, telephone))) < 10:
                st.error("Le téléphone doit contenir au moins 10 chiffres")
                form_valid = False
            updated_client['telephone'] = telephone
            
            # Affichage des contrats souscrits sans possibilité de modification
            st.write("**Contrats souscrits:**")
            if client['contrats_souscrits']:
                st.write(client['contrats_souscrits'])
            else:
                st.write("Aucun contrat souscrit")
            
            # Conserver la valeur des contrats souscrits sans modification
            updated_client['contrats_souscrits'] = client['contrats_souscrits']
        
        submit_button = st.form_submit_button("Mettre à jour les informations")
        
        if submit_button and form_valid:
            # Mise à jour des informations du client dans le DataFrame
            for field in updated_client.keys():
                st.session_state.clients_df.loc[st.session_state.clients_df['ref_client'] == client['ref_client'], field] = updated_client[field]
            
            # Mise à jour du client sélectionné
            st.session_state.selected_client = updated_client
            st.session_state.clients_df.to_csv('clients_data.csv', index=False)
            st.success("Informations mises à jour avec succès!")
            st.rerun()
        elif submit_button and not form_valid:
            st.error("Veuillez corriger les erreurs avant de soumettre le formulaire")
    
    # Vérification des champs essentiels pour l'analyse
    missing_fields, invalid_formats = check_essential_fields(client)
    
    # Analyse et recommandations
    analyze_button = st.button("Analyser", disabled=bool(missing_fields) or bool(invalid_formats))
    
    if missing_fields:
        with st.warning("Certaines informations essentielles sont manquantes. Veuillez compléter votre profil avant l'analyse."):
            st.write(", ".join([field.capitalize() for field in missing_fields]))
    
    if invalid_formats:
        with st.error("Certains champs ont un format invalide. Veuillez les corriger avant l'analyse."):
            for field, message in invalid_formats.items():
                st.write(f"{field.capitalize()}: {message}")
    
    if analyze_button or st.session_state.final_pitch:
        # Générer des recommandations
        recommendations = generate_recommendations(client)
        
        # Afficher les recommandations
        with st.expander("Recommandations", expanded=True):
            for rec in recommendations:
                st.markdown(f"- {rec}")
        
        # Générer le pitch initial si pas encore fait
        if not st.session_state.final_pitch:
            initial_pitch = generate_pitch(client, recommendations)
            st.session_state.final_pitch = initial_pitch
        
        # Afficher le pitch et permettre son édition
        st.subheader("Pitch commercial")
        pitch_area = st.text_area("Pitch actuel", value=st.session_state.final_pitch, height=250)
        st.session_state.final_pitch = pitch_area
        
        # Chat pour affiner le pitch
        st.subheader("Affinage du pitch")
        
        # Afficher l'historique du chat
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Zone de saisie pour le chat
        user_input = st.chat_input("Demandez des modifications du pitch...")
        
        if user_input:
            # Ajouter le message de l'utilisateur à l'historique
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Simuler une réponse de l'IA
            if "court" in user_input.lower():
                shorter_pitch = st.session_state.final_pitch.split("\n\n")[0] + "\n\nSeriez-vous disponible pour un échange rapide?\n\nCordialement,\nVotre conseiller"
                ai_response = "Voici une version plus courte du pitch:"
                st.session_state.final_pitch = shorter_pitch
            elif "santé" in user_input.lower():
                health_focused = st.session_state.final_pitch.replace("optimiser votre protection", "améliorer votre couverture santé")
                for rec in recommendations:
                    if "Santé" in rec:
                        health_focused = health_focused.replace(rec, f"**{rec}**")
                ai_response = "J'ai mis l'accent sur la couverture santé:"
                st.session_state.final_pitch = health_focused
            else:
                ai_response = "J'ai ajusté le pitch selon votre demande."
            
            # Ajouter la réponse de l'IA à l'historique
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            
            st.rerun()
        
        # Options d'envoi multicanal
        st.subheader("Envoi du message")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Envoyer par Email") and client['email']:
                st.success(send_message("Email", client, st.session_state.final_pitch))
        
        with col2:
            if st.button("Envoyer par WhatsApp") and client['telephone']:
                st.success(send_message("WhatsApp", client, st.session_state.final_pitch))
        
        with col3:
            if st.button("Envoyer par SMS") and client['telephone']:
                st.success(send_message("SMS", client, st.session_state.final_pitch))