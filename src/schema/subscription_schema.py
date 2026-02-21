from typing import AsyncGenerator

import strawberry

from src.resolvers.subscription_resolver import get_subscription_resolver
from src.schema.types.fileBrowse_type import BatchOperationStatus, DirectoryVideosBatchOperationInput, VideosBatchOperationInput


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def batchUpdateSubscription(
        self, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in get_subscription_resolver().resolve_batch_operations(input, update=True):
            yield status

    @strawberry.subscription
    async def batchDeleteSubscription(
        self, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in get_subscription_resolver().resolve_batch_operations(input, update=False):
            yield status

    @strawberry.subscription
    async def batchUpdateDirectorySubscription(
        self, input: DirectoryVideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in get_subscription_resolver().resolve_directory_batch_operations(input, update=True):
            yield status

    @strawberry.subscription
    async def batchDeleteDirectorySubscription(
        self, input: DirectoryVideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in get_subscription_resolver().resolve_directory_batch_operations(input, update=False):
            yield status