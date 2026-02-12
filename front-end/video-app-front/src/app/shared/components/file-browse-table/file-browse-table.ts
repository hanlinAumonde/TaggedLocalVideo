import { Component, input, output, computed, viewChild, ElementRef, effect } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { ResultState, BrowsedVideo, FileBrowseNode } from '../../models/GQL-result.model';
import { SortCriterion } from '../../models/management.model';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-file-browse-table',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatMenuModule,
    MatTooltipModule,
    RouterLink
  ],
  templateUrl: './file-browse-table.html'
})
export class FileBrowseTable {
  // --- Inputs ---
  directoryContents = input.required<ResultState<FileBrowseNode[]>>();
  sortCriteria = input.required<SortCriterion>();
  selectedIds = input.required<Set<string>>();
  visibleTagsCount = input<number>(3);

  // --- Outputs ---
  sort = output<number>();
  refresh = output<void>();
  nodeClick = output<FileBrowseNode>();
  selectionToggle = output<string>();
  selectAllToggle = output<void>();
  editVideo = output<BrowsedVideo>();
  deleteVideo = output<BrowsedVideo>();
  batchSyncDirectory = output<string>();
  refreshDirectoryMeta = output<FileBrowseNode>();
  tableResize = output<number>();

  tableElement = viewChild<ElementRef>('tableElement');

  // --- Computed ---
  isAllSelected = computed(() => {
    const contents = this.directoryContents().data;
    if (!contents || contents.length === 0) return false;
    const selectableItems = contents.filter(item => !item.node.isDir);
    return selectableItems.length > 0 && selectableItems.every(item => this.selectedIds().has(item.node.id));
  });

  hasSelection = computed(() => this.selectedIds().size > 0);

  private resizeCallback() {
    const tableEl = this.tableElement();
    if(tableEl){
      const width = tableEl.nativeElement.offsetWidth;
      this.tableResize.emit(width);
    }
  }

  constructor(){
    effect(() => {
      this.resizeCallback();
    });
    window.addEventListener('resize', () => this.resizeCallback());
  }

  // --- Template Helpers ---

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
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
    return [environment.videopage_api, video.id];
  }
}
