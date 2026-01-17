import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { startWith } from 'rxjs/operators';

import { SearchField, VideoTagsMappingInput } from '../../../core/graphql/generated/graphql';
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
    tagInput: [''],
    mode: ['append' as 'append' | 'remove']
  });

  tags = signal<string[]>([]);
  isSaving = signal<boolean>(false);

  tagSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(
      this.form.controls.tagInput.valueChanges.pipe(
        startWith(this.form.controls.tagInput.value),
      ),
      SearchField.Tag
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  );

  addTag(tagValue?: string) {
    const value = tagValue || this.form.get('tagInput')?.value;

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
    if (this.tags().length === 0) return;

    this.isSaving.set(true);

    const mappings: VideoTagsMappingInput[] = this.videos.map(video => ({
      videoId: video.id,
      tags: this.tags()
    }));

    const isAppend = this.form.value.mode === 'append';

    this.gqlService.batchUpdateVideoTagsMutation(mappings, isAppend).subscribe({
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