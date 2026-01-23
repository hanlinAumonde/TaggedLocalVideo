from beanie import init_beanie
from pymongo import AsyncMongoClient
from .models.Video_model import VideoModel, VideoTagModel
from src.config import MongoConfig, get_settings
from src.logger import get_logger

logger = get_logger("setup_mongo")

async def setup_mongo():
    mongo_config: MongoConfig = get_settings().mongo
    #create an async MongoDB client
    mongo_uri = "mongodb://"
    mongo_host_port = f"{mongo_config.host}:{mongo_config.port}"
    if mongo_config.username and mongo_config.password:
        mongo_uri += f"{mongo_config.username}:{mongo_config.password}@" + mongo_host_port + f"/{mongo_config.database}?authSource={mongo_config.database}"
    else:
        mongo_uri += mongo_host_port
    
    client = AsyncMongoClient(mongo_uri)

    #initialize Beanie with the client and database name
    await init_beanie(database=client.get_database(mongo_config.database), document_models=[VideoModel, VideoTagModel])
    logger.info("MongoDB setup complete")