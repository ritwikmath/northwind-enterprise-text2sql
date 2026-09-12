from operator import add
from typing import Annotated, TypedDict

from llm.structured_output.schema_coverage import SQLQueryIR
from llm.structured_output.symantic_analysis import QueryIR


class CustomAgentState(TypedDict):
    messages: Annotated[list[str], add]
    symantic_analysis: QueryIR
    columns: list[str] | None
    sql_query_ir: SQLQueryIR
    unresolved: list[str]
    schema_ir: bool
