from pathlib import Path
import sqlite3
import pytest

from app.services.memory.persistent_memory import PersistentMemoryStore
from app.services.memory.vector_store import PersistentRAGStore


# -------------------------------------------------------------------------
# 1. RAG Persistence & Restart Recovery
# -------------------------------------------------------------------------
def test_rag_persistence_and_restart_recovery(tmp_path: Path):
    db_file = tmp_path / "rag_restart_test.db"
    
    # Session 1: Create and index document
    store_1 = PersistentRAGStore(db_path=db_file)
    doc_text = (
        "Quantum error correction protects quantum information from errors due to decoherence and other quantum noise. "
        "Surface codes are a family of quantum error-correcting codes defined on a 2D lattice of physical qubits. "
        "Fault-tolerant quantum computation enables reliable calculation despite imperfect components."
    )
    chunks_created = store_1.chunk_and_index(
        file_id="qec_doc_1",
        filename="Quantum_Error_Correction.pdf",
        full_text=doc_text,
        session_id="session_alpha",
    )
    assert chunks_created >= 1

    # Simulate full process restart by instantiating a completely new store instance on same DB file
    store_2 = PersistentRAGStore(db_path=db_file)
    stats = store_2.get_document_stats()
    assert stats["total_documents"] == 1
    assert stats["total_chunks"] == chunks_created

    # Verify search query succeeds on revived instance
    results = store_2.search("surface codes 2D lattice qubits", top_k=2, session_id="session_alpha")
    assert len(results) > 0
    assert "surface codes" in results[0]["text"].lower()
    assert results[0]["filename"] == "Quantum_Error_Correction.pdf"
    assert results[0]["chunk_index"] == 0


# -------------------------------------------------------------------------
# 2. Session Scoping & Cross-Session Isolation
# -------------------------------------------------------------------------
def test_rag_session_scoping_and_cross_session_isolation(tmp_path: Path):
    db_file = tmp_path / "isolation_test.db"
    store = PersistentRAGStore(db_path=db_file)

    # Document A uploaded in session_alice
    alice_text = "Confidential Q3 financial results: Revenue was $45M with an EBITDA margin of 24%."
    store.chunk_and_index("doc_alice", "Alice_Finances.pdf", alice_text, session_id="session_alice")

    # Document B uploaded in session_bob
    bob_text = "Public server configuration: Nginx is running on port 8080 with SSL certificate."
    store.chunk_and_index("doc_bob", "Bob_Server.txt", bob_text, session_id="session_bob")

    # Alice searches for "revenue EBITDA" -> Gets Alice_Finances
    alice_matches = store.search("revenue EBITDA", top_k=3, session_id="session_alice")
    assert len(alice_matches) == 1
    assert alice_matches[0]["file_id"] == "doc_alice"

    # Bob searches for "revenue EBITDA" -> MUST NOT retrieve Alice's confidential document
    bob_matches = store.search("revenue EBITDA", top_k=3, session_id="session_bob")
    assert len(bob_matches) == 0

    # Bob searches for "nginx" -> Gets Bob_Server
    bob_server_matches = store.search("nginx port", top_k=3, session_id="session_bob")
    assert len(bob_server_matches) == 1
    assert bob_server_matches[0]["file_id"] == "doc_bob"


# -------------------------------------------------------------------------
# 3. Document Deletion & Cascade Purge
# -------------------------------------------------------------------------
def test_rag_document_deletion(tmp_path: Path):
    db_file = tmp_path / "delete_test.db"
    store = PersistentRAGStore(db_path=db_file)

    store.chunk_and_index("doc_temp", "Temporary.pdf", "Temporary text to be purged", session_id="sess_1")
    assert store.get_document_stats()["total_documents"] == 1

    # Delete document
    deleted = store.delete_document("doc_temp")
    assert deleted is True
    assert store.get_document_stats()["total_documents"] == 0
    assert store.get_document_stats()["total_chunks"] == 0

    # Search should now yield empty results
    assert len(store.search("temporary", session_id="sess_1")) == 0


# -------------------------------------------------------------------------
# 4. Memory Lifecycle, Updating, and Conflict Detection
# -------------------------------------------------------------------------
def test_memory_lifecycle_and_conflict_detection(tmp_path: Path):
    db_file = tmp_path / "memory_lifecycle.db"
    store = PersistentMemoryStore(db_path=str(db_file))

    # 1. Create initial memory
    item, is_conflict = store.set_memory("theme_preference", "dark", category="ui")
    assert item.value == "dark"
    assert is_conflict is False
    assert store.get_memory("theme_preference") == "dark"

    # 2. Update memory with same value (idempotent, no conflict)
    item2, is_conflict2 = store.set_memory("theme_preference", "dark", category="ui")
    assert is_conflict2 is False

    # 3. Update memory with conflicting value
    item3, is_conflict3 = store.set_memory("theme_preference", "light", category="ui")
    assert item3.value == "light"
    assert is_conflict3 is True
    assert store.get_memory("theme_preference") == "light"

    # 4. Delete memory
    assert store.delete_memory("theme_preference") is True
    assert store.get_memory("theme_preference") is None


# -------------------------------------------------------------------------
# 5. Large, Empty, and Corrupted Document Handling
# -------------------------------------------------------------------------
def test_rag_boundary_document_handling(tmp_path: Path):
    db_file = tmp_path / "boundary_test.db"
    store = PersistentRAGStore(db_path=db_file)

    # Empty text
    empty_chunks = store.chunk_and_index("empty_doc", "Empty.txt", "")
    assert empty_chunks == 0

    # Large text (10,000 words)
    large_text = " ".join([f"paragraph_{i} with key factual term alpha beta gamma." for i in range(2000)])
    large_chunks = store.chunk_and_index("large_doc", "Large.txt", large_text, chunk_size=300, overlap=50)
    assert large_chunks > 1

    # Search in large text
    matches = store.search("alpha beta gamma", top_k=3)
    assert len(matches) <= 3
    assert matches[0]["file_id"] == "large_doc"
