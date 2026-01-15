import { UpdateVideoMetadataInput } from '../../core/graphql/generated/graphql';
import { VideoDetail } from './GQL-result.model';


export type VideoEditPanelMode = 'full' | 'filter';


export interface EditFormState {
  name: string;
  author: string;
  loved: boolean;
  introduction: string;
  tags: string[];
}

export type SaveEventData = UpdateVideoMetadataInput | string[];

export interface VideoEditPanelData {
  mode: VideoEditPanelMode;
  video?: VideoDetail;
  selectedTags?: string[];
}


export interface AuthorSuggestion {
  value: string;
}

export interface TagSuggestion {
  value: string;
}
