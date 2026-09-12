from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FieldSelection(BaseModel):
    """A data attribute or entity that the user explicitly requests as part of the result."""

    name: str = Field(description="The attribute as the user referred to it along with the associated entity (if any), e.g. 'revenue' or 'customer name'.")
    type: Literal["dimension", "metric"] = Field(
        description="'metric' if the user is asking for something measurable or countable (revenue, number of orders); 'dimension' if it describes or categorises the results (region, product, month)."
    )
    aggregation: Literal["sum", "avg", "count", "min", "max"] | None = Field(
        default=None,
        description="How the user wants the metric summarised, if they said so: 'total'/'combined' -> sum, 'average'/'typical' -> avg, 'how many' -> count, 'lowest' -> min, 'highest' -> max. Leave null if they did not indicate any summarisation.",
    )


class Filter(BaseModel):
    """A restriction the user placed on which results they care about."""

    entity: str = Field(description="The entity the field closely relate to, eg country is entoty name can be field")
    field: str = Field(description="The attribute the restriction applies to, e.g. 'country' or 'signup date'.")
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
            "between"
        ] = Field(
        description="The comparison operation expressed by the user."
    )
    value: str = Field(description="What the attribute is being compared against, exactly as the user expressed it.")


class Ordering(BaseModel):
    """How the user wants the results arranged."""

    field: str = Field(description="The attribute the user wants the results arranged by.")
    direction: Literal["asc", "desc"] = Field(
        default="desc",
        description="'desc' when the user asks for the highest, largest, most recent or best; 'asc' when they ask for the lowest, smallest, oldest or worst.",
    )


class QueryParams(BaseModel):
    """How many results the user asked for."""

    limit: int | None = Field(
        default=None, ge=1, description="How many results the user wants, e.g. 'top 10' -> 10. Null if unspecified."
    )
    offset: int | None = Field(
        default=None, ge=0, description="How many results to skip past, e.g. 'the next 20 after the first 20' -> 20."
    )


class TimeRange(BaseModel):
    """The time period the user's question is scoped to."""

    field: str = Field(
        description=(
            "The business time field the period applies to, "
            "for example 'order date', 'purchase date', or 'signup date'."
        )
    )

    type: Literal[
        "absolute",
        "relative",
        "upcoming",
        "between",
    ] = Field(
        description=(
            "The type of temporal expression used by the user. "
            "'absolute' for explicit dates, 'relative' for periods such as "
            "'last month' or 'previous year', 'upcoming' for future periods "
            "such as 'next 30 days', and 'between' for a range between two "
            "temporal expressions."
        )
    )

    start_date: datetime | None = Field(
        default=None,
        description=(
            "Explicit beginning date when the user provides an absolute date. "
            "Do not calculate this for relative expressions."
        )
    )

    end_date: datetime | None = Field(
        default=None,
        description=(
            "Explicit ending date when the user provides an absolute date. "
            "Do not calculate this for relative expressions."
        )
    )

    expression: str | None = Field(
        default=None,
        description=(
            "The temporal expression exactly as expressed by the user, "
            "for example 'last month', 'previous year', or "
            "'the month that just ended'."
        )
    )

    value: int | None = Field(
        default=None,
        description=(
            "Numeric duration when the user specifies one, "
            "for example 30 in 'next 30 days'."
        )
    )

    unit: Literal[
        "day",
        "week",
        "month",
        "quarter",
        "year",
    ] | None = Field(
        default=None,
        description="The unit associated with a duration."
    )


class QueryIR(BaseModel):
    """A structured restatement of what the user asked for, in their own terms."""

    intent: list[str] = Field(
        default_factory=list,
        description="What the user is trying to find out, e.g. 'summarise', 'compare', 'rank', 'see a trend', 'list individual records'.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="The subjects the question is about, e.g. 'customers', 'orders', 'support tickets'.",
    )
    fields: list[FieldSelection] = Field(
        default_factory=list, description="The attributes the user mentioned wanting to see or measure."
    )
    filters: list[Filter] = Field(
        default_factory=list, description="The restrictions the user placed on which results they care about."
    )
    grouping: list[str] = Field(
        default_factory=list,
        description="Attributes the user wants the results broken down by, e.g. 'by region' -> ['region'].",
    )
    time_range: TimeRange | None = Field(
        default=None, description="The time period the question is scoped to, resolved against the current date and time."
    )
