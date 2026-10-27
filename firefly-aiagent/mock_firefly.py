"""
Mock Firefly III REST API Server.

Provides a lightweight local emulator using FastAPI & Uvicorn for testing the
Firefly III AI Agent without requiring a running Docker instance.
Includes sample accounts, transactions, budgets, categories, piggy banks, and bills.
"""

from datetime import datetime
from typing import Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

app = FastAPI(title="Mock Firefly III API", version="1.0.0")

# ── In-Memory Mock Database ─────────────────────────────────────
ACCOUNTS = [
    {
        "id": "1",
        "type": "accounts",
        "attributes": {
            "name": "Rekening Utama BCA",
            "type": "asset",
            "current_balance": "8500000.00",
            "currency_code": "IDR",
            "currency_symbol": "Rp",
            "active": True,
            "notes": "Rekening payroll dan transaksi utama",
        },
    },
    {
        "id": "2",
        "type": "accounts",
        "attributes": {
            "name": "Dompet Tunai",
            "type": "asset",
            "current_balance": "350000.00",
            "currency_code": "IDR",
            "currency_symbol": "Rp",
            "active": True,
            "notes": "Uang fisik di dompet",
        },
    },
    {
        "id": "3",
        "type": "accounts",
        "attributes": {
            "name": "Tabungan Masa Depan (Mandiri)",
            "type": "asset",
            "current_balance": "25000000.00",
            "currency_code": "IDR",
            "currency_symbol": "Rp",
            "active": True,
            "notes": "Rekening khusus tabungan",
        },
    },
]

CATEGORIES = [
    {"id": "1", "type": "categories", "attributes": {"name": "Makanan & Minuman", "notes": "Makan sehari-hari & jajan"}},
    {"id": "2", "type": "categories", "attributes": {"name": "Transportasi", "notes": "Bensin, ojek online, tiket"}},
    {"id": "3", "type": "categories", "attributes": {"name": "Tagihan & Utilitas", "notes": "Listrik, WiFi, pulsa"}},
    {"id": "4", "type": "categories", "attributes": {"name": "Belanja", "notes": "Kebutuhan bulanan & pakaian"}},
    {"id": "5", "type": "categories", "attributes": {"name": "Hiburan", "notes": "Bioskop, game, rekreasi"}},
]

BUDGETS = [
    {
        "id": "1",
        "type": "budgets",
        "attributes": {
            "name": "Jajan Bulanan",
            "active": True,
            "auto_budget_amount": "1500000.00",
            "auto_budget_period": "monthly",
            "spent": [{"sum": "850000.00", "currency_symbol": "Rp"}],
        },
        "limits": [
            {
                "start": "2026-10-01",
                "end": "2026-10-31",
                "amount": "1500000.00",
                "spent": "850000.00",
            }
        ],
    },
    {
        "id": "2",
        "type": "budgets",
        "attributes": {
            "name": "Transportasi & Bensin",
            "active": True,
            "auto_budget_amount": "600000.00",
            "auto_budget_period": "monthly",
            "spent": [{"sum": "250000.00", "currency_symbol": "Rp"}],
        },
        "limits": [
            {
                "start": "2026-10-01",
                "end": "2026-10-31",
                "amount": "600000.00",
                "spent": "250000.00",
            }
        ],
    },
]

PIGGY_BANKS = [
    {
        "id": "1",
        "type": "piggy_banks",
        "attributes": {
            "name": "Dana Darurat",
            "account_id": "3",
            "account_name": "Tabungan Masa Depan (Mandiri)",
            "target_amount": "30000000.00",
            "current_amount": "15000000.00",
            "left_to_save": "15000000.00",
            "percentage": 50.0,
            "start_date": "2026-01-01",
            "target_date": "2026-12-31",
        },
    },
    {
        "id": "2",
        "type": "piggy_banks",
        "attributes": {
            "name": "Beli Laptop Kerja Baru",
            "account_id": "3",
            "account_name": "Tabungan Masa Depan (Mandiri)",
            "target_amount": "18000000.00",
            "current_amount": "7200000.00",
            "left_to_save": "10800000.00",
            "percentage": 40.0,
            "start_date": "2026-03-01",
            "target_date": "2026-11-30",
        },
    },
]

BILLS = [
    {
        "id": "1",
        "type": "bills",
        "attributes": {
            "name": "WiFi Indihome Rumah",
            "amount_min": "385000.00",
            "amount_max": "385000.00",
            "date": "2026-10-20",
            "repeat_freq": "monthly",
            "active": True,
            "paid_dates": [],
            "next_expected_match": "2026-10-20",
        },
    },
    {
        "id": "2",
        "type": "bills",
        "attributes": {
            "name": "Langganan Spotify & YouTube Premium",
            "amount_min": "105000.00",
            "amount_max": "105000.00",
            "date": "2026-10-25",
            "repeat_freq": "monthly",
            "active": True,
            "paid_dates": [],
            "next_expected_match": "2026-10-25",
        },
    },
]

TRANSACTIONS = [
    {
        "id": "101",
        "type": "transactions",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "date": "2026-10-15",
                    "amount": "35000.00",
                    "description": "Kopi Latte di Fore Coffee",
                    "source_name": "Rekening Utama BCA",
                    "destination_name": "Fore Coffee",
                    "category_name": "Makanan & Minuman",
                    "budget_name": "Jajan Bulanan",
                    "currency_code": "IDR",
                    "currency_symbol": "Rp",
                    "notes": "Beli saat istirahat kerja",
                }
            ]
        },
    },
    {
        "id": "102",
        "type": "transactions",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "date": "2026-10-16",
                    "amount": "25000.00",
                    "description": "Makan siang Nasi Padang Sederhana",
                    "source_name": "Dompet Tunai",
                    "destination_name": "RM Padang",
                    "category_name": "Makanan & Minuman",
                    "budget_name": "Jajan Bulanan",
                    "currency_code": "IDR",
                    "currency_symbol": "Rp",
                    "notes": "Ayam bakar + es teh manis",
                }
            ]
        },
    },
    {
        "id": "103",
        "type": "transactions",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "date": "2026-10-17",
                    "amount": "150000.00",
                    "description": "Bensin Pertamax Mobil",
                    "source_name": "Rekening Utama BCA",
                    "destination_name": "SPBU Pertamina",
                    "category_name": "Transportasi",
                    "budget_name": "Transportasi & Bensin",
                    "currency_code": "IDR",
                    "currency_symbol": "Rp",
                    "notes": "Isi full tank",
                }
            ]
        },
    },
]


# ── API Endpoints ───────────────────────────────────────────────

@app.get("/api/v1/about")
def get_about():
    """Return system information."""
    return {
        "data": {
            "type": "about",
            "id": "1",
            "attributes": {
                "version": "6.1.15-mock",
                "api_version": "2.0.0",
                "php_version": "8.3.0",
                "os": "Linux (Mock Container)",
                "driver": "mariadb",
            },
        }
    }


@app.get("/api/v1/about/user")
def get_about_user():
    """Return current authenticated user profile."""
    return {
        "data": {
            "type": "users",
            "id": "1",
            "attributes": {
                "email": "rozin@gmail.com",
                "role": "owner",
                "blocked": False,
                "created_at": "2026-10-18T05:57:17+00:00",
            },
        }
    }


@app.get("/api/v1/accounts")
def get_accounts(type: Optional[str] = None):
    """List financial accounts."""
    if not type or type == "all":
        return {"data": ACCOUNTS}
    filtered = [a for a in ACCOUNTS if a["attributes"]["type"] == type]
    return {"data": filtered}


@app.get("/api/v1/accounts/{account_id}")
def get_account(account_id: str):
    """Get single account."""
    for a in ACCOUNTS:
        if a["id"] == account_id:
            return {"data": a}
    raise HTTPException(status_code=404, detail="Account not found")


@app.post("/api/v1/accounts")
def create_account(payload: dict[str, Any]):
    """Create a new financial account."""
    new_id = str(len(ACCOUNTS) + 1)
    acc = {
        "id": new_id,
        "type": "accounts",
        "attributes": {
            "name": payload.get("name", f"Account {new_id}"),
            "type": payload.get("type", "asset"),
            "current_balance": str(payload.get("opening_balance", "0.00")),
            "currency_code": payload.get("currency_code", "IDR"),
            "currency_symbol": "Rp",
            "active": True,
            "notes": payload.get("notes", ""),
        },
    }
    ACCOUNTS.append(acc)
    return {"data": acc}


@app.get("/api/v1/transactions")
def get_transactions(
    start: Optional[str] = None,
    end: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
):
    """List transactions with optional filtering."""
    results = TRANSACTIONS
    if type:
        results = [
            t for t in results
            if t["attributes"]["transactions"][0].get("type") == type
        ]
    return {"data": results[:limit]}


@app.get("/api/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get single transaction."""
    for t in TRANSACTIONS:
        if t["id"] == transaction_id:
            return {"data": t}
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.post("/api/v1/transactions")
def create_transaction(payload: dict[str, Any]):
    """Create a new transaction and update relevant account balance."""
    splits = payload.get("transactions", [])
    if not splits:
        raise HTTPException(status_code=422, detail="No split transaction provided.")

    t = splits[0]
    new_id = str(len(TRANSACTIONS) + 101)
    new_entry = {
        "id": new_id,
        "type": "transactions",
        "attributes": {
            "transactions": [
                {
                    "type": t.get("type", "withdrawal"),
                    "date": t.get("date", datetime.now().strftime("%Y-%m-%d")),
                    "amount": str(t.get("amount", "0.00")),
                    "description": t.get("description", "Untitled"),
                    "source_name": t.get("source_name", "Rekening Utama BCA"),
                    "destination_name": t.get("destination_name", "External"),
                    "category_name": t.get("category_name", "Lain-lain"),
                    "budget_name": t.get("budget_name", ""),
                    "currency_code": "IDR",
                    "currency_symbol": "Rp",
                    "notes": t.get("notes", ""),
                }
            ]
        },
    }
    TRANSACTIONS.insert(0, new_entry)

    # Adjust account balance if source exists
    source_name = t.get("source_name")
    amount_val = float(t.get("amount", 0))
    if source_name:
        for acc in ACCOUNTS:
            if acc["attributes"]["name"].lower() == source_name.lower():
                current = float(acc["attributes"]["current_balance"])
                if t.get("type") == "withdrawal":
                    acc["attributes"]["current_balance"] = f"{current - amount_val:.2f}"
                elif t.get("type") == "deposit":
                    acc["attributes"]["current_balance"] = f"{current + amount_val:.2f}"

    return {"data": new_entry}


@app.delete("/api/v1/transactions/{transaction_id}")
def delete_transaction(transaction_id: str):
    """Delete a transaction."""
    global TRANSACTIONS
    initial_len = len(TRANSACTIONS)
    TRANSACTIONS = [t for t in TRANSACTIONS if t["id"] != transaction_id]
    if len(TRANSACTIONS) == initial_len:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Response(status_code=204)


@app.get("/api/v1/search/transactions")
def search_transactions(query: str):
    """Search transactions by text."""
    q = query.lower()
    matches = []
    for t in TRANSACTIONS:
        split = t["attributes"]["transactions"][0]
        desc = split.get("description", "").lower()
        notes = split.get("notes", "").lower()
        cat = split.get("category_name", "").lower()
        if q in desc or q in notes or q in cat:
            matches.append(t)
    return {"data": matches}


@app.get("/api/v1/categories")
def get_categories():
    """List transaction categories."""
    return {"data": CATEGORIES}


@app.post("/api/v1/categories")
def create_category(payload: dict[str, Any]):
    """Create a new category."""
    new_id = str(len(CATEGORIES) + 1)
    cat = {
        "id": new_id,
        "type": "categories",
        "attributes": {
            "name": payload.get("name", f"Category {new_id}"),
            "notes": payload.get("notes", ""),
        },
    }
    CATEGORIES.append(cat)
    return {"data": cat}


@app.get("/api/v1/budgets")
def get_budgets():
    """List budgets."""
    return {"data": BUDGETS}


@app.post("/api/v1/budgets")
def create_budget(payload: dict[str, Any]):
    """Create a new budget."""
    new_id = str(len(BUDGETS) + 1)
    b = {
        "id": new_id,
        "type": "budgets",
        "attributes": {
            "name": payload.get("name", f"Budget {new_id}"),
            "active": True,
            "auto_budget_amount": str(payload.get("auto_budget_amount", "0.00")),
            "auto_budget_period": payload.get("auto_budget_period", "monthly"),
            "spent": [{"sum": "0.00", "currency_symbol": "Rp"}],
        },
        "limits": [
            {
                "start": datetime.now().strftime("%Y-%m-01"),
                "end": datetime.now().strftime("%Y-%m-28"),
                "amount": str(payload.get("auto_budget_amount", "0.00")),
                "spent": "0.00",
            }
        ],
    }
    BUDGETS.append(b)
    return {"data": b}


@app.get("/api/v1/budgets/{budget_id}/limits")
def get_budget_limits(budget_id: str):
    """Get budget limit and spent metrics."""
    for b in BUDGETS:
        if b["id"] == budget_id:
            limits = b.get("limits", [])
            data = []
            for idx, lim in enumerate(limits, 1):
                data.append({
                    "id": str(idx),
                    "type": "budget_limits",
                    "attributes": {
                        "start": lim["start"],
                        "end": lim["end"],
                        "amount": lim["amount"],
                        "spent": lim["spent"],
                        "currency_symbol": "Rp",
                        "currency_code": "IDR",
                    },
                })
            return {"data": data}
    raise HTTPException(status_code=404, detail="Budget not found")


@app.get("/api/v1/piggy-banks")
def get_piggy_banks():
    """List piggy banks / savings goals."""
    return {"data": PIGGY_BANKS}


@app.post("/api/v1/piggy-banks")
def create_piggy_bank(payload: dict[str, Any]):
    """Create a new savings goal."""
    new_id = str(len(PIGGY_BANKS) + 1)
    target = float(payload.get("target_amount", 0))
    p = {
        "id": new_id,
        "type": "piggy_banks",
        "attributes": {
            "name": payload.get("name", f"Goal {new_id}"),
            "account_id": str(payload.get("account_id", "3")),
            "account_name": "Tabungan Masa Depan (Mandiri)",
            "target_amount": f"{target:.2f}",
            "current_amount": "0.00",
            "left_to_save": f"{target:.2f}",
            "percentage": 0.0,
            "start_date": payload.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            "target_date": payload.get("target_date", ""),
        },
    }
    PIGGY_BANKS.append(p)
    return {"data": p}


@app.put("/api/v1/piggy-banks/{piggy_bank_id}")
def update_piggy_bank(piggy_bank_id: str, payload: dict[str, Any]):
    """Update piggy bank target or saved amount."""
    for p in PIGGY_BANKS:
        if p["id"] == piggy_bank_id:
            attrs = p["attributes"]
            if "name" in payload:
                attrs["name"] = payload["name"]
            if "target_amount" in payload:
                attrs["target_amount"] = str(payload["target_amount"])
            if "current_amount" in payload:
                cur = float(payload["current_amount"])
                tar = float(attrs["target_amount"])
                attrs["current_amount"] = f"{cur:.2f}"
                attrs["left_to_save"] = f"{max(0.0, tar - cur):.2f}"
                attrs["percentage"] = round((cur / tar * 100) if tar > 0 else 0, 1)
            return {"data": p}
    raise HTTPException(status_code=404, detail="Piggy bank not found")


@app.get("/api/v1/bills")
def get_bills():
    """List recurring bills."""
    return {"data": BILLS}


@app.post("/api/v1/bills")
def create_bill(payload: dict[str, Any]):
    """Create recurring bill."""
    new_id = str(len(BILLS) + 1)
    b = {
        "id": new_id,
        "type": "bills",
        "attributes": {
            "name": payload.get("name", f"Bill {new_id}"),
            "amount_min": str(payload.get("amount_min", "0.00")),
            "amount_max": str(payload.get("amount_max", "0.00")),
            "date": payload.get("date", datetime.now().strftime("%Y-%m-%d")),
            "repeat_freq": payload.get("repeat_freq", "monthly"),
            "active": True,
            "paid_dates": [],
            "next_expected_match": payload.get("date", datetime.now().strftime("%Y-%m-%d")),
        },
    }
    BILLS.append(b)
    return {"data": b}


@app.get("/api/v1/summary/basic")
def get_summary(start: str, end: str):
    """Aggregate financial summary."""
    return {
        "spent": {
            "label": "Total Spent",
            "monetary_value": 1025000.0,
            "value_parsed": "Rp 1.025.000",
        },
        "earned": {
            "label": "Total Earned",
            "monetary_value": 8500000.0,
            "value_parsed": "Rp 8.500.000",
        },
        "net": {
            "label": "Net Savings",
            "monetary_value": 7475000.0,
            "value_parsed": "Rp 7.475.000",
        },
    }


import os
import sys

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FIREFLY_MOCK_PORT", "8088")))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    print(f"[INFO] Starting Mock Firefly III Server on http://127.0.0.1:{port} ...")
    uvicorn.run(app, host="127.0.0.1", port=port)
