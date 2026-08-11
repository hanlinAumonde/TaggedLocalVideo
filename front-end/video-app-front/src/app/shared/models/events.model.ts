export enum VideoUpdateType {
  Updated = 'updated',
  Deleted = 'deleted',
  Migrated = 'migrated',
}

export interface VideoUpdateEvent {
  type: VideoUpdateType;
  videoIds: string[];
  directoryPath?: string;
  targetDirectoryPath?: string;
}