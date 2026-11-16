# Voice Assistant Workers

A Streamlit app for managing a small shop's customer credit, inventory, and orders, with text and browser-based voice commands.

## Features

- Dashboard with outstanding credit, inventory totals, and recent activity
- Customer credit additions, payments, balances, and transaction history
- Inventory stock adjustments and low-stock warnings
- Orders that reduce available stock
- Text commands and browser speech recognition

## Requirements

- Python 3.10 or later
- A browser with speech-recognition support for voice commands

## Run locally

From the project directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install streamlit
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit prints the local URL when the app starts.

## Voice commands

Voice input requires microphone permission and a secure context, such as `localhost` or HTTPS. The browser's speech-recognition service may process audio outside this app; typed commands stay in the app.

Spoken commands run automatically when speech recognition finishes after a pause. Typed commands run when you click **Run command**. Check the recognized command and result, since speech recognition can mishear names or amounts.

Examples:

- `Add ₹40 credit for Ramesh`
- `What is the balance for Ramesh`
- `Record a payment of ₹100 from Ramesh`
- `Add 20 milk packets to stock`
- `Reduce 5 tea packets from stock`
- `Record an order for 5 tea packets`

## Data

The app stores data in `database/shopkeeper.db`, creating the database schema on startup. A new database is seeded with Ramesh and ₹100 opening credit, Milk with zero stock, and Tea with 10 packets. Existing database records are retained between runs.

## Project layout

```text
app.py                           Streamlit pages and forms
database/db.py                   SQLite connection, schema, and initial data
database/shopkeeper.db           Local persistent database
modules/business.py              Credit, inventory, and order operations
modules/command_processor.py     Text and voice command parsing
modules/voice_input.py           Streamlit voice component integration
modules/voice_component/index.html  Browser speech-recognition control
```
