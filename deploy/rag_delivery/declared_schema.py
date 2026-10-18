"""Declared schema fingerprint of a Backend image.

Run inside the Backend image, fed through stdin, so the image is not
modified::

    docker run --rm -i --network none --entrypoint python IMAGE - < declared_schema.py

It compiles the SQLAlchemy metadata declared by ``Backend.models`` with the
SQLite dialect (``CREATE TABLE`` plus ``CREATE INDEX`` statements, ordered by
table name and then index name) and prints one JSON line with the sha256.
The fingerprint is compared only with the same field of another release
manifest, never with a schema observed on a data volume.

Only the standard library is imported at module level; SQLAlchemy and the
Backend package are imported in ``main`` from the image's own environment.
"""

import hashlib
import json


def fingerprint(statements_by_table):
    """sha256 over DDL statements, ordered by table name.

    ``statements_by_table`` maps a table name to its ordered list of DDL
    statements. Statements are stripped and joined with a blank line.
    """
    text = "\n\n".join(
        statement.strip()
        for table in sorted(statements_by_table)
        for statement in statements_by_table[table]
    )
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def declared_statements(metadata, dialect):
    from sqlalchemy.schema import CreateIndex, CreateTable

    statements = {}
    for name, table in metadata.tables.items():
        ddl = [str(CreateTable(table).compile(dialect=dialect))]
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            ddl.append(str(CreateIndex(index).compile(dialect=dialect)))
        statements[name] = ddl
    return statements


def main():
    from sqlalchemy.dialects import sqlite

    from Backend.models import db

    statements = declared_statements(db.metadata, sqlite.dialect())
    print(json.dumps({
        "declared_schema_fingerprint": fingerprint(statements),
        "tables": sorted(statements),
    }))


if __name__ == "__main__":
    main()
