from typing import TypedDict

class AgentState(TypedDict):
    recommendations: dict
    pitchs: dict
    refinements: list
    client_conversation: list
    current_agent: str
    garanties: dict[str, str]
    page: int
    page_size: int