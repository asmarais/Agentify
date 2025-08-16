from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from app.config import OLLAMA_MODEL
from .db_service import DBService
from datetime import datetime

class AgentService:
    def __init__(self):
        self.llm = Ollama(model=OLLAMA_MODEL)
        self.memory = ConversationBufferMemory()
        self.conversation = ConversationChain(llm=self.llm, memory=self.memory)
        self.db = DBService()
    
    
    
    #def generate_pitch(self, profile_summary, product, canal='email'):