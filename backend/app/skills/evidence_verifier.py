"""EvidenceVerifierSkill: conservative relationship admission.

This is a preliminary metadata/claim gate. It does not independently establish
that an excerpt truly supports a claim or that publishers are editorially independent.
"""
from urllib.parse import urlsplit

from app.schemas import EvidenceKind, RelationKind, ValidationFinding
from app.skills.researcher import ResearchBundle


def _host(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        return parsed.hostname.lower().removeprefix("www.")
    except ValueError:
        return None


def _independent_pair(items) -> bool:
    """Require a pair with distinct host, publisher AND original source."""
    for i, first in enumerate(items):
        for second in items[i + 1:]:
            if (
                first.id != second.id
                and _host(first.source_url) != _host(second.source_url)
                and first.provenance.publisher_key != second.provenance.publisher_key
                and first.provenance.original_source_key != second.provenance.original_source_key
            ):
                return True
    return False


class EvidenceVerifierSkill:
    def run(self, bundle: ResearchBundle):
        evidence = {item.id: item for item in bundle.evidence}
        accepted = []
        findings = []

        for relation in bundle.candidate_relations:
            label = f"{relation.source} → {relation.target}"
            if relation.kind == RelationKind.candidate:
                findings.append(ValidationFinding(
                    code="CANDIDATE_ONLY", level="warning",
                    message=f"{label} 尚待確認，不納入風險傳播",
                ))
                continue

            related = [evidence[eid] for eid in dict.fromkeys(relation.evidence_ids) if eid in evidence]
            if not related:
                findings.append(ValidationFinding(
                    code="MISSING_EVIDENCE", level="error",
                    message=f"{label} 缺乏可追溯證據",
                ))
                continue

            supported = [item for item in related if item.supports_claim]
            if not supported:
                findings.append(ValidationFinding(
                    code="UNSUPPORTED_CLAIM", level="error",
                    message=f"{label} 來源沒有支持該主張",
                ))
                continue

            if relation.kind in (RelationKind.verified_direct, RelationKind.corroborated_direct):
                official = any(
                    item.kind == EvidenceKind.official and _host(item.source_url)
                    for item in supported
                )
                eligible = [
                    item for item in supported
                    if item.kind == EvidenceKind.third_party
                    and item.independently_verified
                    and _host(item.source_url)
                    and item.provenance.publisher_key
                    and item.provenance.original_source_key
                    and item.provenance.independence_basis in (
                        "publisher_and_original_source", "manual_review"
                    )
                ]
                if not official and not _independent_pair(eligible):
                    findings.append(ValidationFinding(
                        code="DIRECT_LINK_UNVERIFIED", level="warning",
                        message=f"{label} 直接關係缺少官方來源或具完整獨立性資料的兩份第三方證據",
                    ))
                    continue

            accepted.append(relation)
        return accepted, findings
