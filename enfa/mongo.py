from pymongo import MongoClient
from django.conf import settings

_client = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client

def get_db():
    return get_client()[settings.MONGO_DB]