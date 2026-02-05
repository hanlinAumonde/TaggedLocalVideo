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
import { startWith } from 'rxjs/operators';

import {
  SearchField,
} from '../../../core/graphql/generated/graphql';
import {
  VideoEditPanelMode,
  VideoEditPanelData,
  EditableVideo,
} from '../../models/video-edit-panel.model';
import { GqlService } from '../../../services/GQL-service/GQL-service';
import { VideoMutationDetail } from '../../models/GQL-result.model';
import { ValidationService } from '../../../services/validation-service/validation-service';
import { ToastService } from '../../../services/toast-service/toast-service';
import { ToastDisplayer } from "../toast-displayer/toast-displayer";

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
    MatProgressSpinnerModule,
    ToastDisplayer
],
  templateUrl: './video-edit-panel.html'
})
export class VideoEditPanel implements OnInit {
  private dialogRef: MatDialogRef<VideoEditPanel, string[] | VideoMutationDetail> = inject(MatDialogRef);
  private data = inject<VideoEditPanelData>(MAT_DIALOG_DATA);
  private formBuilder = inject(FormBuilder);
  private gqlService = inject(GqlService);
  private validationService = inject(ValidationService);
  private toastService = inject(ToastService);

  mode: VideoEditPanelMode = this.data.mode;
  video = signal<EditableVideo | undefined>(this.data.video);
  selectedTags?: string[] = this.data.selectedTags;

  editForm = this.formBuilder.group({
      name: [this.video()?.name ?? '', [Validators.required, this.validationService.nameValidator()]],
      author: [this.video()?.author ?? '', [this.validationService.authorValidator()]],
      loved: [this.video()?.loved ?? false],
      introduction: [this.video()?.introduction ?? '', [this.validationService.introductionValidator()]],
      tagInput: ['', [this.validationService.tagValidator()]],
  });

  tags = signal<string[]>([]);
  isSaving = signal<boolean>(false);

  authorSuggestions = this.mode === 'full'?
    toSignal(
      this.gqlService.getSuggestionsQuery(
        this.editForm.controls.author.valueChanges,
        SearchField.Author
      ),
      { initialValue: this.gqlService.initialSignalData<string[]>([]) }
    )
    : signal(this.gqlService.initialSignalData<string[]>([]));

  tagSuggestions = toSignal(
    this.gqlService.getSuggestionsQuery(
      this.editForm.controls.tagInput.valueChanges.pipe(
        startWith(this.editForm.controls.tagInput.value)
      ),
      SearchField.Tag
    ),
    { initialValue: this.gqlService.initialSignalData<string[]>([]) }
  )

  tagsError = computed(() => {
    const result = this.validationService.validateTagsArray(this.tags());
    return result.valid ? null : result.error;
  });

  isFullMode = computed(() => this.mode === 'full');

  saveButtonText = computed(() =>
    this.mode === 'filter' ? 'Apply Filter' : (this.isSaving() ? 'Saving...' : 'Save')
  );

  ngOnInit() { this.initializeFormState(); }

  private initializeFormState() {
    if (this.mode === 'full' && this.video) {
      this.editForm.patchValue({
        name: this.video()?.name,
        author: this.video()?.author,
        loved: this.video()?.loved,
        introduction: this.video()?.introduction,
      });
      this.tags.set(this.video()?.tags.map(tag => tag.name) ?? []);
    } else if (this.mode === 'filter' && this.selectedTags) {
      this.tags.set([...this.selectedTags]);
    }
  }

  selectAuthorSuggestion(author: string) {
    this.editForm.patchValue({ author });
  }

  toggleLoved() {
    const currentLoved = this.editForm.get('loved')?.value;
    this.editForm.patchValue({ loved: !currentLoved });
  }

  addTag(tagValue?: string) {
    const value = tagValue || this.editForm.get('tagInput')?.value;

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
      if (this.editForm.valid && !this.tagsError() && this.video()) {
        const formValue = this.editForm.value;

        this.isSaving.set(true);

        this.gqlService.updateVideoMetadataMutation(
          this.video()!.id,
          formValue.loved ?? false,
          this.tags(),
          formValue.name ?? '',
          formValue.introduction ?? '',
          formValue.author ?? ''
        ).subscribe({
          next: (result) => {
            this.isSaving.set(false);
            if (result.data?.success) {
              this.dialogRef.close(result.data);
            } else {
              // update failed, keep the dialog open for user to retry
              this.toastService.emitErrorOrWarning('Failed to update video metadata', 'error');
            }
          },
          error: (err) => {
            this.isSaving.set(false);
            this.toastService.emitErrorOrWarning('Error updating video metadata: ' + err.message, 'error');
          }
        });
      }
    }
  }

  handleCancel() {
    this.dialogRef.close();
  }
}
