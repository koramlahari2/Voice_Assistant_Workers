import sqlite3
from contextlib import closing
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "shopkeeper.db"


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with closing(get_connection()) as connection:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS credit_transactions (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL
                        CHECK (transaction_type IN ('credit', 'payment')),
                    amount REAL NOT NULL CHECK (amount > 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );

                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                    unit TEXT NOT NULL DEFAULT 'items',
                    low_stock_threshold INTEGER NOT NULL DEFAULT 5
                        CHECK (low_stock_threshold >= 0),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (product_id) REFERENCES inventory(id)
                );

                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                INSERT OR IGNORE INTO customers (name) VALUES ('Ramesh');
                INSERT OR IGNORE INTO inventory (name, quantity, unit)
                    VALUES ('Milk', 0, 'packets');
                INSERT OR IGNORE INTO inventory (name, quantity, unit)
                    VALUES ('Tea', 10, 'packets');
                """
            )
            seed_credit = connection.execute(
                """
                INSERT INTO credit_transactions
                    (customer_id, transaction_type, amount, note)
                SELECT id, 'credit', 100, 'Demo opening balance'
                FROM customers
                WHERE name = 'Ramesh'
                  AND NOT EXISTS (
                      SELECT 1 FROM credit_transactions
                      WHERE customer_id = customers.id
                  )
                """
            )
            if seed_credit.rowcount:
                connection.execute(
                    "INSERT INTO activities (description) VALUES (?)",
                    ("Demo opening balance: ₹100.00 credit for Ramesh",),
                )
