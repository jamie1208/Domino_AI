"""Synthetic tests for curated public-document research (no network)."""
import pytest

from app.schemas import EvidenceKind, Scenario
from app.skills.public_documents import CuratedPublicDocumentProvider, PublicDocument
from app.skills.researcher import ResearchSkill


def document(*, title="材料產業報告", url="https://publisher.example/report",
             content="介紹半導體材料產業的公開資訊", date="2026-01-01"):
    return PublicDocument(title=title, source_url=url, published_at=date,
                          content=content, kind=EvidenceKind.official)


def test_retrieval_keeps_source_and_does_not_assert_evidence_verification():
    provider = CuratedPublicDocumentProvider([document()])
    bundle = ResearchSkill(provider).run(Scenario(
        description="材料供應鏈事件", product="半導體材料"
    ))
    assert len(bundle.evidence) == 1
    item = bundle.evidence[0]
    assert item.id.startswith("document-sha256:")
    assert item.source_url == "https://publisher.example/report"
    assert item.kind == EvidenceKind.unverified
    assert item.supports_claim is False
    assert item.independently_verified is False
    assert bundle.candidate_relations == []


def test_deduplication_uses_content_addressed_id():
    provider = CuratedPublicDocumentProvider([document(), document()])
    bundle = provider.retrieve(Scenario(description="測試材料", product="材料"))
    assert len(bundle.evidence) == 1


def test_results_are_relevant_and_bounded():
    provider = CuratedPublicDocumentProvider([
        document(title="半導體供應", content="半導體材料"),
        document(title="汽車產業", url="https://other.example/auto", content="車用產業資訊"),
    ], max_results=1)
    bundle = provider.retrieve(Scenario(description="供應鏈假設", product="半導體"))
    assert len(bundle.evidence) == 1
    assert bundle.evidence[0].title == "半導體供應"


@pytest.mark.parametrize("url", [
    "http://publisher.example/report",
    "file:///etc/passwd",
    "https://user:pass@publisher.example/report",
    "https:///missing-host",
])
def test_unsupported_document_url_rejected(url):
    with pytest.raises(ValueError):
        CuratedPublicDocumentProvider([document(url=url)])


def test_invalid_timestamp_rejected():
    with pytest.raises(ValueError):
        CuratedPublicDocumentProvider([document(date="yesterday")])


def test_document_budget_enforced():
    with pytest.raises(ValueError):
        CuratedPublicDocumentProvider([document(content="x" * 200)], max_document_chars=100)


def test_empty_no_query_match_returns_no_evidence():
    provider = CuratedPublicDocumentProvider([document()])
    bundle = provider.retrieve(Scenario(description="測試災害", product="石油"))
    assert bundle.evidence == []
    assert bundle.candidate_relations == []


def test_stable_document_id_across_provider_instances():
    one = CuratedPublicDocumentProvider([document()]).retrieve(Scenario(description="測試情境"))
    two = CuratedPublicDocumentProvider([document()]).retrieve(Scenario(description="測試情境"))
    assert one.evidence[0].id == two.evidence[0].id
