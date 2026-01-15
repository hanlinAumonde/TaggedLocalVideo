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
import { ActivatedRoute, Router } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { switchMap, take, map } from 'rxjs/operators';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import videojs from 'video.js';
import Player from 'video.js/dist/types/player';
import { Subject, merge } from 'rxjs';

import { GqlService } from '../../services/GQL-service/GQL-service';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData } from '../../shared/models/video-edit-panel.model';
import { VideoDetail } from '../../shared/models/GQL-result.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-video-player',
  imports: [
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDialogModule,
  ],
  templateUrl: './video-player.html'
})
export class VideoPlayer implements AfterViewInit, OnDestroy {
  videoTarget = viewChild<ElementRef<HTMLVideoElement>>('videoTarget');

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);

  private player: Player | null = null;
  private hasRecordedView = signal<boolean>(false);

  private refreshTrigger$ = new Subject<void>();

  videoId = toSignal(
    this.route.paramMap.pipe(
      map((params) => params.get('id') ?? '')
    ),
    { initialValue: '' }
  );

  video = toSignal(
    merge(
      this.route.paramMap.pipe(map(() => 'route')),
      this.refreshTrigger$.pipe(map(() => 'refresh'))
    ).pipe(
      switchMap((source) => {
        const id = this.route.snapshot.paramMap.get('id') ?? '';
        if (source === 'route') {
          this.hasRecordedView.set(false);
        }
        return this.gqlService.getVideoByIdQuery(id);
      })
    ),
    { initialValue: this.gqlService.initialSignalData<VideoDetail | null>(null) }
  );

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
      const url = this.videoStreamUrl();
      if (url && this.player) {
        this.player.src({ type: 'video/mp4', src: url });
      }
      this.initializePlayer();
    });
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
      fluid: true,
      responsive: true,
      playbackRates: [0.5, 1, 1.5, 2],
      controlBar: {
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
    console.log('Setting video source URL:', url);
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
            window.alert('Failed to record video view');
            console.error('Failed to record video view');
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
        if (result.data?.success) {
          //this.refreshTrigger$.next();
        }else{
          window.alert('Failed to update loved status');
          console.error('Failed to update loved status');
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

    this.dialog.open(VideoEditPanel, {
      width: '600px',
      maxHeight: '90vh',
      data: dialogData,
    });
  }

  onTagClick(tagName: string) {
    this.router.navigate(['/search'], {
      queryParams: { tag: tagName }
    });
  }

  onAuthorClick(author: string) {
    this.router.navigate(['/search'], {
      queryParams: { author: author }
    });
  }
}