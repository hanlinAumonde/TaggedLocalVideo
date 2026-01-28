import { gql } from 'apollo-angular';

export const UPDATE_VIDEO_METADATA = gql`
  mutation UpdateVideoMetadata($input: UpdateVideoMetadataInput!) {
    updateVideoMetadata(input: $input) {
      success
      video {
        id
        name
        tags {
          name
        }
        author
        loved
        introduction
      }
    }
  }
`;

export const BATCH_UPDATE_VIDEOS = gql`
  mutation BatchUpdateVideos($input: VideosBatchOperationInput!) {
    batchUpdate(input: $input) {
      resultType
    }
  }
`;

export const RECORD_VIDEO_VIEW = gql`
  mutation RecordVideoView($videoId: ID!) {
    recordVideoView(videoId: $videoId) {
      success
      video {
        id
        viewCount
        lastViewTime
      }
    }
  }
`;

export const DELETE_VIDEO = gql`
  mutation DeleteVideo($videoId: ID!) {
    deleteVideo(videoId: $videoId) {
      success
      video {
        id
      }
    }
  }
`;

export const BATCH_UPDATE_DIRECTORY = gql`
  mutation BatchUpdateDirectory($input: DirectoryVideosBatchOperationInput!) {
    batchUpdateDirectory(input: $input) {
      resultType
    }
  }
`;