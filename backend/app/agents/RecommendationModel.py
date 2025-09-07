import math
from app.workflows.AgentState import AgentState
from app.data import data_utils
import json
import os

from backend.app.models.Predictions.recommendation_model import generate_recommendations, get_data

dir = os.path.dirname(os.path.abspath(__file__))



def recommendation_node(state: AgentState) -> AgentState:
    """
    Node to generate recommendations using the model implemented in the notebook.
    Updates state["recommendations"].
    """
    page = state.get("page", 1)
    page_size = state.get("page_size", 5)
    if state.get("type_personne") == "Moral":
        page_clients = recommendations.get("clients", [])

        total_pages = max(1, math.ceil(total_clients / page_size))

    else:
        
        start_idx = (page - 1) * page_size
        total_clients,df= get_data()
        print('total clients', total_clients)
        end_idx = min(start_idx + page_size, total_clients)

        recommendations = generate_recommendations(start_idx, end_idx, df)
        page_clients = recommendations.get("clients", [])

        total_pages = max(1, math.ceil(total_clients / page_size))
        
    return {
        **state,
        "recommendations": page_clients,
        "current_agent": "recommender",
        "total_pages": total_pages,
    }
