"""Contracts shared by API, Skills and deterministic risk calculation."""
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class EvidenceKind(str, Enum):
    official = 'official'
    third_party = 'third_party'
    industry_model = 'industry_model'
    unverified = 'unverified'

class RelationKind(str, Enum):
    verified_direct = 'verified_direct'
    corroborated_direct = 'corroborated_direct'
    industry_dependency = 'industry_dependency'
    shared_exposure = 'shared_exposure'
    candidate = 'candidate'

class Evidence(BaseModel):
    id: str
    title: str
    source_url: str
    published_at: str  # ISO date; production: require validated timestamps
    kind: EvidenceKind
    supports_claim: bool = False
    quote_or_summary: str = ''
    independently_verified: bool = False

class Relation(BaseModel):
    source: str
    target: str
    kind: RelationKind
    weight: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    as_of: str | None = None

class Scenario(BaseModel):
    description: str = Field(min_length=3, max_length=3000)
    event_type: Literal['natural_disaster', 'supply_chain', 'economic_policy', 'unknown'] = 'unknown'
    region: str | None = None
    product: str | None = None
    severity: float | None = Field(default=None, ge=0, le=1)
    duration_days: int | None = Field(default=None, ge=0, le=3650)
    seed_nodes: list[str] = Field(default_factory=list)
    @model_validator(mode='after')
    def dedup_seeds(self):
        self.seed_nodes = list(dict.fromkeys(self.seed_nodes))
        return self

class ValidationFinding(BaseModel):
    code: str
    level: Literal['info','warning','error']
    message: str

class RiskCompany(BaseModel):
    node_id: str
    relative_risk: float = Field(ge=0, le=1)
    risk_index: float = Field(ge=0, le=100)
    top_paths: list[list[str]] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    status: Literal['complete', 'insufficient_evidence', 'invalid_input']
    scenario: Scenario
    entities: list[str] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    companies: list[RiskCompany] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    explanation: str = ''
    model_version: str = 'demo-0.1'
    data_mode: Literal['fixture','verified_public_data'] = 'fixture'
    disclaimer: str = '相對情境指標，非財務損失估計、實際機率或投資建議。'
