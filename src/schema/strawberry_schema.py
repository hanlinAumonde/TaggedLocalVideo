import strawberry
from src.logger import get_logger
from src.schema.mutation_schema import Mutation
from src.schema.query_schema import Query

logger = get_logger("strawberry_execution")
    
class StrawberrySchema(strawberry.Schema):
    def __init__(self, query: strawberry.type, mutation: strawberry.type):
        super().__init__(
            query=query,
            mutation=mutation
        )
    
    def process_errors(self, errors, execution_context = None) -> None:
        for error in errors:
            logger.error(f"GraphQL Execution Error: {error.message}")
        #return super().process_errors(errors, execution_context)
        
schema = StrawberrySchema(query=Query, mutation=Mutation)