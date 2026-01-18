import { Component, inject, signal, computed, effect, ViewChild, AfterViewInit, viewChild, OnInit } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { SelectionModel } from '@angular/cdk/collections';

import { GqlService } from '../../services/GQL-service/GQL-service';
import { BrowsedVideo, FileBrowseNode, VideoMutationDetail } from '../../shared/models/GQL-result.model';
import { VideoEditPanel } from '../../shared/components/video-edit-panel/video-edit-panel';
import { VideoEditPanelData, VideoEditPanelMode } from '../../shared/models/video-edit-panel.model';
import { BatchTagsPanel } from './batch-tags-panel/batch-tags-panel';
import { PageStateService } from '../../services/Page-state-service/page-state';
import { environment } from '../../../environments/environment';
import { RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-management',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatMenuModule,
    MatTooltipModule,
    MatTableModule,
    MatSortModule,
    RouterLink
  ],
  templateUrl: './management.html'
})
export class Management {
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);
  private statService = inject(PageStateService);

  //@ViewChild(MatSort) sort!: MatSort;
  private sort = viewChild(MatSort);

  displayedColumns: string[] = ['select', 'type', 'name', 'size', 'lastModifyTime', 'tags'];
  dataSource = new MatTableDataSource<FileBrowseNode>([]);
  selection = new SelectionModel<FileBrowseNode>(true, []);

  currentPath = signal<string[]>([]);
  isLoading = signal(false);
  hasError = signal(false);

  private selectionChanged = toSignal(this.selection.changed);

  currentPathDisplay = computed(() => {
    const path = this.currentPath();
    return path.length === 0 ? './' : './' + path.join('/');
  });

  isAtRoot = computed(() => this.currentPath().length === 0);
  selectedCount = signal<number>(this.selection.selected.length);
  hasSelection = signal<boolean>(this.selection.hasValue());

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

    // Update selection signals when selection changes
    effect(() => {
      this.selectionChanged();
      this.selectedCount.set(this.selection.selected.length);
      this.hasSelection.set(this.selection.hasValue());
    });
    
    // Set up sorting after view init
    effect(() => {
      const sort = this.sort();
      if (sort) {
        this.dataSource.sort = sort;
      }
    });

    // Custom sorting for mat-table
    this.dataSource.sortingDataAccessor = (data: FileBrowseNode, sortHeaderId: string): string | number => {
      switch (sortHeaderId) {
        case 'name': return data.node.name.toLowerCase();
        case 'size': return data.node.size;
        case 'lastModifyTime': return data.node.lastModifyTime;
        default: return '';
      }
    };

    
  }

  private loadDirectory(relativePath?: string) {
    this.isLoading.set(true);
    this.hasError.set(false);
    this.gqlService.browseDirectoryQuery(relativePath).subscribe(result => {
      this.isLoading.set(result.loading);
      this.hasError.set(!!result.error);
      this.dataSource.data = result.data ?? [];
      this.selection.clear();
    });
  }

  private getSelectedVideos(): BrowsedVideo[] {
    return this.selection.selected
      .filter(item => !item.node.isDir)
      .map(item => item.node);
  }

  refreshDirectory() {
    const path = this.currentPath();
    this.loadDirectory(path.length > 0 ? path.join('/') : undefined);
  }

  onRowClick(row: FileBrowseNode) {
    if (row.node.isDir) {
      this.currentPath.update(path => [...path, row.node.name]);
    } else {
      this.selection.toggle(row);
    }
  }

  navigateBack() {
    this.currentPath.update(path => path.slice(0, -1));
  }

  /** Whether the number of selected elements matches the total number of selectable rows. */
  isAllSelected(): boolean {
    const selectableRows = this.dataSource.data.filter(row => !row.node.isDir);
    return selectableRows.length > 0 && selectableRows.every(row => this.selection.isSelected(row));
  }

  /** Selects all rows if they are not all selected; otherwise clear selection. */
  toggleAllRows() {
    if (this.isAllSelected()) {
      this.selection.clear();
    } else {
      const selectableRows = this.dataSource.data.filter(row => !row.node.isDir);
      this.selection.select(...selectableRows);
    }
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
        // Update dataSource data directly
        this.dataSource.data = this.dataSource.data.map(item => {
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
      }
    });
  }

  deleteVideo(video: BrowsedVideo) {
    if (confirm(`Are you sure you want to delete "${video.name}"? This action cannot be undone.`)) {
      this.gqlService.deleteVideoMutation(video.id).subscribe(result => {
        if (result.data?.success) {
          const deletedVideoId = result.data?.video?.id ?? video.id;
          this.dataSource.data = this.dataSource.data.filter(item => item.node.id !== deletedVideoId);
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
        this.selection.clear();
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