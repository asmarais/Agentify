from typing import List, Optional, TypedDict


class ChatState(TypedDict):
    messages: List[dict]
    client_name: Optional[str]
    user_input: Optional[str]
    pitch: Optional[str]
    previous_pitch: Optional[str]
    instruction: str
    product: Optional[str]
    guarantees: Optional[str]