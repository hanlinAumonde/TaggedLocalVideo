import { UpdateVideoMetadataInput } from '../../core/graphql/generated/graphql';
import { BrowsedVideo, VideoDetail } from './GQL-result.model';


export type VideoEditPanelMode = 'full' | 'filter';


export interface EditFormState {
  name: string;
  author: string;
  loved: boolean;
  introduction: string;
  tags: string[];
}

export type SaveEventData = UpdateVideoMetadataInput | string[];

// VideoEditPanel requires: id, name, author, loved, introduction, tags
export type EditableVideo = VideoDetail | BrowsedVideo;

export interface VideoEditPanelData {
  mode: VideoEditPanelMode;
  video?: EditableVideo;
  selectedTags?: string[];
}


export interface AuthorSuggestion {
  value: string;
}

export interface TagSuggestion {
  value: string;
}
