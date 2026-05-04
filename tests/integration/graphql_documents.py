# -----------------------------------------------------------------------
# GraphQL documents
# -----------------------------------------------------------------------

BROWSE_DIRECTORY = """
query BrowseDirectory($input: RelativePathInput!) {
  browseDirectory(input: $input) {
    node { id name isDir size lastModifyTime duration author tags { name count } }
  }
}
"""

SEARCH_VIDEOS = """
query SearchVideos($input: VideoSearchInput!) {
  SearchVideos(input: $input) {
    pagination { size totalCount currentPageNumber }
    videos { id name author loved duration tags { name count } seriesName seriesOrder }
  }
}
"""

GET_VIDEO_BY_ID = """
query GetVideoById($videoId: ID!) {
  getVideoById(videoId: $videoId) {
    id name author loved introduction tags { name count }
    viewCount lastViewTime duration seriesName seriesOrder
  }
}
"""

UPDATE_VIDEO_METADATA = """
mutation UpdateVideoMetadata($input: UpdateVideoMetadataInput!) {
  updateVideoMetadata(input: $input) {
    success
    video { id name author loved introduction tags { name count } seriesName seriesOrder }
  }
}
"""

RECORD_VIDEO_VIEW = """
mutation RecordVideoView($videoId: ID!) {
  recordVideoView(videoId: $videoId) {
    success
    video { id viewCount lastViewTime }
  }
}
"""

DELETE_VIDEO = """
mutation DeleteVideo($videoId: ID!) {
  deleteVideo(videoId: $videoId) {
    success
    video { id }
  }
}
"""

GET_TOP_TAGS = """
query GetTopTags {
  getTopTags { name count }
}
"""

GET_SUGGESTIONS = """
query GetSuggestions($input: SuggestionInput!) {
  getSuggestions(input: $input)
}
"""

GET_DIRECTORY_METADATA = """
query GetDirectoryMetadata($input: RelativePathInput!) {
  getDirectoryMetadata(input: $input) {
    totalSize
    lastModifiedTime
  }
}
"""

SEARCH_SERIES_BY_PREFIX = """
query SearchSeries($prefix: String!, $limit: Int!) {
  searchSeriesByPrefix(prefix: $prefix, limit: $limit)
}
"""

GET_SERIES_VIDEOS = """
query GetSeriesVideos($name: String!) {
  getSeriesVideos(name: $name) { id name seriesName seriesOrder }
}
"""

BATCH_UPDATE_SUBSCRIPTION = """
subscription BatchUpdate($input: VideosBatchOperationInput!) {
  batchUpdateSubscription(input: $input) {
    status
    result { resultType message }
  }
}
"""

BATCH_DELETE_SUBSCRIPTION = """
subscription BatchDelete($input: VideosBatchOperationInput!) {
  batchDeleteSubscription(input: $input) {
    status
    result { resultType message }
  }
}
"""