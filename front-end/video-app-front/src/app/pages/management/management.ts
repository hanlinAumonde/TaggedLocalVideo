import { Component, inject, signal, computed, effect } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';

import { GqlService } from '../../services/GQL-service/GQL-service';
import {
  BrowseDirectoryDetail,
  BrowsedVideo,
  FileBrowseNode,
  VideoMutationDetail
} from '../../shared/models/GQL-result.model';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData, VideoEditPanelMode } from '../../shared/models/video-edit-panel.model';
import { BatchOperationPanel } from './batch-operation-panel/batch-operation-panel';
import { PageStateService } from '../../services/Page-state-service/page-state';
import { environment } from '../../../environments/environment';
import { SortCriterion, ItemsSortOption, ManagementRefreshState, comparatorBySortOption } from '../../shared/models/management.model';
import { RouterLink } from '@angular/router';
import { DeleteCheckPanel } from './delete-check-panel/delete-check-panel';
import { ToastService } from '../../services/toast-service/toast-service';

@Component({
  selector: 'app-management',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatMenuModule,
    MatTooltipModule,
    RouterLink
  ],
  templateUrl: './management.html'
})
export class Management {
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);
  private statService = inject(PageStateService);
  private toastService = inject(ToastService);

  SORT_OPTIONS = ItemsSortOption;

  // true for ascending, false for descending
  sortCriteria = signal<SortCriterion>({
    index: 0,
    order: true
  });

  currentPath = signal<string[]>([]);

  directoryContents = signal(this.gqlService.initialSignalData<BrowseDirectoryDetail>([]));

  selectedIds = signal<Set<string>>(new Set());

  visibleTagsCount = signal<number>(3);

  currentPathDisplay = computed(() => {
    const path = this.currentPath();
    return path.length === 0 ? './' : './' + path.join('/');
  });

  isAtRoot = computed(() => this.currentPath().length === 0);

  selectedCount = computed(() => this.selectedIds().size);

  isAllSelected = computed(() => {
    const contents = this.directoryContents().data;
    if (!contents || contents.length === 0) return false;
    const selectableItems = contents.filter(item => !item.node.isDir);
    return selectableItems.length > 0 && selectableItems.every(item => this.selectedIds().has(item.node.id));
  });

  hasSelection = computed(() => this.selectedIds().size > 0);

  constructor() {
    const hasStatePredicate = (state: string[] | undefined) =>
      state && Array.isArray(state);

    const state = this.statService.getState<string[]>(
      environment.management_api + environment.refreshKey,
      false
    );

    if (hasStatePredicate(state)) {
      this.currentPath.set(state!);
    }

    this.setRefreshState();

    // Load directory when path changes
    effect(() => {
      const path = this.currentPath();
      this.statService.setState(
        environment.management_api + environment.refreshKey,
        path,
        false
      );
      this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
    });
  }

  // ─── Directory Data Loading ────────────────────────────────────────

  private loadDirectory(relativePath?: string, refreshCache: boolean = false) {
    this.gqlService.browseDirectoryQuery(relativePath, refreshCache).subscribe({
      next: (result) => {
        // Sometimes this condition can be true twice in a single request, because of the cache update after the request
        // So for the second time, newState will be undefined, and we shoudn't apply the sorting and scrolling again
        if(!result.loading && result.data) {
          const newState = this.statService.getState<ManagementRefreshState>(
            environment.management_api + environment.refreshKey + environment.scrollKey,
            false
          );
          if(newState?.sortCriteria){
            this.sortCriteria.set(newState.sortCriteria);
            this.sortItemsBy(this.sortCriteria().index, result.data);
            this.directoryContents.set({...this.directoryContents(), loading: result.loading, error: result.error});
            setTimeout(() => {
              if(newState !== undefined){
                this.scrollTo(newState.scrollPosition);
              }
            }, 200);
          }
        }else{
          this.directoryContents.set(result);
        }
        this.selectedIds.set(new Set());
      },
      error: (err) => {
        this.toastService.emitErrorOrWarning('Failed to load directory: ' + err.message, 'error');
      }
    });
  }

  refreshDirectory() {
    const path = this.currentPath();
    // get current scroll position
    this.setRefreshState(this.getParentScrollContainer()?.scrollTop, {
      index: this.sortCriteria().index,
      order: !this.sortCriteria().order
    });
    this.loadDirectory(path.length > 0 ? path.join('/') : undefined, true);
  }

  refreshSelectedDirectory(item: FileBrowseNode) {
    this.gqlService.getDirectoryMetadataQuery(
      this.currentPath().join('/') + '/' + item.node.name
    ).subscribe({
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
        this.toastService.emitErrorOrWarning('Failed to refresh directory metadata: ' + err.message, 'error');
      }
    });
  }

  setRefreshState(scrollTop: number = 0, sortCriteria: SortCriterion = { index: 0, order: false }) {
    this.statService.setState<ManagementRefreshState>(
      environment.management_api + environment.refreshKey + environment.scrollKey,
      { scrollPosition: scrollTop, sortCriteria: sortCriteria} as ManagementRefreshState,
      false
    );
  }

  // ─── Directory Navigation ──────────────────────────────────────────

  onClickFileBrowseNode(node: FileBrowseNode) {
    if(!node.node.isDir) {
      this.toggleSelection(node.node.id);
      return;
    };
    this.setRefreshState(this.getParentScrollContainer()?.scrollTop);
    this.currentPath.update(path => [...path, node.node.name]);
  }

  navigateBack() {
    this.setRefreshState(this.getParentScrollContainer()?.scrollTop);
    this.currentPath.update(path => path.slice(0, -1));
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

    if (this.isAllSelected()) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(selectableItems.map(item => item.node.id)));
    }
  }

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
  }

  private getSelectedVideos(): BrowsedVideo[] {
    const contents = this.directoryContents().data;
    if (!contents) return [];
    return contents
      .filter(item => !item.node.isDir && this.selectedIds().has(item.node.id))
      .map(item => item.node);
  }

  // ─── Sorting ───────────────────────────────────────────────────────

  getSortOptionForColumn(columnIndex: number, asc: ItemsSortOption, desc: ItemsSortOption): ItemsSortOption {
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
    return this.sortCriteria().order ? asc : desc;
  }

  sortItemsBy(columnIndex: number, contents: FileBrowseNode[] | null) {
    if (!contents) return;
    let sortedContents = [...contents];

    const option = (() => {
      switch(columnIndex){
        case 0:
          return this.getSortOptionForColumn(0, ItemsSortOption.NAME_ASC, ItemsSortOption.NAME_DESC);
        case 1:
          return this.getSortOptionForColumn(1, ItemsSortOption.SIZE_ASC, ItemsSortOption.SIZE_DESC);
        case 2:
          return this.getSortOptionForColumn(2, ItemsSortOption.DATE_ASC, ItemsSortOption.DATE_DESC);
        default:
          return ItemsSortOption.NAME_ASC;
      }
    })();

    sortedContents.sort(comparatorBySortOption(option))
    this.directoryContents.set({ ...this.directoryContents(), data: sortedContents });
  }

  // ─── Dialog Operations ─────────────────────────────────────────────

  openEditPanel(video: BrowsedVideo) {
    const dialogRef: MatDialogRef<VideoEditPanel, VideoMutationDetail>
     = this.dialog.open(VideoEditPanel, {
      width: '500px',
      data: {
        mode: 'full' as VideoEditPanelMode,
        video: video
      } as VideoEditPanelData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.refreshDirectory();
      }
    });
  }

  deleteVideo(video: BrowsedVideo) {
    const checkResult = this.dialog.open(DeleteCheckPanel, {
      width: '400px'
    })
    checkResult.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.gqlService.deleteVideoMutation(video.id).subscribe(result => {
          if (result.data?.success) {
            this.refreshDirectory();
          }
        });
      }
    });
  }

  openBatchOperationPanel(mode: 'videos' | 'directory', dirName?:string) {
    const selectedVideos = this.getSelectedVideos();
    if (selectedVideos.length === 0 && mode === 'videos') return;
    if(mode === 'directory' && !dirName) return;

    const data = mode === 'videos' ? { mode: mode, videos: selectedVideos }
    : { mode: mode, selectedDirectoryPath: this.currentPath().join('/') + '/' + dirName! };

    this.toastService.clearAllToasts();

    const dialogRef = this.dialog.open(BatchOperationPanel, {
      width: '500px',
      data: data,
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.refreshDirectory();
        this.selectedIds.set(new Set());
        this.toastService.clearAllToastsBeyondDialog();
      }
    });
  }

  // ─── Template Helpers ──────────────────────────────────────────────

  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  formatDate(timestamp: number): string {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleDateString('zh-CN');
  }

  getVisibleTags(video: BrowsedVideo): string[] {
    return video.tags?.slice(0, this.visibleTagsCount()).map(t => t.name) ?? [];
  }

  getRemainingTagsCount(video: BrowsedVideo): number {
    const total = video.tags?.length ?? 0;
    return Math.max(0, total - this.visibleTagsCount());
  }

  getAllRemainingTags(video: BrowsedVideo): string {
    return video.tags?.slice(this.visibleTagsCount()).map(t => t.name).join(',  ') ?? '';
  }

  videoPage(video: BrowsedVideo) {
    return [environment.videopage_api, video.id]
  }

  // ─── DOM Utilities ─────────────────────────────────────────────────

  private getParentScrollContainer(): HTMLElement | null {
    return document.getElementById(environment.rootMainContainerId);
  }

  scrollTo(position: number) {
    const mainContainer = this.getParentScrollContainer();
    if (mainContainer) {
      mainContainer.scrollTo({ top: position, behavior: 'smooth' });
    }
  }
}
