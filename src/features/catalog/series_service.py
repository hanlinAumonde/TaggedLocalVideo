import re
import pymongo
from src.features.catalog.video import VideoModel
from src.logger import get_logger

logger = get_logger("series_service")

class SeriesService:

    async def search_by_prefix(self, keyword: str, limit: int) -> list[str]:
        """
        Return series names (derived from VideoModel.seriesName) containing `keyword`
        case-insensitively, capped at `limit`. No dictionary collection is used; this
        reads `distinct` directly off the videos collection.

        Names starting with the keyword are ranked ahead of names merely containing it,
        mirroring the prefix-then-contains ordering of `getSuggestions`. Both groups are
        sorted alphabetically, so a shrinking `limit` only ever trims the weaker matches.

        :param keyword: The substring to search for; empty means "no filter".
        :type keyword: str
        :param limit: The maximum number of series names to return.
        :type limit: int
        :return: List of series names matching the keyword.
        :rtype: list[str]
        """
        query: dict = {"seriesName": {"$ne": None}}
        if keyword:
            escaped = re.escape(keyword)
            query["seriesName"] = {"$ne": None, "$regex": escaped, "$options": "i"}

        names = await VideoModel.get_pymongo_collection().distinct("seriesName", query)
        names = sorted(n for n in names if n)
        if not keyword:
            return names[:limit]

        lowered = keyword.lower()
        prefix_matches = [n for n in names if n.lower().startswith(lowered)]
        contains_matches = [n for n in names if not n.lower().startswith(lowered)]
        return (prefix_matches + contains_matches)[:limit]

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
