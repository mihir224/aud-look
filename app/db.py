from contextlib import contextmanager
from typing import Iterator

import psycopg

from app.config import get_settings


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Open a short-lived connection; API searches use one connection per branch."""
    with psycopg.connect(get_settings().database_url) as connection:
        yield connection


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"

