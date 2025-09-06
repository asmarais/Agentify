from typing import Optional
from pydantic import BaseModel

from app.Graph.GraphState.info import InfoStateEnum

class Info_extraction_response(BaseModel):
    valid:Optional[InfoStateEnum] 
    problem:Optional[str] 
    value:Optional[object]