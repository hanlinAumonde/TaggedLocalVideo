import { Component, inject, signal, computed, effect } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';

import { GqlService } from '../../services/GQL-service/GQL-service';
import { BrowseDirectoryDetail, BrowsedVideo } from '../../shared/models/GQL-result.model';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData, VideoEditPanelMode } from '../../shared/models/video-edit-panel.model';
import { BatchTagsPanel } from './batch-tags-panel/batch-tags-panel';

@Component({
  selector: 'app-management',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatMenuModule,
    MatTooltipModule
  ],
  templateUrl: './management.html',
  styleUrl: './management.css',
})
export class Management {
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);

  // Current path segments for navigation
  currentPath = signal<string[]>([]);

  // Directory contents
  directoryContents = signal(this.gqlService.initialSignalData<BrowseDirectoryDetail>([]));

  // Selected items for batch operations
  selectedIds = signal<Set<string>>(new Set());

  // Computed values
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
    // Load directory when path changes
    effect(() => {
      const path = this.currentPath();
      this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
    });
  }

  private loadDirectory(relativePath?: string) {
    this.gqlService.browseDirectoryQuery(relativePath).subscribe(result => {
      this.directoryContents.set(result);
      // Clear selection when navigating
      this.selectedIds.set(new Set());
    });
  }

  refreshDirectory() {
    const path = this.currentPath();
    this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
  }

  navigateToFolder(folderName: string) {
    this.currentPath.update(path => [...path, folderName]);
  }

  navigateBack() {
    this.currentPath.update(path => path.slice(0, -1));
  }

  // Selection methods
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

  // Format size for display
  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Format date for display
  formatDate(timestamp: number): string {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleDateString('zh-CN');
  }

  // Get visible tags (first 2) and remaining count
  getVisibleTags(video: BrowsedVideo): string[] {
    return video.tags?.slice(0, 2).map(t => t.name) ?? [];
  }

  getRemainingTagsCount(video: BrowsedVideo): number {
    const total = video.tags?.length ?? 0;
    return Math.max(0, total - 2);
  }

  getAllTags(video: BrowsedVideo): string {
    return video.tags?.map(t => t.name).join(', ') ?? '';
  }

  // Operations
  openEditPanel(video: BrowsedVideo) {
    const dialogRef = this.dialog.open(VideoEditPanel, {
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
    if (confirm(`确定要删除 "${video.name}" 吗？此操作不可恢复。`)) {
      this.gqlService.deleteVideoMutation(video.id).subscribe(result => {
        if (result.data?.success) {
          this.refreshDirectory();
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

  private getSelectedVideos(): BrowsedVideo[] {
    const contents = this.directoryContents().data;
    if (!contents) return [];
    return contents
      .filter(item => !item.node.isDir && this.selectedIds().has(item.node.id))
      .map(item => item.node);
  }
}