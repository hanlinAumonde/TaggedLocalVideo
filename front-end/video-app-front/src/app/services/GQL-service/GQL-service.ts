import { inject, Injectable } from '@angular/core';
import { 
  GetSuggestionsGQL, 
  GetTopTagsGQL, 
  QueryGetSuggestionsArgs, 
  SearchField 
} from '../../core/graphql/generated/graphql';
import { map } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class GqlService {
  private getSuggestionsGQL = inject(GetSuggestionsGQL)
  private getTopTagsGQL = inject(GetTopTagsGQL)

  getSuggestionsQuery(keyword: string, field: SearchField){
    return this.getSuggestionsGQL
      .watch({
        variables: {
          input: {
            keyword: {
              keyWord: keyword 
            },
            suggestionType: field
          }
        } as QueryGetSuggestionsArgs
      })
      .valueChanges
      .pipe(map((result) => result.data?.getSuggestions))
  }

  getTopTagsQuery(){
    return this.getTopTagsGQL.watch().valueChanges
      .pipe(
        map(result => {
          const tags = result.data?.getTopTags || [];
          return tags.map(tag => tag?.name);
        }))
  }
}
