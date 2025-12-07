import datetime
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME


_client: AsyncIOMotorClient = None
_collection = None


async def init_db():
    global _client, _collection

    # ===== FIX FOR RENDER + ATLAS TLS ERROR =====
    _client = AsyncIOMotorClient(
        MONGO_URI,
        tls=True,                              # Force encrypted connection
        tlsAllowInvalidCertificates=True,      # Bypass SSL handshake problem
        retryWrites=True,                      # Safe retries
        serverSelectionTimeoutMS=30000,        # 30s fail tolerance
    )
    # ===========================================

    db = _client[MONGO_DB_NAME]
    _collection = db[MONGO_COLLECTION_NAME]


async def close_db():
    global _client
    if _client:
        _client.close()


def get_collection():
    if _collection is None:
        raise RuntimeError("DB not initialized! Call init_db() first.")
    return _collection


# ---------------- CRUD Helpers ---------------- #

async def add_tracking(user_id: int, chat_id: int, product_url: str, size: str, initial_status: str):
    col = get_collection()
    doc = {
        "user_id": user_id,
        "chat_id": chat_id,
        "product_url": product_url,
        "size": size,
        "last_status": initial_status,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    }
    result = await col.insert_one(doc)
    return str(result.inserted_id)


async def get_user_trackings(user_id: int) -> List[dict]:
    col = get_collection()
    cursor = col.find({"user_id": user_id}).sort("created_at", 1)
    return [doc async for doc in cursor]


async def delete_user_tracking_by_index(user_id: int, index: int) -> bool:
    items = await get_user_trackings(user_id)
    if index < 1 or index > len(items):
        return False

    target = items[index - 1]
    col = get_collection()
    await col.delete_one({"_id": target["_id"]})
    return True


async def get_all_trackings() -> List[dict]:
    col = get_collection()
    cursor = col.find({})
    return [doc async for doc in cursor]


async def update_tracking_status(doc_id, new_status: str):
    col = get_collection()
    await col.update_one(
        {"_id": doc_id},
        {"$set": {"last_status": new_status, "updated_at": datetime.datetime.utcnow()}}
    )
