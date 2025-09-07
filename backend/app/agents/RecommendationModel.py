import math
from app.workflows.AgentState import AgentState
from app.data import data_utils
import os

from backend.app.models.Predictions.recommendation_model import generate_recommendations, get_data
from backend.app.models.Predictions.moralexecution import generate_moral_recommendations


def recommendation_node(state: AgentState) -> AgentState:
    """
    Node to generate recommendations using the model.
    Updates state["recommendations"] with a paginated slice.
    """
    page = state.get("page", 1)
    page_size = state.get("page_size", 5)

    # Load dataset once (works for both physical and moral)
    total_clients, df = get_data()
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_clients)

    # Generate recommendations depending on type of client
    if state.get("type_personne") == "Moral":
        # Call with proper parameters for moral recommendations
        recommendations = generate_moral_recommendations(
            start=start_idx,
            end=end_idx
        )
    elif state.get("type_personne") == "Physique":
        recommendations = generate_recommendations(start_idx,end_idx, df)

    # Normalize recommendations (handle dict vs list)
    if isinstance(recommendations, dict):
        page_clients = recommendations.get("clients", [])
    elif isinstance(recommendations, list):
        page_clients = recommendations
    else:
        page_clients = []

    # Calculate total pages
    total_pages = max(1, math.ceil(total_clients / page_size))

    return {
        **state,
        "recommendations": page_clients,
        "current_agent": "recommender",
        "total_pages": total_pages,
    }
