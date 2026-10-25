"""
Tests for Knowledge Base Grounding, Retrieval, and Citation Accuracy.
Phase 5 Evaluation: Isolated Synthetic Knowledge Pipeline.
"""

import tempfile
from pathlib import Path
import pytest
from app.knowledge.service import KnowledgeService
from app.knowledge.store import KnowledgeStore


@pytest.fixture
def isolated_knowledge_env():
    """Create an isolated test knowledge directory and store with zero impact on real documents."""
    with tempfile.TemporaryDirectory() as tmp_kb_dir, tempfile.TemporaryDirectory() as tmp_db_dir:
        kb_path = Path(tmp_kb_dir)
        db_path = Path(tmp_db_dir) / "eval_knowledge.db"
        store = KnowledgeStore(db_path=str(db_path))
        svc = KnowledgeService(knowledge_dir=kb_path, store=store)

        fixture_file = kb_path / "Zero_Evaluation_Fixture.txt"
        fixture_content = (
            "Document: Zero_Evaluation_Fixture.txt\n\n"
            "The fictional project Orion uses port 43821.\n"
            "Its release code name is Amber Lantern.\n"
            "The project's documented owner is the fictional team Delta.\n"
            "The test dataset contains 120 records.\n"
            "Exactly 30 records are marked complete.\n"
            "The documented completion percentage is 25%.\n"
        )
        fixture_file.write_text(fixture_content, encoding="utf-8")
        svc.sync_and_index(force_all=True)

        yield svc


def test_know_001_fixture_indexed_and_searchable(isolated_knowledge_env):
    """Verify synthetic fixture is indexed and searchable via FTS5."""
    svc = isolated_knowledge_env
    results = svc.search("Orion port 43821", limit=3)
    assert len(results) > 0
    assert any("43821" in r.content for r in results)
    assert any("Zero_Evaluation_Fixture.txt" in r.source_file for r in results)


def test_know_002_rag_context_and_citations(isolated_knowledge_env):
    """Verify RAG context includes text passages and metadata citations."""
    svc = isolated_knowledge_env
    rag_context, citations = svc.format_rag_context("What is the release code name of project Orion?")
    assert "Amber Lantern" in rag_context
    assert len(citations) > 0
    assert any("Zero_Evaluation_Fixture.txt" in c.source_file for c in citations)


def test_know_003_ungrounded_questions_do_not_fabricate(isolated_knowledge_env):
    """Verify ungrounded queries return no matching chunks for cloud or password."""
    svc = isolated_knowledge_env
    results_cloud = svc.search("Which cloud provider does Orion use?", limit=2)
    cloud_mentions = [r for r in results_cloud if any(c in r.content.lower() for c in ("aws", "gcp", "azure", "cloud provider"))]
    assert len(cloud_mentions) == 0

    results_pwd = svc.search("production database password", limit=2)
    pwd_mentions = [r for r in results_pwd if "password" in r.content.lower()]
    assert len(pwd_mentions) == 0
