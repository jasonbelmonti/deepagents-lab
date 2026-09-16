"""Small, deterministic sales database for interactive SQL experiments."""
from pathlib import Path

import duckdb


def create_fixture(path: Path) -> Path:
    """Create a new database; never overwrite an existing investigation."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with duckdb.connect(str(path)) as connection:
        connection.execute("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                unit_price_cents INTEGER NOT NULL
            );
            INSERT INTO products VALUES
                (1, 'Keyboard', 7500), (2, 'Mouse', 2500), (3, 'Monitor', 30000);
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                ordered_at DATE NOT NULL,
                region VARCHAR NOT NULL,
                product_id INTEGER REFERENCES products(product_id),
                quantity INTEGER NOT NULL,
                status VARCHAR NOT NULL
            );
            INSERT INTO orders VALUES
                (1, '2026-09-01', 'West',    1, 2, 'paid'),
                (2, '2026-09-01', 'West',    3, 1, 'paid'),
                (3, '2026-09-02', 'East',    2, 4, 'paid'),
                (4, '2026-09-02', 'East',    1, 2, 'paid'),
                (5, '2026-09-03', 'Central', 3, 1, 'paid'),
                (6, '2026-09-03', 'Central', 2, 2, 'paid'),
                (7, '2026-09-04', 'East',    3, 3, 'cancelled'),
                (8, '2026-09-04', 'West',    2, 1, 'pending'),
                (9, '2026-09-05', 'West',    2, 2, 'paid');
        """)
    return path
