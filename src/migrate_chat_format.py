"""
Migration script to update existing chat histories to Cohere API v2 format
This script converts old message formats to use 'content' field consistently
"""
import pymongo
from config import MONGODB_URI, DATABASE_NAME

def migrate_chat_history():
    """Migrate existing chat histories to use consistent 'content' field"""
    
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    # Collections to check
    collections_to_migrate = [
        "chats",
        "chat_history"  # New direct MongoDB collection
    ]
    
    for collection_name in collections_to_migrate:
        try:
            collection = db[collection_name]
            print(f"\n=== Migrating {collection_name} ===")
            
            # Find documents that might need migration
            cursor = collection.find({})
            migrated_count = 0
            
            for doc in cursor:
                updated = False
                
                # Handle different document structures
                if collection_name == "chats" and "messages" in doc:
                    # Standard chats collection format
                    for message in doc["messages"]:
                        if "message" in message and "content" not in message:
                            # Migrate 'message' field to 'content'
                            message["content"] = message.pop("message")
                            updated = True
                elif collection_name == "chat_history":
                    # New direct MongoDB format - check message array
                    if "messages" in doc:
                        for message in doc["messages"]:
                            if "message" in message and "content" not in message:
                                # Migrate 'message' field to 'content'
                                message["content"] = message.pop("message")
                                updated = True
                
                # Update the document if changes were made
                if updated:
                    collection.replace_one({"_id": doc["_id"]}, doc)
                    migrated_count += 1
            
            print(f"Migrated {migrated_count} documents in {collection_name}")
            
        except Exception as e:
            print(f"Error migrating {collection_name}: {e}")
    
    client.close()
    print("\n=== Migration completed ===")

def validate_migration():
    """Validate that the migration was successful"""
    
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    print("\n=== Validating migration ===")
    
    # Check chats collection
    chats_collection = db["chats"]
    problem_docs = list(chats_collection.find({
        "messages": {
            "$elemMatch": {
                "message": {"$exists": True},
                "content": {"$exists": False}
            }
        }
    }))
    
    if problem_docs:
        print(f"⚠️  Found {len(problem_docs)} documents still using 'message' field in chats collection")
    else:
        print("✅ All chat documents use 'content' field correctly")
    
    client.close()

if __name__ == "__main__":
    print("NeuroGym Chat Format Migration")
    print("=" * 40)
    
    # Ask for confirmation
    confirm = input("This will update your chat history format. Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        exit()
    
    # Run migration
    migrate_chat_history()
    
    # Validate results
    validate_migration()
    
    print("\n✅ Migration completed successfully!")
    print("You can now run the app without conversion functions.")
