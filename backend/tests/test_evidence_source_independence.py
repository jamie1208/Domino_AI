"""Regression tests for duplicate-source admission in F58."""
from app.schemas import Evidence, EvidenceKind, Relation, RelationKind
from app.skills.researcher import ResearchBundle
from app.skills.evidence_verifier import EvidenceVerifierSkill


def _evidence(identifier: str, url: str, *, kind=EvidenceKind.third_party, verified=True):
    return Evidence(
        id=identifier, title="Synthetic example", source_url=url,
        published_at="2026-01-01", kind=kind,
        supports_claim=True, independently_verified=verified,
    )


def _relation(ids):
    return Relation(
        source="Synthetic A", target="Synthetic B",
        kind=RelationKind.corroborated_direct,
        weight=0.5, evidence_ids=ids,
    )


def test_two_articles_from_same_host_are_not_independent():
    bundle = ResearchBundle(
        evidence=[
            _evidence("e1", "https://www.example.org/a"),
            _evidence("e2", "https://example.org/b"),
        ],
        candidate_relations=[_relation(["e1", "e2"])],
    )
    accepted, findings = EvidenceVerifierSkill().run(bundle)
    assert accepted == []
    assert any(item.code == "DIRECT_LINK_UNVERIFIED" for item in findings)


def test_duplicate_evidence_ids_do_not_count_twice():
    bundle = ResearchBundle(
        evidence=[_evidence("e1", "https://example.org/a")],
        candidate_relations=[_relation(["e1", "e1"])],
    )
    accepted, _ = EvidenceVerifierSkill().run(bundle)
    assert accepted == []


def test_two_distinct_hosts_can_pass_preliminary_corroboration():
    bundle = ResearchBundle(
        evidence=[
            _evidence("e1", "https://source-one.example/report"),
            _evidence("e2", "https://source-two.example/report"),
        ],
        candidate_relations=[_relation(["e1", "e2"])],
    )
    accepted, findings = EvidenceVerifierSkill().run(bundle)
    assert len(accepted) == 1
    assert not any(item.level == "error" for item in findings)


def test_single_official_source_can_support_direct_relationship():
    bundle = ResearchBundle(
        evidence=[_evidence("official1", "https://issuer.example/announcement", kind=EvidenceKind.official, verified=False)],
        candidate_relations=[_relation(["official1"])],
    )
    accepted, _ = EvidenceVerifierSkill().run(bundle)
    assert len(accepted) == 1


def test_candidate_is_always_excluded_even_if_supported():
    bundle = ResearchBundle(
        evidence=[_evidence("official1", "https://issuer.example/announcement", kind=EvidenceKind.official)],
        candidate_relations=[Relation(
            source="Synthetic A", target="Synthetic B", kind=RelationKind.candidate,
            weight=0.5, evidence_ids=["official1"],
        )],
    )
    accepted, findings = EvidenceVerifierSkill().run(bundle)
    assert accepted == []
    assert any(item.code == "CANDIDATE_ONLY" for item in findings)
