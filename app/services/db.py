# app/services/db.py
"""
MongoDB Database Connection & Utilities using PyMongo.
"""

import os
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient

_client = None

def load_env(filepath=".env"):
    """Load environment variables if not already set."""
    if not os.path.exists(filepath):
        # Check one level up (if running from subdirectories)
        alt_path = os.path.join("..", filepath)
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            return False

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")
    return True

def get_client():
    """Retrieve or initialize the PyMongo MongoClient singleton."""
    global _client
    if _client is None:
        load_env()
        mongo_uri = os.environ.get("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI is missing from environment variables.")
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    return _client

def get_db():
    """Retrieve the target MongoDB database instance."""
    client = get_client()
    db_name = os.environ.get("DB_NAME", "eventsphere_db")
    return client[db_name]

def to_object_id(val):
    """
    Safely convert a string or value to a BSON ObjectId.
    Raises ValueError with descriptive message if format is invalid.
    """
    if val is None:
        return None
    if isinstance(val, ObjectId):
        return val
    try:
        return ObjectId(str(val))
    except (InvalidId, TypeError) as e:
        raise ValueError(f"Invalid ObjectId format: '{val}'. Expected 24-character hex string.") from e

def close_client():
    """Close the MongoDB client connection if open."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
