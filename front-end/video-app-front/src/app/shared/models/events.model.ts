export enum VideoUpdateType {
  Updated = 'updated',
  Deleted = 'deleted',
}

export interface VideoUpdateEvent {
  type: VideoUpdateType;
  /** Video IDs affected by this operation */
  videoIds: string[];
}