from beanie import Document, Indexed
import pymongo


class SeriesModel(Document):
    name: Indexed(str, pymongo.ASCENDING, unique=True)  # type: ignore

    class Settings:
        name = "series"
