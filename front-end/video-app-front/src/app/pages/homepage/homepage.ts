import { Component, inject, OnDestroy, signal } from '@angular/core';
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
import { VideoUpdateEvent, VideoUpdateType } from '../../shared/models/events.model';
import { Subject, takeUntil } from 'rxjs';
import { GetTopTagsDetail, ResultState, SearchVideosDetail } from '../../shared/models/GQL-result.model';

@Component({
  selector: 'app-homepage',
  imports: [VideoCard, MatButtonModule, RouterModule],
  templateUrl: './homepage.html',
})
export class Homepage implements OnDestroy {
  private gqlService = inject(GqlService);
  private router = inject(Router);
  private stateService = inject(PageStateService);
  private videoUpdateEventService = inject(VideoUpdateEventService);
  private destroy$ = new Subject<void>();

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
    this.loadLovedVideos();
    this.loadLatestViewedVideos();
    this.loadMostViewedVideos();
    this.loadTopTags();

    this.videoUpdateEventService.onEvent()
      .pipe(takeUntil(this.destroy$))
      .subscribe(event => {
        const ids = new Set(event.videoIds);

        const sectionContainsAffectedId = (section: ResultState<SearchVideosDetail>) =>
          section.data?.videos.some(v => ids.has(v.id)) ?? false;

        if (sectionContainsAffectedId(this.lovedVideos())) {
          this.loadLovedVideos();
        }
        if (sectionContainsAffectedId(this.latestViewedVideos())) {
          this.loadLatestViewedVideos();
        }
        if (sectionContainsAffectedId(this.mostViewedVideos())) {
          this.loadMostViewedVideos();
        }

        this.loadTopTags();
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadLovedVideos() {
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.Loved)
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => this.lovedVideos.set(result));
  }

  loadLatestViewedVideos() {
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.Latest)
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => this.latestViewedVideos.set(result));
  }

  loadMostViewedVideos() {
    this.gqlService.searchVideosQuery(SearchFrom.FrontalPage, VideoSortOption.MostViewed)
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => this.mostViewedVideos.set(result));
  }

  loadTopTags() {
    this.gqlService.getTopTagsQuery()
      .pipe(takeUntil(this.destroy$))
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
