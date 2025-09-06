from enum import Enum
from typing import Optional
from pydantic import BaseModel
class InfoStateEnum(Enum):
    invalid = "invalid"
    valid = "valid"
    missing = "missing"
class InfoState(BaseModel):
    # The email being processed
    attr: Optional[str] = None
    #type: Optional[object] = None # Use str for JSON serialization
    
    state: Optional[InfoStateEnum] = InfoStateEnum.missing
    problem: Optional[str] = None
    

