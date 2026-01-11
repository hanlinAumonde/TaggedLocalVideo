import {
  Component,
  Input,
  Output,
  EventEmitter,
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
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { debounceTime, distinctUntilChanged, switchMap, startWith } from 'rxjs/operators';

import {
  Video,
  UpdateVideoMetadataInput,
  SearchField,
  GetTopTagsGQL,
} from '../../../core/graphql/generated/graphql';
import {
  VideoEditPanelMode,
  SaveEventData,
} from '../../models/video-edit-panel.model';
import { GqlService } from '../../../services/GQL-service/GQL-service';

@Component({
  selector: 'app-video-edit-panel',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
    MatChipsModule,
    MatAutocompleteModule,
    MatIconModule,
  ],
  templateUrl: './video-edit-panel.html'
})
export class VideoEditPanel implements OnInit {
  @Input({ required: true }) mode!: VideoEditPanelMode;
  @Input() video?: Video;
  @Input() selectedTags?: string[];

  @Output() onSave = new EventEmitter<SaveEventData>();
  @Output() onCancel = new EventEmitter<void>();

  private formBuilder = inject(FormBuilder)
  private getTopTagsGQL = inject(GetTopTagsGQL)
  private gqlService = inject(GqlService)

  editForm: FormGroup = this.formBuilder.group({
      name: ['', Validators.required],
      author: [''],
      loved: [false],
      introduction: [''],
      tagInput: [''],
  });

  tags = signal<string[]>([]);

  authorSuggestions = this.mode === 'full'?
    toSignal(
      this.editForm.controls['author'].valueChanges.pipe(
        debounceTime(500),
        distinctUntilChanged(),
        switchMap(authorKeyword => 
          (!authorKeyword || authorKeyword.length < 1) ? 
            [] : this.gqlService.getSuggestionsQuery(authorKeyword,SearchField.Author)
        )
      ), { initialValue: [] }
    ) : signal<string[]>([])

  tagSuggestions = toSignal(
    this.editForm.controls['tagInput'].valueChanges.pipe(
      startWith(this.editForm.controls['tagInput'].value),
      debounceTime(500),
      distinctUntilChanged(),
      switchMap(tagKeyword => 
        (!tagKeyword || tagKeyword.length < 1)?
          this.gqlService.getTopTagsQuery() : this.gqlService.getSuggestionsQuery(tagKeyword,SearchField.Tag)
      )
    ),
    { initialValue: [] }
  )

  isFullMode = computed(() => this.mode === 'full');
  
  saveButtonText = computed(() =>
    this.mode === 'filter' ? 'Apply Filter' : 'Save'
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

  /**
   * 处理标签输入框回车
   */
  onTagInputEnter(event: Event) {
    event.preventDefault();
    this.addTag();
  }

  handleSave() {
    if (this.mode === 'filter') {
      this.onSave.emit(this.tags());
    } else {
      if (this.editForm.valid && this.video) {
        const formValue = this.editForm.value;
        const updateData: UpdateVideoMetadataInput = {
          videoId: this.video.id,
          name: formValue.name,
          author: formValue.author || '',
          loved: formValue.loved,
          introduction: formValue.introduction || '',
          tags: this.tags(),
        };
        this.onSave.emit(updateData);
      }
    }
  }

  handleCancel() {
    this.onCancel.emit();
  }
}
