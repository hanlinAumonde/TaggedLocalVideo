import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { SearchedVideo } from '../../models/GQL-result.model';
import { environment } from '../../../../environments/environment';
import { HttpClientService } from '../../../services/Http-client-service/Http-client-service';

@Component({
  selector: 'app-video-card',
  imports: [RouterLink, MatCardModule, MatChipsModule],
  templateUrl: './video-card.html',
})
export class VideoCard {
  video = input<SearchedVideo | null>(null);

  private httpClientService = inject(HttpClientService);

  readonly defaultThumbnail = '/videoicon.png';

  thumbnailSrc = signal(this.defaultThumbnail);
  isDefaultThumbnail = signal(true);
  duration = signal<number>(0);

  formattedDuration = computed(() => {
    const totalSeconds = this.duration();
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  });

  views = computed(() => {
    if (!this.video()?.viewCount) return '0';
    // use x, xK, xM format
    const count = this.video()!.viewCount;
    if (count < 1000) return count.toString();
    if (count < 1_000_000) return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return (count / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  });

  constructor() {
    effect(() => {
      const video = this.video();
      if (!video?.id) {
        this.thumbnailSrc.set(this.defaultThumbnail);
        this.isDefaultThumbnail.set(true);
        return;
      }

      this.httpClientService.getThumbnailAndDurationUrl(video.id, video.thumbnail ?? '')
        .subscribe(response => {
          const blob = response.body;
          if (blob) {
            const url = URL.createObjectURL(blob);
            this.thumbnailSrc.set(url);
            this.isDefaultThumbnail.set(false);
            const durationHeader = response.headers.get(environment.VIDEO_DURATION_HEADER);
            if (durationHeader) {
              const durationSeconds = Math.floor(parseFloat(durationHeader));
              if (!isNaN(durationSeconds)) {
                this.duration.set(durationSeconds);
              }
            }
          } else {
            this.thumbnailSrc.set(this.defaultThumbnail);
            this.isDefaultThumbnail.set(true);
          }
        }
      );
    });
  }

  get formattedDate(): string {
    if (!this.video()) return '';
    return new Date(this.video()!.lastModifyTime * 1000).toLocaleDateString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }
}
