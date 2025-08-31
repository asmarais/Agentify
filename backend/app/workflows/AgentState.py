from typing import TypedDict
from app.data.data_utils import get_garanties


class AgentState(TypedDict):
    recommendations: dict
    pitchs: dict
    refinements: list
    client_conversation: list
    current_agent: str
    garanties: dict[str, str]
    page: int
    page_size: int