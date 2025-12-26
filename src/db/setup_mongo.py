from beanie import init_beanie
#from pymongo import AsyncMongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from .models.Video_model import VideoModel, VideoTagModel

async def setup_mongo():
    #create an async MongoDB client
    client = AsyncIOMotorClient("mongodb://localhost:27017")

    #initialize Beanie with the client and database name
    await init_beanie(database=client.video_tag_db, document_models=[VideoModel, VideoTagModel])
    print("MongoDB setup complete")