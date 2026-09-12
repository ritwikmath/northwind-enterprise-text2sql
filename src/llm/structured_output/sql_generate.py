from typing import Any

from pydantic import BaseModel, Field


class SQLQuery(BaseModel):
    """What the generating model returns: the statement, and nothing else.

    There is no field here for values. The model is never shown one, so it has none to
    report, and a response shape with nowhere to put a value is a response that cannot
    carry one into the SQL. The parameters are assembled in code — see `llm.sql_spec`.
    """

    sql: str = Field(
        description=(
            "The finished SELECT statement. Use the :name placeholders from the "
            "specification exactly as written, every one of them, and write no literal "
            "value of your own. Read-only: a single SELECT, nothing that modifies data."
        )
    )


class PreparedStatement(BaseModel):
    """A statement and its values, kept apart, ready to execute.

    The pair is what a driver wants: `connection.execute(text(sql), parameters)` on
    SQLAlchemy, or `cursor.execute(sql, parameters)` on psycopg. The database parses the
    statement once and binds the values afterwards, so a value can never be read as SQL
    however it was spelled.
    """

    sql: str = Field(description="The statement, containing :name placeholders and no values.")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Placeholder name -> value, bound at execution. Named, so the pairing is legible.",
    )
    omitted: list[str] = Field(
        default_factory=list,
        description="Anything the request asked for that could not be expressed in the statement.",
    )
