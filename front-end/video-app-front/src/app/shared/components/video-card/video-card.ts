import { Component, computed, effect, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { SearchedVideo } from '../../models/GQL-result.model';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-video-card',
  imports: [RouterLink, MatCardModule, MatChipsModule],
  templateUrl: './video-card.html',
})
export class VideoCard {
  video = input<SearchedVideo | null>(null);

  readonly defaultThumbnail = '/videoicon.png';
  thumbnailSrc = signal(this.defaultThumbnail);
  isDefaultThumbnail = signal(true);

  views = computed(() => {
    if (!this.video()?.viewCount) return '0';
    // use x, xK, xM format
    const count = this.video()!.viewCount;
    if (count < 1000) return count.toString();
    if (count < 1_000_000) return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return (count / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  })

  constructor() {
    effect(() => {
      const video = this.video();
      if (!video?.id) {
        this.thumbnailSrc.set(this.defaultThumbnail);
        this.isDefaultThumbnail.set(true);
        return;
      }

      const realUrl = environment.backend_api +
        `/video/thumbnail?video_id=${video.id}&thumbnail_id=${video.thumbnail ?? ''}`;

      const img = new Image();
      img.src = realUrl;

      img.onload = () => {
        this.thumbnailSrc.set(realUrl);
        this.isDefaultThumbnail.set(false);
      };
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
