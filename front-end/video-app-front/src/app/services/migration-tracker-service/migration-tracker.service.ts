import { Injectable, inject, signal } from '@angular/core';
import { Observable, Subject, takeWhile } from 'rxjs';
import { GqlService } from '../GQL-service/GQL.service';
import { VideoUpdateEventService } from '../video-update-event-service/video-update-event.service';
import { MigrationStatusEnum, MigrationTaskQueryInput } from '../../core/graphql/generated/graphql';
import {
  MigrationProgressDetail,
  MigrationTaskItem,
  ResultState,
} from '../../shared/models/GQL-result.model';
import {
  ACTIVE_MIGRATION_STATUSES,
  isMigrationTerminal,
  parentDirectoryOf,
} from '../../shared/models/migration.model';


@Injectable({ providedIn: 'root' })
export class MigrationTrackerService {

  private gqlService = inject(GqlService);
  private videoUpdateEventService = inject(VideoUpdateEventService);

  private watched = new Map<string, MigrationTaskItem>();

  private progress = signal<ReadonlyMap<string, MigrationProgressDetail>>(new Map());
  private settled$ = new Subject<string>();

  readonly liveProgress = this.progress.asReadonly();

  /** Fires with a task id each time one reaches a terminal status. */
  onTaskSettled(): Observable<string> {
    return this.settled$.asObservable();
  }

  track(tasks: MigrationTaskItem[]): void {
    for (const task of tasks) {
      if (isMigrationTerminal(task.status) || this.watched.has(task.id)) continue;
      this.watch(task, this.gqlService.migrationProgressSubscription({ taskId: task.id }));
    }
  }

  /**
   * Watch the running tasks whose source or target file sits directly in
   * `directoryPath` (DB-format, '/'-joined — the same shape the file browser holds).
   *
   * Callers gate this on having actually seen a locked entry, so the task list
   * query only runs when something on screen is mid-migration.
   */
  trackTasksInDirectory(directoryPath: string): void {
    const input: MigrationTaskQueryInput = {
      page: 1,
      pageSize: 100,
      statusFilter: ACTIVE_MIGRATION_STATUSES.map(status => status.toString()),
    };

    this.gqlService.getMigrationTasksQuery(input).subscribe({
      next: (result) => {
        const tasks: MigrationTaskItem[] = result.data?.tasks ?? [];
        this.track(tasks.filter(task =>
          parentDirectoryOf(task.sourcePath) === directoryPath ||
          parentDirectoryOf(task.targetPath) === directoryPath
        ));
      },
    });
  }

  /**
   * Retry a failed task and watch the run it starts. Unlike track(), this is an
   * action: the subscription is what tells the backend to re-queue the task.
   */
  retry(task: MigrationTaskItem): void {
    // Guards a double-click: the button stays enabled until the first frame lands,
    // and a second retry subscription would re-queue a task already on its way.
    if (this.watched.has(task.id)) return;
    this.watch(task, this.gqlService.migrationRetrySubscription({ taskId: task.id }));
  }

  /** Stop treating a task as watched, e.g. after cancelling it from the UI. */
  forget(taskId: string): void {
    this.watched.delete(taskId);
  }

  private watch(task: MigrationTaskItem, frames: Observable<ResultState<MigrationProgressDetail | null>>): void {
    this.watched.set(task.id, task);

    frames
      .pipe(takeWhile(result => {
        const status = result.data?.status;
        return status !== undefined && !isMigrationTerminal(status);
      }, true))
      .subscribe({
        next: (result) => {
          const frame = result.data;
          if (!frame) return;

          this.progress.update(current => new Map(current).set(task.id, frame));
          if (isMigrationTerminal(frame.status)) {
            this.settle(task, frame.status);
          }
        },
        error: () => this.watched.delete(task.id),
      });
  }

  private settle(task: MigrationTaskItem, status: MigrationStatusEnum): void {
    this.watched.delete(task.id);
    this.settled$.next(task.id);

    // Cancelled and Failed leave the file where it was; only a completed run moved it.
    if (status !== MigrationStatusEnum.Completed) return;

    this.videoUpdateEventService.emitMigrated(
      parentDirectoryOf(task.sourcePath),
      parentDirectoryOf(task.targetPath),
    );
  }
}
