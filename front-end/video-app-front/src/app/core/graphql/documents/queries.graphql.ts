import { gql } from 'apollo-angular';

export const SEARCH_VIDEOS = gql`
  query SearchVideos($input: VideoSearchInput!) {
    SearchVideos(input: $input) {
      pagination {
        size
        totalCount
        currentPageNumber
      }
      videos {
        id
        isDir
        name
        tags {
          name
          count
        }
        author
        viewCount
        loved
        lastViewTime
        lastModifyTime
        introduction
        size
        thumbnail
      }
    }
  }
`;

export const GET_TOP_TAGS = gql`
  query GetTopTags {
    getTopTags {
      name
      count
    }
  }
`;

export const GET_VIDEO_BY_ID = gql`
  query GetVideoById($videoId: ID!) {
    getVideoById(videoId: $videoId) {
      id
      isDir
      name
      tags {
        name
        count
      }
      author
      viewCount
      loved
      lastViewTime
      lastModifyTime
      introduction
      size
      thumbnail
    }
  }
`;

export const GET_SUGGESTIONS = gql`
  query GetSuggestions($input: SuggestionInput!) {
    getSuggestions(input: $input)
  }
`;

export const BROWSE_DIRECTORY = gql`
  query BrowseDirectory($path: RelativePathInput!) {
    browseDirectory(path: $path) {
      node {
        id
        isDir
        name
        tags {
          name
          count
        }
        author
        viewCount
        loved
        lastViewTime
        lastModifyTime
        introduction
        size
        thumbnail
      }
    }
  }
`;
