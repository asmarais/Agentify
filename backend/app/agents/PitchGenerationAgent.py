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

    # Prompt template
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "Vous êtes un assistant commercial expert en assurance. "
            "Toujours répondre en format JSON valide et rien d'autre. "
            "Respectez strictement la limite de mots demandée ({max_words})."
        ),
        HumanMessagePromptTemplate.from_template(
            "Générez un texte commercial court et professionnel pour un assureur.\n"
            "Détails du client :\n"
            "- Nom : {client_name}\n"
            "- Produit recommandé : {first_product}\n"
            "- Garanties du produit : {garantie}\n\n"
            "Format attendu :\n"
            "{{\n"
            '  "client": "{client_name}",\n'
            '  "product": "{first_product}",\n'
            '  "pitch": "Texte commercial généré ici (environ {max_words} mots)"\n'
            "}}"
        )
    ])

    garanties_dict = {normalize_text(k): v for k, v in state.get('garanties', {}).items()}

    for client in page_clients:
        client_name = client.get('name') or client.get('RAISON_SOCIALE', 'Client')
        produits_recommandes = client.get('top_recommendations', [])
        first_product = produits_recommandes[0].get('product', 'N/A') if produits_recommandes else 'N/A'

        # Extract product names
        product_names = [normalize_text(rec.get('product', 'N/A')) for rec in produits_recommandes]
        produits_recommandes_text = ', '.join(product_names) or 'N/A'

        # Extract garanties
        garantie_text = garanties_dict.get(normalize_text(first_product), "N/A")

        # Format prompt
        formatted_prompt = prompt_template.format_prompt(
            style=style,
            max_words=max_words,
            client_name=client_name,
            first_product=first_product,
            garantie=garantie_text
        )

        pitch_text = await llm.ainvoke(formatted_prompt.to_messages())

        cleaned_output = str(pitch_text).strip()
        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.strip("`").replace("json", "").strip()

        try:
            pitch_json = json.loads(cleaned_output)
        except json.JSONDecodeError:
            pitch_json = {
                "client": client_name,
                "product": first_product,
                "pitch": "Erreur lors de la génération du pitch."
            }

        pitches.append({
            "recommendations": produits_recommandes_text,
            "client_ref": client.get("REF_PERSONNE", f"client_{client_name}"),
            "pitch": pitch_json
        })

    return {
        **state,
        "pitchs": pitches,
        "current_agent": "pitch_generator",
        "page": page,
        "page_size": page_size,
        "total_clients": total_clients,
        "total_pages": total_pages
    }
