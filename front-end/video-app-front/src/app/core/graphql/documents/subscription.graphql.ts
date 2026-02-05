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