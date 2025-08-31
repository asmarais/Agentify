from fastapi import APIRouter, HTTPException, Query
from app.workflows.langgraph_workflows import create_workflow
from app.workflows.AgentState import AgentState
from app.data.data_utils import get_garanties

router = APIRouter()
workflow = create_workflow()

@router.get("/run_workflow")
async def run_workflow(
    page: int = Query(1, ge=1, description="Current page number"),
    page_size: int = Query(5, ge=1, le=50, description="Number of clients per page")
):
    state: AgentState = {
        "recommendations": {},   
        "pitchs": [],             
        "refinements": [],
        "client_conversation": [], 
        "current_agent": "recommender",
        "garanties": get_garanties(),
        "page": page,
        "page_size": page_size
    }

    try:
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
