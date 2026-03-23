import { Injectable, OnDestroy } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { VideoUpdateEvent, VideoUpdateType } from '../../shared/models/events.model';

@Injectable({ providedIn: 'root' })
export class VideoUpdateEventService implements OnDestroy {
  private channel = new BroadcastChannel(environment.videoUpdateChannel);
  private event$ = new Subject<VideoUpdateEvent>();

  constructor() {
    this.channel.onmessage = (e: MessageEvent<VideoUpdateEvent>) => {
      this.event$.next(e.data);
    };
  }

  /** Emit an event to current tab and all other tabs */
  emit(event: VideoUpdateEvent): void {
    this.event$.next(event);
    this.channel.postMessage(event);
  }

  emitUpdated(videoIds: string[]): void {
    this.emit({ type: VideoUpdateType.Updated, videoIds });
  }

  emitDeleted(videoIds: string[]): void {
    this.emit({ type: VideoUpdateType.Deleted, videoIds });
  }

  /** Subscribe to all events */
  onEvent(): Observable<VideoUpdateEvent> {
    return this.event$.asObservable();
  }

  /** Subscribe only to update events */
  onUpdated(): Observable<VideoUpdateEvent> {
    return this.event$.pipe(filter(e => e.type === VideoUpdateType.Updated));
  }

  /** Subscribe only to delete events */
  onDeleted(): Observable<VideoUpdateEvent> {
    return this.event$.pipe(filter(e => e.type === VideoUpdateType.Deleted));
  }

  ngOnDestroy(): void {
    this.channel.close();
    this.event$.complete();
  }
}
