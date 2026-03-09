from beanie import Document, Indexed
import pymongo


class DirMetadataModel(Document):
    path: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore
    total_size: float
    last_modified_time: float

    class Settings:
        name = "dir_metadata"
