export enum VideoUpdateType {
  Updated = 'updated',
  Deleted = 'deleted',
}

export interface VideoUpdateEvent {
  type: VideoUpdateType;
  /** Video IDs affected by this operation */
  videoIds: string[];
  directoryPath?: string; // Optional, only for delete events that involve directories
}