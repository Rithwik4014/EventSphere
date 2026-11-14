# scripts/init_db.py
"""
Database Initialization Script for EventSphere.
- Configures schema validators ($jsonSchema) for 'users', 'events', and 'bookings'.
- Creates unique, compound, and full-text indexes.
- Verifies collection creation, validators, and index configuration.
"""

import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import PyMongoError, OperationFailure
from app.models.schemas import USER_SCHEMA, EVENT_SCHEMA, BOOKING_SCHEMA

def load_env(filepath=".env"):
    if not os.path.exists(filepath):
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

def initialize_database():
    env_path = os.path.join(BASE_DIR, ".env")
    if not load_env(env_path):
        print("ERROR: .env file not found.")
        sys.exit(1)

    mongo_uri = os.environ.get("MONGO_URI")
    db_name = os.environ.get("DB_NAME", "eventsphere_db")

    if not mongo_uri:
        print("ERROR: MONGO_URI is missing from .env.")
        sys.exit(1)

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        print(f"Connected to MongoDB Atlas. Initializing database '{db_name}'...\n")

        # Define collection configurations
        collections_config = {
            "users": USER_SCHEMA,
            "events": EVENT_SCHEMA,
            "bookings": BOOKING_SCHEMA
        }

        existing_collections = db.list_collection_names()

        # Step 1: Create collections with $jsonSchema validation
        for col_name, schema in collections_config.items():
            if col_name not in existing_collections:
                db.create_collection(
                    col_name,
                    validator=schema,
                    validationLevel="strict",
                    validationAction="error"
                )
                print(f"[OK] Created collection '{col_name}' with JSON Schema validator.")
            else:
                # Update validator if collection already exists
                db.command({
                    "collMod": col_name,
                    "validator": schema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
                print(f"[OK] Updated JSON Schema validator for existing collection '{col_name}'.")

        # Step 2: Create Indexes
        print("\nCreating indexes...")

        # Indexes for 'users'
        db.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="idx_users_email_unique"
        )
        print("[OK] Created index 'idx_users_email_unique' on users (unique).")

        # Indexes for 'events'
        db.events.create_index(
            [("title", TEXT), ("description", TEXT), ("tags", TEXT)],
            name="idx_events_text_search"
        )
        print("[OK] Created index 'idx_events_text_search' on events (full-text).")

        db.events.create_index(
            [("category", ASCENDING), ("status", ASCENDING), ("event_date", ASCENDING)],
            name="idx_events_cat_status_date"
        )
        print("[OK] Created compound index 'idx_events_cat_status_date' on events.")

        db.events.create_index(
            [("event_date", ASCENDING)],
            name="idx_events_date"
        )
        print("[OK] Created single-field index 'idx_events_date' on events.")

        # Indexes for 'bookings'
        db.bookings.create_index(
            [("booking_code", ASCENDING)],
            unique=True,
            name="idx_bookings_code_unique"
        )
        print("[OK] Created index 'idx_bookings_code_unique' on bookings (unique).")

        db.bookings.create_index(
            [("user_id", ASCENDING), ("booking_date", DESCENDING)],
            name="idx_bookings_user_date"
        )
        print("[OK] Created compound index 'idx_bookings_user_date' on bookings.")

        db.bookings.create_index(
            [("event_id", ASCENDING), ("status", ASCENDING)],
            name="idx_bookings_event_status"
        )
        print("[OK] Created compound index 'idx_bookings_event_status' on bookings.")

        # Step 3: Verification
        print("\n" + "="*50)
        print("VERIFICATION OF DATABASE INITIALIZATION")
        print("="*50)

        # 3a. Verify Collections Exist
        current_cols = db.list_collection_names()
        expected_cols = ["users", "events", "bookings"]
        all_cols_exist = all(c in current_cols for c in expected_cols)
        print(f"Collections in '{db_name}': {current_cols}")
        print(f"All expected collections exist: {'YES' if all_cols_exist else 'NO'}")

        # 3b. Verify Schema Validators
        col_infos = {info["name"]: info.get("options", {}) for info in db.command("listCollections")["cursor"]["firstBatch"]}
        print("\nSchema Validator Status:")
        for col in expected_cols:
            opts = col_infos.get(col, {})
            has_validator = "validator" in opts and bool(opts["validator"])
            validation_level = opts.get("validationLevel", "default")
            validation_action = opts.get("validationAction", "default")
            print(f"  - {col}: Active = {has_validator} (Level: {validation_level}, Action: {validation_action})")

        # 3c. Verify Indexes
        print("\nIndex Information:")
        for col in expected_cols:
            indexes = db[col].index_information()
            print(f"  - {col} indexes ({len(indexes)} total):")
            for idx_name, idx_info in indexes.items():
                keys = idx_info.get("key", [])
                unique = idx_info.get("unique", False)
                print(f"      * {idx_name}: keys={keys}{' (UNIQUE)' if unique else ''}")

        client.close()
        print("\nDatabase initialization and verification completed successfully!")
        return True

    except OperationFailure as e:
        print(f"\nOperation Failure: {e.details if hasattr(e, 'details') else str(e)}")
        return False
    except PyMongoError as e:
        print(f"\nPyMongo Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
