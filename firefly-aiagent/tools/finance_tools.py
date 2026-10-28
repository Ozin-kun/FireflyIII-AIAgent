"""
Finance Tools for LangChain & LangGraph.

Wraps FireflyClient methods into LangChain BaseTool instances using
the @tool decorator, providing comprehensive capabilities for:
- Accounts (listing, details, creation)
- Transactions (listing, search, creation, deletion)
- Budgets (listing, limit & progress checking, creation)
- Piggy Banks (savings goals inquiry, creation, contributions)
- Bills (recurring bill obligations & reminders)
- Categories (inquiry and creation)
- Spending Reports
"""

import logging
from typing import Optional
from langchain_core.tools import tool, BaseTool
from api.firefly_client import FireflyClient

logger = logging.getLogger(__name__)


def create_finance_tools(client: FireflyClient) -> list[BaseTool]:
    """Create and return all LangChain finance tools bound to a FireflyClient."""

    # ── 1. Accounts Tools ─────────────────────────────────────────

    @tool
    def list_accounts(account_type: str = "all") -> str:
        """List all financial accounts and their current balances.
        
        Args:
            account_type: Filter by account type ('asset', 'expense', 'revenue', 'liability', or 'all').
        """
        try:
            accounts = client.get_accounts(account_type)
            if not accounts:
                return "No accounts found."
            lines = [f"Found {len(accounts)} account(s):"]
            for acc in accounts:
                status = "✓" if acc.get("active") else "✗"
                lines.append(
                    f"- [{acc['id']}] {acc['name']} ({acc['type']}): "
                    f"{acc.get('currency_symbol', '')}{acc['current_balance']} {acc['currency_code']} [{status}]"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving accounts: {e}"

    @tool
    def get_account_details(account_id: int) -> str:
        """Get detailed information about a specific account by its numeric ID.
        
        Args:
            account_id: Numeric ID of the account.
        """
        try:
            acc = client.get_account(account_id)
            return (
                f"Account Details:\n"
                f"  ID: {acc['id']}\n"
                f"  Name: {acc['name']}\n"
                f"  Type: {acc['type']}\n"
                f"  Balance: {acc.get('currency_symbol', '')}{acc['current_balance']} {acc['currency_code']}\n"
                f"  Active: {'Yes' if acc.get('active') else 'No'}\n"
                f"  Notes: {acc.get('notes', 'N/A')}"
            )
        except Exception as e:
            return f"Error retrieving account {account_id}: {e}"

    @tool
    def create_account(
        name: str,
        account_type: str = "asset",
        currency_code: str = "IDR",
        opening_balance: float = 0.0,
    ) -> str:
        """Create a new financial account (e.g. Bank Account, Cash Wallet, or Credit Card).
        
        Args:
            name: Name of the account (e.g. 'Bank Mandiri', 'GoPay', 'Dompet Tunai').
            account_type: Type of account ('asset' for bank/cash, 'liability' for loan/credit card).
            currency_code: Currency code, default 'IDR'.
            opening_balance: Initial balance amount (default 0.0).
        """
        try:
            acc = client.create_account(
                name=name,
                account_type=account_type,
                currency_code=currency_code,
                opening_balance=opening_balance,
            )
            return f"✓ Account '{acc.get('name')}' (ID: {acc.get('id')}) created with balance {acc.get('current_balance')} {currency_code}."
        except Exception as e:
            return f"Error creating account: {e}"

    # ── 2. Transactions Tools ─────────────────────────────────────

    @tool
    def list_transactions(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 25,
    ) -> str:
        """List recent financial transactions with optional date and type filters.
        
        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            type: Filter by type ('withdrawal', 'deposit', or 'transfer').
            limit: Maximum number of transactions to return (default: 25).
        """
        try:
            txs = client.get_transactions(start=start_date, end=end_date, type=type, limit=limit)
            if not txs:
                return "No transactions found matching criteria."
            lines = [f"Found {len(txs)} transaction(s):"]
            for tx in txs:
                cat = f" [{tx['category_name']}]" if tx.get("category_name") else ""
                lines.append(
                    f"- [{tx['id']}] {tx['date']} | {tx['description']} | "
                    f"{tx.get('currency_symbol', '')}{tx['amount']} {tx['currency_code']} ({tx['type']}){cat}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing transactions: {e}"

    @tool
    def search_transactions(query: str) -> str:
        """Search transactions by exact keyword in description, category, or notes.
        
        Args:
            query: Keyword to search for.
        """
        try:
            txs = client.search_transactions(query)
            if not txs:
                return f"No transactions found matching '{query}'."
            lines = [f"Found {len(txs)} matching transaction(s):"]
            for tx in txs:
                lines.append(
                    f"- [{tx['id']}] {tx['date']} | {tx['description']} | "
                    f"{tx.get('currency_symbol', '')}{tx['amount']} [{tx['type']}]"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching transactions: {e}"

    @tool
    def create_transaction(
        description: str,
        amount: float,
        type: str = "withdrawal",
        source_name: Optional[str] = None,
        destination_name: Optional[str] = None,
        category_name: Optional[str] = None,
        budget_name: Optional[str] = None,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Create a new financial transaction in Firefly III.
        
        Args:
            description: Description of the expense or income (e.g. 'Coffee at Starbucks', 'Makan Siang').
            amount: Positive numeric amount (e.g. 45000.0).
            type: Transaction type: 'withdrawal' (expense), 'deposit' (income), or 'transfer'.
            source_name: Optional name of source account. If omitted for withdrawals, automatically resolves to primary asset account.
            destination_name: Optional name of destination account. If omitted for withdrawals, defaults to description.
            category_name: Optional category name.
            budget_name: Optional budget name.
            date: Transaction date in YYYY-MM-DD format (defaults to today).
            notes: Optional additional notes.
        """
        try:
            tx = client.create_transaction(
                description=description,
                amount=amount,
                type=type,
                source_name=source_name,
                destination_name=destination_name,
                category_name=category_name,
                budget_name=budget_name,
                date=date,
                notes=notes,
            )
            return (
                f"✓ Transaction created successfully!\n"
                f"  ID: {tx.get('id')}\n"
                f"  Description: {tx.get('description')}\n"
                f"  Amount: {tx.get('currency_symbol', '')}{tx.get('amount')} {tx.get('currency_code', '')}\n"
                f"  Type: {tx.get('type')}\n"
                f"  Date: {tx.get('date')}\n"
                f"  Category: {tx.get('category_name', 'N/A')}"
            )
        except Exception as e:
            return f"Error creating transaction: {e}"

    @tool
    def delete_transaction(transaction_id: int) -> str:
        """Delete an erroneous or cancelled transaction by its numeric ID.
        
        Args:
            transaction_id: ID of the transaction to delete.
        """
        try:
            client.delete_transaction(transaction_id)
            return f"✓ Transaction [{transaction_id}] has been deleted."
        except Exception as e:
            return f"Error deleting transaction {transaction_id}: {e}"

    # ── 3. Categories Tools ───────────────────────────────────────

    @tool
    def list_categories() -> str:
        """List all available transaction categories in Firefly III."""
        try:
            cats = client.get_categories()
            if not cats:
                return "No categories found."
            lines = [f"Found {len(cats)} categories:"]
            for c in cats:
                notes = f" ({c['notes']})" if c.get("notes") else ""
                lines.append(f"- [{c['id']}] {c['name']}{notes}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing categories: {e}"

    @tool
    def create_category(name: str, notes: Optional[str] = "") -> str:
        """Create a new category for grouping expenses or incomes.
        
        Args:
            name: Category name (e.g. 'Pendidikan', 'Investasi', 'Kesehatan').
            notes: Optional notes or description.
        """
        try:
            cat = client.create_category(name=name, notes=notes or "")
            return f"✓ Category '{cat.get('name')}' (ID: {cat.get('id')}) created."
        except Exception as e:
            return f"Error creating category: {e}"

    # ── 4. Budgets & Limits Tools ─────────────────────────────────

    @tool
    def list_budgets() -> str:
        """List all financial budgets with their spending limits and periods."""
        try:
            budgets = client.get_budgets()
            if not budgets:
                return "No budgets found."
            lines = [f"Found {len(budgets)} budget(s):"]
            for b in budgets:
                status = "Active" if b.get("active") else "Inactive"
                lines.append(
                    f"- [{b['id']}] {b['name']} ({status}) "
                    f"Limit: Rp{b.get('auto_budget_amount', '0')}/{b.get('auto_budget_period', 'monthly')} "
                    f"| Spent so far: Rp{b.get('spent', '0')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing budgets: {e}"

    @tool
    def check_budget_spending_and_limit(budget_name_or_id: str) -> str:
        """Check the detailed allocated limit, spent amount, and remaining balance for a specific budget.
        
        Args:
            budget_name_or_id: The name of the budget (e.g. 'Jajan Bulanan') or its numeric ID.
        """
        try:
            budgets = client.get_budgets()
            target_budget = None
            for b in budgets:
                if str(b["id"]) == budget_name_or_id or b["name"].lower() == budget_name_or_id.lower():
                    target_budget = b
                    break

            if not target_budget:
                return f"Budget '{budget_name_or_id}' not found. Available budgets: {', '.join(b['name'] for b in budgets)}"

            b_id = int(target_budget["id"])
            limits = client.get_budget_limits(b_id)

            if limits:
                lim = limits[0]
                allocated = float(lim.get("amount", 0))
                spent = float(lim.get("spent", 0))
                remaining = max(0.0, allocated - spent)
                pct = (spent / allocated * 100) if allocated > 0 else 0
                return (
                    f"Budget Report for '{target_budget['name']}':\n"
                    f"  Period: {lim.get('start', 'N/A')} to {lim.get('end', 'N/A')}\n"
                    f"  Allocated Limit: Rp{allocated:,.2f}\n"
                    f"  Total Spent: Rp{spent:,.2f} ({pct:.1f}%)\n"
                    f"  Remaining Balance: Rp{remaining:,.2f}\n"
                    f"  Status: {'⚠️ OVER BUDGET!' if spent > allocated else '✓ Within budget'}"
                )
            else:
                # Fallback to general budget attributes
                allocated = float(target_budget.get("auto_budget_amount", 0))
                spent = float(target_budget.get("spent", 0))
                remaining = max(0.0, allocated - spent)
                return (
                    f"Budget Report for '{target_budget['name']}':\n"
                    f"  Allocated Limit: Rp{allocated:,.2f} ({target_budget.get('auto_budget_period', 'monthly')})\n"
                    f"  Total Spent: Rp{spent:,.2f}\n"
                    f"  Remaining Balance: Rp{remaining:,.2f}"
                )
        except Exception as e:
            return f"Error checking budget limits: {e}"

    @tool
    def create_budget(
        name: str,
        limit_amount: float,
        period: str = "monthly",
    ) -> str:
        """Create a new financial budget with an auto-budget limit.
        
        Args:
            name: Name of the budget (e.g. 'Jajan Bulanan', 'Bensin', 'Olahraga').
            limit_amount: Maximum spending limit amount (e.g. 1500000.0).
            period: Budget period ('daily', 'weekly', 'monthly', 'yearly').
        """
        try:
            b = client.create_budget(name=name, auto_budget_amount=limit_amount, auto_budget_period=period)
            return f"✓ Budget '{b.get('name')}' created with limit Rp{limit_amount:,.2f} per {period}."
        except Exception as e:
            return f"Error creating budget: {e}"

    # ── 5. Piggy Banks (Savings Goals / Celengan) Tools ───────────

    @tool
    def list_piggy_banks() -> str:
        """List all piggy banks (savings goals) showing target amounts, saved amounts, and progress percentages."""
        try:
            piggies = client.get_piggy_banks()
            if not piggies:
                return "No piggy banks (savings goals) found."
            lines = [f"Found {len(piggies)} savings goal(s):"]
            for p in piggies:
                lines.append(
                    f"- [{p['id']}] {p['name']}: Saved Rp{p.get('current_amount', '0')} of Rp{p.get('target_amount', '0')} "
                    f"({p.get('percentage', 0)}%) | Left: Rp{p.get('left_to_save', '0')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing piggy banks: {e}"

    @tool
    def create_piggy_bank(
        name: str,
        target_amount: float,
        target_date: Optional[str] = None,
        account_name: Optional[str] = None,
    ) -> str:
        """Create a new piggy bank savings goal in Firefly III.
        
        Args:
            name: Goal title (e.g. 'Beli Laptop Baru', 'Dana Darurat 2026', 'Liburan Bali').
            target_amount: Total money needed (e.g. 15000000.0).
            target_date: Optional completion target date in YYYY-MM-DD format.
            account_name: Optional asset account where savings are allocated (e.g. 'BCA', 'Dompet Tunai'). If omitted, primary asset account is automatically used.
        """
        try:
            p = client.create_piggy_bank(
                name=name,
                target_amount=target_amount,
                account_name=account_name,
                target_date=target_date,
            )
            return f"✓ Target tabungan (piggy bank) '{p.get('name')}' berhasil dibuat dengan target Rp{target_amount:,.2f}."
        except Exception as e:
            return f"Error creating piggy bank: {e}"

    @tool
    def add_to_piggy_bank(
        piggy_bank_id: int,
        amount: float,
        source_account_name: Optional[str] = None,
    ) -> str:
        """Deposit or save money into a piggy bank (savings goal).
        
        Args:
            piggy_bank_id: The ID of the piggy bank.
            amount: Amount of money to add (e.g. 500000.0).
            source_account_name: Optional source account where money comes from (e.g. 'Rekening Utama BCA').
        """
        try:
            # First, check piggy bank
            piggies = client.get_piggy_banks()
            target_pb = next((p for p in piggies if str(p["id"]) == str(piggy_bank_id)), None)
            if not target_pb:
                return f"Piggy bank ID {piggy_bank_id} not found."

            current = float(target_pb.get("current_amount", 0))
            new_amount = current + amount
            res = client.update_piggy_bank_amount(piggy_bank_id, new_amount)

            # If source account provided, record a withdrawal/transfer transaction
            if source_account_name:
                client.create_transaction(
                    description=f"Tabungan Celengan: {target_pb['name']}",
                    amount=amount,
                    type="withdrawal",
                    source_name=source_account_name,
                    notes=f"Alokasi ke piggy bank {target_pb['name']}",
                    piggy_bank_id=piggy_bank_id,
                )

            return (
                f"✓ Successfully added Rp{amount:,.2f} to '{target_pb['name']}'!\n"
                f"  New Saved Amount: Rp{res.get('current_amount')}\n"
                f"  Progress: {res.get('percentage')}%\n"
                f"  Remaining: Rp{res.get('left_to_save')}"
            )
        except Exception as e:
            return f"Error adding to piggy bank: {e}"

    # ── 6. Bills Tools ────────────────────────────────────────────

    @tool
    def list_bills() -> str:
        """List all registered recurring bills (e.g. WiFi, Electricity, Subscriptions) and their payment schedule."""
        try:
            bills = client.get_bills()
            if not bills:
                return "No recurring bills found."
            lines = [f"Found {len(bills)} bill(s):"]
            for b in bills:
                status = "Active" if b.get("active") else "Inactive"
                lines.append(
                    f"- [{b['id']}] {b['name']} ({status}): Rp{b.get('amount_min', '0')} - Rp{b.get('amount_max', '0')} "
                    f"({b.get('repeat_freq', 'monthly')}) | Next: {b.get('next_expected_match', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing bills: {e}"

    @tool
    def create_bill(
        name: str,
        amount_min: float,
        amount_max: Optional[float] = None,
        due_date: Optional[str] = None,
        repeat_frequency: str = "monthly",
    ) -> str:
        """Create a new recurring bill reminder (e.g. Indihome, Spotify, Kos/Sewa).
        
        Args:
            name: Bill title (e.g. 'WiFi Indihome Rumah', 'Listrik PLN').
            amount_min: Minimum expected amount (e.g. 350000.0).
            amount_max: Maximum expected amount. If omitted, defaults to amount_min.
            due_date: First expected due date (YYYY-MM-DD).
            repeat_frequency: Frequency ('weekly', 'monthly', 'quarterly', 'yearly').
        """
        try:
            actual_max = amount_max if amount_max is not None else amount_min
            b = client.create_bill(
                name=name,
                amount_min=amount_min,
                amount_max=actual_max,
                date=due_date,
                repeat_freq=repeat_frequency,
            )
            return f"✓ Bill '{b.get('name')}' created (Rp{amount_min:,.2f} - Rp{actual_max:,.2f}, {repeat_frequency})."
        except Exception as e:
            return f"Error creating bill: {e}"

    # ── 7. Spending Reports & Summary Tools ────────────────────────

    @tool
    def get_spending_report(start_date: str, end_date: str) -> str:
        """Get an aggregate financial summary report (total spent, earned, net) for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
        """
        try:
            summary = client.get_summary(start_date, end_date)
            if not summary:
                return f"No financial summary data available for {start_date} to {end_date}."
            lines = [f"Financial Summary ({start_date} to {end_date}):"]
            for key, val in summary.items():
                if isinstance(val, dict):
                    label = val.get("label", key)
                    amount = val.get("value_parsed", val.get("monetary_value", "N/A"))
                    lines.append(f"- {label}: {amount}")
                else:
                    lines.append(f"- {key}: {val}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving summary: {e}"

    # ── 8. User Profile Tool ──────────────────────────────────────
    @tool
    def get_user_profile() -> str:
        """Get the profile details of the currently authenticated / logged-in Firefly III user (email, role, ID)."""
        try:
            u = client.get_current_user()
            return (
                f"Currently Logged-in User Information:\n"
                f"  Email: {u.get('email', 'N/A')}\n"
                f"  Role: {u.get('role', 'N/A')}\n"
                f"  User ID: {u.get('id', 'N/A')}"
            )
        except Exception as e:
            return f"Error retrieving user profile: {e}"

    # ── 9. Transfers & Deposits Tools ────────────────────────────
    @tool
    def create_transfer(
        source_account: str,
        destination_account: str,
        amount: float,
        description: str,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Transfer money between two of your own asset accounts (e.g. from Bank BCA to Dompet Tunai or GoPay).

        Args:
            source_account: The account money is taken from (e.g. 'Rekening Utama BCA').
            destination_account: The account receiving the money (e.g. 'Dompet Tunai').
            amount: Positive numeric amount to transfer.
            description: Description/purpose of transfer (e.g. 'Tarik tunai ATM', 'Top up GoPay').
            date: Optional date in YYYY-MM-DD format (defaults to today).
            notes: Optional additional notes.
        """
        try:
            tx = client.create_transfer(
                source_name=source_account,
                destination_name=destination_account,
                amount=amount,
                description=description,
                date=date,
                notes=notes,
            )
            return (
                f"✓ Transfer of Rp{amount:,.2f} completed successfully!\n"
                f"  From: {source_account} -> To: {destination_account}\n"
                f"  Description: {tx.get('description', description)}\n"
                f"  ID: {tx.get('id')}"
            )
        except Exception as e:
            return f"Error executing transfer: {e}"

    @tool
    def create_deposit(
        amount: float,
        description: str,
        destination_account: Optional[str] = None,
        source_name: Optional[str] = None,
        category_name: Optional[str] = None,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Record income or deposit into an asset account (e.g. salary, freelance, gift, cashback).

        Args:
            amount: Positive numeric amount of income.
            description: Description of income (e.g. 'Gaji Bulanan Oktober', 'Hasil Proyek Web').
            destination_account: Optional asset account receiving the income (e.g. 'Rekening BCA'). If omitted, primary asset account is automatically used.
            source_name: Name of revenue source (e.g. 'PT Maju Bersama', 'Klien Freelance').
            category_name: Optional category (e.g. 'Gaji & Pemasukan').
            date: Optional date in YYYY-MM-DD format.
            notes: Optional notes.
        """
        try:
            tx = client.create_deposit(
                destination_name=destination_account,
                amount=amount,
                description=description,
                source_name=source_name,
                category_name=category_name,
                date=date,
                notes=notes,
            )
            target_acc = tx.get("destination_name") or destination_account or "Kas / Rekening Utama"
            return (
                f"✓ Deposit of Rp{amount:,.2f} recorded successfully!\n"
                f"  Account: {target_acc}\n"
                f"  Description: {tx.get('description')}\n"
                f"  Source: {tx.get('source_name', 'N/A')}\n"
                f"  ID: {tx.get('id')}"
            )
        except Exception as e:
            return f"Error recording deposit: {e}"

    # ── 10. Tags Tools ───────────────────────────────────────────
    @tool
    def list_tags() -> str:
        """List all transaction tags in Firefly III (used for labeling specific events, e.g. #liburan, #reimburse)."""
        try:
            tags = client.get_tags()
            if not tags:
                return "No tags found in Firefly III."
            lines = [f"Found {len(tags)} tag(s):"]
            for t in tags:
                desc = f" ({t['description']})" if t.get("description") else ""
                lines.append(f"- #{t['tag']}{desc}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving tags: {e}"

    @tool
    def create_tag(tag: str, description: Optional[str] = "") -> str:
        """Create a new tag in Firefly III.

        Args:
            tag: Tag name without hash symbol (e.g. 'liburan-bali', 'reimburse-kantor').
            description: Optional explanation of the tag.
        """
        try:
            t = client.create_tag(tag=tag, description=description or "")
            return f"✓ Tag '#{t.get('tag')}' created successfully."
        except Exception as e:
            return f"Error creating tag: {e}"

    # ── 11. Recurrences & Rules Tools ────────────────────────────
    @tool
    def list_recurrences() -> str:
        """List all automatic recurring transaction schedules (e.g. auto monthly salary, recurring rent)."""
        try:
            recs = client.get_recurrences()
            if not recs:
                return "No recurring transaction schedules found."
            lines = [f"Found {len(recs)} recurrence schedule(s):"]
            for r in recs:
                status = "Active" if r.get("active") else "Inactive"
                lines.append(
                    f"- [{r['id']}] {r['title']} ({r.get('type')}, {r.get('repeat_freq')}) [{status}] | Next: {r.get('latest_date', 'N/A')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving recurrences: {e}"

    @tool
    def list_rules() -> str:
        """List all automated transaction rules and rule groups in Firefly III."""
        try:
            rules = client.get_rules()
            if not rules:
                return "No automation rules defined in Firefly III."
            lines = [f"Found {len(rules)} automation rule(s):"]
            for r in rules:
                status = "Active" if r.get("active") else "Inactive"
                lines.append(f"- [{r['id']}] {r['title']} [{status}] (Trigger: {r.get('trigger', 'transaction')})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving rules: {e}"

    return [
        # User Profile
        get_user_profile,
        # Accounts
        list_accounts,
        get_account_details,
        create_account,
        # Transactions & Transfers
        list_transactions,
        search_transactions,
        create_transaction,
        create_transfer,
        create_deposit,
        delete_transaction,
        # Categories
        list_categories,
        create_category,
        # Tags
        list_tags,
        create_tag,
        # Budgets
        list_budgets,
        check_budget_spending_and_limit,
        create_budget,
        # Piggy Banks
        list_piggy_banks,
        create_piggy_bank,
        add_to_piggy_bank,
        # Bills & Recurrences
        list_bills,
        create_bill,
        list_recurrences,
        # Rules & Automations
        list_rules,
        # Reports
        get_spending_report,
    ]
