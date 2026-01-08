from beanie import init_beanie
#from pymongo import AsyncMongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from .models.Video_model import VideoModel, VideoTagModel
from src.config import MongoConfig, get_settings

async def setup_mongo():
    mongo_config: MongoConfig = get_settings().mongo
    #create an async MongoDB client
    mongo_uri = "mongodb://"
    if mongo_config.username and mongo_config.password:
        mongo_uri += f"{mongo_config.username}:{mongo_config.password}@"
    mogno_uri += f"{mongo_config.host}:{mongo_config.port}"
    client = AsyncIOMotorClient(mongo_uri)

    #initialize Beanie with the client and database name
    await init_beanie(database=client.video_tag_db, document_models=[VideoModel, VideoTagModel])
    print("MongoDB setup complete")