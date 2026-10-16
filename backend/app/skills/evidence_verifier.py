"""EvidenceVerifierSkill: deterministic eligibility rules. AI assertions never suffice."""
from app.schemas import EvidenceKind, RelationKind, ValidationFinding
from app.skills.researcher import ResearchBundle

class EvidenceVerifierSkill:
    def run(self, bundle: ResearchBundle):
        evidence = {e.id:e for e in bundle.evidence}
        accepted = []
        findings = []
        for rel in bundle.candidate_relations:
            related = [evidence[eid] for eid in rel.evidence_ids if eid in evidence]
            if not related:
                findings.append(ValidationFinding(code='MISSING_EVIDENCE',level='error',message=f'{rel.source} → {rel.target} 缺乏可追溯證據'))
                continue
            supported = [e for e in related if e.supports_claim]
            if not supported:
                findings.append(ValidationFinding(code='UNSUPPORTED_CLAIM',level='error',message=f'{rel.source} → {rel.target} 來源沒有支持該主張'))
                continue
            if rel.kind in (RelationKind.verified_direct,RelationKind.corroborated_direct):
                official = any(e.kind == EvidenceKind.official for e in supported)
                independent = sum(1 for e in supported if e.kind == EvidenceKind.third_party and e.independently_verified) >= 2
                if not (official or independent):
                    findings.append(ValidationFinding(code='DIRECT_LINK_UNVERIFIED',level='warning',message=f'{rel.source} → {rel.target} 不可視為直接供應鏈'))
                    continue
            if rel.kind == RelationKind.candidate:
                findings.append(ValidationFinding(code='CANDIDATE_ONLY',level='warning',message=f'{rel.source} → {rel.target} 尚待確認'))
                continue
            accepted.append(rel)
        return accepted, findings
