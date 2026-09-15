from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIProvider(Protocol):
    """Common interface every LLM provider (Ollama, OpenAI, Azure OpenAI) implements.

    See architecture/AI_ARCHITECTURE.md for the design this protocol supports —
    agents depend on this interface, never a concrete provider class.
    """

    async def complete(
        self,
        prompt: str,
        *,
        response_schema: type[SchemaT],
        temperature: float = 0.2,
    ) -> SchemaT: ...
