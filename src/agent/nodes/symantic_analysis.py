from datetime import datetime
from typing import Literal

from langchain.agents import create_agent
from pydantic import BaseModel, Field


class FieldSelection(BaseModel):
    name: str = Field(description="Column or field name referenced by the user, e.g. 'revenue' or 'customer_name'.")
    type: Literal["dimension", "metric"] = Field(
        description="'dimension' for categorical/groupable fields (e.g. region, product); 'metric' for numeric fields meant to be aggregated (e.g. revenue, count)."
    )
    aggregation: Literal["sum", "avg", "count", "min", "max"] | None = Field(
        default=None,
        description="Aggregation function to apply to a metric field, if the user implies one (e.g. 'total revenue' -> sum). Leave null for dimensions or when no aggregation is implied.",
    )


class Filter(BaseModel):
    field: str = Field(description="Field the filter applies to, e.g. 'country' or 'order_date'.")
    operator: str = Field(
        description="Comparison operator implied by the user's phrasing, e.g. 'more than' -> '>', 'is' -> '=', 'includes' -> 'contains'."
    )
    value: str = Field(description="Value to compare the field against, as stated or implied by the user.")


class Ordering(BaseModel):
    field: str = Field(description="Field to sort results by.")
    direction: Literal["asc", "desc"] = Field(
        default="desc", description="Sort direction; 'desc' for highest/most/top-N style requests, 'asc' for lowest/oldest."
    )


class QueryParams(BaseModel):
    limit: int | None = Field(default=None, ge=1, description="Max number of rows to return, e.g. from 'top 10' -> 10.")
    offset: int | None = Field(default=None, ge=0, description="Number of rows to skip, for pagination requests.")


class TimeStamp(BaseModel):
    field: str = Field(description="Date/time field the time range applies to, e.g. 'created_at'.")
    start_date: datetime | None = Field(default=None, description="Start of the requested time range, if any.")
    end_date: datetime | None = Field(default=None, description="End of the requested time range, if any.")


class QueryIR(BaseModel):
    intent: list[str] = Field(
        default_factory=list,
        description="High-level goals of the query, e.g. 'aggregate', 'compare', 'rank', 'trend'.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Business entities or tables the query is about, e.g. 'customers', 'orders'.",
    )
    fields: list[FieldSelection] = Field(
        default_factory=list, description="Fields the user wants returned or computed, as dimensions or metrics."
    )
    filters: list[Filter] = Field(
        default_factory=list, description="Conditions that restrict which rows are included."
    )
    grouping: list[str] = Field(
        default_factory=list, description="Fields to group/aggregate by, e.g. from 'by region' -> ['region']."
    )



symantic_analysis = create_agent(
    model='openai:gpt-4o',
    response_format=QueryIR
)