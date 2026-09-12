from typing import Literal

from pydantic import BaseModel, Field

from llm.structured_output.symantic_analysis import FieldSelection, Filter, TimeRange


class ColumnRef(BaseModel):
    """A concrete attribute in the fetched schema."""

    table: str = Field(description="The table name exactly as it appears in the fetched schema.")
    column: str = Field(description="The column name exactly as it appears in the fetched schema.")

    def __str__(self) -> str:
        return f"{self.table}.{self.column}"


class Resolution(BaseModel):
    """One term from the user's query bound to an attribute in the fetched schema."""

    user_term: str = Field(
        description="The term exactly as it appears in the query IR, e.g. 'revenue' or 'customer name'."
    )
    column: ColumnRef | None = Field(
        default=None,
        description="The attribute this term refers to. Null when nothing in the fetched schema means this term.",
    )
    confidence: Literal["exact", "likely", "guess"] = Field(
        description=(
            "'exact' when the name or description states the same thing as the user's term; "
            "'likely' when the description makes the meaning clear under a different name; "
            "'guess' when the match is plausible but the schema does not confirm it."
        )
    )
    reason: str | None = Field(
        default=None,
        description="Why this attribute was chosen, or what is missing when no attribute matches.",
    )


class SchemaResolution(BaseModel):
    """The mapping the model produces: every term in the query IR, bound or reported unbound."""

    resolutions: list[Resolution] = Field(
        default_factory=list,
        description="One entry per term in the query IR. Include terms you could not resolve, with a null column.",
    )

    @property
    def covered(self) -> bool:
        return bool(self.resolutions) and all(r.column is not None for r in self.resolutions)

    def by_term(self) -> dict[str, Resolution]:
        return {r.user_term: r for r in self.resolutions}


class BoundField(BaseModel):
    """A requested attribute, bound to a column. `spec` carries the user's intent unchanged."""

    column: ColumnRef
    spec: FieldSelection


class BoundFilter(BaseModel):
    """A restriction, bound to a column. `spec` carries the operator and value unchanged."""

    column: ColumnRef
    spec: Filter


class BoundTimeRange(BaseModel):
    """The time scope, bound to a date column. `spec` stays symbolic; resolve it to bounds downstream."""

    column: ColumnRef
    spec: TimeRange


class SQLQueryIR(BaseModel):
    """The query IR with user terms replaced by schema attributes, assembled from a SchemaResolution."""

    tables: list[str] = Field(
        default_factory=list, description="Every table referenced by the bound columns, deduplicated."
    )
    fields: list[BoundField] = Field(default_factory=list)
    filters: list[BoundFilter] = Field(default_factory=list)
    grouping: list[ColumnRef] = Field(default_factory=list)
    time_range: BoundTimeRange | None = None
    unresolved: list[Resolution] = Field(
        default_factory=list, description="Terms with no matching attribute in the fetched schema."
    )

    @property
    def covered(self) -> bool:
        return not self.unresolved
