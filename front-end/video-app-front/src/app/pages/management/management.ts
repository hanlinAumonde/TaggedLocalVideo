import { Component, inject, signal, computed, effect, OnDestroy, DestroyRef } from '@angular/core';
import { GqlService } from '../../services/GQL-service/GQL.service';
import {
  BrowseDirectoryDetail,
  FileBrowseNode,
} from '../../shared/models/GQL-result.model';
import { PageStateService } from '../../services/Page-state-service/page-state.service';
import { environment } from '../../../environments/environment';
import { 
  SortCriterion, 
  ManagementRefreshState, 
  comparatorBySortOption
} from '../../shared/models/management.model';
import { BottomToolbar } from '../../shared/components/bottom-toolbar/bottom-toolbar';
import { FileBrowseTable } from '../../shared/components/file-browse-table/file-browse-table';
import { ToastService } from '../../services/toast-service/toast.service';
import { PathHistoryService } from '../../services/path-history-service/path-history.service';
import { VideoUpdateEventService } from '../../services/video-update-event-service/video-update-event.service';
import { VideoUpdateEvent } from '../../shared/models/events.model';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription } from 'rxjs';
import { ToastType } from '../../shared/models/toast.model';

@Component({
  selector: 'app-management',
  imports: [
    BottomToolbar,
    FileBrowseTable
  ],
  templateUrl: './management.html'
})
export class Management implements OnDestroy{
  private gqlService = inject(GqlService);
  private stateService = inject(PageStateService);
  private toastService = inject(ToastService);
  private destroyRef = inject(DestroyRef);
  
  private videoUpdateEventService = inject(VideoUpdateEventService);
  pathHistoryService = inject(PathHistoryService)

  tableWidth = signal<number>(0);
  // true for ascending, false for descending
  sortCriteria = signal<SortCriterion>({
    index: 0,
    order: true
  });
  currentPath = signal<string[]>([]);
  directoryContents = signal(this.gqlService.initialSignalData<BrowseDirectoryDetail>([]));
  selectedIds = signal<Set<string>>(new Set());

  private directorySubscription: Subscription | null = null;

  isAtRoot = computed(() => this.currentPath().length === 0);
  selectedCount = computed(() => this.selectedIds().size);
  hasSelection = computed(() => this.selectedIds().size > 0);

  private setRefreshState(scrollTop: number = 0, sortIndex: number = 0, order: boolean = false, currentPath?: string[]) {
    this.stateService.setState<ManagementRefreshState>(
      environment.management_api + environment.refreshKey + environment.scrollKey,
      { 
        scrollPosition: scrollTop, 
        sortCriteria: { index: sortIndex, order: order }, 
        currentPath: currentPath 
      } as ManagementRefreshState,
      false
    );
  }

  private getRefreshState(): ManagementRefreshState | undefined {
    return this.stateService.getState<ManagementRefreshState>(
      environment.management_api + environment.refreshKey + environment.scrollKey,
      false
    );
  }

  constructor() {
    const hasValidState = (state: ManagementRefreshState | undefined) =>
      state && Array.isArray(state.currentPath);

    const state = this.getRefreshState();

    if (hasValidState(state)) {
      this.currentPath.set(state!.currentPath!);
    }

    this.setRefreshState(
      state?.scrollPosition ?? 0,
      state?.sortCriteria.index ?? 0,
      state?.sortCriteria.order ?? true,
      state?.currentPath
    );

    // Load directory when path changes
    effect(() => {
      const path = this.currentPath();
      this.loadDirectory(path);
    });

    // Refresh directory when videos in current view are updated/deleted
    this.videoUpdateEventService.onEvent().pipe(takeUntilDestroyed()).subscribe(event => {
      const isAffected = (event: VideoUpdateEvent) => {
        const ids = new Set(event.videoIds);
        const contents = this.directoryContents().data;
        if (!contents) return false;
        return contents.some(item => ids.has(item.node.id));
      }
      if (isAffected(event)) {
        this.refreshDirectory();
      }
    });
  }

  ngOnDestroy(): void {
    this.pathHistoryService.clearAllHistory();
  }

  // ─── Directory Data Loading ────────────────────────────────────────

  private loadDirectory(path: string[], skipCache: boolean = false, recursiveCalculation: boolean = true) {
    this.directorySubscription?.unsubscribe();
    const relativePath =  path.length > 0 ? path.join('/') : undefined;
    this.directorySubscription = this.gqlService.browseDirectoryQuery(relativePath, skipCache, recursiveCalculation)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if(!result.loading && result.data) {
            const newState = this.getRefreshState();
            if(newState?.sortCriteria){
              this.sortCriteria.set(newState.sortCriteria);
              this.sortItemsBy(newState.sortCriteria, result.data);
              this.directoryContents.set({...this.directoryContents(), loading: result.loading, error: result.error});
              setTimeout(() => {
                if(newState !== undefined){
                  this.scrollTo(newState.scrollPosition);
                }
              }, 200);
            }
            this.setRefreshState(
              newState?.scrollPosition ?? 0, 
              newState?.sortCriteria?.index ?? 0, 
              newState?.sortCriteria?.order ?? true, 
              newState?.currentPath ?? (path.length > 0 ? path : this.currentPath())
            );
          }else{
            this.directoryContents.set(result);
          }
          this.selectedIds.set(new Set());
        },
        error: (err) => {
          this.toastService.emitErrorOrWarning('Failed to load directory: ' + err.message, ToastType.Error);
        }
      });
  }

  refreshDirectory() {
    const path = this.currentPath();
    this.setRefreshState(
      this.getParentScrollContainer()?.scrollTop ?? 0, 
      this.sortCriteria().index, 
      this.sortCriteria().order, 
      path
    );
    this.loadDirectory(path, true, false);
  }

  refreshSelectedDirectory(item: FileBrowseNode) {
    this.gqlService.getDirectoryMetadataQuery(
      this.currentPath().join('/') + '/' + item.node.name
    )
    .pipe(takeUntilDestroyed(this.destroyRef))
    .subscribe({
      next: (result) => {
        if (result.data) {
          this.directoryContents.update(contents => {
            const updatedData = contents.data!.map(entry => {
              if (entry.node.id === item.node.id && entry.node.isDir && result.data) {
                return {
                  ...entry,
                  node: {
                    ...entry.node,
                    size: result.data.totalSize,
                    lastModifyTime: result.data.lastModifiedTime
                  }
                };
              }
              return entry;
            });
            return { ...contents, data: updatedData };
          });
        }
      },
      error: (err) => {
        this.toastService.emitErrorOrWarning('Failed to refresh directory metadata: ' + err.message, ToastType.Error);
      }
    });
  }

  // ─── Directory Navigation ──────────────────────────────────────────

  onClickFileBrowseNode(node: FileBrowseNode) {
    if(!node.node.isDir) {
      this.toggleSelection(node.node.id);
      return;
    };
    const newPath = [...this.currentPath(), node.node.name];
    this.setRefreshState(0, this.sortCriteria().index, this.sortCriteria().order, newPath);
    this.currentPath.set(newPath);
    this.pathHistoryService.pushNewPath(this.currentPath());
  }

  navigateToPath(path: string[]) {
    this.setRefreshState(0, this.sortCriteria().index, this.sortCriteria().order, path);
    this.currentPath.set(path);
  }

  // ─── Selection ─────────────────────────────────────────────────────

  toggleSelection(id: string) {
    this.selectedIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  toggleSelectAll() {
    const contents = this.directoryContents().data;
    if (!contents) return;

    const selectableItems = contents.filter(item => !item.node.isDir);
    const allSelected = selectableItems.length > 0
      && selectableItems.every(item => this.selectedIds().has(item.node.id));

    if (allSelected) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(selectableItems.map(item => item.node.id)));
    }
  }

  // ─── Sorting ───────────────────────────────────────────────────────

  toggleSort(columnIndex: number){
    this.sortCriteria.update(criteria => {
      if (criteria.index === columnIndex) {
        // Toggle sort order
        criteria.order = !criteria.order;
      } else {
        criteria.index = columnIndex;
        criteria.order = true;
      }
      return criteria;
    });
    this.sortItemsBy(this.sortCriteria(), this.directoryContents().data);
  }

  sortItemsBy(sortCriteria: SortCriterion, contents: FileBrowseNode[] | null) {
    if (!contents) return;
    let sortedContents = [...contents];

    const sortComparator = comparatorBySortOption(sortCriteria);
    sortedContents.sort(sortComparator);
    this.directoryContents.set({ ...this.directoryContents(), data: sortedContents });
  }

  // ─── Dialog Operations result ─────────────────────────────────────────────

  operationResult(result: boolean) {
    if (!result) return;
    else {
      this.refreshDirectory();
      this.selectedIds.set(new Set());
    }
  }

  // ─── DOM Utilities ─────────────────────────────────────────────────

  private getParentScrollContainer(): HTMLElement | null {
    return document.getElementById(environment.containerIds.rootMainContainerId);
  }

  scrollTo(position: number) {
    const mainContainer = this.getParentScrollContainer();
    if (mainContainer) {
      mainContainer.scrollTo({ top: position, behavior: 'smooth' });
    }
  }

  updateTableWidth(width: number) {
    this.tableWidth.set(width);
  }
}
