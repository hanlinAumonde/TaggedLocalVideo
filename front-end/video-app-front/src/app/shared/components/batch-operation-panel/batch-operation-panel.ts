import { Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatRadioModule } from '@angular/material/radio';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { 
  BatchResultType, 
  DirectoryVideosBatchOperationInput, 
  SearchField, 
  VideosBatchOperationInput 
} from '../../../core/graphql/generated/graphql';
import { GqlService } from '../../../services/GQL-service/GQL.service';
import { ValidationService } from '../../../services/validation-service/validation.service';
import { startWith, Subject, takeUntil, takeWhile } from 'rxjs';
import { ToastService } from '../../../services/toast-service/toast.service';
import { ToastDisplayer } from "../../../shared/components/toast-displayer/toast-displayer";
import { BatchPanelData } from '../../models/panels.model';

@Component({
  selector: 'app-batch-tags-panel',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatChipsModule,
    MatAutocompleteModule,
    MatIconModule,
    MatRadioModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatProgressBarModule,
    ToastDisplayer
],
  templateUrl: './batch-operation-panel.html'
})
export class BatchOperationPanel implements OnDestroy {
  private dialogRef = inject(MatDialogRef<BatchOperationPanel>);
  private data = inject<BatchPanelData>(MAT_DIALOG_DATA);
  private formBuilder = inject(FormBuilder);
  private gqlService = inject(GqlService);
  private validationService = inject(ValidationService);
  private toastService = inject(ToastService);

  readonly isVideoMode = this.data.mode === 'videos';
  readonly videoIds = this.data.videos ?? new Set<string>();
  readonly directoryPath = this.data.selectedDirectoryPath ?? '';

  form = this.formBuilder.group({
    authorInput: ['', [this.validationService.authorValidator()]],
    tagInput: ['', [this.validationService.tagValidator()]],
    mode: ['append' as 'append' | 'remove']
  });

  get authorInput() { return this.form.get('authorInput') as FormControl<string>; }
  get tagInput() { return this.form.get('tagInput') as FormControl<string>; }

  newAuthor = toSignal(
    this.authorInput.valueChanges.pipe(startWith(this.authorInput.value)), 
    { initialValue: '' }
  );

  tags = signal<string[]>([]);
  isSaving = signal<boolean>(false);

  authorSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(this.authorInput.valueChanges, SearchField.Author),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  );

  tagSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(
      this.tagInput.valueChanges.pipe(startWith(this.tagInput.value)),
      SearchField.Tag
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  );

  tagsError = computed(() => {
    const result = this.validationService.validateTagsArray(this.tags());
    return result.valid ? null : result.error;
  });

  processingMessage = signal<string>('');
  private destroy$ = new Subject<void>();

  addTag(tagValue?: string) {
    const value = tagValue ?? this.tagInput.value;

    if (!value || value.trim() === '') {
      return;
    }

    const trimmedTag = value.trim();

    const tagValidation = this.validationService.validateTag(trimmedTag);
    if (!tagValidation.valid) {
      return;
    }

    const tagsArrayValidation = this.validationService.validateTagsArray([...this.tags(), trimmedTag]);
    if (!tagsArrayValidation.valid) {
      return;
    }

    if (this.tags().includes(trimmedTag)) {
      this.form.patchValue({ tagInput: '' });
      return;
    }

    this.tags.update(tags => [...tags, trimmedTag]);
    this.form.patchValue({ tagInput: '' });
  }

  selectAuthorSuggestion(author: string) {
    this.form.patchValue({ authorInput: author });
  }

  selectTagSuggestion(tag: string) {
    this.addTag(tag);
  }

  removeTag(tag: string) {
    this.tags.update(tags => tags.filter(t => t !== tag));
  }

  onTagInputEnter(event: Event) {
    event.preventDefault();
    this.addTag();
  }

  handleSave() {
    if (this.tags().length === 0 && this.newAuthor() === '' && this.isVideoMode) return;
    if (this.form.invalid || this.tagsError()) return;
    console.log("toggling saving to true")
    this.isSaving.set(true);

    const tagsOperation = this.tags().length > 0 ? {
      tags: this.tags(),
      append: this.form.value.mode === 'append'
    } : undefined;

    const author = this.form.value.authorInput && this.form.value.authorInput.trim() !== ''
      ? this.form.value.authorInput.trim()
      : undefined;

    const subscription$ = this.isVideoMode
      ? this.gqlService.batchUpdateVideosSubscription({
          videoIds: Array.from(this.videoIds),
          tagsOperation,
          author
        } as VideosBatchOperationInput)
      : this.gqlService.batchUpdateDirectorySubscription({
          relativePath: { relativePath: this.directoryPath },
          tagsOperation,
          author
        } as DirectoryVideosBatchOperationInput);

    subscription$.pipe(
      takeWhile(result => result.data?.result?.resultType === undefined, true),
      takeUntil(this.destroy$)
    )
    .subscribe({
      next: (result) => {
        if(result.data?.result?.resultType === undefined && result.data?.status){
          this.processingMessage.set(result.data.status);
        }else if(result.data?.result?.resultType){
          this.isSaving.set(false);
          this.processingMessage.set('');
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
            case BatchResultType.AlreadyUpToDate:
              this.toastService.emitErrorOrWarning(
                'All selected videos are already up to date. No changes were made.', 
                'warning'
              );
              break;
          }
        } else {
          this.toastService.emitErrorOrWarning(
            'Batch update failed. Please try again.', 
            'error', true
          );
          this.processingMessage.set('');
        }
      },
      error: (err) => {
        this.isSaving.set(false);
        this.toastService.emitErrorOrWarning(
          'Error performing batch update: ' + err.message, 
          'error'
        );
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  isInvalid = computed(() => 
    this.form.invalid || this.tagsError() ? true : false 
    || (this.tags().length === 0 && this.newAuthor() === '' && this.isVideoMode)
  );

  handleCancel() {
    this.dialogRef.close();
  }
}