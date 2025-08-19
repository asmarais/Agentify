# config.py
# backend/app/config.py
MONGO_URI = "mongodb+srv://bh_user:S9oO8WmKApiobgJ7@bh-assurance-cluster.izae38r.mongodb.net/?retryWrites=true&w=majority&appName=bh-assurance-cluster"
DB_NAME = "bh-assurance"
COLLECTION_NAME = "Clients"
OLLAMA_MODEL = "llama2"
QUERY_PROMPT = """
Vous êtes un assistant d'assurance. Voici les données d'un client :
{client_data}
Répondez à la question suivante sur ce client : {question}
Fournissez une réponse claire et concise.
"""