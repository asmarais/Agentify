from pymongo import MongoClient, ASCENDING
from app.config import MONGO_URI, DB_NAME

class DBService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.col = self.db["Clients"]
        self.col.create_index([("REF_PERSONNE", ASCENDING)], name="uniq_ref_personne", unique=True)

    @staticmethod
    def _normalize_ref(ref):
        return float(ref)

    def get_client_profile(self, ref, projection=None):
        if projection is None:
            projection = {"_id": 0}
        key = self._normalize_ref(ref)
        doc = self.col.find_one({"REF_PERSONNE": key}, projection)
        if doc is None:
            doc = self.col.find_one({"REF_PERSONNE": str(int(key))}, projection)
        return doc
