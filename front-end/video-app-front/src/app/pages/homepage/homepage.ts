import { Component, inject, signal, WritableSignal } from '@angular/core';
import { VideoCard } from '../../shared/components/video-card/video-card';
import { MatButtonModule } from '@angular/material/button';
import { GqlService } from '../../services/GQL-service/GQL.service';
import { Router, RouterModule } from '@angular/router';
import {
  SearchFrom,
  VideoSortOption
} from '../../core/graphql/generated/graphql';
import { SearchPageParam } from '../../shared/models/search.model';
import { environment } from '../../../environments/environment';
import { PageStateService } from '../../services/Page-state-service/page-state.service';
import { VideoUpdateEventService } from '../../services/video-update-event-service/video-update-event.service';
import { GetTopTagsDetail, ResultState, SearchVideosDetail } from '../../shared/models/GQL-result.model';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-homepage',
  imports: [VideoCard, MatButtonModule, RouterModule],
  templateUrl: './homepage.html',
})
export class Homepage {
  private gqlService = inject(GqlService);
  private router = inject(Router);
  private stateService = inject(PageStateService);
  private videoUpdateEventService = inject(VideoUpdateEventService);

  searchPageApi = environment.searchpage_api;

  INITIAL_VIDEOS_SEARCH_RESULT : SearchVideosDetail = {
    videos: [],
    pagination: {
      size: 0,
      currentPageNumber: 0,
      totalCount: 0
    }
  }

  // Loved Videos
  lovedVideos = signal<ResultState<SearchVideosDetail>>(
    this.gqlService.initialSignalData<SearchVideosDetail>(this.INITIAL_VIDEOS_SEARCH_RESULT)
  );

  // Latest Viewed
  latestViewedVideos = signal<ResultState<SearchVideosDetail>>(
    this.gqlService.initialSignalData<SearchVideosDetail>(this.INITIAL_VIDEOS_SEARCH_RESULT)
  );

  // Most Viewed
  mostViewedVideos = signal<ResultState<SearchVideosDetail>>(
    this.gqlService.initialSignalData<SearchVideosDetail>(this.INITIAL_VIDEOS_SEARCH_RESULT)
  );

  // Top Tags
  topTags = signal<ResultState<GetTopTagsDetail>>(
    this.gqlService.initialSignalData<GetTopTagsDetail>([])
  );

  constructor() {
    this.loadVideos(VideoSortOption.Loved, this.lovedVideos);
    this.loadVideos(VideoSortOption.Latest, this.latestViewedVideos);
    this.loadVideos(VideoSortOption.MostViewed, this.mostViewedVideos);
    this.loadTopTags();

    this.videoUpdateEventService.onEvent()
      .pipe(takeUntilDestroyed())
      .subscribe(event => {
        const ids = new Set(event.videoIds);

        const sectionContainsAffectedId = (section: ResultState<SearchVideosDetail>) =>
          section.data?.videos.some(v => ids.has(v.id)) ?? false;

        if (sectionContainsAffectedId(this.lovedVideos())) {
          this.loadVideos(VideoSortOption.Loved, this.lovedVideos);
        }
        if (sectionContainsAffectedId(this.latestViewedVideos())) {
          this.loadVideos(VideoSortOption.Latest, this.latestViewedVideos);
        }
        if (sectionContainsAffectedId(this.mostViewedVideos())) {
          this.loadVideos(VideoSortOption.MostViewed, this.mostViewedVideos);
        }

        this.loadTopTags();
      });
  }

  loadVideos(sortBy: VideoSortOption, signal: WritableSignal<ResultState<SearchVideosDetail>>) {
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, sortBy)
      .pipe(takeUntilDestroyed())
      .subscribe(result => signal.set(result));
  }

  loadTopTags() {
    this.gqlService.getTopTagsQuery()
      .pipe(takeUntilDestroyed())
      .subscribe(result => this.topTags.set(result));
  }

  OnMoreClick(section: 'loved' | 'latest' | 'mostViewed'){
    const option = () => {
      switch(section){
        case 'loved': return VideoSortOption.Loved;
        case 'latest': return VideoSortOption.Latest;
        case 'mostViewed': return VideoSortOption.MostViewed;
        default: { return VideoSortOption.Loved; }
      }
    }
    this.stateService.clearState(environment.searchpage_api + environment.refreshKey, false);
    this.router.navigate([environment.searchpage_api], {
      state: { sortBy: option() } as SearchPageParam,
      queryParams: { currentPageNumber: 1 }
    });
  }

  tagState(tagName: string): SearchPageParam {
    return { tags: [tagName] };
  }

  onTagClick(tagName: string) {
    this.stateService.setState<SearchPageParam>(environment.searchpage_api, { tags: [tagName] }, true);
  }
}
