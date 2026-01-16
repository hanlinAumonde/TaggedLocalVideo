import { Component, inject } from '@angular/core';
import { VideoCard } from '../../shared/components/video-card/video-card';
import { MatButtonModule } from '@angular/material/button';
import { GqlService } from '../../services/GQL-service/GQL-service';
import { Router } from '@angular/router';
import { SearchFrom, VideoSearchResult, VideoSortOption, VideoTag } from '../../core/graphql/generated/graphql';
import { toSignal } from '@angular/core/rxjs-interop';
import { SearchPageParam } from '../../shared/models/search.model';

@Component({
  selector: 'app-homepage',
  imports: [VideoCard, MatButtonModule],
  templateUrl: './homepage.html',
})
export class Homepage{
  private gqlService = inject(GqlService);
  private router = inject(Router);

  INITIAL_VIDEOS_SEARCH_RESULT : VideoSearchResult = { 
    videos: [], 
    pagination: {
      size: 0,
      currentPageNumber: 0,
      totalCount: 0
    } 
  }

  // Loved Videos
  lovedVideos = toSignal(
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.Loved),
    { 
      initialValue: this.gqlService.initialSignalData<VideoSearchResult>(this.INITIAL_VIDEOS_SEARCH_RESULT) 
    }
  )
  

  // Latest Viewed
  latestViewedVideos = toSignal(
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.Latest),
    { 
      initialValue: this.gqlService.initialSignalData<VideoSearchResult>(this.INITIAL_VIDEOS_SEARCH_RESULT) 
    }
  )

  // Most Viewed
  mostViewedVideos = toSignal(
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.MostViewed),
    { 
      initialValue: this.gqlService.initialSignalData<VideoSearchResult>(this.INITIAL_VIDEOS_SEARCH_RESULT) 
    }
  )

  // Top Tags
  topTags = toSignal(
    this.gqlService.getTopTagsQuery(), { initialValue: this.gqlService.initialSignalData<VideoTag[]>([])}
  )

  OnMoreClick(section: 'loved' | 'latest' | 'mostViewed'){
    const option = () => {
      switch(section){
        case 'loved': return VideoSortOption.Loved;
        case 'latest': return VideoSortOption.Latest;
        case 'mostViewed': return VideoSortOption.MostViewed;
        default: { return VideoSortOption.Loved; }
      }
    }
    this.router.navigate(['/search'], {
      state: { sortBy: option() } as SearchPageParam,
      queryParams: { currentPageNumber: 1 }
    });
  }

  onTagClick(tagName: string) {
    this.router.navigate(['/search'], {
      state: { tags: [tagName] } as SearchPageParam,
      queryParams: { currentPageNumber: 1 }
    });
  }
}
