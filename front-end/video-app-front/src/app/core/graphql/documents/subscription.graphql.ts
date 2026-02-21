import { gql } from 'apollo-angular';

export const BATCH_UPDATE = gql`
    subscription BatchUpdateSubscription($input: VideosBatchOperationInput!) {
        batchUpdateSubscription(input: $input) {
            result {
                resultType
                message
            }
            status
        }
    }
`

export const DIRECTORY_BATCH_UPDATE = gql`
    subscription BatchUpdateDirectorySubscription($input: DirectoryVideosBatchOperationInput!) {
        batchUpdateDirectorySubscription(input: $input) {
            result {
                resultType
                message
            }
            status
        }
    }
`

export const BATCH_DELETE = gql`
    subscription BatchDeleteSubscription($input: VideosBatchOperationInput!) {
        batchDeleteSubscription(input: $input) {
            result {
                resultType
                message
            }
            status
        }   
    }
`

export const DIRECTORY_BATCH_DELETE = gql`
    subscription BatchDeleteDirectorySubscription($input: DirectoryVideosBatchOperationInput!) {
        batchDeleteDirectorySubscription(input: $input) {
            result {
                resultType
                message
            }
            status
        }
    }
`