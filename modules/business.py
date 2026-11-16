import math
import sqlite3
from contextlib import closing, contextmanager
from typing import Iterator

from database.db import get_connection


@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    with closing(get_connection()) as connection:
        with connection:
            yield connection


def _clean_name(name: str, kind: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{kind} name cannot be empty.")
    return name.strip()


def _validate_amount(amount: float) -> None:
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("Amount must be a number greater than zero.")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a number greater than zero.")


def _validate_quantity(quantity: int) -> None:
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a whole number greater than zero.")


def _get_or_create_customer(connection: sqlite3.Connection, name: str) -> int:
    connection.execute(
        "INSERT OR IGNORE INTO customers (name) VALUES (?)",
        (name,),
    )
    row = connection.execute(
        "SELECT id FROM customers WHERE name = ?",
        (name,),
    ).fetchone()
    return row["id"]


def _customer_id(connection: sqlite3.Connection, name: str) -> int:
    row = connection.execute(
        "SELECT id FROM customers WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Customer '{name}' was not found.")
    return row["id"]


def _balance(connection: sqlite3.Connection, customer_id: int) -> float:
    row = connection.execute(
        """
        SELECT COALESCE(SUM(
            CASE transaction_type
                WHEN 'credit' THEN amount
                ELSE -amount
            END
        ), 0) AS balance
        FROM credit_transactions
        WHERE customer_id = ?
        """,
        (customer_id,),
    ).fetchone()
    return row["balance"]


def add_credit(customer_name: str, amount: float, note: str = "") -> float:
    customer_name = _clean_name(customer_name, "Customer")
    _validate_amount(amount)
    with _transaction() as connection:
        customer_id = _get_or_create_customer(connection, customer_name)
        connection.execute(
            """
            INSERT INTO credit_transactions
                (customer_id, transaction_type, amount, note)
            VALUES (?, 'credit', ?, ?)
            """,
            (customer_id, amount, note.strip()),
        )
        connection.execute(
            "INSERT INTO activities (description) VALUES (?)",
            (f"Added ₹{amount:.2f} credit for {customer_name}",),
        )
        return _balance(connection, customer_id)


def get_customer_balance(customer_name: str) -> float:
    customer_name = _clean_name(customer_name, "Customer")
    with _transaction() as connection:
        return _balance(connection, _customer_id(connection, customer_name))


def record_payment(customer_name: str, amount: float, note: str = "") -> float:
    customer_name = _clean_name(customer_name, "Customer")
    _validate_amount(amount)
    with _transaction() as connection:
        customer_id = _customer_id(connection, customer_name)
        balance = _balance(connection, customer_id)
        if amount > balance:
            raise ValueError(
                f"Payment of ₹{amount:.2f} exceeds {customer_name}'s "
                f"outstanding balance of ₹{balance:.2f}."
            )
        connection.execute(
            """
            INSERT INTO credit_transactions
                (customer_id, transaction_type, amount, note)
            VALUES (?, 'payment', ?, ?)
            """,
            (customer_id, amount, note.strip()),
        )
        connection.execute(
            "INSERT INTO activities (description) VALUES (?)",
            (f"Recorded ₹{amount:.2f} payment from {customer_name}",),
        )
        return _balance(connection, customer_id)


def get_customer_history(customer_name: str) -> list[sqlite3.Row]:
    customer_name = _clean_name(customer_name, "Customer")
    with _transaction() as connection:
        customer_id = _customer_id(connection, customer_name)
        return list(
            connection.execute(
                """
                SELECT transaction_type, amount, note, created_at
                FROM credit_transactions
                WHERE customer_id = ?
                ORDER BY id DESC
                """,
                (customer_id,),
            )
        )


def get_customers() -> list[str]:
    with _transaction() as connection:
        return [
            row["name"]
            for row in connection.execute("SELECT name FROM customers ORDER BY name")
        ]


def adjust_stock(
    product_name: str,
    quantity: int,
    action: str = "add",
    unit: str = "items",
) -> int:
    product_name = _clean_name(product_name, "Product")
    _validate_quantity(quantity)
    if action not in {"add", "reduce"}:
        raise ValueError("Stock action must be 'add' or 'reduce'.")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("Unit cannot be empty.")

    with _transaction() as connection:
        product = connection.execute(
            "SELECT id, quantity FROM inventory WHERE name = ?",
            (product_name,),
        ).fetchone()
        if product is None:
            if action == "reduce":
                raise ValueError(f"Product '{product_name}' was not found.")
            connection.execute(
                "INSERT INTO inventory (name, quantity, unit) VALUES (?, 0, ?)",
                (product_name, unit.strip()),
            )
            product = connection.execute(
                "SELECT id, quantity FROM inventory WHERE name = ?",
                (product_name,),
            ).fetchone()

        updated_quantity = product["quantity"] + (
            quantity if action == "add" else -quantity
        )
        if updated_quantity < 0:
            raise ValueError(
                f"Cannot reduce {product_name}: only {product['quantity']} available."
            )
        connection.execute(
            """
            UPDATE inventory
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (updated_quantity, product["id"]),
        )
        connection.execute(
            "INSERT INTO activities (description) VALUES (?)",
            (
                f"{'Added' if action == 'add' else 'Reduced'} {quantity} "
                f"{unit.strip()} of {product_name}",
            ),
        )
        return updated_quantity


def place_order(
    product_name: str,
    quantity: int,
    customer_name: str | None = None,
) -> int:
    product_name = _clean_name(product_name, "Product")
    _validate_quantity(quantity)
    if customer_name is not None:
        customer_name = _clean_name(customer_name, "Customer")

    with _transaction() as connection:
        product = connection.execute(
            "SELECT id, quantity FROM inventory WHERE name = ?",
            (product_name,),
        ).fetchone()
        if product is None:
            raise ValueError(f"Product '{product_name}' was not found.")
        if product["quantity"] < quantity:
            raise ValueError(
                f"Only {product['quantity']} {product_name} available; "
                f"cannot order {quantity}."
            )

        customer_id = (
            _get_or_create_customer(connection, customer_name)
            if customer_name is not None
            else None
        )
        order = connection.execute(
            "INSERT INTO orders (customer_id) VALUES (?)",
            (customer_id,),
        )
        order_id = order.lastrowid
        connection.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, ?)
            """,
            (order_id, product["id"], quantity),
        )
        connection.execute(
            """
            UPDATE inventory
            SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (quantity, product["id"]),
        )
        description = f"Order recorded: {quantity} {product_name}"
        if customer_name is not None:
            description += f" for {customer_name}"
        connection.execute(
            "INSERT INTO activities (description) VALUES (?)",
            (description,),
        )
        return order_id


def get_inventory() -> list[sqlite3.Row]:
    with _transaction() as connection:
        return list(
            connection.execute(
                """
                SELECT name, quantity, unit, low_stock_threshold
                FROM inventory
                ORDER BY name
                """
            )
        )


def get_order_history() -> list[sqlite3.Row]:
    with _transaction() as connection:
        return list(
            connection.execute(
                """
                SELECT orders.id, orders.created_at,
                       customers.name AS customer_name,
                       inventory.name AS product_name,
                       order_items.quantity, inventory.unit
                FROM orders
                JOIN order_items ON order_items.order_id = orders.id
                JOIN inventory ON inventory.id = order_items.product_id
                LEFT JOIN customers ON customers.id = orders.customer_id
                ORDER BY orders.id DESC
                """
            )
        )


def get_dashboard_summary() -> dict[str, int | float]:
    with _transaction() as connection:
        customer_count = connection.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]
        outstanding_credit = connection.execute(
            """
            SELECT COALESCE(SUM(
                CASE transaction_type
                    WHEN 'credit' THEN amount
                    ELSE -amount
                END
            ), 0)
            FROM credit_transactions
            """
        ).fetchone()[0]
        inventory_units = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM inventory"
        ).fetchone()[0]
        return {
            "total_customers": customer_count,
            "outstanding_credit": outstanding_credit,
            "inventory_units": inventory_units,
        }


def get_recent_activities(limit: int = 10) -> list[sqlite3.Row]:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("Activity limit must be a whole number greater than zero.")
    with _transaction() as connection:
        return list(
            connection.execute(
                """
                SELECT description, created_at
                FROM activities
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        )
