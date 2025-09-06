from app.workflows.AgentState import AgentState
from app.data import data_utils
import json
import os

dir = os.path.dirname(os.path.abspath(__file__))



def recommendation_node(state: AgentState) -> AgentState:
    """
    Node to generate recommendations using the model implemented in the notebook.
    Updates state["recommendations"].
    """
    if state.get("type_personne") == "Moral":
 
        file_path = os.path.join(dir, "recommendations.json")

        with open(file_path, "r", encoding="utf-8") as f:
            recommendations_json = json.load(f)
    else:
        file_path = os.path.join(dir, "personne_physique_recommendations.json")
        with open(file_path, "r", encoding="utf-8") as f:
            recommendations_json = json.load(f)

        with open(file_path, "r", encoding="utf-8") as f:
            recommendations_json = json.load(f)
    return {
        **state,
        "recommendations": recommendations_json,
        "current_agent": "recommender",
    }
