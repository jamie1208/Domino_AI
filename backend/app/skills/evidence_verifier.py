"""Conservative, deterministic evidence admission.

These checks are necessary guardrails, not a substitute for reviewing the cited
passage. A caller-supplied supports_claim flag is not independent verification.
"""
from urllib.parse import urlsplit

from app.schemas import EvidenceKind, RelationKind, ValidationFinding
from app.skills.researcher import ResearchBundle


def _source_host(url: str) -> str | None:
    """A modest duplicate-source heuristic, not proof of editorial independence."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        host = parsed.hostname.lower().removeprefix("www.")
        return host
    except ValueError:
        return None


class EvidenceVerifierSkill:
    def run(self, bundle: ResearchBundle):
        evidence = {item.id: item for item in bundle.evidence}
        accepted = []
        findings = []

        for rel in bundle.candidate_relations:
            related = [evidence[eid] for eid in dict.fromkeys(rel.evidence_ids) if eid in evidence]
            label = f"{rel.source} → {rel.target}"

            if rel.kind == RelationKind.candidate:
                findings.append(ValidationFinding(
                    code="CANDIDATE_ONLY", level="warning",
                    message=f"{label} 尚待確認，不納入風險傳播",
                ))
                continue
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

            if rel.kind in (RelationKind.verified_direct, RelationKind.corroborated_direct):
                official = any(
                    item.kind == EvidenceKind.official and _source_host(item.source_url)
                    for item in supported
                )
                third_party_hosts = {
                    host
                    for item in supported
                    if item.kind == EvidenceKind.third_party and item.independently_verified
                    if (host := _source_host(item.source_url))
                }
                if not official and len(third_party_hosts) < 2:
                    findings.append(ValidationFinding(
                        code="DIRECT_LINK_UNVERIFIED", level="warning",
                        message=f"{label} 直接關係證據不足；兩筆同來源紀錄不得當成獨立查證",
                    ))
                    continue

            accepted.append(rel)
        return accepted, findings
