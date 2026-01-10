import { Component, Input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { Video } from '../../../core/graphql/generated/graphql';

@Component({
  selector: 'app-video-card',
  imports: [RouterLink, MatCardModule, MatChipsModule],
  templateUrl: './video-card.html',
})
export class VideoCard {
  @Input({ required: true }) video!: Video;

  imageLoaded = signal(false);
  imageError = signal(false);

  get thumbnailUrl(): string {
    if (!this.video.thumbnail) {
      return '/videoicon.png';
    }
    return `/video/thumbnail/?video_id=${this.video.id}&thumbnail_id=${this.video.thumbnail}`;
  }

  get formattedDate(): string {
    return new Date(this.video.lastModifyTime).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }

  onImageLoad() {
    this.imageLoaded.set(true);
  }

  onImageError() {
    this.imageError.set(true);
  }
}
