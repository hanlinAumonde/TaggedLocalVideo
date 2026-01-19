import { Component, inject, signal } from '@angular/core';
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
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { map, startWith, tap } from 'rxjs/operators';

import { SearchField, VideosBatchOperationInput } from '../../../core/graphql/generated/graphql';
import { GqlService } from '../../../services/GQL-service/GQL-service';
import { BrowsedVideo } from '../../../shared/models/GQL-result.model';

export interface BatchTagsPanelData {
  videos: BrowsedVideo[];
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
    MatProgressSpinnerModule
  ],
  templateUrl: './batch-tags-panel.html'
})
export class BatchTagsPanel {
  private dialogRef = inject(MatDialogRef<BatchTagsPanel>);
  private data = inject<BatchTagsPanelData>(MAT_DIALOG_DATA);
  private formBuilder = inject(FormBuilder);
  private gqlService = inject(GqlService);

  videos = this.data.videos;

  form = this.formBuilder.group({
    authorInput: [''],
    tagInput: [''],
    mode: ['append' as 'append' | 'remove']
  });

  get authorInput() { return this.form.get('authorInput') as FormControl<string>; }
  get tagInput() { return this.form.get('tagInput') as FormControl<string>; }

  tags = signal<string[]>([]);
  isSaving = signal<boolean>(false);

  authorSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(
      this.authorInput.valueChanges,
      SearchField.Author
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  );

  tagSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(
      this.tagInput.valueChanges.pipe(
        startWith(this.tagInput.value),
      ),
      SearchField.Tag
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  );

  addTag(tagValue?: string) {
    const value = tagValue ?? this.tagInput.value;

    if (!value || value.trim() === '') {
      return;
    }

    const trimmedTag = value.trim();

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
    if (this.tags().length === 0 && this.authorInput.value.trim() === '') return;

    this.isSaving.set(true);

    const input: VideosBatchOperationInput = {
      videoIds: this.videos.map(video => video.id),
      tagsOperation: this.tags().length > 0 ? {
        tags: this.tags(),
        append: this.form.value.mode === 'append'
      } : undefined,
      author: this.form.value.authorInput && this.form.value.authorInput.trim() !== '' ? 
              this.form.value.authorInput.trim() : undefined
    };

    this.gqlService.batchUpdateVideosMutation(input).subscribe({
      next: (result) => {
        this.isSaving.set(false);
        if (result.data?.success) {
          this.dialogRef.close(true);
        }
      },
      error: () => {
        this.isSaving.set(false);
      }
    });
  }

  handleCancel() {
    this.dialogRef.close();
  }
}