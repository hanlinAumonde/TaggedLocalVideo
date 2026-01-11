import { Video, UpdateVideoMetadataInput } from '../../core/graphql/generated/graphql';

/**
 * 组件模式
 */
export type VideoEditPanelMode = 'full' | 'filter';

/**
 * 编辑表单状态
 */
export interface EditFormState {
  name: string;
  author: string;
  loved: boolean;
  introduction: string;
  tags: string[];
}

/**
 * 保存事件数据
 */
export type SaveEventData = UpdateVideoMetadataInput | string[];

/**
 * 组件输入参数
 */
export interface VideoEditPanelInput {
  mode: VideoEditPanelMode;
  video?: Video;
  selectedTags?: string[];
}

/**
 * 作者建议项
 */
export interface AuthorSuggestion {
  value: string;
}

/**
 * 标签建议项
 */
export interface TagSuggestion {
  value: string;
}
