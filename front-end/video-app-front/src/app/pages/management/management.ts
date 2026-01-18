import { Component, inject, signal, computed, effect } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';

import { GqlService } from '../../services/GQL-service/GQL-service';
import { BrowseDirectoryDetail, BrowsedVideo, FileBrowseNode, VideoMutationDetail } from '../../shared/models/GQL-result.model';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData, VideoEditPanelMode } from '../../shared/models/video-edit-panel.model';
import { BatchTagsPanel } from './batch-tags-panel/batch-tags-panel';
import { PageStateService } from '../../services/Page-state-service/page-state';
import { environment } from '../../../environments/environment';
import { ItemsSortOption, comparatorBySortOption } from '../../shared/models/management.model';
import { RouterLink } from '@angular/router';

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

  SORT_OPTIONS = ItemsSortOption;
  // true for ascending, false for descending
  // First click: Column name initially ascending, size descending, date descending
  sortCriteria = signal<boolean[]>([false, true, true]);

  currentPath = signal<string[]>([]);

  // list of videos and folders in the current directory
  directoryContents = signal(this.gqlService.initialSignalData<BrowseDirectoryDetail>([]));

  // Selected items for batch operations
  selectedIds = signal<Set<string>>(new Set());

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
    const hasStatePredicate = (state: { currentPath: string[] } | undefined) => 
      state && Array.isArray(state.currentPath);

    const state = this.statService.getState<{ currentPath: string[] }>(
      environment.management_api + environment.refreshKey,
      false
    );

    if (hasStatePredicate(state)) {
      this.currentPath.set(state!.currentPath);
    }

    // Load directory when path changes
    effect(() => {
      const path = this.currentPath();
      this.statService.setState(environment.management_api + environment.refreshKey, { currentPath : path },false);
      this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
    });
  }

  private loadDirectory(relativePath?: string) {
    this.gqlService.browseDirectoryQuery(relativePath).subscribe(result => {
      this.directoryContents.set(result);
      this.selectedIds.set(new Set());
    });
  }

  private getSelectedVideos(): BrowsedVideo[] {
    const contents = this.directoryContents().data;
    if (!contents) return [];
    return contents
      .filter(item => !item.node.isDir && this.selectedIds().has(item.node.id))
      .map(item => item.node);
  }

  refreshDirectory() {
    const path = this.currentPath();
    this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
  }

  onClickFileBrowseNode(node: FileBrowseNode) {
    if(!node.node.isDir) {
      this.toggleSelection(node.node.id);
      return;
    };
    this.currentPath.update(path => [...path, node.node.name]);
  }

  navigateBack() {
    this.currentPath.update(path => path.slice(0, -1));
  }

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

  getSortOptionForColumn(columnIndex: number, asc: ItemsSortOption, desc: ItemsSortOption): ItemsSortOption {
    this.sortCriteria.update(arr => {
      arr[columnIndex] = !arr[columnIndex];
      return arr;
    });
    return this.sortCriteria()[columnIndex] ? asc : desc;
  }

  sortItemsBy(columnIndex: number) {
    const contents = this.directoryContents().data;
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

  // Get visible tags (first 4) and remaining count
  getVisibleTags(video: BrowsedVideo): string[] {
    return video.tags?.slice(0, 4).map(t => t.name) ?? [];
  }

  getRemainingTagsCount(video: BrowsedVideo): number {
    const total = video.tags?.length ?? 0;
    return Math.max(0, total - 4);
  }

  getAllRemainingTags(video: BrowsedVideo): string {
    return video.tags?.slice(4).map(t => t.name).join(', ') ?? '';
  }

  videoPage(video: BrowsedVideo) {
    return [environment.videopage_api, video.id]
  }

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
        //this.refreshDirectory();
        this.directoryContents.update(dir => {
          const contents = dir.data;
          if (!contents) return dir;
          const updatedContents = contents.map(item => {
            if (item.node.id === result.video?.id) {
              return {
                ...item,
                node: {
                  ...item.node,
                  name: result.video?.name ?? item.node.name,
                  introduction: result.video?.introduction ?? item.node.introduction,
                  author: result.video?.author ?? item.node.author,
                  tags: result.video?.tags ?? item.node.tags,
                }
              };
            }
            return item;
          });
          return { ...dir, data: updatedContents };
        });
      }
    });
  }

  deleteVideo(video: BrowsedVideo) {
    if (confirm(`Are you sure you want to delete "${video.name}"? This action cannot be undone.`)) {
      this.gqlService.deleteVideoMutation(video.id).subscribe(result => {
        if (result.data?.success) {
          //this.refreshDirectory();
          this.directoryContents.update(dir => {
            const contents = dir.data;
            if (!contents) return dir;
            const deletedVideoId = result.data?.video?.id ?? video.id;
            const updatedContents = contents.filter(item => item.node.id !== deletedVideoId);
            return { ...dir, data: updatedContents };
          })
        }
      });
    }
  }

  openBatchTagsPanel() {
    const selectedVideos = this.getSelectedVideos();
    if (selectedVideos.length === 0) return;

    const dialogRef = this.dialog.open(BatchTagsPanel, {
      width: '500px',
      data: { videos: selectedVideos }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.refreshDirectory();
        this.selectedIds.set(new Set());
      }
    });
  }

  scrollToTop() {
    const mainContainer = document.getElementById(environment.rootMainContainerId);
    if (mainContainer) {
      mainContainer.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
}