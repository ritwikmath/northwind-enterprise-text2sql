"""Reconcile a model-produced SQLQueryIR with the schema that was actually retrieved.

The model turns the semantic analysis into a query over columns. Whether that query
mirrors the user's phrasing term for term is not checkable here — user wording is
open-ended and will not line up with schema names — so it is not checked. What is
checkable is whether every column the model named exists in the retrieved schema.

What comes back from a column that does not exist is *text*, never a column reference.
An unresolved part of a request is by definition one no column expresses: reporting it
as `orders.refund_status` would assert the very thing that just failed, and would name
a column that exists nowhere. Downstream the unresolved text is a retrieval query —
against a business glossary, against example SQL, neither of which exists yet — and
those are searched by meaning, so what they need is words, not a fabricated identifier.

So a binding whose column is absent is dropped from the query and its subject is added
to the unresolved text, leaving an IR that only ever references real columns.
"""

from llm.structured_output.schema_coverage import SQLQueryIR


def known_columns(documents: list[dict]) -> set[tuple[str, str]]:
    """The (table, column) pairs the retrieved schema actually contains."""
    return {
        (doc["table"], doc["column"])
        for doc in documents or []
        if doc.get("type") == "column" and doc.get("table") and doc.get("column")
    }


def __describe(binding) -> str:
    """What a dropped binding was trying to get at, in words that can be searched.

    The model's own wording is used when it gave any. Otherwise the fabricated column
    name is the only trace left of what it meant, so it is spelled out as words —
    'refund status' rather than `orders.refund_status`. A made-up name is still a
    description of something; it is only useless as an identifier.
    """
    user_term = getattr(binding, "user_term", "")
    if user_term:
        return user_term
    return binding.column.column.replace("_", " ").strip()


def resolve_against_schema(
    sql_query_ir: SQLQueryIR, documents: list[dict]
) -> tuple[SQLQueryIR, list[str]]:
    """Split the query into the part the schema supports and the part it does not.

    Returns the query with every unbacked binding removed — safe to build SQL from,
    because each column in it was found in the retrieved schema — and the unresolved
    text: what the model itself reported as missing, plus the subject of each binding
    that was dropped. Both are plain descriptions, ready to be searched with.

    An empty unresolved list means the retrieved schema covers the whole request.
    """
    available = known_columns(documents)

    def backed(binding) -> bool:
        return (binding.column.table, binding.column.column) in available

    unresolved: list[str] = list(sql_query_ir.unresolved)

    def keep(bindings: list) -> list:
        kept = []
        for binding in bindings:
            if backed(binding):
                kept.append(binding)
            else:
                unresolved.append(__describe(binding))
        return kept

    fields = keep(sql_query_ir.fields)
    filters = keep(sql_query_ir.filters)
    grouping = keep(sql_query_ir.grouping)

    time_range = sql_query_ir.time_range
    if time_range is not None and not backed(time_range):
        unresolved.append(__describe(time_range))
        time_range = None

    # Two parts of a request can go missing for the same reason; the retrieval that
    # reads this gains nothing from being asked the same question twice.
    deduplicated = list(dict.fromkeys(text for text in unresolved if text))

    resolved = sql_query_ir.model_copy(
        update={
            "fields": fields,
            "filters": filters,
            "grouping": grouping,
            "time_range": time_range,
            "unresolved": deduplicated,
        }
    )

    return resolved, deduplicated
