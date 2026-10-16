"""Regression tests for source independence and Phase 4 provenance semantics."""
from app.schemas import Evidence, EvidenceKind, EvidenceProvenance, Relation, RelationKind
from app.skills.researcher import ResearchBundle
from app.skills.evidence_verifier import EvidenceVerifierSkill


def _evidence(identifier, url, *, kind=EvidenceKind.third_party, verified=True,
              publisher=None, original=None, basis="publisher_and_original_source"):
    return Evidence(
        id=identifier, title="Synthetic example", source_url=url,
        published_at="2026-01-01", kind=kind, supports_claim=True,
        independently_verified=verified,
        provenance=EvidenceProvenance(
            publisher_key=publisher,
            original_source_key=original,
            independence_basis=basis if publisher and original else None,
        ),
    )


def _relation(ids, kind=RelationKind.corroborated_direct):
    return Relation(source="Synthetic A", target="Synthetic B", kind=kind,
                    weight=0.5, evidence_ids=ids)


def _check(items, ids, kind=RelationKind.corroborated_direct):
    return EvidenceVerifierSkill().run(ResearchBundle(items, [_relation(ids, kind)]))


def test_same_host_is_not_independent_even_with_distinct_publishers():
    accepted, findings = _check([
        _evidence("e1", "https://www.example.org/a", publisher="publisher-one", original="origin-one"),
        _evidence("e2", "https://example.org/b", publisher="publisher-two", original="origin-two"),
    ], ["e1", "e2"])
    assert accepted == []
    assert any(f.code == "DIRECT_LINK_UNVERIFIED" for f in findings)


def test_duplicate_evidence_ids_not_counted_twice():
    accepted, _ = _check([
        _evidence("e1", "https://one.example/a", publisher="publisher-one", original="origin-one")
    ], ["e1", "e1"])
    assert accepted == []


def test_two_independent_sources_with_provenance_pass_preliminary_gate():
    accepted, findings = _check([
        _evidence("e1", "https://source-one.example/report", publisher="publisher-one", original="origin-one"),
        _evidence("e2", "https://source-two.example/report", publisher="publisher-two", original="origin-two"),
    ], ["e1", "e2"])
    assert len(accepted) == 1
    assert not any(f.level == "error" for f in findings)


def test_distinct_hosts_without_provenance_cannot_verify_direct_edge():
    accepted, findings = _check([
        _evidence("e1", "https://source-one.example/report"),
        _evidence("e2", "https://source-two.example/report"),
    ], ["e1", "e2"])
    assert accepted == []
    assert any(f.code == "DIRECT_LINK_UNVERIFIED" for f in findings)


def test_same_original_source_does_not_count_as_two():
    accepted, _ = _check([
        _evidence("e1", "https://source-one.example/report", publisher="publisher-one", original="same-original"),
        _evidence("e2", "https://source-two.example/report", publisher="publisher-two", original="same-original"),
    ], ["e1", "e2"])
    assert accepted == []


def test_single_official_source_can_support_direct_relationship():
    accepted, _ = _check([
        _evidence("official1", "https://issuer.example/announcement",
                  kind=EvidenceKind.official, verified=False),
    ], ["official1"])
    assert len(accepted) == 1


def test_candidate_is_excluded_even_with_official_support():
    accepted, findings = _check([
        _evidence("official1", "https://issuer.example/announcement", kind=EvidenceKind.official),
    ], ["official1"], RelationKind.candidate)
    assert accepted == []
    assert any(f.code == "CANDIDATE_ONLY" for f in findings)
