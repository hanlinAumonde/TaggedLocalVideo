import { gql } from 'apollo-angular';

export const MIGRATION_PREFLIGHT = gql`
  mutation MigrationPreflight($input: MigrationPreflightInput!) {
    migrationPreflight(input: $input) {
      valid
      sourceFileSize
      conflictExists
      spaceAvailable
      spaceSufficient
      alreadyMigrating
      sameLocation
      errorMessage
    }
  }
`;

export const CREATE_MIGRATION_TASK = gql`
  mutation CreateMigrationTask($input: CreateMigrationTaskInput!) {
    createMigrationTask(input: $input) {
      success
      errorMessage
      task {
        id
        sourcePath
        sourceCategory
        targetPath
        targetCategory
        fileName
        fileSize
        bytesTransferred
        status
        errorMessage
        failedStep
        conflictStrategy
        renamedTargetPath
        createdAt
        updatedAt
        completedAt
      }
    }
  }
`;

export const CANCEL_MIGRATION_TASK = gql`
  mutation CancelMigrationTask($input: MigrationTaskActionInput!) {
    cancelMigrationTask(input: $input) {
      success
      errorMessage
      task {
        id
        sourcePath
        targetPath
        fileName
        status
      }
    }
  }
`;

export const GET_MIGRATION_TASKS = gql`
  query GetMigrationTasks($input: MigrationTaskQueryInput!) {
    getMigrationTasks(input: $input) {
      totalCount
      page
      pageSize
      tasks {
        id
        sourcePath
        sourceCategory
        targetPath
        targetCategory
        fileName
        fileSize
        bytesTransferred
        status
        errorMessage
        failedStep
        conflictStrategy
        renamedTargetPath
        createdAt
        updatedAt
        completedAt
      }
    }
  }
`;

export const MIGRATION_PROGRESS = gql`
  subscription MigrationProgress($input: MigrationTaskActionInput!) {
    migrationProgressSubscription(input: $input) {
      taskId
      status
      bytesTransferred
      totalBytes
      progressPercentage
      message
    }
  }
`;

export const MIGRATION_RETRY = gql`
  subscription MigrationRetry($input: MigrationTaskActionInput!) {
    migrationRetrySubscription(input: $input) {
      taskId
      status
      bytesTransferred
      totalBytes
      progressPercentage
      message
    }
  }
`;
