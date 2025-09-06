#Get Client Data

from datetime import date, datetime
import json
from langgraph.types import Command, interrupt
from langchain_ollama import ChatOllama
from app.Graph.GraphNodes.Responses import Info_extraction_response
from app.Graph.utils import person_type_schema
from app.Graph.GraphState.info import InfoState, InfoStateEnum
from app.Graph.GraphState.state import State
from app.services.db_service import DBService
from langchain_core.messages import HumanMessage

def GetClientData(client_ref:int)->State:
    db = DBService()
    client_data = db.get_client_profile(client_ref)
    
    state = State()
    state.infos = []
    state.lastInfo = 0
    state.profileState = False
    if not client_data:
        state.profileState = False
        ''# Or False, default as you want
    client_type = client_data.get("type_client", "").lower()
    state.person_type=client_type
    schema = person_type_schema(client_type)
    
    state.infos=[]
    for attr_name in schema:
        attr_value = client_data.get(attr_name)
        info_state = InfoState()
        info_state.attr=attr_name
        
        info_state.state=InfoStateEnum.valid if attr_value else InfoStateEnum.missing
        info_state.problem=None 
        
        state.infos.append(info_state)
        

    ''
#extract info from the user input
def Extract_info_from_user_input(state: State, model: ChatOllama):
    input = state.input
    
    ref_personne = state.infos[0]
    if ref_personne.state == InfoStateEnum.missing:
        state.lastInfo = 0
        
    info = state.infos[state.lastInfo]
    attr = info.attr
    
    schema = person_type_schema(state.person_type)
    type = schema[attr]['type']

    description = schema[attr]['description']
    if 'values' in schema[attr]:
        values = schema[attr]['values']
    else:
        values = None
    
    prompt = f"""ROLE:
You are a precise information extraction algorithm. Your sole purpose is to analyze text and return JSON.

TASK:
Extract the value for the attribute `{attr}` from the user's input. Use the schema below to guide your extraction:

**ATTRIBUTE SCHEMA:**
- **Description:** {description}
- **Required Type:** {type.__name__}
- **Allowed Values:** {values if values else 'Any valid value'}

USER'S INPUT TO ANALYZE:
"{input}"

INSTRUCTIONS:
1.  **ANALYZE:** Does the input contain information that matches the attribute's description?
2.  **VALIDATE:** If found, does the information match the required data type?
3.  **CHECK:** If the attribute has a list of `values`, the extracted data MUST be one of them.
4.  **RESPOND:** Output ONLY the JSON object with one of the following outcomes:
    -   `"valid"`: Information was found, is correct type, and matches allowed values (if any). Put the value after converting it to the type {type.__name__} in `"value"`.
    -   `"invalid"`: Information was found but is the wrong type or not an allowed value. Describe the issue in `"problem"`.
    -   `"missing"`: No relevant information was found in the input. Describe what was missing in `"problem"`.

CRITICAL: Your final answer must be ONLY the JSON object. Do not add any other text, commentary, or formatting.

JSON RESPONSE:
```json
{{"valid": "valid|invalid|missing", "problem": "The problem you identified if it exists otherwise null", "value": "extracted_value if it exists otherwise null"}}
NOW EXTRACT THE INFORMATION:"""
    
    messages = [HumanMessage(content=prompt)]
    response = model.invoke(messages)
    print(response)
    try:
        response_text = response.content.strip()
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end != 0:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
        else:
            # Set extraction result on state and ''
            state.extraction_result = {
                "valid": InfoStateEnum.invalid,
                "problem": "LLM did not return valid JSON format",
                "value": None,
                "attribute": attr
            }
            return
            
        
        valid_value = result.get('valid')
        if valid_value not in ['valid', 'invalid', 'missing']:
            state.extraction_result = {
                "valid": InfoStateEnum.invalid,
                "problem": f"Invalid 'valid' value: {valid_value}. Must be 'valid', 'invalid', or 'missing'",
                "value": None,
                "attribute": attr
            }
        else:
        
            valid_enum = InfoStateEnum(valid_value)
            
            if valid_enum == InfoStateEnum.valid:
                value = result.get('value')
                
                if value is None:
                    state.extraction_result = {
                        "valid": InfoStateEnum.invalid,
                        "problem": "LLM returned 'valid' but no value provided",
                        "value": None,
                        "attribute": attr
                    }
                    return
                
                try:
                    converted_value = None
                    
                    if type == int:
                        converted_value = int(value)
                    elif type == float:
                        converted_value = float(value)
                    elif type == str:
                        converted_value = str(value)
                    elif type == date:
                        if isinstance(value, str):
                            try:
                                converted_value = datetime.strptime(value, "%Y-%m-%d").date()
                            except ValueError:
                                state.extraction_result = {
                                    "valid": InfoStateEnum.invalid,
                                    "problem": f"Date format should be YYYY-MM-DD, got: {value}",
                                    "value": None,
                                    "attribute": attr
                                }
                                
                        else:
                            converted_value = value
                    
                    if values and converted_value not in values:
                        state.extraction_result = {
                            "valid": InfoStateEnum.invalid,
                            "problem": f"Value '{converted_value}' not in allowed values: {values}",
                            "value": None,
                            "attribute": attr
                        }
                        return
                       
                    
                    # Success case
                    state.extraction_result = {
                        "valid": InfoStateEnum.valid,
                        "problem": None,
                        "value": converted_value,
                        "attribute": attr
                    }
                    
                    
                except (ValueError, TypeError) as e:
                    state.extraction_result = {
                        "valid": InfoStateEnum.invalid,
                        "problem": f"Type conversion failed: {str(e)}. Expected {type.__name__}, got {type(value).__name__}",
                        "value": None,
                        "attribute": attr
                    }
                    
                    
            # For invalid or missing responses
            state.extraction_result = {
                "valid": valid_enum,
                "problem": result.get('problem'),
                "value": result.get('value'),
                "attribute": attr
            }
            
        
    except json.JSONDecodeError as e:
        state.extraction_result = {
            "valid": InfoStateEnum.invalid,
            "problem": f"Failed to parse LLM response as JSON: {str(e)}",
            "value": None,
            "attribute": attr
        }
        
    



    
    
    
#human_interaction
def human_feedback(state):
    print("---human_feedback---")
    feedback = interrupt("Please provide feedback:")
    return {"user_feedback": feedback}