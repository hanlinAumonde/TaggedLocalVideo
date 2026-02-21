import { Component, computed, inject, input, output, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from "@angular/material/button";
import { PathHistoryService } from '../../../services/path-history-service/path-history.service';
import { ToastService } from '../../../services/toast-service/toast.service';
import { MatDialog } from '@angular/material/dialog';
import { BatchOperationPanel } from '../batch-operation-panel/batch-operation-panel';
import { MatMenuModule } from "@angular/material/menu";
import { DeleteCheckPanel } from '../delete-check-panel/delete-check-panel';
import { GqlService } from '../../../services/GQL-service/GQL.service';
import { BatchResultType } from '../../../core/graphql/generated/graphql';
import { DeleteCheckPanelData, DeleteType } from '../../models/panels.model';

@Component({
  selector: 'app-bottom-toolbar',
  imports: [MatIconModule, MatButtonModule, MatMenuModule],
  templateUrl: './bottom-toolbar.html'
})
export class BottomToolbar {
  pathHistoryService = inject(PathHistoryService)
  private toastService = inject(ToastService);
  private gqlService = inject(GqlService);
  private dialog = inject(MatDialog);

  currentPath = input.required<string[]>();
  hasSelection = input.required<boolean>();
  selectedCount = input.required<number>();
  selectedIds = input.required<Set<string>>();
  isAtRoot = input.required<boolean>();
  tableWidth = input.required<number>();

  batchOperationResult = output<boolean>();
  navigateBack = output<void>();
  navigateToPath = output<string[]>();

  paths = computed(() => {
    return ["Root", ...this.currentPath()];
  });

  toolbarVisible = signal<boolean>(true);

  toggleToolbar() {
    this.toolbarVisible.update(v => !v);
  }

  navigateOnClickButton(back: boolean = true){
    this.navigateToPath.emit(
      (back? this.pathHistoryService.popHisotryPath() : this.pathHistoryService.pushForwardPath())
       ?? []
    );
  }

  navigateOnClickPathElement(index: number){
    if(index < 0 || index > this.currentPath().length) return;
    if(index === this.currentPath().length) return;
    const targetPath = this.currentPath().slice(0, index);
    this.pathHistoryService.pushNewPath(targetPath);
    this.navigateToPath.emit(targetPath);
  }

  openBatchOperationPanel() {
    if (this.selectedIds().size === 0) return;

    const data = { mode: 'videos', videos: this.selectedIds() };
    
    this.toastService.clearAllToasts();

    const dialogRef = this.dialog.open(BatchOperationPanel, {
      width: '500px',
      data: data,
      disableClose: true,
    });

    dialogRef.afterClosed().subscribe(result => {
      this.batchOperationResult.emit(result? true : false);
    });
  }

  openBatchDeleteCheckPanel() {
    if (this.selectedIds().size === 0) return;
    this.toastService.clearAllToasts();

    const dialogRef = this.dialog.open(DeleteCheckPanel, {
      width: '400px',
      data: { 
        deleteType: DeleteType.Batch,
        videoCount: this.selectedIds().size,
        videoIds: this.selectedIds()
      } as DeleteCheckPanelData
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      this.batchOperationResult.emit(confirmed? true : false);
    })
  }
}
