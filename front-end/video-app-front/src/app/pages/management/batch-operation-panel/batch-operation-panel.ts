import { Component, computed, inject, signal } from '@angular/core';
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

import { BatchResultType, DirectoryVideosBatchOperationInput, SearchField, VideosBatchOperationInput } from '../../../core/graphql/generated/graphql';
import { GqlService } from '../../../services/GQL-service/GQL-service';
import { BrowsedVideo } from '../../../shared/models/GQL-result.model';
import { ValidationService } from '../../../services/validation-service/validation-service';
import { startWith } from 'rxjs';
import { ErrorHandlerService } from '../../../services/errorHandler-service/error-handler-service';

export interface BatchPanelData {
  mode: 'videos' | 'directory';
  videos?: BrowsedVideo[];
  selectedDirectoryPath?: string;
}

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
    MatExpansionModule
  ],
  templateUrl: './batch-operation-panel.html'
})
export class BatchOperationPanel {
  private dialogRef = inject(MatDialogRef<BatchOperationPanel>);
  private data = inject<BatchPanelData>(MAT_DIALOG_DATA);
  private formBuilder = inject(FormBuilder);
  private gqlService = inject(GqlService);
  private validationService = inject(ValidationService);
  private errorHandlerService = inject(ErrorHandlerService);

  readonly isVideoMode = this.data.mode === 'videos';
  readonly videos = this.data.videos ?? [];
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

    this.isSaving.set(true);

    const tagsOperation = this.tags().length > 0 ? {
      tags: this.tags(),
      append: this.form.value.mode === 'append'
    } : undefined;

    const author = this.form.value.authorInput && this.form.value.authorInput.trim() !== ''
      ? this.form.value.authorInput.trim()
      : undefined;

    const mutation$ = this.isVideoMode
      ? this.gqlService.batchUpdateVideosMutation({
          videoIds: this.videos.map(video => video.id),
          tagsOperation,
          author
        } as VideosBatchOperationInput)
      : this.gqlService.batchUpdateDirectoryMutation({
          relativePath: { relativePath: this.directoryPath },
          tagsOperation,
          author
        } as DirectoryVideosBatchOperationInput);

    mutation$.subscribe({
      next: (result) => {
        this.isSaving.set(false);
        if (result.data?.resultType === BatchResultType.Success) {
          this.dialogRef.close(true);
        } else if (result.data?.resultType === BatchResultType.PartialSuccess) {
          this.errorHandlerService.emitError('Batch update completed with partial success. Some videos may not have been updated.');
          this.dialogRef.close(true);
        } else {
          this.errorHandlerService.emitError('Batch update failed. No videos were updated.');
        }
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorHandlerService.emitError('Error performing batch update: ' + err.message);
        console.error('Error performing batch update:', err);
      }
    });
  }

  saveButtonDisabled = computed(() => {
    return this.isSaving() || this.form.invalid || this.tagsError()? true : false || 
      (this.tags().length === 0 && this.newAuthor() === '' && this.isVideoMode)
  });

  handleCancel() {
    this.dialogRef.close();
  }
}