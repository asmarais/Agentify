from app.workflows.AgentState import AgentState
from typing import List, Dict
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import unicodedata
import math
import json

llm = OllamaLLM(model="llama3.2")

def normalize_text(text: str) -> str:
    """Normalize text to uppercase and remove accents for consistent matching."""
    text = text.strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

async def pitch_generation_node(state: AgentState, style: str = "professionnel", max_words: int = 80) -> AgentState:
    recommendations = state.get("recommendations", {}).get("clients", [])
    total_clients = len(recommendations)

    page = state.get("page", 1)
    page_size = state.get("page_size", 5)

    total_pages = max(1, math.ceil(total_clients / page_size))

    # Validate page
    if page < 1 or page > total_pages:
        return {**state, "error": f"Invalid page number {page}. Total pages: {total_pages}"}

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_clients)
    page_clients = recommendations[start_idx:end_idx]

    pitches: List[Dict] = []
    type_personne = state.get("type_personne", "Moral")
    
    print("type personne", type_personne)

    # Define prompt templates based on person type
    if type_personne == "Moral":
        # Prompt template for moral persons (companies)
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "Vous êtes un assistant commercial expert en assurance. "
                "Toujours répondre en format JSON valide et rien d'autre. "
                "Respectez strictement la limite de mots demandée ({max_words})."
            ),
            HumanMessagePromptTemplate.from_template(
                "Générez un texte commercial court et professionnel pour un assureur destiné à une entreprise.\n"
                "Détails de l'entreprise :\n"
                "- Nom de l'entreprise : {client_name}\n"
                "- Secteur d'activité : {LIB_SECTEUR_ACTIVITE}\n"
                "- Activité spécifique : {LIB_ACTIVITE}\n"
                "- Produit recommandé : {first_product}\n"
                "- Garanties du produit : {garantie}\n\n"
                "Personnalisez le pitch selon le secteur d'activité et les besoins professionnels de l'entreprise.\n"
                "Format attendu :\n"
                "{{\n"
                '  "pitch": "Texte commercial personnalisé pour l\'entreprise selon son secteur d\'activité (environ {max_words} mots)"\n'
                "}}"
            )
        ])
    else:
        # Prompt template for physical persons (individuals)
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "Vous êtes un assistant commercial expert en assurance. "
                "Toujours répondre en format JSON valide et rien d'autre. "
                "Respectez strictement la limite de mots demandée ({max_words})."
            ),
            HumanMessagePromptTemplate.from_template(
                "Générez un texte commercial court et professionnel pour un assureur destiné à un particulier qui a cette profession {profession}\n"
                "Détails du client :\n"
                "- Nom : {client_name}\n"
                "- Profession : {profession}\n"
                "- Produit recommandé : {first_product}\n"
                "- Garanties du produit : {garantie}\n\n"
                "Personnalisez le pitch selon la profession et les besoins personnels du client.\n"
                "Format attendu :\n"
                "{{\n"
                '  "pitch": "Texte commercial personnalisé selon la profession et les besoins individuels (environ {max_words} mots)"\n'
                "}}"
            )
        ])

    garanties_dict = {normalize_text(k): v for k, v in state.get('garanties', {}).items()}

    for client in page_clients:
        produits_recommandes = client.get('top_recommendations', [])
        first_product = produits_recommandes[0].get('product', 'N/A') if produits_recommandes else 'N/A'
        product_names = [{"product": rec.get('product', 'N/A').lower().capitalize(), "final_score": rec.get("final_score", 'N/A')} for rec in produits_recommandes]
        garantie_text = garanties_dict.get(normalize_text(first_product), "N/A")

        if type_personne == "Moral":
            # Handle moral person (company) case
            client_name = client.get('name') or client.get('RAISON_SOCIALE', 'Client')
            profession = client.get('LIB_SECTEUR_ACTIVITE', 'Client')
            secteur_activite = client.get('LIB_ACTIVITE', 'Client')
            
            formatted_prompt = prompt_template.format_prompt(
                style=style,
                max_words=max_words,
                client_name=client_name,
                LIB_SECTEUR_ACTIVITE=profession,
                LIB_ACTIVITE=secteur_activite,
                first_product=first_product,
                garantie=garantie_text
            )
            
            client_data = {
                "recommendations": product_names,
                "LIB_SECTEUR_ACTIVITE": client.get("LIB_SECTEUR_ACTIVITE", "").lower().capitalize(),
                "client_name": client_name,
                "LIB_ACTIVITE": client.get("LIB_ACTIVITE", "").lower().capitalize(),
                "ref_personne": client.get("REF_PERSONNE"),
            }
        else:
            # Handle physical person (individual) case
            client_name = client.get('name') or client.get('PRENOM', '') + ' ' + client.get('NOM', 'Client')
            profession = client.get('profession', 'N/A')
            age = client.get('age', 'N/A')
            print(age)
            sexe = client.get('sexe', 'N/A')
            print(sexe)
            
            formatted_prompt = prompt_template.format_prompt(
                style=style,
                max_words=max_words,
                client_name=client_name.strip(),
                profession=profession,
                age=age,
                sexe=sexe,
                first_product=first_product,
                garantie=garantie_text
            )
            
            client_data = {
                "recommendations": product_names,
                "profession": profession,
                "client_name": client_name.strip(),
                "ref_personne": client.get("REF_PERSONNE"),
                "age": age,
                "sexe": sexe
            }
        
        # Generate pitch using LLM
        test = False
        while not test:
            try:
                pitch_text = await llm.ainvoke(formatted_prompt.to_messages())
                cleaned_output = str(pitch_text).strip()
                
                if cleaned_output.startswith("```"):
                    cleaned_output = cleaned_output.strip("`").replace("json", "").strip()

                pitch_json = json.loads(cleaned_output)                
                test = True
                
                client_data["pitch"] = pitch_json.get("pitch", "N/A")
                pitches.append(client_data)
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error for client {client_name}: {e}")
                test = False
            except Exception as e:
                print(f"Error generating pitch for client {client_name}: {e}")
                client_data["pitch"] = f"Pitch personnalisé pour {client_name} concernant {first_product}"
                pitches.append(client_data)
                test = True

    return {
        **state,
        "pitchs": pitches,
        "current_agent": "pitch_generator",
        "page": page,
        "page_size": page_size,
        "total_clients": total_clients,
        "total_pages": total_pages
    }