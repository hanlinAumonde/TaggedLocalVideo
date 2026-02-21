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
  VideoSortOption,
  BrowseDirectoryGQL,
  DeleteVideoGQL,
  VideosBatchOperationInput,
  DirectoryVideosBatchOperationInput,
  GetDirectoryMetadataGQL,
  BatchUpdateDirectorySubscriptionGQL,
  BatchUpdateSubscriptionGQL,
  BatchDeleteSubscriptionGQL,
  BatchDeleteDirectorySubscriptionGQL
} from '../../core/graphql/generated/graphql';
import { 
  catchError, 
  debounceTime, 
  distinctUntilChanged, 
  map, 
  Observable, 
  of, 
  switchMap, 
  tap } from 'rxjs';
import { ObservableQuery } from '@apollo/client';
import { DeepPartial } from '@apollo/client/utilities';
import {
  BatchUpdateVideosDetail,
  BrowseDirectoryDetail,
  DeleteVideoDetail,
  DirectoryMetadataDetail,
  GetTopTagsDetail,
  ResultState,
  SearchVideosDetail,
  VideoDetail,
  VideoMutationDetail,
  VideoRecordViewDetail } from '../../shared/models/GQL-result.model';
import { Apollo } from 'apollo-angular';
import { ValidationService } from '../validation-service/validation.service';
import { ToastService } from '../toast-service/toast.service';

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
  private browseDirectoryGQL = inject(BrowseDirectoryGQL)
  private deleteVideoGQL = inject(DeleteVideoGQL)
  private getDirectoryMetadataGQL = inject(GetDirectoryMetadataGQL)
  private batchUpdateVideosSubscriptionGQL = inject(BatchUpdateSubscriptionGQL)
  private batchDeleteVideosSubscriptionGQL = inject(BatchDeleteSubscriptionGQL)
  private batchUpdateDirectorySubscriptionGQL = inject(BatchUpdateDirectorySubscriptionGQL)
  private batchDeleteDirectorySubscriptionGQL = inject(BatchDeleteDirectorySubscriptionGQL)
  private validationService = inject(ValidationService);
  private toastService = inject(ToastService);

  private filterUndefinedResult<T>(result : T[]){
    return result.filter((r) => r != undefined)
  }

  initialSignalData<T>(data: T): ResultState<T> {
    return {
      loading: true,
      error: null,
      data: data
    } 
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
            this.toastService.emitErrorOrWarning(`Failed GraphQL request: ${result.error}`, 'error');
          }
        })
        
      )
  }

  // ----------------------------Query----------------------------

  private getTopTagsAsSuggestionQuery(): Observable<ResultState<string[]>>{
    return this.toResultStateObservable(
      this.getTopTagsAsSuggestionGQL.watch().valueChanges,
      (data) => {
        return this.filterUndefinedResult(
          this.filterUndefinedResult(data?.getTopTags ?? []).map(tag => tag.name)
        );
      }
    )
  }

  getSuggestionsQuery(formValueChanges: Observable<string | null>, field: SearchField): Observable<ResultState<string[]>> {
    return formValueChanges.pipe(
      this.validationService.filterValidInput(field),
      debounceTime(500),
      distinctUntilChanged(),
      switchMap(keyword => 
        (!keyword || keyword.length < 1)? 
        (field === SearchField.Tag? this.getTopTagsAsSuggestionQuery() : of(this.initialSignalData<string[]>([]))) 
        :
        this.toResultStateObservable(
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
      )
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
                    currentPageNumber: number = 1, tags: string[] = []): Observable<ResultState<SearchVideosDetail>> {
    const input = {
      author: { keyWord: author ?? undefined },
      currentPageNumber: currentPageNumber,
      fromPage: fromPage,
      sortBy: sortBy,
      tags: tags,
      titleKeyword: { keyWord: title ?? undefined },
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

  browseDirectoryQuery(relativePath?: string, refreshCache: boolean = false): Observable<ResultState<BrowseDirectoryDetail>> {
    return this.toResultStateObservable(
      this.browseDirectoryGQL.watch({
        variables: { path: { 
          relativePath: relativePath,
          refreshFlag: refreshCache 
        } }
      }).valueChanges,
      (data) => this.filterUndefinedResult(data.browseDirectory ?? []) as BrowseDirectoryDetail
    )
  }

  getDirectoryMetadataQuery(relativePath?: string): Observable<ResultState<DirectoryMetadataDetail>> {
    return this.toResultStateObservable(
      this.getDirectoryMetadataGQL.watch({
        variables: { path: { 
          relativePath: relativePath
        } }
      }).valueChanges,
      (data) => ({
        totalSize: data.getDirectoryMetadata?.totalSize ?? 0,
        lastModifiedTime: data.getDirectoryMetadata?.lastModifiedTime ?? ''
      } as DirectoryMetadataDetail)
    )
  }

  // ----------------------------Mutation----------------------------

  recordVideoViewMutation(videoId: string): Observable<ResultState<VideoRecordViewDetail>> {
    return this.toResultStateObservable(
      this.recordVideoViewGQL.mutate({ variables: { videoId } }),
      (data) => ({
        success: data.recordVideoView?.success ?? false,
        video: data.recordVideoView?.video
      } as VideoRecordViewDetail)
    )
  }

  deleteVideoMutation(videoId: string): Observable<ResultState<DeleteVideoDetail>> {
    return this.toResultStateObservable(
      this.deleteVideoGQL.mutate({ variables: { videoId } }),
      (data) => ({
        success: data.deleteVideo?.success ?? false,
        video: data.deleteVideo?.video
      } as DeleteVideoDetail)
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
              loved: loved,
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

  // ----------------------------Subscription----------------------------

  private batchOperationDataConverter(subscriptionResult: any): BatchUpdateVideosDetail {
    return {
      result: {
        resultType: subscriptionResult?.result?.resultType ?? undefined,
        message: subscriptionResult?.result?.message ?? undefined
      },
      status: subscriptionResult?.status ?? undefined
    } as BatchUpdateVideosDetail
  }

  batchUpdateVideosSubscription(input: VideosBatchOperationInput){
    return this.toResultStateObservable(
      this.batchUpdateVideosSubscriptionGQL.subscribe({
        variables: {
          input: {
            videoIds: input.videoIds,
            tagsOperation: input.tagsOperation ?? undefined,
            author: input.author ?? undefined,
          }
        }
      }),
      (data) => this.batchOperationDataConverter(data.batchUpdateSubscription)
    )
  }

  batchDeleteVideosSubscription(input: VideosBatchOperationInput){
    return this.toResultStateObservable(
      this.batchDeleteVideosSubscriptionGQL.subscribe({
        variables: { input: { videoIds: input.videoIds } }
      }),
      (data) => this.batchOperationDataConverter(data.batchDeleteSubscription)
    )
  }

  batchUpdateDirectorySubscription(input: DirectoryVideosBatchOperationInput){
    return this.toResultStateObservable(
      this.batchUpdateDirectorySubscriptionGQL.subscribe({
        variables: {
          input: {
            relativePath: input.relativePath,
            tagsOperation: input.tagsOperation ?? undefined,
            author: input.author ?? undefined,
          }
        }
      }),
      (data) => this.batchOperationDataConverter(data.batchUpdateDirectorySubscription)
    )
  }

  batchDeleteDirectorySubscription(input: DirectoryVideosBatchOperationInput){
    return this.toResultStateObservable(
      this.batchDeleteDirectorySubscriptionGQL.subscribe({
        variables: { input: { relativePath: input.relativePath } }
      }),
      (data) => this.batchOperationDataConverter(data.batchDeleteDirectorySubscription)
    )
  }
}
