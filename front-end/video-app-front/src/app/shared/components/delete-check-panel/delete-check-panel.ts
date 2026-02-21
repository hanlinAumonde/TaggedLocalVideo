import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { DeleteCheckPanelData, DeleteType } from '../../models/panels.model';
import { GqlService } from '../../../services/GQL-service/GQL.service';
import { Observable, tap } from 'rxjs';
import { ToastService } from '../../../services/toast-service/toast.service';
import { BatchResultType } from '../../../core/graphql/generated/graphql';
import { ToastDisplayer } from "../toast-displayer/toast-displayer";

@Component({
  selector: 'app-delete-check-panel',
  imports: [MatButtonModule, MatDialogActions, MatDialogClose, MatDialogTitle, MatDialogContent, ToastDisplayer],
  templateUrl: './delete-check-panel.html',
})
export class DeleteCheckPanel {
  readonly dialogRef = inject(MatDialogRef<DeleteCheckPanel>);
  readonly data = inject<DeleteCheckPanelData>(MAT_DIALOG_DATA);
  private gqlService = inject(GqlService);
  private toastService = inject(ToastService);
  private gqlRequest$!: Observable<any>;

  processingMessage = signal<string>("");
  isSaving = signal<boolean>(false);

  textToDelete = computed(() => {
    switch(this.data.deleteType){
      case DeleteType.Single:
        return "this video";
      case DeleteType.Batch:
        return `the selected ${this.data.videoCount} videos`;
      case DeleteType.Directory:
        return `all videos in the directory "${this.data.directoryPath}"`;
      default:
        return "the selected items";
    }
  });

  confirmDelete() {
    this.isSaving.set(true);
    const type = this.data.deleteType;
    if(!this.data.videoIds && !this.data.directoryPath) {
      this.isSaving.set(false);
      this.toastService.emitErrorOrWarning('No videoIds or directoryPath provided for deletion.', 'error');
      this.dialogRef.close(false);
      return;
    }
    switch(type){
      case DeleteType.Single:
        this.gqlRequest$ = this.processDeletionMutation();
        break;
      case DeleteType.Batch:
        this.gqlRequest$ = this.processBatchDeletion(
          this.gqlService.batchDeleteVideosSubscription(
          { videoIds: this.data.videoIds ? Array.from(this.data.videoIds) : [] })
        );
        break;
      case DeleteType.Directory:
        this.gqlRequest$ = this.processBatchDeletion(
          this.gqlService.batchDeleteDirectorySubscription(
          { relativePath: { relativePath: this.data.directoryPath ? this.data.directoryPath : "" } })
        );
        break;
    }
    if(!this.gqlRequest$) {
      this.toastService.emitErrorOrWarning('No deletion operation specified.', 'error');
      this.dialogRef.close(false);
      return;
    }
    this.gqlRequest$.subscribe({
      error: (err) => {
        this.isSaving.set(false);
        this.toastService.emitErrorOrWarning(`An error occurred during deletion: ${err.message || err}`, 'error');
        this.dialogRef.close(false);
      }
    })
  }

  processDeletionMutation(){
    const gqlRequest$ = this.gqlService.deleteVideoMutation(
          this.data.videoIds ? Array.from(this.data.videoIds)[0] : "");
    return gqlRequest$.pipe(
      tap(result => {
        this.isSaving.set(false);
        if(result.data?.success){
          this.dialogRef.close(true);
        }else{
          this.toastService.emitErrorOrWarning('Failed to delete video', 'error', true);
          this.dialogRef.close(false);
        }
      })
    )
  }

  processBatchDeletion(gqlRequest$: Observable<any>) {
    return gqlRequest$.pipe(
      tap(
        result => {
          if(result.data?.result?.resultType === undefined && result.data?.status){
            this.processingMessage.set(result.data.status);
          }else if(result.data?.result?.resultType){
            this.isSaving.set(false);
            const resultType = result.data.result.resultType;
            switch(resultType) {
              case BatchResultType.Success:
                this.dialogRef.close(true);
                break;
              case BatchResultType.PartialSuccess:
                this.toastService.emitErrorOrWarning(
                  `Batch update partially success. Some videos may not have been updated.
                  \nMessage: ${result.data.result.message ?? 'No additional information provided.'}`, 
                  'warning'
                );
                this.dialogRef.close(true);
                break;
              case BatchResultType.Failure:
                this.toastService.emitErrorOrWarning(
                  `Batch delete failed. Please try again.
                  \nMessage: ${result.data.result.message ?? 'No additional information provided.'}`, 
                  'error'
                );
                this.dialogRef.close(false);
                break;
            }
          }
        }
      )
    );
  }
}
