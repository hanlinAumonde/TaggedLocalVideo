import { inject, Injectable } from '@angular/core';
import {
  GetSuggestionsGQL,
  GetTopTagsAsSuggestionGQL,
  QueryGetSuggestionsArgs,
  SearchField,
  UpdateVideoMetadataGQL,
} from '../../core/graphql/generated/graphql';
import { catchError, map, Observable, of, tap } from 'rxjs';
import { ObservableQuery } from '@apollo/client';
import { DeepPartial } from '@apollo/client/utilities';
import { ResultState } from '../../shared/models/GQL-result.model';
import { Apollo } from 'apollo-angular';

@Injectable({
  providedIn: 'root',
})
export class GqlService {
  private getSuggestionsGQL = inject(GetSuggestionsGQL)
  private getTopTagsAsSuggestionGQL = inject(GetTopTagsAsSuggestionGQL)
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
            window.alert(`Failed to update video metadata: ${result.error}`)
            // Currently use alert to notify user, TODO: emit event to a custom component to show notification
          }
        })
        
      )
  }

  initialSignalData<T>(data: T): ResultState<T> {
    return {
      loading: false,
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

  updateVideoMetadataMutation(videoID: string, 
                              title?: string, 
                              description?: string, 
                              tags?: string[], 
                              author?: string, 
                              loved: boolean = false){
    return this.toResultStateObservable(  
      this.updateVideoMetadataGQL.mutate(
        {
          variables: {
            input: {
              videoId: videoID,
              name: title,
              introduction: description,
              tags: tags || [],
              author: author,
              loved: loved
            }
          }
        }
      ),
      (data) => data?.updateVideoMetadata ?? null
    )
  }
}
