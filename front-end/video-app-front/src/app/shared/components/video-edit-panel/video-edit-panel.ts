import {
  Component,
  OnInit,
  signal,
  computed,
  inject,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { debounceTime, distinctUntilChanged, switchMap, startWith } from 'rxjs/operators';

import {
  Video,
  SearchField,
} from '../../../core/graphql/generated/graphql';
import {
  VideoEditPanelMode,
  VideoEditPanelData,
} from '../../models/video-edit-panel.model';
import { GqlService } from '../../../services/GQL-service/GQL-service';

@Component({
  selector: 'app-video-edit-panel',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatChipsModule,
    MatAutocompleteModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './video-edit-panel.html'
})
export class VideoEditPanel implements OnInit {
  private dialogRef = inject(MatDialogRef<VideoEditPanel>);
  private data = inject<VideoEditPanelData>(MAT_DIALOG_DATA);
  private formBuilder = inject(FormBuilder);
  private gqlService = inject(GqlService);

  mode: VideoEditPanelMode = this.data.mode;
  video?: Video = this.data.video;
  selectedTags?: string[] = this.data.selectedTags;

  editForm: FormGroup = this.formBuilder.group({
      name: [this.video?.name ?? '', Validators.required],
      author: [this.video?.author ?? ''],
      loved: [this.video?.loved ?? false],
      introduction: [this.video?.introduction ?? ''],
      tagInput: [''],
  });

  tags = signal<string[]>([]);
  isSaving = signal<boolean>(false);

  authorSuggestions = this.mode === 'full'?
    toSignal(
      this.editForm.controls['author'].valueChanges.pipe(
        debounceTime(500),
        distinctUntilChanged(),
        switchMap(authorKeyword =>
          (!authorKeyword || authorKeyword.length < 1) ?
            [] : this.gqlService.getSuggestionsQuery(authorKeyword,SearchField.Author)
        )
      ), { initialValue: this.gqlService.initialSignalData<string[]>([]) }
    ) : signal(this.gqlService.initialSignalData<string[]>([]));

  tagSuggestions = toSignal(
    this.editForm.controls['tagInput'].valueChanges.pipe(
      startWith(this.editForm.controls['tagInput'].value),
      debounceTime(500),
      distinctUntilChanged(),
      switchMap(tagKeyword =>
        (!tagKeyword || tagKeyword.length < 1)?
          this.gqlService.getTopTagsAsSuggestionQuery()
          : this.gqlService.getSuggestionsQuery(tagKeyword,SearchField.Tag)
      )
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  )

  isFullMode = computed(() => this.mode === 'full');

  saveButtonText = computed(() =>
    this.mode === 'filter' ? 'Apply Filter' : (this.isSaving() ? 'Saving...' : 'Save')
  );

  ngOnInit() { this.initializeFormState(); }

  private initializeFormState() {
    if (this.mode === 'full' && this.video) {
      this.editForm.patchValue({
        name: this.video.name,
        author: this.video.author,
        loved: this.video.loved,
        introduction: this.video.introduction,
      });
      this.tags.set(this.video.tags.map(tag => tag.name));
    } else if (this.mode === 'filter' && this.selectedTags) {
      this.tags.set([...this.selectedTags]);
    }
  }

  selectAuthorSuggestion(author: string) {
    this.editForm.patchValue({ author });
  }

  addTag(tagValue?: string) {
    const value = tagValue || this.editForm.get('tagInput')?.value;

    if (!value || value.trim() === '') {
      return;
    }

    const trimmedTag = value.trim();

    if (this.tags().includes(trimmedTag)) {
      this.editForm.patchValue({ tagInput: '' });
      return;
    }

    this.tags.update(tags => [...tags, trimmedTag]);

    this.editForm.patchValue({ tagInput: '' });
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
    if (this.mode === 'filter') {
      this.dialogRef.close(this.tags());
    } 
    else {
      if (this.editForm.valid && this.video) {
        const formValue = this.editForm.value;

        this.isSaving.set(true);

        this.gqlService.updateVideoMetadataMutation(
          this.video.id,
          formValue.name,
          formValue.introduction || '',
          this.tags(),
          formValue.author || '',
          formValue.loved
        ).subscribe({
          next: (result) => {
            this.isSaving.set(false);
            if (result.data) {
              this.dialogRef.close({ success: true, data: result.data });
            } else {
              // update failed, keep the dialog open for user to retry
              console.error('Failed to update video metadata');
            }
          },
          error: (err) => {
            this.isSaving.set(false);
            console.error('Error updating video metadata:', err);
          }
        });
      }
    }
  }

  handleCancel() {
    this.dialogRef.close();
  }
}
