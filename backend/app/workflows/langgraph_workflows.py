from langgraph.graph import StateGraph, END, START
from app.agents.RecommendationModel import recommendation_node
from app.agents.PitchGenerationAgent import pitch_generation_node
from app.workflows.AgentState import AgentState


def create_workflow():
    workflow = StateGraph(AgentState)
    # Add nodes
    workflow.add_node("recommender", recommendation_node)
    workflow.add_node("pitch_generator", pitch_generation_node)
        
    # Add edges
    workflow.add_edge(START, "recommender") 
    workflow.add_edge("recommender", "pitch_generator")
    workflow.add_edge("pitch_generator", END)
    
    return workflow.compile()
