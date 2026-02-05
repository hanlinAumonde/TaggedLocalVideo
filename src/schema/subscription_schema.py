import strawberry

from src.resolvers.subscription_resolver import get_subscription_resolver
from src.schema.types.fileBrowse_type import BatchOperationStatus


@strawberry.type
class Subscription:
    batchUpdateSubscription: BatchOperationStatus = strawberry.subscription(resolver=get_subscription_resolver().resolve_batch_update)

    batchUpdateDirectorySubscription: BatchOperationStatus = strawberry.subscription(resolver=get_subscription_resolver().resolve_directory_batch_update)