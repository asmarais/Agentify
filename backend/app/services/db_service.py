from pymongo import MongoClient
from app.config import MONGO_URI, DB_NAME

class DBService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]

    def get_client_profile(self, ref):
        return self.db.clients.find_one({"_id": ref})