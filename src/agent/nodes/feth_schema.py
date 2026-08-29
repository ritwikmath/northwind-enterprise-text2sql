from agent.graph_state import CustomAgentState
from knowledge import fetch_columns_tables_from_vectord_db


def fetch_schema_from_vector_db(state: CustomAgentState):
    symantic_analysis = state["symantic_analysis"]
    columns = set()
    for field in symantic_analysis.filters:
        columns.add(f"{field.entity}.{field.field}")
    for field in symantic_analysis.fields:
        columns.add(field.name)

    columns.update(symantic_analysis.entities)
    matched_schema = fetch_columns_tables_from_vectord_db(list(columns))

    return {"columns": matched_schema}