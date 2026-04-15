import re
from functools import lru_cache

import pymongo

from src.db.models.Video_model import VideoModel
from src.logger import get_logger

logger = get_logger("series_service")


class SeriesService:

    async def search_by_prefix(self, prefix: str, limit: int) -> list[str]:
        """
        Return series names (derived from VideoModel.seriesName) whose prefix matches
        case-insensitively, capped at `limit`. No dictionary collection is used; this
        reads `distinct` directly off the videos collection.

        :param prefix: The prefix to search for.
        :type prefix: str
        :param limit: The maximum number of series names to return.
        :type limit: int
        :return: List of series names matching the prefix.
        :rtype: list[str]
        """
        query: dict = {"seriesName": {"$ne": None}}
        if prefix:
            escaped = re.escape(prefix)
            query["seriesName"] = {"$regex": f"^{escaped}", "$options": "i"}

        names = await VideoModel.get_pymongo_collection().distinct("seriesName", query)
        names = [n for n in names if n]
        names.sort()
        return names[:limit]

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


@lru_cache
def get_series_service() -> SeriesService:
    return SeriesService()
