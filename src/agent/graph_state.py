from typing import TypedDict

from llm.structured_output.symantic_analysis import QueryIR


class CustomAgentState(TypedDict):
    messages: list[str] | None
    symantic_analysis: QueryIR