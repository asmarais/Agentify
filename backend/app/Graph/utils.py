from app.config import profile_moral_schema,profile_physique_schema
def person_type_schema(client_type):
    schema = set()
    if client_type == "physique":
        schema = profile_physique_schema
    elif client_type == "morale":
        schema = profile_moral_schema 
    return schema