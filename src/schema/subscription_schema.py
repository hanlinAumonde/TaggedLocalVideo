from typing import AsyncGenerator
import strawberry
from src.resolvers.subscription_resolver import get_subscription_resolver
from src.schema.types.fileBrowse_type import (
    BatchOperationStatus, 
    VideosBatchOperationInput
)

resolver = get_subscription_resolver()

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def batchUpdateSubscription(
        self, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in resolver.resolve_batch_operations(input, update=True):
            yield status

    @strawberry.subscription
    async def batchDeleteSubscription(
        self, input: VideosBatchOperationInput
    ) -> AsyncGenerator[BatchOperationStatus, None]:
        async for status in resolver.resolve_batch_operations(input, update=False):
            yield status
