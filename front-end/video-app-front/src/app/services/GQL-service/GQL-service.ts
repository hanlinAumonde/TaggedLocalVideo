import { inject, Injectable } from '@angular/core';
import {
  GetSuggestionsGQL,
  GetTopTagsAsSuggestionGQL,
  GetTopTagsGQL,
  GetVideoByIdGQL,
  SearchVideosGQL,
  RecordVideoViewGQL,
  QueryGetSuggestionsArgs,
  SearchField,
  UpdateVideoMetadataGQL,
  VideoSearchInput,
  SearchFrom,
  VideoSortOption
} from '../../core/graphql/generated/graphql';
import { catchError, map, Observable, of, tap } from 'rxjs';
import { ObservableQuery } from '@apollo/client';
import { DeepPartial } from '@apollo/client/utilities';
import { GetTopTagsDetail, ResultState, SearchVideosDetail, VideoDetail, VideoMutationDetail } from '../../shared/models/GQL-result.model';
import { Apollo } from 'apollo-angular';

@Injectable({
  providedIn: 'root',
})
export class GqlService {
  private getSuggestionsGQL = inject(GetSuggestionsGQL)
  private getTopTagsAsSuggestionGQL = inject(GetTopTagsAsSuggestionGQL)
  private getTopTagsGQL = inject(GetTopTagsGQL)
  private getVideoByIdGQL = inject(GetVideoByIdGQL)
  private searchVideosGQL = inject(SearchVideosGQL)
  private recordVideoViewGQL = inject(RecordVideoViewGQL)
  private updateVideoMetadataGQL = inject(UpdateVideoMetadataGQL)

  private filterUndefinedResult<T>(result : T[]){
    return result.filter((r) => r != undefined)
  }

  private toResultStateObservable<TData, TResult>(
    gqlValueChanges: Observable<ObservableQuery.Result<TData, "empty" | "complete" | "streaming" | "partial"> | Apollo.MutateResult<TData>>,
    dataExtractor: (data: NonNullable<TData> | NonNullable<DeepPartial<TData>>) => TResult | null
  ): Observable<ResultState<TResult>> {
    return gqlValueChanges.pipe(
        map(result => ({
          loading: result.loading ?? true,
          error: result.error?.message ?? null,
          data: result.data ? dataExtractor(result.data) : null
        })),
        catchError((error) => {
          return of<ResultState<TResult>>({
            loading: false,
            error: error.message ?? 'An unknown error occurred',
            data: null
          });
        }),
        tap(result => {
          if(result.error){
            window.alert(`Failed GraphQL request: ${result.error}`)
            // Currently use alert to notify user, TODO: emit event to a custom component to show notification
          }
        })
        
      )
  }

  initialSignalData<T>(data: T): ResultState<T> {
    return {
      loading: true,
      error: null,
      data: data
    } 
  }

  getSuggestionsQuery(keyword: string, field: SearchField): Observable<ResultState<string[]>> {
    return this.toResultStateObservable(
      this.getSuggestionsGQL.watch({
        variables: {
          input: {
            keyword: {
              keyWord: keyword
            },
            suggestionType: field
          }
        } as QueryGetSuggestionsArgs
      })
      .valueChanges,
      (data) => this.filterUndefinedResult(data?.getSuggestions ?? [])
    )
  }

  getTopTagsAsSuggestionQuery(limit?: number): Observable<ResultState<string[]>>{
    return this.toResultStateObservable(
      this.getTopTagsAsSuggestionGQL.watch().valueChanges,
      (data) => {
        const tags = this.filterUndefinedResult(
          this.filterUndefinedResult(data?.getTopTags ?? []).map(tag => tag.name)
        );
        return limit ? tags.slice(0, limit) : tags;
      }
    )
  }

  updateVideoMetadataMutation(videoID: string,loved: boolean = false,tags?: string[],
                              title?: string,description?: string,author?: string): Observable<ResultState<VideoMutationDetail>>{
    return this.toResultStateObservable(this.updateVideoMetadataGQL.mutate({
          variables: {
            input: {
              videoId: videoID,
              name: title,
              introduction: description,
              tags: tags ?? [],
              author: author,
              loved: loved
            }
          }
        }
      ),
      (data) => ({
        success: data.updateVideoMetadata?.success ?? false,
        video: data.updateVideoMetadata?.video ?? null
      } as VideoMutationDetail)
    )
  }

  getTopTagsQuery(limit? : number): Observable<ResultState<GetTopTagsDetail>> {
    return this.toResultStateObservable(
      this.getTopTagsGQL.watch().valueChanges,
      (data) => {
        const tags = this.filterUndefinedResult(
          this.filterUndefinedResult(data?.getTopTags ?? [])
            .filter(tag => tag.name && tag.count)
        ) as GetTopTagsDetail;
        return limit ? tags.slice(0, limit) : tags;
      }
    )
  }
  
  searchVideosQuery(fromPage: SearchFrom,sortBy?: VideoSortOption, author?: string, title?: string,
                    currentPageNumber: number = 0, tags: string[] = []): Observable<ResultState<SearchVideosDetail>> {
    const input = {
      author: { keyWord: author },
      currentPageNumber: currentPageNumber,
      fromPage: fromPage,
      sortBy: sortBy,
      tags: tags,
      titleKeyword: { keyWord: title },
    } as VideoSearchInput;
    return this.toResultStateObservable(
      this.searchVideosGQL.watch({ variables: { input: input }}).valueChanges,
      (data) => ({
        pagination: data.SearchVideos?.pagination ?? { size: 0, currentPageNumber: 0, totalCount: 0 },
        videos: this.filterUndefinedResult(data.SearchVideos?.videos ?? [])
      } as SearchVideosDetail)
    )
  }

  getVideoByIdQuery(videoId: string): Observable<ResultState<VideoDetail | null>> {
    return this.toResultStateObservable(
      this.getVideoByIdGQL.watch({ variables: { videoId } }).valueChanges,
      (data) => (data.getVideoById ?? null) as VideoDetail | null
    )
  }

  recordVideoViewMutation(videoId: string): Observable<ResultState<VideoMutationDetail>> {
    return this.toResultStateObservable(
      this.recordVideoViewGQL.mutate({ variables: { videoId } }),
      (data) => ({
        success: data.recordVideoView?.success ?? false,
        video: data.recordVideoView?.video
      } as VideoMutationDetail)
    )
  }
}

