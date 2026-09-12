from datetime import datetime
from typing import Iterator, Literal

from pydantic import BaseModel, Field


class ColumnRef(BaseModel):
    """A concrete attribute in the fetched schema."""

    table: str = Field(description="The table name exactly as it appears in the fetched schema.")
    column: str = Field(description="The column name exactly as it appears in the fetched schema.")

    def __str__(self) -> str:
        return f"{self.table}.{self.column}"


class BoundField(BaseModel):
    """A column to select, and how it should be summarised."""

    column: ColumnRef
    aggregation: Literal["sum", "avg", "count", "min", "max"] | None = Field(
        default=None,
        description=(
            "How this column is summarised, carried across from the request: 'total' -> sum, "
            "'average' -> avg, 'how many' -> count, 'lowest' -> min, 'highest' -> max. "
            "Null when the column is selected as is."
        ),
    )
    user_term: str = Field(
        default="",
        description="The attribute in the user's own words, e.g. 'revenue'. For readability only.",
    )


class BoundFilter(BaseModel):
    """A restriction on which rows to keep, applied to one column."""

    column: ColumnRef
    operator: Literal[
        "equals",
        "not_equals",
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
        "in",
        "not_in",
        "contains",
        "starts_with",
        "ends_with",
        "between",
    ] = Field(description="The comparison, carried across from the request unchanged.")
    value: str = Field(
        description="What the column is compared against, carried across from the request unchanged."
    )
    user_term: str = Field(
        default="",
        description="The restricted attribute in the user's own words, e.g. 'country'. For readability only.",
    )


class BoundGrouping(BaseModel):
    """A column the results are broken down by."""

    column: ColumnRef
    user_term: str = Field(
        default="",
        description="The breakdown attribute in the user's own words, e.g. 'region'. For readability only.",
    )


class BoundTimeRange(BaseModel):
    """The time scope, applied to a date column.

    The period stays symbolic — copy the user's expression across rather than working
    out dates for it; it is resolved to bounds downstream.
    """

    column: ColumnRef
    type: Literal["absolute", "relative", "upcoming", "between"] = Field(
        description=(
            "'absolute' for explicit dates, 'relative' for periods such as 'last month', "
            "'upcoming' for future periods such as 'next 30 days', 'between' for a range."
        )
    )
    start_date: datetime | None = Field(
        default=None,
        description="Beginning date, only when the request states an absolute one. Never calculate it.",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Ending date, only when the request states an absolute one. Never calculate it.",
    )
    expression: str | None = Field(
        default=None,
        description="The period as the user expressed it, e.g. 'last month', copied across unchanged.",
    )
    value: int | None = Field(
        default=None, description="Numeric duration when one is given, e.g. 30 in 'next 30 days'."
    )
    unit: Literal["day", "week", "month", "quarter", "year"] | None = Field(
        default=None, description="The unit associated with a duration."
    )
    user_term: str = Field(
        default="",
        description="The time attribute in the user's own words, e.g. 'order date'. For readability only.",
    )


class SQLQueryIR(BaseModel):
    """The query to build, stated in columns instead of the user's words.

    This is what the schema-coverage model returns. It is derived from the semantic
    analysis, but it does not have to mirror it term for term: the model may drop a
    term the schema cannot express, and may add a column the query needs. The only
    thing checked afterwards is that every column named here really exists in the
    fetched schema — see `llm.binding.resolve_against_schema`.

    Nothing here restates a user term as a required value. Once a column is chosen,
    the wording that led to it carries no further meaning, and a field the model has
    no reason to write is a field it cannot omit and fail on.
    """

    fields: list[BoundField] = Field(
        default_factory=list, description="The columns to select, with their aggregation if any."
    )
    filters: list[BoundFilter] = Field(
        default_factory=list, description="The restrictions to apply, each on one column."
    )
    grouping: list[BoundGrouping] = Field(
        default_factory=list, description="The columns the results are broken down by."
    )
    time_range: BoundTimeRange | None = Field(
        default=None, description="The date column the question is scoped to, and the period."
    )
    unresolved: list[str] = Field(
        default_factory=list,
        description=(
            "Anything the request asks for that no retrieved column can express, one entry each, "
            "written as a plain description of the information that is missing — 'the segment a "
            "customer belongs to', 'whether an order was refunded'. This is searched against other "
            "sources later, so write words someone could look the meaning up by. Never write a "
            "table or column name here, and never invent one to name the gap: if a column for it "
            "existed you would have used it, so there is nothing here to name."
        ),
    )

    def columns(self) -> Iterator[ColumnRef]:
        """Every column this query references, in the order it appears."""
        for field in self.fields:
            yield field.column
        for filter_ in self.filters:
            yield filter_.column
        for group in self.grouping:
            yield group.column
        if self.time_range is not None:
            yield self.time_range.column

    @property
    def tables(self) -> list[str]:
        """Every table referenced by the bound columns, deduplicated, in first-seen order."""
        return list(dict.fromkeys(column.table for column in self.columns()))
