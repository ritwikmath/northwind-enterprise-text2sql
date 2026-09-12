"""Check the model's SQL before it is allowed near a database.

The prompt asks for a read-only SELECT using only the given placeholders. This does not
trust that. Everything the prompt asks for is checked here, because the request that
produced this SQL came from a user, and a model that can be persuaded to write
`DROP TABLE` will also write the sentence explaining why it was fine to.

The important check is the one for literals. Parameterisation is worth nothing if the
model writes `WHERE city = 'London'` instead of `WHERE city = :city` — the statement
still runs and still returns the right rows, so nothing downstream notices that the
value is now part of the SQL text. Since the model is never shown a value, any literal
in its output is either invented or copied out of the user's question, and both are
rejected rather than run.
"""

import re

__STATEMENT_START = re.compile(r"^\s*(?:WITH|SELECT)\b", re.IGNORECASE)

# Statements that change data or schema, and the routes out of a single SELECT.
__FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COMMENT|COPY|MERGE|"
    r"CALL|DO|EXECUTE|PREPARE|VACUUM|ANALYZE|SET|RESET|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|"
    r"LISTEN|NOTIFY|LOCK|REINDEX|CLUSTER|REFRESH|SECURITY\s+LABEL|INTO\s+OUTFILE|"
    r"pg_sleep|pg_read_file|pg_ls_dir|dblink|lo_import|lo_export)\b",
    re.IGNORECASE,
)

__PLACEHOLDER = re.compile(r"(?<![:\w]):([a-zA-Z_][a-zA-Z0-9_]*)")
__STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
__ESCAPE_CLAUSE = re.compile(r"\bESCAPE\s*'(?:[^']|'')*'", re.IGNORECASE)
__LINE_COMMENT = re.compile(r"--[^\n]*")
__BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


class UnsafeSQL(ValueError):
    """The model's SQL failed a check and must not be run."""


def __stripped(sql: str) -> str:
    """The statement with comments and ESCAPE clauses removed.

    Comments go first: everything below asks what the statement *does*, and a keyword or
    quote inside a comment does nothing. The ESCAPE clause is the one string literal the
    spec itself writes, so it is removed too and every literal that remains is the
    model's own.
    """
    without_comments = __LINE_COMMENT.sub(" ", __BLOCK_COMMENT.sub(" ", sql))
    return __ESCAPE_CLAUSE.sub(" ", without_comments)


def verify(sql: str, allowed: frozenset[str]) -> str:
    """Return the statement unchanged, or raise `UnsafeSQL` saying what is wrong.

    `allowed` is the set of placeholder names the spec created. A name outside it would
    go unbound at execution; a name missing from the statement means a filter the user
    asked for was quietly dropped, which returns more rows than they asked to see.
    """
    if not sql or not sql.strip():
        raise UnsafeSQL("The model returned no SQL.")

    body = __stripped(sql)

    if not __STATEMENT_START.match(body):
        raise UnsafeSQL("The statement does not begin with SELECT or WITH.")

    # One statement only: a trailing semicolon is fine, a second statement is not.
    if ";" in body.strip().rstrip(";"):
        raise UnsafeSQL("More than one statement was returned; only a single SELECT may be run.")

    forbidden = __FORBIDDEN.search(body)
    if forbidden:
        raise UnsafeSQL(f"The statement contains {forbidden.group(1).upper()}, which cannot be run.")

    literal = __STRING_LITERAL.search(body)
    if literal:
        raise UnsafeSQL(
            f"The statement contains the literal {literal.group(0)} where a bound parameter "
            "belongs. Values must stay out of the SQL text."
        )

    used = set(__PLACEHOLDER.findall(body))

    unknown = sorted(used - allowed)
    if unknown:
        raise UnsafeSQL(
            f"The statement uses {', '.join(':' + name for name in unknown)}, which nothing binds."
        )

    unused = sorted(allowed - used)
    if unused:
        raise UnsafeSQL(
            f"The statement never uses {', '.join(':' + name for name in unused)}, so a restriction "
            "the user asked for would not be applied."
        )

    return sql.strip()
