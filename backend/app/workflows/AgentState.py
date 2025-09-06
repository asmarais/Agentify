from typing import TypedDict
from typing import TypedDict, Dict, List, Any


class AgentState(TypedDict):
    recommendations: Dict[str, Any]
    pitchs: Dict[str, Any] 
    refinements: List[Any]
    client_conversation: List[Any]
    current_agent: str
    garanties: Dict[str, str]