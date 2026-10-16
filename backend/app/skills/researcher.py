"""ResearchSkill is intentionally NOT a pretend web crawler.
Replace the provider with licensed public-data fetching + hybrid RAG later.
"""
from dataclasses import dataclass
from app.schemas import Evidence, Relation

@dataclass
class ResearchBundle:
    evidence: list[Evidence]
    candidate_relations: list[Relation]

class ResearchSkill:
    def __init__(self, provider): self.provider = provider
    def run(self, scenario) -> ResearchBundle:
        return self.provider.retrieve(scenario)

class EmptyPublicDataProvider:
    def retrieve(self, scenario) -> ResearchBundle:
        return ResearchBundle(evidence=[], candidate_relations=[])
