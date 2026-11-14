import os
import re
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError, OperationFailure, ServerSelectionTimeoutError

def load_env_file(filepath=".env"):
    if not os.path.exists(filepath):
        return False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip("'\"")
    return True

def sanitize_message(msg):
    return re.sub(r'mongodb(\+srv)?://[^@]+@', 'mongodb+srv://<REDACTED_CREDENTIALS>@', msg)

def test_connection():
    load_env_file()
    mongo_uri = os.environ.get("MONGO_URI", "")
    db_name = os.environ.get("DB_NAME", "eventsphere_db")

    # Try standard URI
    print("Testing connection to MongoDB Atlas...")
    for auth_source in [None, "admin", db_name]:
        try:
            kwargs = {"serverSelectionTimeoutMS": 5000}
            if auth_source:
                kwargs["authSource"] = auth_source
            client = MongoClient(mongo_uri, **kwargs)
            client.admin.command("ping")
            db = client[db_name]
            cols = db.list_collection_names()
            print("SUCCESS: Connected to MongoDB Atlas cluster successfully!")
            if auth_source:
                print(f"Auth source used: {auth_source}")
            print(f"Database: '{db_name}'")
            print(f"Collections: {cols}")
            client.close()
            return True
        except OperationFailure as e:
            last_err = e
        except Exception as e:
            last_err = e

    print("FAIL: MongoDB Operation / Authentication failure.")
    print(f"Details: {sanitize_message(str(last_err))}")
    print("Explanation: The Atlas cluster responded, but rejected the credentials provided ('bad auth : authentication failed').")
    return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
