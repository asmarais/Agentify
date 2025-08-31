from app.workflows.AgentState import AgentState
from app.data import data_utils
import json
import os

dir = os.path.dirname(os.path.abspath(__file__))
 
file_path = os.path.join(dir, "recommendations.json")

with open(file_path, "r", encoding="utf-8") as f:
    recommendations_json = json.load(f)


def recommendation_node(state: AgentState) -> AgentState:
    """
    Node to generate recommendations using the model implemented in the notebook.
    Updates state["recommendations"].
    """
    # load client_data
    client_data = data_utils.load_excel_data("app/data/client_data.xlsx")

    #execute the model

    """
    recommendations_json = {
        "clients": [
            {
                "REF_PERSONNE": "PP-0001",
                "type": "physique",
                "name": "Ali Ben Salah",
                "age": 54,
                "profession": "Cadre Supérieur",
                "ville": "Tunis",
                "gouvernorat": "Tunis",
                "email": "ali.ben.salah@example.com",
                "numero_de_tel": "12345678",
                "current_products": [
                    {"product": "AUTOMOBILE", "expiration": True},
                    {"product": "Incendie", "expiration": False}
                ],
                "top_recommendations": [
                    {"rank": 1, "product": "R.C PARAMEDICALE", "final_score": 0.78}
                ]
            },
            {
                "REF_PERSONNE": "PM-1007",
                "type": "morale",
                "RAISON_SOCIALE": "Tech Solutions SARL",
                "matricule_fiscale": "MF1234567",
                "LIB_SECTEUR_ACTIVITE": "Technologie",
                "LIB_ACTIVITE": "SERVICES INFORMATIQUES",
                "current_products": ["AUTOMOBILE FLOTTE", "MULTIRISQUE BUREAUX"],
                "top_recommendations": [
                    {"rank": 1, "product": "RESPONSABILITE CIVILE", "final_score": 0.78}
                ]
            }
        ]
    }
    """

    # Update the workflow state
    return {
        **state,
        "recommendations": recommendations_json,
        "current_agent": "recommender"
    }
