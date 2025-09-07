from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import OllamaLLM
from app.workflows.ChatState import ChatState

router = APIRouter()

llm = OllamaLLM(model="llama3.2")

memory_store = {}

memory_saver = MemorySaver()

class PitchRequest(BaseModel):
    client_name: str
    product: str
    user_input: str

# Define the prompt template
prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        """Vous êtes un assistant expert en rédaction de pitches commerciaux pour des produits d'assurance.

        INSTRUCTIONS BASÉES SUR L'INPUT UTILISATEUR:
        - Analysez l'instruction de l'utilisateur : "{user_input}"
        - Si l'utilisateur demande de "générer un pitch pour un produit [NOM_PRODUIT]":
          * Identifiez le produit mentionné dans l'instruction
          * Créez un pitch entièrement nouveau pour ce produit spécifique
          * Utilisez UNIQUEMENT les garanties de ce produit: {product_guarantees}
        - Si l'utilisateur demande de "raffiner" ou "modifier" un pitch existant:
          * Modifiez le pitch précédent selon les instructions spécifiques
          * Conservez le produit original : {product}

        RÈGLES DE GÉNÉRATION:
        - Créez un texte commercial professionnel et persuasif
        - Intégrez naturellement les garanties pertinentes du produit
        - Adaptez le ton et le style aux besoins du client : {client_name}
        - Limitez le pitch à environ 180 mots
        - Mettez l'accent sur les avantages et la valeur ajoutée

        CONTEXT:
        - Client : {client_name}
        - Garanties du produit spécifique : {product_guarantees}
        - Pitch précédent (si disponible) : {previous_pitch}
        
        RÉPONDEZ UNIQUEMENT EN FORMAT JSON VALIDE, SANS TEXTE SUPPLÉMENTAIRE."""
    ),
    HumanMessagePromptTemplate.from_template(
        """Instruction de l'utilisateur: {user_input}

Format de réponse requis (JSON uniquement):
{{
  "client": "{client_name}",
  "product": "[produit identifié dans l'instruction ou produit par défaut]",
  "pitch": "[texte commercial généré ou raffiné selon l'instruction, environ 180 mots]"
}}"""
    )
])


def pitch_node(state: ChatState) -> ChatState:
    from app.data.data_utils import get_garanties
    import json
    import re
    
    messages = state.get("messages", [])
    client_name = state.get("client_name", "Client")
    user_input = state.get("user_input", "")
    current_pitch = state.get("previous_pitch", "")
    instruction = state.get("instruction", "")
    default_product = state.get("product", "")
    
    # Get all available guarantees
    all_guarantees = get_garanties()
    
    # Extract product name from user input
    extracted_product = extract_product_from_input(user_input, all_guarantees.keys())
    
    # Determine which product to use
    target_product = extracted_product if extracted_product else default_product    
    # Get guarantees for the specific product
    product_guarantees = all_guarantees.get(target_product, "Aucune garantie disponible pour ce produit")

    # Store conversation in memory
    conversation_key = f"{client_name}_{target_product}"
    if conversation_key not in memory_store:
        memory_store[conversation_key] = []
    
    # Add current user input to memory
    memory_store[conversation_key].append({
        "role": "user", 
        "content": user_input,
        "timestamp": str(__import__('datetime').datetime.now())
    })
    
    print(f"Memory key: {conversation_key}")
    print(f"Memory entries for this conversation: {len(memory_store[conversation_key])}")
    print(f"Last 3 memory entries: {memory_store[conversation_key][-3:]}")

    # Format messages for the LLM
    formatted_messages = [
        HumanMessage(content=msg["content"]) if msg["role"] == "user"
        else AIMessage(content=msg["content"])
        for msg in messages
    ]

    # Update prompt with context
    prompt = prompt_template.format_prompt(
        client_name=client_name,
        user_input=user_input,
        product=target_product,
        product_guarantees=product_guarantees,
        previous_pitch=current_pitch
    )
    test = False
    while (not test):

    # Invoke LLM
        llm_response = llm.invoke(prompt.to_messages())
        
        try:
            response_json = json.loads(llm_response)
            test = True

        except json.JSONDecodeError:
            test = False
            print(f"LLM fail: {llm_response}")

    memory_store[conversation_key].append({
        "role": "assistant", 
        "content": json.dumps(response_json, ensure_ascii=False),
        "timestamp": str(__import__('datetime').datetime.now())
    })

    new_state = state.copy()
    new_state.update({
        "messages": messages + [{"role": "assistant", "content": json.dumps(response_json, ensure_ascii=False)}],
        "client_name": client_name,
        "product": response_json.get("product", target_product),
        "guarantees": str(product_guarantees),
        "pitch": response_json.get("pitch", ""),
        "previous_pitch": current_pitch,
        "instruction": instruction
    })
    
    return new_state

def extract_product_from_input(user_input: str, available_products) -> str:
    """
    Extract product name from user input by matching against available products.
    
    Args:
        user_input (str): The user's input text
        available_products: List or set of available product names
    
    Returns:
        str: The matched product name, or empty string if no match found
    """
    user_input_upper = user_input.upper()
    
    # Look for exact matches first
    for product in available_products:
        if product.upper() in user_input_upper:
            return product
    
    for product in available_products:
        product_words = product.upper().split()
        for word in product_words:
            if len(word) >= 5 and word in user_input_upper:
                return product
    
    return ""

# Create the LangGraph chatbot
def create_chatbot():
    workflow = StateGraph(ChatState)
    workflow.add_node("pitch", pitch_node)
    workflow.add_edge(START, "pitch")
    workflow.add_edge("pitch", END)
    compiled_workflow = workflow.compile(checkpointer=memory_saver)
    
    return compiled_workflow

def get_memory_info():
    """Get current memory information for debugging"""
   
    for key, conversations in memory_store.items():
        print(f"Conversation {key}: {len(conversations)} messages")
        if conversations:
            last_msg = conversations[-1]
            print(f"  Last message: {last_msg.get('role', 'unknown')} at {last_msg.get('timestamp', 'unknown time')}")
    return memory_store

def clear_memory(conversation_key=None):
    """Clear memory for a specific conversation or all conversations"""
    if conversation_key:
        if conversation_key in memory_store:
            del memory_store[conversation_key]
    else:
        memory_store.clear()
    return memory_store