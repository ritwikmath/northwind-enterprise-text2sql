"""Render a SQLQueryIR as a SQL specification, with every value pulled out as a parameter.

The generating model is shown SQL and asked for SQL. The IR is not handed over as JSON:
a model reading JSON is doing a translation exercise and will paraphrase the structure,
whereas a model reading a SELECT skeleton is finishing a statement it can already see
the shape of. So the spec below *is* SQL — clause keywords, qualified column names,
real predicates — with only the parts the IR cannot determine left for the model.

Values never appear in it. Each one becomes a named placeholder here and is put in a
dict the model never receives, so there is no value in the prompt for the model to
inline, quote wrongly, or be talked into concatenating. That is the injection defence:
not a rule the model is asked to follow, but a value it was never given.

Named placeholders rather than positional ones, throughout. `:city` next to
`{"city": "London"}` can be read and checked at a glance; `%s` next to `["London"]`
is correct only as long as nobody edits the statement, and a reordered SELECT list is
a silent wrong answer rather than an error.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from llm import period
from llm.structured_output.schema_coverage import BoundFilter, ColumnRef, SQLQueryIR

# LIKE treats these as wildcards, so a user searching for "50%" or "a_b" means the
# characters themselves. They are escaped in the value and the escape is declared.
__LIKE_ESCAPE = "\\"

__COMPARISONS = {
    "equals": "=",
    "not_equals": "<>",
    "greater_than": ">",
    "greater_than_or_equal": ">=",
    "less_than": "<",
    "less_than_or_equal": "<=",
}


@dataclass
class SQLSpec:
    """The SQL skeleton shown to the model, and the values it was never shown."""

    text: str
    parameters: dict[str, Any] = field(default_factory=dict)
    omitted: list[str] = field(default_factory=list)

    @property
    def placeholders(self) -> frozenset[str]:
        return frozenset(self.parameters)


class __Parameters:
    """Assigns each value a readable, unique placeholder name.

    Named after the column it restricts, so the finished dict reads as a description of
    the query rather than a list of anonymous slots. A name is only ever derived from a
    schema column, never from a user value, so nothing a user typed reaches the SQL text.
    """

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def add(self, hint: str, value: Any) -> str:
        base = "".join(char if char.isalnum() else "_" for char in hint.lower()).strip("_")
        base = base if base and not base[0].isdigit() else f"p_{base}"
        name, suffix = base, 2
        while name in self.values:
            name, suffix = f"{base}_{suffix}", suffix + 1
        self.values[name] = value
        return name


def __typed(raw: str) -> Any:
    """The value as the database will want to compare it.

    Filter values arrive as text because that is how the user said them. Sending "20"
    to an integer column fails outright on Postgres — `operator does not exist:
    integer = text` — so the obvious numeric and date forms are converted here. Anything
    else stays a string, which is right for every text column and harmless elsewhere.
    """
    text = raw.strip().strip("'\"").strip()
    for convert in (int, float, datetime.fromisoformat):
        try:
            return convert(text)
        except (TypeError, ValueError):
            continue
    return text


def __items(raw: str) -> list[str]:
    """Split a list the user expressed as one string, e.g. 'US, UK' or 'US and UK'."""
    text = raw.replace(" and ", ",")
    return [part.strip() for part in text.split(",") if part.strip()] or [raw.strip()]


def __escaped_like(raw: str, pattern: str) -> str:
    """A LIKE value with the user's own %, _ and \\ neutralised before the wildcards go on."""
    literal = (
        str(raw).replace(__LIKE_ESCAPE, __LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")
    )
    return pattern.format(value=literal)


def __predicate(spec: BoundFilter, parameters: __Parameters) -> str:
    """One WHERE condition, with its value replaced by a placeholder."""
    column, hint = str(spec.column), spec.column.column

    if spec.operator in __COMPARISONS:
        name = parameters.add(hint, __typed(spec.value))
        return f"{column} {__COMPARISONS[spec.operator]} :{name}"

    if spec.operator in ("in", "not_in"):
        names = [parameters.add(hint, __typed(item)) for item in __items(spec.value)]
        keyword = "IN" if spec.operator == "in" else "NOT IN"
        return f"{column} {keyword} ({', '.join(f':{name}' for name in names)})"

    if spec.operator == "between":
        low, high = (__items(spec.value) + ["", ""])[:2]
        start = parameters.add(f"{hint}_from", __typed(low))
        end = parameters.add(f"{hint}_to", __typed(high))
        return f"{column} BETWEEN :{start} AND :{end}"

    patterns = {"contains": "%{value}%", "starts_with": "{value}%", "ends_with": "%{value}"}
    name = parameters.add(hint, __escaped_like(spec.value, patterns[spec.operator]))
    return f"{column} LIKE :{name} ESCAPE '{__LIKE_ESCAPE}'"


def __selected(sql_query_ir: SQLQueryIR) -> list[str]:
    """The SELECT list: the aggregate where one was asked for, the bare column otherwise."""
    items = []
    for bound in sql_query_ir.fields:
        column = str(bound.column)
        expression = f"{bound.aggregation.upper()}({column})" if bound.aggregation else column
        items.append(f"{expression}{f'  -- {bound.user_term}' if bound.user_term else ''}")
    return items


def build(sql_query_ir: SQLQueryIR, now: datetime | None = None) -> SQLSpec:
    """The SQL specification for the model, and the parameters that go with it.

    Everything the IR determines is written out as SQL. What it does not determine is
    left open, and there is only one such thing: how the tables relate. The IR records
    which columns the query needs, never which key joins their tables, so when more than
    one table is involved the join is the model's to work out and the only part of the
    statement it is really authoring.
    """
    now = now or datetime.now()
    parameters = __Parameters()
    omitted: list[str] = []

    conditions = [__predicate(spec, parameters) for spec in sql_query_ir.filters]

    if sql_query_ir.time_range is not None:
        column = str(sql_query_ir.time_range.column)
        start, end = period.resolve(sql_query_ir.time_range, now)
        if start is None and end is None:
            omitted.append(
                f"the time period"
                f"{f' ({sql_query_ir.time_range.expression})' if sql_query_ir.time_range.expression else ''}"
                f" — too little was said about it to place on a calendar"
            )
        if start is not None:
            conditions.append(f"{column} >= :{parameters.add('period_start', start)}")
        if end is not None:
            conditions.append(f"{column} < :{parameters.add('period_end', end)}")

    lines = [
        "-- Complete this SELECT statement. It is already correct; it is not finished.",
        "-- Every :name is a bound parameter. Write it exactly as it appears.",
        "",
        "SELECT",
    ]

    selected = __selected(sql_query_ir)
    if selected:
        lines.extend(f"    {',' if index else ' '} {item}" for index, item in enumerate(selected))
    else:
        lines.append("      -- nothing was named; select the columns this query needs")

    tables = sql_query_ir.tables
    lines.append("FROM")
    if len(tables) == 1:
        lines.append(f"    {tables[0]}")
    else:
        lines.append(f"    {tables[0]}")
        lines.extend(
            f"    -- JOIN {table} ON <the key that relates it — yours to determine>"
            for table in tables[1:]
        )

    if conditions:
        lines.append("WHERE")
        lines.extend(
            f"    {'AND' if index else '   '} {condition}"
            for index, condition in enumerate(conditions)
        )

    if sql_query_ir.grouping:
        lines.append("GROUP BY")
        lines.extend(
            f"    {',' if index else ' '} {str(bound.column)}"
            f"{f'  -- {bound.user_term}' if bound.user_term else ''}"
            for index, bound in enumerate(sql_query_ir.grouping)
        )

    lines.append(";")

    if parameters.values:
        lines.append("")
        lines.append("-- Bound parameters, supplied at execution. Their values are deliberately")
        lines.append("-- not shown: you have no use for them and must not write one.")
        lines.extend(f"--   :{name}" for name in parameters.values)

    return SQLSpec(text="\n".join(lines), parameters=parameters.values, omitted=omitted)


def columns_in(sql_query_ir: SQLQueryIR) -> set[str]:
    """Every qualified column the IR permits, for checking what the model wrote."""
    return {str(column) for column in sql_query_ir.columns()}


__all__ = ["SQLSpec", "build", "columns_in", "ColumnRef"]
