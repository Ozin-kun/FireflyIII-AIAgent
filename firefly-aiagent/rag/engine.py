"""
Dynamic RAG Engine for Firefly III Transactions using ChromaDB.

Implements incremental delta indexing to handle high-frequency transaction updates,
and exposes a LangChain retriever tool for semantic queries.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Any
from langchain_core.documents import Document
from langchain_core.tools import BaseTool, create_retriever_tool
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from api.firefly_client import FireflyClient

logger = logging.getLogger(__name__)


class DynamicRAGEngine:
    """Dynamic RAG engine with delta synchronization for Firefly III."""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "firefly_transactions",
        gemini_api_key: str = "",
        firefly_client: Optional[FireflyClient] = None,
    ) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.firefly_client = firefly_client
        self.last_sync: Optional[datetime] = None
        self._indexed_ids: set[str] = set()

        # Google Generative AI Embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=gemini_api_key,
        )

        # ChromaDB Vector Store
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )

        # Pre-load indexed document IDs to prevent duplicate embedding
        self._load_existing_ids()

    def _load_existing_ids(self) -> None:
        """Cache existing document IDs from the vector store."""
        try:
            col = self.vectorstore._collection
            existing = col.get()
            if existing and "ids" in existing:
                self._indexed_ids = set(existing["ids"])
                logger.info("Loaded %d existing transaction IDs into RAG cache.", len(self._indexed_ids))
        except Exception as e:
            logger.warning("Could not pre-load indexed IDs from vector store: %s", e)
            self._indexed_ids = set()

    def _transaction_to_doc(self, tx: dict[str, Any]) -> Document:
        """Convert a flattened transaction into a semantic Document."""
        tx_id = str(tx.get("id", ""))
        desc = tx.get("description", "Untitled")
        amount = tx.get("amount", "0")
        currency = tx.get("currency_code", "IDR")
        tx_type = tx.get("type", "transaction")
        tx_date = tx.get("date", "")
        category = tx.get("category_name") or "Uncategorized"
        src = tx.get("source_name") or "Unknown"
        dst = tx.get("destination_name") or "Unknown"
        notes = tx.get("notes") or ""

        page_content = (
            f"Transaction Date: {tx_date}\n"
            f"Description: {desc}\n"
            f"Amount: {amount} {currency} ({tx_type})\n"
            f"Category: {category}\n"
            f"Flow: From {src} to {dst}\n"
            f"Notes: {notes}"
        )

        metadata = {
            "id": tx_id,
            "date": tx_date,
            "category": category,
            "type": tx_type,
            "amount": str(amount),
        }

        return Document(page_content=page_content, metadata=metadata, id=tx_id)

    def sync_with_firefly(self, days_back: int = 90, limit: int = 250) -> int:
        """Dynamically fetch transactions from Firefly III and index only new ones (delta sync).

        Returns:
            Number of newly indexed transactions.
        """
        if not self.firefly_client:
            logger.warning("No FireflyClient provided for RAG sync.")
            return 0

        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        try:
            txs = self.firefly_client.get_transactions(start=start_date, limit=limit)
        except Exception as e:
            logger.error("Failed to fetch transactions for RAG sync: %s", e)
            return 0

        new_docs: list[Document] = []
        for tx in txs:
            tx_id = str(tx.get("id", ""))
            if tx_id and tx_id not in self._indexed_ids:
                doc = self._transaction_to_doc(tx)
                new_docs.append(doc)
                self._indexed_ids.add(tx_id)

        if new_docs:
            logger.info("Indexing %d new transactions into ChromaDB Dynamic RAG...", len(new_docs))
            self.vectorstore.add_documents(new_docs, ids=[d.id for d in new_docs])

        self.last_sync = datetime.now()
        return len(new_docs)

    def get_retriever_tool(self, top_k: int = 5) -> BaseTool:
        """Create a LangChain retriever tool that the agent can invoke semantically."""
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": top_k})
        return create_retriever_tool(
            retriever=retriever,
            name="semantic_transaction_search",
            description=(
                "Search past financial transactions and spending history using natural language semantic queries. "
                "Use this tool when the user asks questions about habits, past purchases, or historical patterns "
                "(e.g., 'kapan terakhir beli kopi?', 'berapa pengeluaran makan di luar bulan lalu?')."
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about the RAG vector store."""
        return {
            "total_indexed": len(self._indexed_ids),
            "collection_name": self.collection_name,
            "last_sync": self.last_sync.isoformat() if self.last_sync else "Never",
            "persist_directory": self.persist_directory,
        }
