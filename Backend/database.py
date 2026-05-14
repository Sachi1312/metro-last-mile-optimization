# ============================================================
# database.py
# MongoDB connection for FastAPI backend
# ============================================================

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("DB_NAME", "metropt")

_client = None
_db     = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        _db     = _client[DB_NAME]
    return _db