import { BatchUpdateVideoTagsMutation, BrowseDirectoryQuery, DeleteVideoMutation, GetTopTagsQuery, GetVideoByIdQuery, RecordVideoViewMutation, SearchVideosQuery, UpdateVideoMetadataMutation } from "../../core/graphql/generated/graphql";

export interface ResultState<T> {
    loading: boolean;
    error: string | null
    data: T | null;
}

export type VideoDetail = GetVideoByIdQuery['getVideoById'];

export type GetTopTagsDetail = GetTopTagsQuery['getTopTags'];

export type SearchVideosDetail = SearchVideosQuery['SearchVideos'];
export type SearchedVideo = SearchVideosQuery['SearchVideos']['videos'][0];

export type VideoMutationDetail = UpdateVideoMetadataMutation['updateVideoMetadata'];

export type VideoRecordViewDetail = RecordVideoViewMutation['recordVideoView'];

export type BrowseDirectoryDetail = BrowseDirectoryQuery['browseDirectory'];
export type FileBrowseNode = BrowseDirectoryQuery['browseDirectory'][0];
export type BrowsedVideo = BrowseDirectoryQuery['browseDirectory'][0]['node'];

export type DeleteVideoDetail = DeleteVideoMutation['deleteVideo'];

export type BatchUpdateTagsDetail = BatchUpdateVideoTagsMutation['batchUpdateVideoTags'];