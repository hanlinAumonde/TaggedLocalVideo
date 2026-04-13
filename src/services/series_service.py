import re
from functools import lru_cache

import pymongo
from pymongo import UpdateOne

from src.db.models.Series_model import SeriesModel
from src.db.models.Video_model import VideoModel
from src.logger import get_logger

logger = get_logger("series_service")


class SeriesService:

    async def search_by_prefix(self, prefix: str, limit: int) -> list[str]:
        """
        Return series names whose prefix matches (case-insensitive), capped at `limit`.

        :param prefix: The prefix to search for.
        :type prefix: str
        :param limit: The maximum number of series names to return.
        :type limit: int
        :return: List of series names matching the prefix.
        :rtype: list[str]
        """
        if not prefix:
            docs = await SeriesModel.find_all().sort([("name", pymongo.ASCENDING)]).limit(limit).to_list()
            return [d.name for d in docs]

        escaped = re.escape(prefix)
        docs = (
            await SeriesModel.find({"name": {"$regex": f"^{escaped}", "$options": "i"}})
            .sort([("name", pymongo.ASCENDING)])
            .limit(limit)
            .to_list()
        )
        return [d.name for d in docs]

    async def get_videos_in_series(self, name: str, valid_categories: list[str]) -> list[VideoModel]:
        """
        Return videos belonging to a series, sorted by seriesOrder ascending (nulls last).

        :param name: The name of the series to retrieve videos for.
        :type name: str
        :param valid_categories: List of valid categories to filter videos.
        :type valid_categories: list[str]
        :return: List of videos in the specified series.
        :rtype: list[VideoModel]
        """
        if not name or not valid_categories:
            return []
        return (
            await VideoModel.find(
                {"seriesName": name, "category": {"$in": valid_categories}}
            )
            .sort([("seriesOrder", pymongo.ASCENDING), ("name", pymongo.ASCENDING)])
            .to_list()
        )

    async def ensure_exists(self, name: str) -> None:
        """
        Upsert a series name into the dictionary collection. No-op if already present.

        :param name: The name of the series to upsert.
        :type name: str
        """
        if not name:
            return
        await SeriesModel.get_pymongo_collection().update_one(
            {"name": name},
            {"$setOnInsert": {"name": name}},
            upsert=True,
        )

    async def ensure_many_exist(self, names: list[str]) -> None:
        """
        Batch upsert multiple series names.

        :param names: List of series names to upsert.
        :type names: list[str]
        """
        unique = {n for n in names if n}
        if not unique:
            return
        operations = [
            UpdateOne({"name": n}, {"$setOnInsert": {"name": n}}, upsert=True)
            for n in unique
        ]
        await SeriesModel.get_pymongo_collection().bulk_write(operations)


@lru_cache
def get_series_service() -> SeriesService:
    return SeriesService()
