import strawberry
from strawberry.schema.config import StrawberryConfig

from src.logger import get_logger
from src.schema.mutation_schema import Mutation
from src.schema.query_schema import Query
from src.schema.subscription_schema import Subscription
from src.schema.types.scalars import BigInt

logger = get_logger("strawberry_execution")

class StrawberrySchema(strawberry.Schema):
    def __init__(self, query: strawberry.type, mutation: strawberry.type, subscription: strawberry.type):
        super().__init__(
            query=query,
            mutation=mutation,
            subscription=subscription,
            config=StrawberryConfig(
                scalar_map={
                    BigInt: strawberry.scalar(
                        name="BigInt",
                        description="A large integer that may exceed GraphQL's 32-bit Int limit. Serialized as a string.",
                        serialize=lambda v: str(v) if v is not None else None,
                        parse_value=lambda v: int(v) if v is not None else None,
                    ),
                }
            ),
        )
    
    def process_errors(self, errors, execution_context = None) -> None:
        for error in errors:
            logger.exception(f"GraphQL Execution Error: {error.message}")
        #return super().process_errors(errors, execution_context)
        
schema = StrawberrySchema(query=Query, mutation=Mutation, subscription=Subscription)