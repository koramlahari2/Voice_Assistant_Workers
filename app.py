import streamlit as st

from database.db import initialize_database
from modules import business
from modules.command_processor import process_command
from modules.voice_input import voice_input


st.set_page_config(
    page_title="Voice Assistant Workers",
    page_icon="🛒",
    layout="wide",
)

initialize_database()

st.title("Voice Assistant Workers")
st.caption("A simple business assistant for small shopkeepers")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Credit", "Inventory", "Orders", "Assistant"],
)


def show_error(error: ValueError) -> None:
    st.error(str(error))


if page == "Dashboard":
    st.header("Dashboard")
    st.info("Demo account: Ramesh starts with ₹100.00 opening credit for the payment demonstration.")

    summary = business.get_dashboard_summary()
    customers_col, credit_col, inventory_col = st.columns(3)
    customers_col.metric("Total customers", summary["total_customers"])
    credit_col.metric(
        "Outstanding credit",
        f"₹{summary['outstanding_credit']:.2f}",
    )
    inventory_col.metric("Available inventory", f"{summary['inventory_units']} units")

    st.subheader("Recent activities")
    activities = business.get_recent_activities()
    if activities:
        st.dataframe(
            [
                {"Activity": row["description"], "Time": row["created_at"]}
                for row in activities
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.write("No activities yet.")

elif page == "Credit":
    st.header("Customer credit")
    add_col, payment_col = st.columns(2)

    with add_col:
        st.subheader("Add credit")
        with st.form("add_credit_form"):
            customer_name = st.text_input("Customer name", key="credit_customer")
            amount = st.number_input("Amount (₹)", min_value=0.01, step=10.0)
            submitted = st.form_submit_button("Add credit")
        if submitted:
            try:
                balance = business.add_credit(customer_name, amount)
                st.success(
                    f"Added ₹{amount:.2f} for {customer_name.strip()}. "
                    f"Outstanding balance: ₹{balance:.2f}."
                )
            except ValueError as error:
                show_error(error)

    with payment_col:
        st.subheader("Record payment")
        customers = business.get_customers()
        if customers:
            with st.form("payment_form"):
                payment_customer = st.selectbox("Customer", customers)
                payment_amount = st.number_input(
                    "Payment amount (₹)", min_value=0.01, step=10.0
                )
                submitted = st.form_submit_button("Record payment")
            if submitted:
                try:
                    balance = business.record_payment(
                        payment_customer,
                        payment_amount,
                    )
                    st.success(
                        f"Payment recorded. {payment_customer}'s balance: "
                        f"₹{balance:.2f}."
                    )
                except ValueError as error:
                    show_error(error)
        else:
            st.info("Add a customer before recording a payment.")

    customers = business.get_customers()
    st.subheader("Balance and transaction history")
    if customers:
        selected_customer = st.selectbox(
            "View customer",
            customers,
            key="history_customer",
        )
        try:
            st.metric(
                f"{selected_customer}'s outstanding balance",
                f"₹{business.get_customer_balance(selected_customer):.2f}",
            )
            history = business.get_customer_history(selected_customer)
            st.dataframe(
                [
                    {
                        "Type": row["transaction_type"].title(),
                        "Amount": f"₹{row['amount']:.2f}",
                        "Note": row["note"],
                        "Time": row["created_at"],
                    }
                    for row in history
                ],
                width="stretch",
                hide_index=True,
            )
        except ValueError as error:
            show_error(error)

elif page == "Inventory":
    st.header("Inventory")
    with st.form("inventory_form"):
        action = st.selectbox("Action", ["Add stock", "Reduce stock"])
        product_name = st.text_input("Product name")
        quantity = st.number_input("Quantity", min_value=1, step=1)
        unit = st.text_input("Unit", value="items")
        submitted = st.form_submit_button("Update inventory")
    if submitted:
        try:
            updated = business.adjust_stock(
                product_name,
                int(quantity),
                action="add" if action == "Add stock" else "reduce",
                unit=unit,
            )
            st.success(f"{product_name.strip()} stock updated. Available: {updated}.")
        except ValueError as error:
            show_error(error)

    inventory = business.get_inventory()
    low_stock = [
        row for row in inventory
        if row["quantity"] <= row["low_stock_threshold"]
    ]
    if low_stock:
        st.warning(
            "Low stock: "
            + ", ".join(
                f"{row['name']} ({row['quantity']} {row['unit']})"
                for row in low_stock
            )
        )
    st.dataframe(
        [
            {
                "Product": row["name"],
                "Available": row["quantity"],
                "Unit": row["unit"],
                "Low-stock threshold": row["low_stock_threshold"],
            }
            for row in inventory
        ],
        width="stretch",
        hide_index=True,
    )

elif page == "Orders":
    st.header("Orders")
    inventory = business.get_inventory()
    available_products = [row for row in inventory if row["quantity"] > 0]
    if available_products:
        product_by_label = {
            f"{row['name']} ({row['quantity']} {row['unit']} available)": row
            for row in available_products
        }
        with st.form("order_form"):
            product_label = st.selectbox(
                "Product",
                list(product_by_label),
            )
            order_quantity = st.number_input(
                "Quantity",
                min_value=1,
                step=1,
            )
            customers = business.get_customers()
            customer_options = ["Walk-in customer", *customers]
            customer_option = st.selectbox("Customer (optional)", customer_options)
            submitted = st.form_submit_button("Record order")
        if submitted:
            selected_product = product_by_label[product_label]
            customer_name = (
                None if customer_option == "Walk-in customer" else customer_option
            )
            try:
                order_id = business.place_order(
                    selected_product["name"],
                    int(order_quantity),
                    customer_name,
                )
                st.success(
                    f"Order #{order_id} recorded. "
                    f"{selected_product['name']} stock has been reduced."
                )
            except ValueError as error:
                show_error(error)
    else:
        st.info("Add stock in Inventory before recording an order.")

    st.subheader("Order history")
    orders = business.get_order_history()
    if orders:
        st.dataframe(
            [
                {
                    "Order": row["id"],
                    "Customer": row["customer_name"] or "Walk-in",
                    "Product": row["product_name"],
                    "Quantity": f"{row['quantity']} {row['unit']}",
                    "Time": row["created_at"],
                }
                for row in orders
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.write("No orders yet.")

elif page == "Assistant":
    st.header("Voice and text assistant")
    st.caption(
        "Use the microphone or type a command in English. "
        "Example: “Add ₹40 credit for Ramesh.” "
        "Spoken commands run when you pause; typed commands need the Run command button."
    )
    st.info(
        "Voice input uses your browser's speech-recognition service. "
        "Audio may be processed by that browser provider; typed commands stay in this app."
    )
    spoken = voice_input()
    new_voice_command = None
    if spoken and st.session_state.get("last_voice_event") != spoken["event_id"]:
        st.session_state["last_voice_event"] = spoken["event_id"]
        st.session_state["assistant_command"] = spoken["transcript"]
        new_voice_command = spoken["transcript"]
    st.caption("The recognized command appears here after speech completes.")
    with st.form("assistant_form"):
        command = st.text_input("Your command", key="assistant_command")
        submitted = st.form_submit_button("Run command")
    if submitted:
        result = process_command(command)
    elif new_voice_command is not None:
        result = process_command(new_voice_command)
    else:
        result = None
    if result is not None:
        if result.startswith("Could not complete") or result.startswith(
            "I couldn't understand"
        ) or result == "Please enter a command.":
            st.warning(result)
        else:
            st.success(result)
