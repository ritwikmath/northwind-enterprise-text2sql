from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FieldSelection(BaseModel):
    """An attribute of the data that the user mentioned wanting to see or measure."""

    name: str = Field(description="The attribute as the user referred to it, e.g. 'revenue' or 'customer name'.")
    type: Literal["dimension", "metric"] = Field(
        description="'metric' if the user is asking for something measurable or countable (revenue, number of orders); 'dimension' if it describes or categorises the results (region, product, month)."
    )
    aggregation: Literal["sum", "avg", "count", "min", "max"] | None = Field(
        default=None,
        description="How the user wants the metric summarised, if they said so: 'total'/'combined' -> sum, 'average'/'typical' -> avg, 'how many' -> count, 'lowest' -> min, 'highest' -> max. Leave null if they did not indicate any summarisation.",
    )


class Filter(BaseModel):
    """A restriction the user placed on which results they care about."""

    field: str = Field(description="The attribute the restriction applies to, e.g. 'country' or 'signup date'.")
    operator: str = Field(
        description="The kind of comparison the user expressed, e.g. 'more than', 'at least', 'equals', 'is not', 'one of', 'contains', 'starts with'."
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

    field: str = Field(description="The point in time the period refers to, as the user framed it, e.g. 'order date'.")
    start_date: datetime | None = Field(default=None, description="Beginning of the period the user described.")
    end_date: datetime | None = Field(default=None, description="End of the period the user described.")


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
