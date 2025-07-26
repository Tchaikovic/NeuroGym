"""
Migration script to move from LangChain chat storage to direct MongoDB storage
This script migrates data from langchain_chat_history to the new chat_history collection
"""
import pymongo
from config import MONGODB_URI, DATABASE_NAME

def migrate_from_langchain_to_direct():
    """Migrate chat data from LangChain format to direct MongoDB format"""
    
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    # Source and destination collections
    langchain_collection = db["langchain_chat_history"]
    new_collection = db["chat_history"]
    
    print("=== Migrating from LangChain to Direct MongoDB Storage ===")
    
    try:
        # Get all LangChain chat sessions
        langchain_docs = list(langchain_collection.find({}))
        print(f"Found {len(langchain_docs)} LangChain chat sessions to migrate")
        
        migrated_count = 0
        
        for doc in langchain_docs:
            try:
                # Extract session_id (which is the user email)
                session_id = doc.get("session_id", "")
                if not session_id:
                    continue
                
                # Extract messages from LangChain format
                history = doc.get("history", [])
                messages = []
                
                for msg_doc in history:
                    # LangChain stores messages in a specific format
                    if "data" in msg_doc and "content" in msg_doc["data"]:
                        data = msg_doc["data"]
                        message_type = msg_doc.get("type", "")
                        
                        # Convert LangChain message types to Cohere format
                        if message_type == "system":
                            messages.append({
                                "role": "system",
                                "content": data["content"]
                            })
                        elif message_type == "human":
                            messages.append({
                                "role": "user", 
                                "content": data["content"]
                            })
                        elif message_type == "ai":
                            messages.append({
                                "role": "assistant",
                                "content": data["content"]
                            })
                
                # Only migrate if we have messages
                if messages:
                    # Create new document in direct format
                    new_doc = {
                        "user_email": session_id,
                        "messages": messages,
                        "migrated_from_langchain": True,
                        "updated_at": doc.get("created_at", None)
                    }
                    
                    # Insert into new collection (upsert)
                    new_collection.update_one(
                        {"user_email": session_id},
                        {"$set": new_doc},
                        upsert=True
                    )
                    
                    migrated_count += 1
                    print(f"Migrated {len(messages)} messages for user: {session_id}")
                
            except Exception as e:
                print(f"Error migrating document {doc.get('_id', 'unknown')}: {e}")
                continue
        
        print(f"\n✅ Successfully migrated {migrated_count} chat sessions")
        
        # Optionally rename the old collection as backup
        backup_name = "langchain_chat_history_backup"
        if backup_name not in db.list_collection_names():
            langchain_collection.rename(backup_name)
            print(f"📦 Renamed old collection to {backup_name}")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
    
    client.close()

def validate_migration():
    """Validate that the migration was successful"""
    
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    
    print("\n=== Validating Migration ===")
    
    # Check new collection
    new_collection = db["chat_history"]
    new_count = new_collection.count_documents({})
    print(f"New collection 'chat_history' has {new_count} documents")
    
    # Check some sample documents
    sample_docs = list(new_collection.find({}).limit(3))
    for doc in sample_docs:
        user_email = doc.get("user_email", "unknown")
        message_count = len(doc.get("messages", []))
        print(f"  User: {user_email} has {message_count} messages")
    
    client.close()

if __name__ == "__main__":
    print("NeuroGym LangChain to Direct MongoDB Migration")
    print("=" * 50)
    
    # Ask for confirmation
    confirm = input("This will migrate your chat data from LangChain to direct storage. Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        exit()
    
    # Run migration
    migrate_from_langchain_to_direct()
    
    # Validate results
    validate_migration()
    
    print("\n🎉 Migration completed successfully!")
    print("LangChain dependencies have been removed.")
