import { GetTopTagsQuery, GetVideoByIdQuery, RecordVideoViewMutation, SearchVideosQuery, UpdateVideoMetadataMutation } from "../../core/graphql/generated/graphql";

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