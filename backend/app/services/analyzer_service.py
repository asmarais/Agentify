from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from app.config import OLLAMA_MODEL, QUERY_PROMPT
from .db_service import DBService
import json

class AnalyzerService:
    def __init__(self):
        """Initialize the AnalyzerService with MongoDB and Ollama LLM."""
        self.db = DBService()
        self.llm = OllamaLLM(model=OLLAMA_MODEL)
        self.prompt = ChatPromptTemplate.from_template(QUERY_PROMPT)

    def analyze_profile(self, ref: int, question="What contracts does this client have?") -> str:
        """
        Query client data from MongoDB and use Ollama LLM to answer a question.
        
        Args:
            ref (int): Client REF_PERSONNE identifier.
            question (str): Question about the client (e.g., "What contracts does this client have?").
        
        Returns:
            str: Response from the LLM or error message if client not found.
        """
        client_data = self.db.get_client_profile(ref)
        if not client_data:
            return "Client not found"
        
        client_data_str = json.dumps(client_data, indent=2, ensure_ascii=False)
        chain = self.prompt | self.llm
        response = chain.invoke({"client_data": client_data_str, "question": question})
        return response