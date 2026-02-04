import { gql } from 'apollo-angular';
import { Injectable } from '@angular/core';
import * as Apollo from 'apollo-angular';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
};

export enum BatchResultType {
  Failure = 'Failure',
  PartialSuccess = 'PartialSuccess',
  Success = 'Success'
}

export type DirectoryMetadataResult = {
  __typename?: 'DirectoryMetadataResult';
  lastModifiedTime: Scalars['Float']['output'];
  totalSize: Scalars['Float']['output'];
};

export type DirectoryVideosBatchOperationInput = {
  author?: InputMaybe<Scalars['String']['input']>;
  relativePath: RelativePathInput;
  tagsOperation?: InputMaybe<TagsOperationMappingInput>;
};

export type FileBrowseNode = {
  __typename?: 'FileBrowseNode';
  node: Video;
};

export type Mutation = {
  __typename?: 'Mutation';
  batchUpdate: VideosBatchOperationResult;
  batchUpdateDirectory: VideosBatchOperationResult;
  deleteVideo: VideoMutationResult;
  recordVideoView: VideoMutationResult;
  updateVideoMetadata: VideoMutationResult;
};


export type MutationBatchUpdateArgs = {
  input: VideosBatchOperationInput;
};


export type MutationBatchUpdateDirectoryArgs = {
  input: DirectoryVideosBatchOperationInput;
};


export type MutationDeleteVideoArgs = {
  videoId: Scalars['ID']['input'];
};


export type MutationRecordVideoViewArgs = {
  videoId: Scalars['ID']['input'];
};


export type MutationUpdateVideoMetadataArgs = {
  input: UpdateVideoMetadataInput;
};

export type Pagination = {
  __typename?: 'Pagination';
  currentPageNumber: Scalars['Int']['output'];
  size: Scalars['Int']['output'];
  totalCount: Scalars['Int']['output'];
};

export type Query = {
  __typename?: 'Query';
  SearchVideos: VideoSearchResult;
  browseDirectory: Array<FileBrowseNode>;
  getDirectoryMetadata: DirectoryMetadataResult;
  getSuggestions: Array<Scalars['String']['output']>;
  getTopTags: Array<VideoTag>;
  getVideoById: Video;
};


export type QuerySearchVideosArgs = {
  input: VideoSearchInput;
};


export type QueryBrowseDirectoryArgs = {
  path: RelativePathInput;
};


export type QueryGetDirectoryMetadataArgs = {
  path: RelativePathInput;
};


export type QueryGetSuggestionsArgs = {
  input: SuggestionInput;
};


export type QueryGetVideoByIdArgs = {
  videoId: Scalars['ID']['input'];
};

export type RelativePathInput = {
  parsedPath?: InputMaybe<Array<Scalars['String']['input']>>;
  refreshFlag?: Scalars['Boolean']['input'];
  relativePath?: InputMaybe<Scalars['String']['input']>;
};

export enum SearchField {
  Author = 'Author',
  Name = 'Name',
  Tag = 'Tag'
}

export enum SearchFrom {
  FrontalPage = 'FrontalPage',
  SearchPage = 'SearchPage'
}

export type SerachKeyword = {
  keyWord?: InputMaybe<Scalars['String']['input']>;
};

export type SuggestionInput = {
  keyword: SerachKeyword;
  suggestionType: SearchField;
};

export type TagsOperationMappingInput = {
  append: Scalars['Boolean']['input'];
  tags: Array<Scalars['String']['input']>;
};

export type UpdateVideoMetadataInput = {
  author?: InputMaybe<Scalars['String']['input']>;
  introduction?: InputMaybe<Scalars['String']['input']>;
  loved?: InputMaybe<Scalars['Boolean']['input']>;
  name?: InputMaybe<Scalars['String']['input']>;
  tags: Array<Scalars['String']['input']>;
  videoId: Scalars['String']['input'];
};

export type Video = {
  __typename?: 'Video';
  author: Scalars['String']['output'];
  duration: Scalars['Float']['output'];
  id: Scalars['ID']['output'];
  introduction: Scalars['String']['output'];
  isDir: Scalars['Boolean']['output'];
  lastModifyTime: Scalars['Float']['output'];
  lastViewTime: Scalars['Float']['output'];
  loved: Scalars['Boolean']['output'];
  name: Scalars['String']['output'];
  size: Scalars['Float']['output'];
  tags: Array<VideoTag>;
  thumbnail?: Maybe<Scalars['String']['output']>;
  viewCount: Scalars['Int']['output'];
};

export type VideoMutationResult = {
  __typename?: 'VideoMutationResult';
  success: Scalars['Boolean']['output'];
  video?: Maybe<Video>;
};

export type VideoSearchInput = {
  author: SerachKeyword;
  currentPageNumber?: InputMaybe<Scalars['Int']['input']>;
  fromPage: SearchFrom;
  sortBy: VideoSortOption;
  tags: Array<Scalars['String']['input']>;
  titleKeyword: SerachKeyword;
};

export type VideoSearchResult = {
  __typename?: 'VideoSearchResult';
  pagination: Pagination;
  videos: Array<Video>;
};

export enum VideoSortOption {
  Latest = 'Latest',
  Longest = 'Longest',
  Loved = 'Loved',
  MostViewed = 'MostViewed'
}

export type VideoTag = {
  __typename?: 'VideoTag';
  count: Scalars['Int']['output'];
  name: Scalars['String']['output'];
};

export type VideosBatchOperationInput = {
  author?: InputMaybe<Scalars['String']['input']>;
  tagsOperation?: InputMaybe<TagsOperationMappingInput>;
  videoIds: Array<Scalars['String']['input']>;
};

export type VideosBatchOperationResult = {
  __typename?: 'VideosBatchOperationResult';
  resultType: BatchResultType;
};

export type UpdateVideoMetadataMutationVariables = Exact<{
  input: UpdateVideoMetadataInput;
}>;


export type UpdateVideoMetadataMutation = { __typename?: 'Mutation', updateVideoMetadata: { __typename?: 'VideoMutationResult', success: boolean, video?: { __typename?: 'Video', id: string, name: string, author: string, loved: boolean, introduction: string, tags: Array<{ __typename?: 'VideoTag', name: string }> } | null } };

export type BatchUpdateVideosMutationVariables = Exact<{
  input: VideosBatchOperationInput;
}>;


export type BatchUpdateVideosMutation = { __typename?: 'Mutation', batchUpdate: { __typename?: 'VideosBatchOperationResult', resultType: BatchResultType } };

export type RecordVideoViewMutationVariables = Exact<{
  videoId: Scalars['ID']['input'];
}>;


export type RecordVideoViewMutation = { __typename?: 'Mutation', recordVideoView: { __typename?: 'VideoMutationResult', success: boolean, video?: { __typename?: 'Video', id: string, viewCount: number, lastViewTime: number } | null } };

export type DeleteVideoMutationVariables = Exact<{
  videoId: Scalars['ID']['input'];
}>;


export type DeleteVideoMutation = { __typename?: 'Mutation', deleteVideo: { __typename?: 'VideoMutationResult', success: boolean, video?: { __typename?: 'Video', id: string } | null } };

export type BatchUpdateDirectoryMutationVariables = Exact<{
  input: DirectoryVideosBatchOperationInput;
}>;


export type BatchUpdateDirectoryMutation = { __typename?: 'Mutation', batchUpdateDirectory: { __typename?: 'VideosBatchOperationResult', resultType: BatchResultType } };

export type SearchVideosQueryVariables = Exact<{
  input: VideoSearchInput;
}>;


export type SearchVideosQuery = { __typename?: 'Query', SearchVideos: { __typename?: 'VideoSearchResult', pagination: { __typename?: 'Pagination', size: number, totalCount: number, currentPageNumber: number }, videos: Array<{ __typename?: 'Video', id: string, name: string, author: string, viewCount: number, loved: boolean, lastViewTime: number, lastModifyTime: number, thumbnail?: string | null, duration: number }> } };

export type GetTopTagsQueryVariables = Exact<{ [key: string]: never; }>;


export type GetTopTagsQuery = { __typename?: 'Query', getTopTags: Array<{ __typename?: 'VideoTag', name: string, count: number }> };

export type GetTopTagsAsSuggestionQueryVariables = Exact<{ [key: string]: never; }>;


export type GetTopTagsAsSuggestionQuery = { __typename?: 'Query', getTopTags: Array<{ __typename?: 'VideoTag', name: string }> };

export type GetVideoByIdQueryVariables = Exact<{
  videoId: Scalars['ID']['input'];
}>;


export type GetVideoByIdQuery = { __typename?: 'Query', getVideoById: { __typename?: 'Video', id: string, name: string, author: string, viewCount: number, loved: boolean, lastViewTime: number, lastModifyTime: number, introduction: string, duration: number, tags: Array<{ __typename?: 'VideoTag', name: string }> } };

export type GetSuggestionsQueryVariables = Exact<{
  input: SuggestionInput;
}>;


export type GetSuggestionsQuery = { __typename?: 'Query', getSuggestions: Array<string> };

export type BrowseDirectoryQueryVariables = Exact<{
  path: RelativePathInput;
}>;


export type BrowseDirectoryQuery = { __typename?: 'Query', browseDirectory: Array<{ __typename?: 'FileBrowseNode', node: { __typename?: 'Video', id: string, isDir: boolean, name: string, author: string, loved: boolean, lastModifyTime: number, introduction: string, size: number, duration: number, tags: Array<{ __typename?: 'VideoTag', name: string }> } }> };

export type GetDirectoryMetadataQueryVariables = Exact<{
  path: RelativePathInput;
}>;


export type GetDirectoryMetadataQuery = { __typename?: 'Query', getDirectoryMetadata: { __typename?: 'DirectoryMetadataResult', totalSize: number, lastModifiedTime: number } };

export const UpdateVideoMetadataDocument = gql`
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

  @Injectable({
    providedIn: 'root'
  })
  export class UpdateVideoMetadataGQL extends Apollo.Mutation<UpdateVideoMetadataMutation, UpdateVideoMetadataMutationVariables> {
    override document = UpdateVideoMetadataDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const BatchUpdateVideosDocument = gql`
    mutation BatchUpdateVideos($input: VideosBatchOperationInput!) {
  batchUpdate(input: $input) {
    resultType
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class BatchUpdateVideosGQL extends Apollo.Mutation<BatchUpdateVideosMutation, BatchUpdateVideosMutationVariables> {
    override document = BatchUpdateVideosDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const RecordVideoViewDocument = gql`
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

  @Injectable({
    providedIn: 'root'
  })
  export class RecordVideoViewGQL extends Apollo.Mutation<RecordVideoViewMutation, RecordVideoViewMutationVariables> {
    override document = RecordVideoViewDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const DeleteVideoDocument = gql`
    mutation DeleteVideo($videoId: ID!) {
  deleteVideo(videoId: $videoId) {
    success
    video {
      id
    }
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class DeleteVideoGQL extends Apollo.Mutation<DeleteVideoMutation, DeleteVideoMutationVariables> {
    override document = DeleteVideoDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const BatchUpdateDirectoryDocument = gql`
    mutation BatchUpdateDirectory($input: DirectoryVideosBatchOperationInput!) {
  batchUpdateDirectory(input: $input) {
    resultType
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class BatchUpdateDirectoryGQL extends Apollo.Mutation<BatchUpdateDirectoryMutation, BatchUpdateDirectoryMutationVariables> {
    override document = BatchUpdateDirectoryDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const SearchVideosDocument = gql`
    query SearchVideos($input: VideoSearchInput!) {
  SearchVideos(input: $input) {
    pagination {
      size
      totalCount
      currentPageNumber
    }
    videos {
      id
      name
      author
      viewCount
      loved
      lastViewTime
      lastModifyTime
      thumbnail
      duration
    }
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class SearchVideosGQL extends Apollo.Query<SearchVideosQuery, SearchVideosQueryVariables> {
    override document = SearchVideosDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const GetTopTagsDocument = gql`
    query GetTopTags {
  getTopTags {
    name
    count
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class GetTopTagsGQL extends Apollo.Query<GetTopTagsQuery, GetTopTagsQueryVariables> {
    override document = GetTopTagsDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const GetTopTagsAsSuggestionDocument = gql`
    query GetTopTagsAsSuggestion {
  getTopTags {
    name
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class GetTopTagsAsSuggestionGQL extends Apollo.Query<GetTopTagsAsSuggestionQuery, GetTopTagsAsSuggestionQueryVariables> {
    override document = GetTopTagsAsSuggestionDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const GetVideoByIdDocument = gql`
    query GetVideoById($videoId: ID!) {
  getVideoById(videoId: $videoId) {
    id
    name
    tags {
      name
    }
    author
    viewCount
    loved
    lastViewTime
    lastModifyTime
    introduction
    duration
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class GetVideoByIdGQL extends Apollo.Query<GetVideoByIdQuery, GetVideoByIdQueryVariables> {
    override document = GetVideoByIdDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const GetSuggestionsDocument = gql`
    query GetSuggestions($input: SuggestionInput!) {
  getSuggestions(input: $input)
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class GetSuggestionsGQL extends Apollo.Query<GetSuggestionsQuery, GetSuggestionsQueryVariables> {
    override document = GetSuggestionsDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const BrowseDirectoryDocument = gql`
    query BrowseDirectory($path: RelativePathInput!) {
  browseDirectory(path: $path) {
    node {
      id
      isDir
      name
      tags {
        name
      }
      author
      loved
      lastModifyTime
      introduction
      size
      duration
    }
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class BrowseDirectoryGQL extends Apollo.Query<BrowseDirectoryQuery, BrowseDirectoryQueryVariables> {
    override document = BrowseDirectoryDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }
export const GetDirectoryMetadataDocument = gql`
    query GetDirectoryMetadata($path: RelativePathInput!) {
  getDirectoryMetadata(path: $path) {
    totalSize
    lastModifiedTime
  }
}
    `;

  @Injectable({
    providedIn: 'root'
  })
  export class GetDirectoryMetadataGQL extends Apollo.Query<GetDirectoryMetadataQuery, GetDirectoryMetadataQueryVariables> {
    override document = GetDirectoryMetadataDocument;
    
    constructor(apollo: Apollo.Apollo) {
      super(apollo);
    }
  }