import {
  Component,
  OnDestroy,
  inject,
  signal,
  computed,
  ElementRef,
  AfterViewInit,
  effect,
  viewChild,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { take } from 'rxjs/operators';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import videojs from 'video.js';
import Player from 'video.js/dist/types/player';

import { GqlService } from '../../services/GQL-service/GQL.service';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData } from '../../shared/models/video-edit-panel.model';
import { ResultState, VideoDetail, VideoMutationDetail, VideoRecordViewDetail } from '../../shared/models/GQL-result.model';
import { environment } from '../../../environments/environment';
import { SearchPageParam } from '../../shared/models/search.model';
import { Title } from '@angular/platform-browser';
import { ToastService } from '../../services/toast-service/toast.service';
import { PageStateService } from '../../services/Page-state-service/page-state';

@Component({
  selector: 'app-video-player',
  imports: [
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    RouterLink
  ],
  templateUrl: './video-player.html'
})
export class VideoPlayer implements AfterViewInit, OnDestroy {
  videoTarget = viewChild<ElementRef<HTMLVideoElement>>('videoTarget');

  private route = inject(ActivatedRoute);
  private gqlService = inject(GqlService);
  private stateService = inject(PageStateService);
  private dialog = inject(MatDialog);
  private title = inject(Title);
  private toastService = inject(ToastService);
  private player: Player | null = null;
  private hasRecordedView = signal<boolean>(false);
  private videoDataLoaded = toSignal(this.route.data)

  searchPageApi = environment.searchpage_api;

  video = signal<ResultState<VideoDetail | null>>(this.gqlService.initialSignalData<VideoDetail | null>(null));
  
  videoId = computed(() => this.video().data?.id ?? null);

  videoStreamUrl = computed(() => {
    const id = this.videoId();
    return id ? environment.backend_api + environment.video_stream_api + id : '';
  });

  formattedViews = computed(() => {
    const count = this.video()?.data?.viewCount ?? 0;
    if (count < 1000) return count.toString();
    if (count < 1_000_000) return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return (count / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  });

  constructor() {
    effect(() => {
      this.video.set(this.videoDataLoaded()!['video']);
      const url = this.videoStreamUrl();
      this.hasRecordedView.set(false);
      if (url && this.player) {
        this.player.src({ type: 'video/mp4', src: url });
      }
      this.initializePlayer();
    });

    effect(() => {
      const videoData = this.video().data;
      if (videoData) {
        this.title.setTitle(`${videoData.name} - Tagged Local Video App`);
      }
    })
  }

  ngAfterViewInit() {
    this.initializePlayer();
  }

  ngOnDestroy() {
    this.disposePlayer();
  }

  private initializePlayer() {
    if (!this.videoTarget()?.nativeElement) return;

    this.player = videojs(this.videoTarget()!.nativeElement, {
      controls: true,
      autoplay: false,
      preload: 'auto',
      //fluid: true,
      fill: true,
      aspectRatio: '16:9',
      responsive: true,
      playbackRates: [0.5, 1, 1.5, 2],
      controlBar: {
          remainingTimeDisplay: {
            displayNegative: false
          },
          children: [
              'playToggle',
              'volumePanel',
              'currentTimeDisplay',
              'timeDivider',
              'durationDisplay',
              'progressControl',
              'playbackRateMenuButton',
              'pictureInPictureToggle',
              'fullscreenToggle'
          ]
      }
    });

    this.player.on('play', () => {
      this.recordView();
    });

    const url = this.videoStreamUrl();
    if (url) {
      this.player.src({ type: 'video/mp4', src: url });
    }
  }

  private disposePlayer() {
    if (this.player) {
      this.player.dispose();
      this.player = null;
    }
  }

  private recordView() {
    const id = this.videoId();
    if (this.hasRecordedView() || !id) return;

    this.hasRecordedView.set(true);
    this.gqlService.recordVideoViewMutation(id)
      .pipe(take(1))
      .subscribe({
        next: (result) => {
          if (!result.data?.success) {
            this.toastService.emitErrorOrWarning('Failed to record video view', 'error');
          }else if(result.data.video){
            this.video.update(current => {
              if (!current.data) return current;
              return this.toVideoDetailResultState(result.data!, current);
            });
          }
        }
      });
  }

  onLovedClick() {
    const videoData = this.video().data;
    if (!videoData) return;

    this.gqlService.updateVideoMetadataMutation(
      videoData.id,
      !videoData.loved,
      videoData.tags.map(tag => tag.name),
    ).pipe(take(1)).subscribe({
      next: (result) => {
        if (result.data?.success && result.data.video) {
          this.video.update(current => {
            if (!current.data) return current;
            return this.toVideoDetailResultState(result.data!, current);
          })
        }else{
          this.toastService.emitErrorOrWarning('Failed to update loved status', 'error');
        }
      }
    });
  }

  onEditClick() {
    const videoData = this.video().data;
    if (!videoData) return;

    const dialogData: VideoEditPanelData = {
      mode: 'full',
      video: videoData as VideoDetail,
    };

    const dialogRef = this.dialog.open(VideoEditPanel, {
      width: '600px',
      maxHeight: '90vh',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe(
      (result: VideoMutationDetail) => {
        if (result && result.video) {
          this.video.update(current => {
            return this.toVideoDetailResultState(result, current);
          });
        }
      }
    )
  }

  searchPageState(state: string, option: "author" | "tags"): SearchPageParam {
    return option === "author" ? { author: state } : { tags: [state] };
  }

  onTagClick(tagName: string) {
    this.stateService.setState<SearchPageParam>(
      environment.searchpage_api, 
      this.searchPageState(tagName, "tags"), 
      true
    );
  }

  onAuthorClick(author: string) {
    this.stateService.setState<SearchPageParam>(
      environment.searchpage_api, 
      this.searchPageState(author, "author"), 
      true
    );
  }

  toVideoDetailResultState(updatedData: VideoMutationDetail | VideoRecordViewDetail, 
                           currentData: ResultState<VideoDetail | null>
                          ): ResultState<VideoDetail | null> {
    if('viewCount' in updatedData.video!){
      return {
        ...currentData,
        data: {
          ...currentData.data!,
          viewCount: updatedData.video!.viewCount!,
          lastViewTime: updatedData.video!.lastViewTime!,
        }
      }
    }else{
      return {
        ...currentData,
        data: {
          ...currentData.data!,
          loved: updatedData.video!.loved!,
          name: updatedData.video!.name!,
          introduction: updatedData.video!.introduction!,
          author: updatedData.video!.author!,
          tags: updatedData.video!.tags!,
        }
      }
    }
  }
}