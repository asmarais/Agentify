from typing import List, Optional, Dict
from pydantic import BaseModel
from app.Graph.GraphState.info import InfoState


class State(BaseModel):
    infos: Optional[List[InfoState]] = None
    lastInfo: Optional[int] = 0
    profileState: Optional[bool] = False
    person_type:Optional[str]="physique"
    input:Optional[str]
    extraction_result: Optional[Dict] = None  # Add this field
    