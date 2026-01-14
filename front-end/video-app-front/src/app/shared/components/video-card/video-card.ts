import { Component, Input, OnChanges, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { Video } from '../../../core/graphql/generated/graphql';

@Component({
  selector: 'app-video-card',
  imports: [RouterLink, MatCardModule, MatChipsModule],
  templateUrl: './video-card.html',
})
export class VideoCard implements OnChanges{
  @Input() video?: Video | null;

  readonly defaultThumbnail = '/videoicon.png';
  thumbnailSrc = this.defaultThumbnail;

  ngOnChanges() {
    if (!this.video?.thumbnail) {
      this.thumbnailSrc = this.defaultThumbnail;
      return;
    }

    const realUrl =
      `/video/thumbnail/?video_id=${this.video.id}&thumbnail_id=${this.video.thumbnail}`;

    const img = new Image();
    img.src = realUrl;

    img.onload = () => {
      this.thumbnailSrc = realUrl;
    };
  }

  get formattedDate(): string {
    if (!this.video) return '';
    return new Date(this.video.lastModifyTime).toLocaleDateString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  }
}
