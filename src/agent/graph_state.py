from operator import add
from typing import Annotated, TypedDict

from llm.structured_output.symantic_analysis import QueryIR


class CustomAgentState(TypedDict):
    messages: Annotated[list[str], add]
    symantic_analysis: QueryIR
    columns: list[str] | None
    schema_enough: bool
