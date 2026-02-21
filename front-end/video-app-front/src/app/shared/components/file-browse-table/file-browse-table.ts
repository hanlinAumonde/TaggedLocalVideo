import { Component, input, output, computed, viewChild, ElementRef, effect, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { ResultState, BrowsedVideo, FileBrowseNode } from '../../models/GQL-result.model';
import { SortCriterion } from '../../models/management.model';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../services/toast-service/toast.service';
import { MatDialog } from '@angular/material/dialog';
import { BatchOperationPanel } from '../batch-operation-panel/batch-operation-panel';
import { DeleteCheckPanel } from '../delete-check-panel/delete-check-panel';
import { GqlService } from '../../../services/GQL-service/GQL.service';
import { DeleteCheckPanelData, DeleteType, VideoEditPanelData, VideoEditPanelMode } from '../../models/panels.model';
import { VideoEditPanel } from '../video-edit-panel/video-edit-panel';

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
  currentPath = input.required<string[]>();
  visibleTagsCount = input<number>(3);

  // --- Outputs ---
  sort = output<number>();
  refresh = output<void>();
  nodeClick = output<FileBrowseNode>();
  selectionToggle = output<string>();
  selectAllToggle = output<void>();
  editVideoResult = output<boolean>();
  deleteVideoResult = output<boolean>();
  batchSyncDirectoryResult = output<boolean>();
  refreshDirectoryMeta = output<FileBrowseNode>();
  tableResize = output<number>();

  tableElement = viewChild<ElementRef<HTMLTableElement>>('tableElement');

  private toastService = inject(ToastService);
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);

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
    effect(() => this.resizeCallback());
    window.addEventListener('resize', () => this.resizeCallback());
  }

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
        this.editVideoResult.emit(true);
      } else {
        this.editVideoResult.emit(false);
      }
    });
  }

  deleteVideo(video: BrowsedVideo) {
    const checkResult = this.dialog.open(DeleteCheckPanel, {
      width: '400px',
      data: {
        deleteType: DeleteType.Single,
        videoIds: new Set<string>([video.id])
       } as DeleteCheckPanelData
    })
    checkResult.afterClosed().subscribe(confirmed => {
      this.deleteVideoResult.emit(confirmed? true : false);
    });
  }

  deleteVideosInDirectory(dirPath: string) {
    const dialogRef = this.dialog.open(DeleteCheckPanel, {
      width: '400px',
      data: {
        deleteType: DeleteType.Directory,
        directoryPath: this.currentPath().join('/') + '/' + dirPath
       } as DeleteCheckPanelData
    });
    dialogRef.afterClosed().subscribe(confirmed => {
      this.deleteVideoResult.emit(confirmed? true : false);
    });
  }

  openBatchOperationPanel(dirName:string) {
    if(!dirName) return;

    const data = { mode: 'directory', selectedDirectoryPath: this.currentPath().join('/') + '/' + dirName! };
    
    this.toastService.clearAllToasts();

    const dialogRef = this.dialog.open(BatchOperationPanel, {
      width: '500px',
      data: data,
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe(result => {
      this.batchSyncDirectoryResult.emit(result? true : false);
    });
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
