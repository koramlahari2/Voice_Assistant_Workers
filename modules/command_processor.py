import re

from modules import business


_NUMBER = r"(?:₹\s*)?(?P<amount>\d+(?:\.\d{1,2})?)"
_QUANTITY = r"(?P<quantity>\d+)"
_TRAILING_PUNCTUATION = r"[.!?]*"


def _match(pattern: str, command: str) -> re.Match[str] | None:
    return re.fullmatch(pattern, command.strip(), flags=re.IGNORECASE)


def process_command(command: str) -> str:
    """Parse a supported English shop command and execute it."""
    if not isinstance(command, str) or not command.strip():
        return "Please enter a command."

    text = command.strip()

    try:
        match = _match(
            rf"(?:what is|what's|show|get|check)?\s*"
            rf"(?:the\s+)?balance\s+(?:for|of)\s+(?P<customer>.+?)"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            customer = match.group("customer").strip()
            balance = business.get_customer_balance(customer)
            return f"{customer}'s outstanding balance is ₹{balance:.2f}."

        match = _match(
            rf"(?:add|record)\s+{_NUMBER}\s*(?:rupees?|rs\.?|₹)?\s+"
            rf"credit\s+(?:for|to)\s+(?P<customer>.+?)"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            customer = match.group("customer").strip()
            balance = business.add_credit(customer, float(match.group("amount")))
            return (
                f"Added ₹{float(match.group('amount')):.2f} credit for {customer}. "
                f"Outstanding balance: ₹{balance:.2f}."
            )

        match = _match(
            rf"(?:record|make|receive)\s+(?:a\s+)?payment\s+"
            rf"(?:of\s+)?{_NUMBER}\s*(?:rupees?|rs\.?|₹)?\s+"
            rf"(?:from|for)\s+(?P<customer>.+?)"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            customer = match.group("customer").strip()
            amount = float(match.group("amount"))
            balance = business.record_payment(customer, amount)
            return (
                f"Recorded ₹{amount:.2f} payment from {customer}. "
                f"Remaining balance: ₹{balance:.2f}."
            )

        match = _match(
            rf"(?:add|increase)\s+{_QUANTITY}\s+"
            rf"(?P<product>.+?)\s+to\s+(?:the\s+)?(?:inventory|stock)"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            product_text = match.group("product").strip()
            product, unit = _product_and_unit(product_text)
            quantity = int(match.group("quantity"))
            updated = business.adjust_stock(product, quantity, unit=unit)
            return f"Added {quantity} {unit} of {product}. Available: {updated}."

        match = _match(
            rf"(?:reduce|remove)\s+{_QUANTITY}\s+"
            rf"(?P<product>.+?)\s+from\s+(?:the\s+)?(?:inventory|stock)"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            product_text = match.group("product").strip()
            product, unit = _product_and_unit(product_text)
            quantity = int(match.group("quantity"))
            updated = business.adjust_stock(
                product, quantity, action="reduce", unit=unit
            )
            return f"Reduced {quantity} {unit} of {product}. Available: {updated}."

        match = _match(
            rf"(?:record\s+)?(?:an?\s+)?order\s+(?:for\s+)?{_QUANTITY}\s+"
            rf"(?P<product>.+?)(?:\s+for\s+(?P<customer>.+?))?"
            rf"\s*{_TRAILING_PUNCTUATION}",
            text,
        )
        if match:
            product_text = match.group("product").strip()
            product, unit = _product_and_unit(product_text)
            quantity = int(match.group("quantity"))
            customer = match.group("customer")
            order_id = business.place_order(product, quantity, customer)
            return (
                f"Recorded order #{order_id} for {quantity} {unit} of {product}."
            )

        return (
            "I couldn't understand that command. Try: "
            "'Add 40 rupees credit for Ramesh', "
            "'What is the balance for Ramesh', "
            "'Record a payment of 100 from Ramesh', "
            "'Add 20 milk packets to stock', or "
            "'Record an order for 5 tea packets'."
        )
    except ValueError as error:
        return f"Could not complete the command: {error}"


def _product_and_unit(product_text: str) -> tuple[str, str]:
    words = product_text.split()
    if len(words) > 1 and words[-1].lower().rstrip("s") in {
        "packet",
        "piece",
        "item",
        "bottle",
        "box",
        "kg",
        "gram",
        "liter",
    }:
        unit = words.pop().lower()
        if unit not in {"kg"}:
            unit = unit.rstrip("s") + ("s" if unit.endswith("s") else "")
        return " ".join(words), unit
    return product_text, "items"
