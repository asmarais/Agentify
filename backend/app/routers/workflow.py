from typing import TypedDict
from unittest import result
from fastapi import APIRouter, HTTPException, Query
from typing import TypedDict, List, Optional

from pydantic import BaseModel
from backend import app
from backend.app.workflows.pitch_workflows import create_workflow
from backend.app.workflows.Reffinment_workflow import create_chatbot
from app.workflows.AgentState import AgentState
from app.workflows.ChatState import ChatState
from app.data.data_utils import get_garanties

router = APIRouter()
memory_store = {}
class PitchRequest(BaseModel):
    client_name: str
    product: str
    user_input: str
    refinement_type: Optional[str] = None

@router.get("/run_workflow")
async def run_workflow(
    page: int = Query(1, ge=1, description="Current page number"),
    page_size: int = Query(5, ge=1, le=50, description="Number of clients per page"),
    type_personne : str = "Moral"
):
    state: AgentState = {
        "recommendations": {},   
        "pitchs": [],             
        "refinements": [],
        "client_conversation": [], 
        "current_agent": "recommender",
        "garanties": get_garanties(),
        "page": page,
        "page_size": page_size,
        "type_personne" : type_personne
    }

    try:
        workflow = create_workflow()
        final_state = await workflow.ainvoke(state)

        return {
            "page": final_state.get("page", page),
            "page_size": final_state.get("page_size", page_size),
            "total_clients": final_state.get("total_clients", 0),
            "total_pages": final_state.get("total_pages", 1),
            "pitchs": final_state.get("pitchs", [])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@router.post("/run_refinement")
async def generate_pitch(request: PitchRequest):
    try:
        guarantees = get_garanties()
        
        client_key = f"{request.client_name}_{request.product}"
        previous_pitch = memory_store.get(client_key, "")
        
        print(f"Previous pitch found: {len(previous_pitch)} characters")
        
        state: ChatState = {
            "messages": [{"role": "user", "content": request.user_input}],
            "client_name": request.client_name,
            "user_input": request.user_input,
            "previous_pitch": previous_pitch,
            "instruction": request.user_input,
            "product": request.product,
            "guarantees": str(guarantees.get(request.product, "")),
            "pitch": ""
        }
        
        print(f"Initial state created with {len(state['messages'])} messages")
        
        chatbot = create_chatbot()
        
        thread_config = {"configurable": {"thread_id": client_key}}
        
        print(f"Invoking chatbot with thread_id: {client_key}")
        result = await chatbot.ainvoke(state, config=thread_config)
        
        print(f"Chatbot result received with {len(result.get('messages', []))} messages")
        
        pitch_content = result.get("pitch", "")
        memory_store[client_key] = pitch_content
        
        return result
    
    except Exception as e:
        print(f"Error in workflow router: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chatbot execution failed: {str(e)}")

# Add endpoint to get memory info for debugging
@router.get("/memory_info")
async def get_memory_debug():
    """Get current memory information for debugging"""
    try:
        from backend.app.workflows.Reffinment_workflow import get_memory_info
        memory_info = get_memory_info()
        return {
            "router_memory_store": memory_store,
            "workflow_memory_store": memory_info,
            "total_conversations": len(memory_store)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory info: {str(e)}")

# Add endpoint to clear memory for debugging
@router.delete("/clear_memory/{conversation_key}")
async def clear_conversation_memory(conversation_key: str):
    """Clear memory for a specific conversation"""
    try:
        from backend.app.workflows.Reffinment_workflow import clear_memory
        if conversation_key in memory_store:
            del memory_store[conversation_key]
        clear_memory(conversation_key)
        return {"message": f"Cleared memory for conversation: {conversation_key}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {str(e)}")
    
