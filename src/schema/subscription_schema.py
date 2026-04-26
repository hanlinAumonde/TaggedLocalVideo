from typing import AsyncGenerator

import strawberry
from src.resolvers.subscription_resolver import SubscriptionResolver
from src.schema.types.fileBrowse_type import (
    BatchOperationStatus,
    VideosBatchOperationInput,
)

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def batchUpdateSubscription(
        self, info: strawberry.Info, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in SubscriptionResolver.resolve_batch_operations(input=input, update=True, info=info):
            yield status

    @strawberry.subscription
    async def batchDeleteSubscription(
        self, info: strawberry.Info, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in SubscriptionResolver.resolve_batch_operations(input=input, update=False, info=info):
            yield status
