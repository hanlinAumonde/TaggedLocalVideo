import { Component, computed, input, OnChanges } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { SearchedVideo } from '../../models/GQL-result.model';

@Component({
  selector: 'app-video-card',
  imports: [RouterLink, MatCardModule, MatChipsModule],
  templateUrl: './video-card.html',
})
export class VideoCard implements OnChanges{
  video = input<SearchedVideo | null>(null);

  readonly defaultThumbnail = '/videoicon.png';
  thumbnailSrc = this.defaultThumbnail;
  isDefaultThumbnail = true;

  views = computed(() => {
    if (!this.video()?.viewCount) return '0';
    // use x, xK, xM format
    const count = this.video()!.viewCount;
    if (count < 1000) return count.toString();
    if (count < 1_000_000) return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return (count / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  })

  ngOnChanges() {
    if (!this.video()?.thumbnail || !this.video()?.id) {
      this.thumbnailSrc = this.defaultThumbnail;
      this.isDefaultThumbnail = true;
      return;
    }

    const realUrl =
      `/video/thumbnail/?video_id=${this.video()?.id}&thumbnail_id=${this.video()?.thumbnail}`;

    const img = new Image();
    img.src = realUrl;

    img.onload = () => {
      this.thumbnailSrc = realUrl;
      this.isDefaultThumbnail = false;
    };
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
