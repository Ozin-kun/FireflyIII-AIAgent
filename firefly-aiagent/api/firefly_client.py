"""
Firefly III REST API Client.

Handles HTTP requests, bearer token authentication, response flattening,
and comprehensive error handling for Firefly III endpoints:
- Accounts (inquiry, creation, balance)
- Transactions (create, search, filter, delete)
- Budgets (inquiry, creation, limit & spent tracking)
- Piggy Banks / Savings Goals (inquiry, creation, contributions)
- Bills / Subscriptions (recurring obligations)
- Categories (tagging & grouping)
- Financial Summaries
"""

import logging
from datetime import datetime
from typing import Any, Optional
import requests

logger = logging.getLogger(__name__)


class FireflyClient:
    """Client for interacting with Firefly III v1 REST API."""

    def __init__(self, base_url: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated HTTP request to Firefly III with descriptive error propagation."""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.status_code != 204 else {}
        except requests.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code} [{method} {endpoint}]: {e}"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    detail = err_data.get("message") or err_data.get("errors") or err_data
                    error_msg += f" | Details: {detail}"
            except Exception:
                error_msg += f" | Body: {response.text[:200]}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except requests.RequestException as e:
            logger.error("Network Error [%s %s]: %s", method, url, e)
            raise RuntimeError(f"Connection to Firefly III failed [{method} {endpoint}]: {e}") from e

    def _flatten_transaction(self, raw: dict) -> dict:
        """Flatten Firefly III's nested transaction response."""
        attrs = raw.get("attributes", {})
        splits = attrs.get("transactions", [])
        if not splits:
            return {"id": raw.get("id"), "error": "No split found"}

        t = splits[0]
        return {
            "id": raw.get("id"),
            "type": t.get("type", "withdrawal"),
            "description": t.get("description", ""),
            "amount": t.get("amount", "0"),
            "date": t.get("date", ""),
            "source_name": t.get("source_name", ""),
            "destination_name": t.get("destination_name", ""),
            "category_name": t.get("category_name", ""),
            "budget_name": t.get("budget_name", ""),
            "notes": t.get("notes", ""),
            "currency_code": t.get("currency_code", "IDR"),
            "currency_symbol": t.get("currency_symbol", "Rp"),
        }

    # ── System / Health ──────────────────────────────────────────
    def get_about(self) -> dict:
        """Check system information and connection status."""
        res = self._request("GET", "about")
        data = res.get("data", res)
        return data.get("attributes", data) if isinstance(data, dict) else {}

    def get_current_user(self) -> dict:
        """Fetch information about the currently authenticated Firefly III user."""
        res = self._request("GET", "about/user")
        data = res.get("data", res)
        attrs = data.get("attributes", data) if isinstance(data, dict) else {}
        return {
            "id": data.get("id"),
            "email": attrs.get("email", ""),
            "role": attrs.get("role", "owner"),
            "blocked": attrs.get("blocked", False),
        }

    # ── Accounts Management ──────────────────────────────────────
    def get_accounts(self, account_type: str = "all") -> list[dict]:
        """Fetch all financial accounts."""
        params = {} if account_type == "all" else {"type": account_type}
        res = self._request("GET", "accounts", params=params)
        accounts = []
        for a in res.get("data", []):
            attrs = a.get("attributes", {})
            accounts.append({
                "id": a.get("id"),
                "name": attrs.get("name", ""),
                "type": attrs.get("type", ""),
                "current_balance": attrs.get("current_balance", "0"),
                "currency_code": attrs.get("currency_code", ""),
                "currency_symbol": attrs.get("currency_symbol", ""),
                "active": attrs.get("active", True),
            })
        return accounts

    def get_account(self, account_id: int) -> dict:
        """Fetch a specific account by ID."""
        res = self._request("GET", f"accounts/{account_id}")
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", ""),
            "type": attrs.get("type", ""),
            "current_balance": attrs.get("current_balance", "0"),
            "currency_code": attrs.get("currency_code", ""),
            "currency_symbol": attrs.get("currency_symbol", ""),
            "active": attrs.get("active", True),
            "notes": attrs.get("notes", ""),
        }

    def _resolve_asset_account(self, name_or_query: Optional[str] = None) -> Optional[dict]:
        """Resolve an asset account by ID, exact name, or fuzzy substring match, defaulting to first asset account."""
        try:
            accounts = self.get_accounts(account_type="asset")
            if not accounts:
                return None
            if not name_or_query:
                return accounts[0]

            q = str(name_or_query).strip().lower()
            # 1. Match by numeric ID
            for acc in accounts:
                if str(acc.get("id")) == q:
                    return acc
            # 2. Match by exact name (case-insensitive)
            for acc in accounts:
                if acc.get("name", "").strip().lower() == q:
                    return acc
            # 3. Match by substring
            for acc in accounts:
                acc_name = acc.get("name", "").strip().lower()
                if q in acc_name or acc_name in q:
                    return acc
            # 4. Fallback to first available asset account
            return accounts[0]
        except Exception as e:
            logger.warning("Could not auto-resolve asset account for '%s': %s", name_or_query, e)
            return None

    def create_account(
        self,
        name: str,
        account_type: str = "asset",
        currency_code: str = "IDR",
        opening_balance: float = 0.0,
        notes: str = "",
        liability_type: str = "debt",
        liability_direction: str = "credit",
    ) -> dict:
        """Create a new financial account (e.g. Bank Account, Cash Wallet, Credit Card).
        
        Compliant with Firefly III v6.2+ requirements:
        - Requires `account_role: defaultAsset` for asset accounts.
        - Requires `opening_balance_date` if `opening_balance` is specified.
        - Requires `liability_type` & `liability_direction` for liability accounts.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        payload: dict[str, Any] = {
            "name": name,
            "type": account_type,
            "currency_code": currency_code,
            "notes": notes,
        }
        if account_type == "asset":
            payload["account_role"] = "defaultAsset"
            if opening_balance is not None and float(opening_balance) != 0.0:
                payload["opening_balance"] = str(opening_balance)
                payload["opening_balance_date"] = today_str
        elif account_type in ("liability", "liabilities"):
            payload["liability_type"] = liability_type
            payload["liability_direction"] = liability_direction
            if opening_balance is not None and float(opening_balance) != 0.0:
                payload["opening_balance"] = str(opening_balance)
                payload["opening_balance_date"] = today_str
        elif opening_balance is not None and float(opening_balance) != 0.0:
            payload["opening_balance"] = str(opening_balance)
            payload["opening_balance_date"] = today_str

        res = self._request("POST", "accounts", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", name),
            "type": attrs.get("type", account_type),
            "current_balance": attrs.get("current_balance", str(opening_balance)),
            "currency_code": attrs.get("currency_code", currency_code),
        }

    # ── Transactions Management ──────────────────────────────────
    def get_transactions(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch transaction records with optional filters."""
        params: dict[str, Any] = {"limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if type:
            params["type"] = type

        res = self._request("GET", "transactions", params=params)
        return [self._flatten_transaction(t) for t in res.get("data", [])]

    def create_transaction(
        self,
        description: str,
        amount: float,
        type: str = "withdrawal",
        source_name: Optional[str] = None,
        destination_name: Optional[str] = None,
        category_name: Optional[str] = None,
        budget_name: Optional[str] = None,
        date: Optional[str] = None,
        notes: Optional[str] = None,
        piggy_bank_id: Optional[int] = None,
    ) -> dict:
        """Create a new transaction in Firefly III with intelligent account resolution."""
        resolved_source = source_name
        resolved_destination = destination_name

        if type == "withdrawal":
            # Source must be a valid asset account; auto-resolve if missing or fuzzy
            acc = self._resolve_asset_account(source_name)
            resolved_source = acc["name"] if acc else (source_name or "Kas")
            # Destination is the expense recipient/merchant; default to description
            if not resolved_destination:
                resolved_destination = description or "Pengeluaran Umum"
        elif type == "deposit":
            # Destination must be a valid asset account; auto-resolve if missing or fuzzy
            acc = self._resolve_asset_account(destination_name)
            resolved_destination = acc["name"] if acc else (destination_name or "Kas")
            # Source is the revenue source
            if not resolved_source:
                resolved_source = "Sumber Pendapatan"
        elif type == "transfer":
            src_acc = self._resolve_asset_account(source_name)
            if src_acc:
                resolved_source = src_acc["name"]
            dst_acc = self._resolve_asset_account(destination_name)
            if dst_acc:
                resolved_destination = dst_acc["name"]

        tx_date = date or datetime.now().strftime("%Y-%m-%d")
        split: dict[str, Any] = {
            "type": type,
            "description": description,
            "amount": str(amount),
            "date": tx_date,
            "source_name": resolved_source,
            "destination_name": resolved_destination,
            "category_name": category_name,
            "budget_name": budget_name,
            "notes": notes or "",
        }
        if piggy_bank_id:
            split["piggy_bank_id"] = piggy_bank_id

        payload = {"transactions": [split]}
        res = self._request("POST", "transactions", json_data=payload)
        return self._flatten_transaction(res.get("data", {}))

    def search_transactions(self, query: str) -> list[dict]:
        """Search transactions by keyword."""
        res = self._request("GET", "search/transactions", params={"query": query})
        return [self._flatten_transaction(t) for t in res.get("data", [])]

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by ID."""
        self._request("DELETE", f"transactions/{transaction_id}")
        return True

    # ── Categories Management ────────────────────────────────────
    def get_categories(self) -> list[dict]:
        """Fetch all categories."""
        res = self._request("GET", "categories")
        categories = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            categories.append({
                "id": item.get("id"),
                "name": attrs.get("name", ""),
                "notes": attrs.get("notes", ""),
            })
        return categories

    def create_category(self, name: str, notes: str = "") -> dict:
        """Create a new transaction category."""
        res = self._request("POST", "categories", json_data={"name": name, "notes": notes})
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", name),
            "notes": attrs.get("notes", notes),
        }

    # ── Budgets & Spending Limits ────────────────────────────────
    def get_budgets(self) -> list[dict]:
        """Fetch all budgets."""
        res = self._request("GET", "budgets")
        budgets = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            spent_data = attrs.get("spent", [])
            spent_sum = spent_data[0].get("sum", "0") if spent_data else "0"
            budgets.append({
                "id": item.get("id"),
                "name": attrs.get("name", ""),
                "active": attrs.get("active", True),
                "auto_budget_amount": attrs.get("auto_budget_amount", "0"),
                "auto_budget_period": attrs.get("auto_budget_period", "monthly"),
                "spent": spent_sum,
            })
        return budgets

    def get_budget_limits(
        self,
        budget_id: int,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        """Fetch spending limits and spent progress for a specific budget."""
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        res = self._request("GET", f"budgets/{budget_id}/limits", params=params)
        limits = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            limits.append({
                "id": item.get("id"),
                "start": attrs.get("start", ""),
                "end": attrs.get("end", ""),
                "amount": attrs.get("amount", "0"),
                "spent": attrs.get("spent", "0"),
                "currency_symbol": attrs.get("currency_symbol", "Rp"),
            })
        return limits

    def create_budget(
        self,
        name: str,
        auto_budget_amount: Optional[float] = None,
        auto_budget_period: str = "monthly",
    ) -> dict:
        """Create a new budget with optional auto-budget limit."""
        payload: dict[str, Any] = {
            "name": name,
            "active": True,
            "auto_budget_period": auto_budget_period,
        }
        if auto_budget_amount is not None:
            payload["auto_budget_amount"] = str(auto_budget_amount)
            payload["auto_budget_type"] = "reset"
            payload["auto_budget_currency_code"] = "IDR"

        res = self._request("POST", "budgets", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", name),
            "auto_budget_amount": attrs.get("auto_budget_amount", "0"),
            "auto_budget_period": attrs.get("auto_budget_period", auto_budget_period),
        }

    # ── Piggy Banks (Savings Goals / Celengan) ────────────────────
    def get_piggy_banks(self) -> list[dict]:
        """Fetch all savings goals (piggy banks)."""
        res = self._request("GET", "piggy-banks")
        piggy_banks = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            piggy_banks.append({
                "id": item.get("id"),
                "name": attrs.get("name", ""),
                "account_id": attrs.get("account_id"),
                "account_name": attrs.get("account_name", ""),
                "target_amount": attrs.get("target_amount", "0"),
                "current_amount": attrs.get("current_amount", "0"),
                "left_to_save": attrs.get("left_to_save", "0"),
                "percentage": attrs.get("percentage", 0),
                "target_date": attrs.get("target_date", ""),
            })
        return piggy_banks

    def create_piggy_bank(
        self,
        name: str,
        target_amount: float,
        account_id: Optional[int] = None,
        account_name: Optional[str] = None,
        target_date: Optional[str] = None,
        start_date: Optional[str] = None,
        currency_code: Optional[str] = None,
    ) -> dict:
        """Create a new piggy bank savings goal in Firefly III."""
        target_acc_id = account_id
        target_currency = currency_code

        # If account_id or currency_code is missing, automatically resolve from asset accounts
        if not target_acc_id or not target_currency:
            try:
                accounts = self.get_accounts()
                asset_accounts = [a for a in accounts if a.get("type") == "asset"]
                chosen = None
                if account_name:
                    chosen = next((a for a in asset_accounts if account_name.lower() in a.get("name", "").lower()), None)
                if not chosen and target_acc_id:
                    chosen = next((a for a in asset_accounts if str(a.get("id")) == str(target_acc_id)), None)
                if not chosen and asset_accounts:
                    chosen = asset_accounts[0]

                if chosen:
                    target_acc_id = int(chosen["id"])
                    if not target_currency:
                        target_currency = chosen.get("currency_code", "IDR")
            except Exception as e:
                logger.warning("Could not auto-resolve account for piggy bank: %s", e)

        if not target_acc_id:
            target_acc_id = 1
        if not target_currency:
            target_currency = "IDR"

        payload: dict[str, Any] = {
            "name": name,
            "target_amount": str(target_amount),
            "start_date": start_date or datetime.now().strftime("%Y-%m-%d"),
            "transaction_currency_code": target_currency,
            "accounts": [{"account_id": int(target_acc_id)}],
        }
        if target_date:
            payload["target_date"] = target_date

        res = self._request("POST", "piggy-banks", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", name),
            "target_amount": attrs.get("target_amount", str(target_amount)),
            "current_amount": attrs.get("current_amount", "0"),
            "left_to_save": attrs.get("left_to_save", str(target_amount)),
        }

    def get_piggy_bank(self, piggy_bank_id: int) -> dict:
        """Fetch a specific piggy bank by numeric ID."""
        res = self._request("GET", f"piggy-banks/{piggy_bank_id}")
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", ""),
            "target_amount": attrs.get("target_amount", "0"),
            "current_amount": attrs.get("current_amount", "0"),
            "left_to_save": attrs.get("left_to_save", "0"),
            "percentage": attrs.get("percentage", 0),
            "target_date": attrs.get("target_date", ""),
            "accounts": attrs.get("accounts", []),
        }

    def update_piggy_bank_amount(
        self,
        piggy_bank_id: int,
        new_current_amount: float,
        account_id: Optional[int] = None,
    ) -> dict:
        """Directly adjust a piggy bank current saved amount using the Firefly III v6.2+ accounts pivot schema."""
        pb = self.get_piggy_bank(piggy_bank_id)
        pb_name = pb.get("name", "Savings Goal")
        target_acc_id = account_id

        if not target_acc_id:
            accounts = pb.get("accounts", [])
            if accounts:
                target_acc_id = int(accounts[0].get("account_id"))
            else:
                primary = self._resolve_asset_account()
                target_acc_id = int(primary["id"]) if primary else 1

        payload = {
            "name": pb_name,
            "accounts": [{
                "account_id": target_acc_id,
                "current_amount": f"{new_current_amount:.2f}",
            }],
        }
        res = self._request("PUT", f"piggy-banks/{piggy_bank_id}", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", pb_name),
            "current_amount": attrs.get("current_amount", f"{new_current_amount:.2f}"),
            "left_to_save": attrs.get("left_to_save", "0"),
            "percentage": attrs.get("percentage", 0),
        }

    # ── Bills / Subscriptions (Tagihan Rutin) ─────────────────────
    def get_bills(self) -> list[dict]:
        """Fetch all recurring bills and subscription obligations."""
        res = self._request("GET", "bills")
        bills = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            bills.append({
                "id": item.get("id"),
                "name": attrs.get("name", ""),
                "amount_min": attrs.get("amount_min", "0"),
                "amount_max": attrs.get("amount_max", "0"),
                "date": attrs.get("date", ""),
                "repeat_freq": attrs.get("repeat_freq", "monthly"),
                "active": attrs.get("active", True),
                "next_expected_match": attrs.get("next_expected_match", ""),
            })
        return bills

    def create_bill(
        self,
        name: str,
        amount_min: float,
        amount_max: Optional[float] = None,
        date: Optional[str] = None,
        repeat_freq: str = "monthly",
    ) -> dict:
        """Create a recurring bill reminder."""
        actual_max = amount_max if amount_max is not None else amount_min
        payload = {
            "name": name,
            "amount_min": str(amount_min),
            "amount_max": str(actual_max),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "repeat_freq": repeat_freq,
            "active": True,
        }
        res = self._request("POST", "bills", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "name": attrs.get("name", name),
            "amount_min": attrs.get("amount_min", str(amount_min)),
            "amount_max": attrs.get("amount_max", str(actual_max)),
            "repeat_freq": attrs.get("repeat_freq", repeat_freq),
        }

    # ── Summary & Insights ───────────────────────────────────────
    def get_summary(self, start: str, end: str) -> dict:
        """Get aggregate spending and income summary for a date range."""
        return self._request("GET", "summary/basic", params={"start": start, "end": end})

    # ── Tags Management ──────────────────────────────────────────
    def get_tags(self) -> list[dict]:
        """Fetch all tags."""
        res = self._request("GET", "tags")
        tags = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            tags.append({
                "id": item.get("id"),
                "tag": attrs.get("tag", ""),
                "description": attrs.get("description", ""),
            })
        return tags

    def create_tag(self, tag: str, description: str = "") -> dict:
        """Create a new tag."""
        payload = {"tag": tag, "description": description}
        res = self._request("POST", "tags", json_data=payload)
        data = res.get("data", {})
        attrs = data.get("attributes", {})
        return {
            "id": data.get("id"),
            "tag": attrs.get("tag", tag),
            "description": attrs.get("description", description),
        }

    # ── Recurring Transactions (Recurrences) ────────────────────
    def get_recurrences(self) -> list[dict]:
        """Fetch recurring transactions schedule."""
        res = self._request("GET", "recurrences")
        recurrences = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            recurrences.append({
                "id": item.get("id"),
                "title": attrs.get("title", ""),
                "type": attrs.get("type", ""),
                "repeat_freq": attrs.get("repeat_freq", ""),
                "active": attrs.get("active", True),
                "first_date": attrs.get("first_date", ""),
                "latest_date": attrs.get("latest_date", ""),
            })
        return recurrences

    # ── Rules & Automation Engine ────────────────────────────────
    def get_rules(self) -> list[dict]:
        """Fetch user-defined automation rules."""
        res = self._request("GET", "rules")
        rules = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            rules.append({
                "id": item.get("id"),
                "title": attrs.get("title", ""),
                "active": attrs.get("active", True),
                "trigger": attrs.get("trigger", ""),
                "rule_group_id": attrs.get("rule_group_id"),
            })
        return rules

    def get_rule_groups(self) -> list[dict]:
        """Fetch rule groups."""
        res = self._request("GET", "rule-groups")
        groups = []
        for item in res.get("data", []):
            attrs = item.get("attributes", {})
            groups.append({
                "id": item.get("id"),
                "title": attrs.get("title", ""),
                "active": attrs.get("active", True),
            })
        return groups

    # ── Specialized Transfer & Deposit Helpers ───────────────────
    def create_transfer(
        self,
        source_name: str,
        destination_name: str,
        amount: float,
        description: str,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Create a transfer between two asset accounts."""
        return self.create_transaction(
            description=description,
            amount=amount,
            type="transfer",
            source_name=source_name,
            destination_name=destination_name,
            date=date,
            notes=notes,
        )

    def create_deposit(
        self,
        destination_name: Optional[str] = None,
        amount: float = 0.0,
        description: str = "",
        source_name: Optional[str] = None,
        category_name: Optional[str] = None,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Create a deposit (income) into an asset account."""
        dest = destination_name
        if not dest:
            primary = self._resolve_asset_account()
            dest = primary["name"] if primary else "Kas"

        return self.create_transaction(
            description=description,
            amount=amount,
            type="deposit",
            source_name=source_name or "Gaji / Pendapatan",
            destination_name=dest,
            category_name=category_name or "Gaji & Pemasukan",
            date=date,
            notes=notes,
        )
