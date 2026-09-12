"""Render a QueryIR as prose for the schema-coverage prompt.

The schema-coverage model must read the user's terms as claims about what was asked
for, never as facts about the database. Handing it the IR as JSON defeats that: a
FieldSelection serialises to something that reads like a schema declaration, so the
model assumes the field exists and takes its only job to be locating it. Prose keeps
every user term quoted and visibly unverified, which leaves the fetched schema as the
only thing that can say what columns exist.
"""

from llm.structured_output.symantic_analysis import Filter, QueryIR, TimeRange

__AGGREGATIONS = {
    "sum": "the total",
    "avg": "the average",
    "count": "the number of",
    "min": "the smallest",
    "max": "the largest",
}

__OPERATORS = {
    "equals": 'is "{value}"',
    "not_equals": 'is not "{value}"',
    "greater_than": 'is greater than "{value}"',
    "greater_than_or_equal": 'is greater than or equal to "{value}"',
    "less_than": 'is less than "{value}"',
    "less_than_or_equal": 'is less than or equal to "{value}"',
    "in": 'is one of "{value}"',
    "not_in": 'is not one of "{value}"',
    "contains": 'contains "{value}"',
    "starts_with": 'starts with "{value}"',
    "ends_with": 'ends with "{value}"',
    "between": 'falls between "{value}"',
}


def __describe_filter(spec: Filter) -> str:
    comparison = __OPERATORS.get(spec.operator, f'{spec.operator} "{spec.value}"')
    return (
        f'- something they called "{spec.field}", belonging to what they called '
        f'"{spec.entity}", {comparison.format(value=spec.value)} '
        f'(operator {spec.operator}, value "{spec.value}")'
    )


def __describe_time_range(spec: TimeRange) -> list[str]:
    lines = [
        f'- the period applies to a moment in time they called "{spec.field}"',
    ]
    if spec.expression:
        lines.append(f'- they expressed the period as "{spec.expression}"')
    if spec.value and spec.unit:
        lines.append(f"- the period spans {spec.value} {spec.unit}(s)")
    if spec.start_date:
        lines.append(f"- it starts at {spec.start_date}")
    if spec.end_date:
        lines.append(f"- it ends at {spec.end_date}")
    lines.append(f"- the period is {spec.type}; leave it symbolic, it is resolved to dates later")
    return lines


def render_query_ir(ir: QueryIR) -> str:
    """Describe what the user asked for in prose, with every term of theirs quoted."""
    lines: list[str] = []

    if ir.entities:
        subjects = ", ".join(f'"{entity}"' for entity in ir.entities)
        lines.append(f"The user is asking about what they called {subjects}.")
    if ir.intent:
        lines.append(f"They are trying to {', and '.join(ir.intent)}.")

    lines.append("")
    if ir.fields:
        lines.append("They want to see:")
        for field in ir.fields:
            described = (
                "something measurable" if field.type == "metric" else "something descriptive"
            )
            summarised = (
                f", summarised as {__AGGREGATIONS[field.aggregation]} ({field.aggregation})"
                if field.aggregation
                else ""
            )
            lines.append(f'- something they called "{field.name}" — {described}{summarised}')
    else:
        lines.append("They did not say which attributes they want to see.")

    lines.append("")
    if ir.filters:
        lines.append("They want to keep only the records where:")
        lines.extend(__describe_filter(spec) for spec in ir.filters)
    else:
        lines.append("They did not restrict which records they care about.")

    lines.append("")
    if ir.grouping:
        lines.append("They want the results broken down by:")
        lines.extend(f'- something they called "{group}"' for group in ir.grouping)
    else:
        lines.append("They did not ask for the results to be broken down.")

    lines.append("")
    if ir.time_range is not None:
        lines.append("They scoped the question to a time period:")
        lines.extend(__describe_time_range(ir.time_range))
    else:
        lines.append("They did not scope the question to a time period.")

    lines.append("")
    lines.append(
        "Everything quoted above is the user's own wording, taken from their question. "
        "None of it has been checked against any database. A term appearing above is not "
        "evidence that a table or column matching it exists."
    )

    return "\n".join(lines)


def __group_by_table(documents: list[dict]) -> tuple[dict[str, str], dict[str, list[dict]]]:
    """Split retrieved chunks into table descriptions and the columns belonging to each table.

    Retrieval returns tables and columns as independent chunks, so a column can arrive
    without its table's chunk and a table without any of its columns. Both are kept:
    the table name on each column chunk is what ties them together.
    """
    tables: dict[str, str] = {}
    columns: dict[str, list[dict]] = {}

    for doc in documents or []:
        if doc.get("type") == "table" and doc.get("name"):
            tables[doc["name"]] = doc.get("text", "")
        elif doc.get("type") == "column" and doc.get("table") and doc.get("column"):
            columns.setdefault(doc["table"], []).append(doc)

    for table in columns:
        tables.setdefault(table, "")

    return tables, columns


def render_schema(documents: list[dict]) -> str:
    """Describe the retrieved schema as tables, each with the columns that belong to it.

    Every column is shown underneath its own table so that the model can never bind a
    column to a table it does not belong to, and can see at a glance which table a
    given meaning lives in.
    """
    tables, columns = __group_by_table(documents)

    if not tables:
        return "No tables or columns were retrieved. There is nothing you can build a query from."

    lines: list[str] = []
    for table, description in tables.items():
        lines.append(f"Table: {table}")
        if description:
            lines.append(f"\t{description}")
        if not columns.get(table):
            lines.append("\tNo columns of this table were retrieved. You cannot use it.")
        for doc in columns.get(table, []):
            lines.append(f"\tColumn: {table}.{doc['column']}")
            if doc.get("text"):
                lines.append(f"\t\t{doc['text']}")
        lines.append("")

    lines.append(
        "These are the only tables and columns that exist. A column belongs to the table "
        "it is listed under and to no other. Anything not listed above does not exist, "
        "however reasonable a name for it would be."
    )

    return "\n".join(lines)
