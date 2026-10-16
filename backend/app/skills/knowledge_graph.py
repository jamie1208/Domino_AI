"""KGSkill: build a transparent, directed weighted graph from accepted edges."""
import networkx as nx

class KnowledgeGraphSkill:
    def run(self, accepted_relations):
        graph=nx.DiGraph()
        for rel in accepted_relations:
            # Edges must have a clear propagation direction, not just a business-relationship direction.
            # Fixture uses source -> downstream target by design; production must verify this.
            graph.add_edge(rel.source, rel.target, weight=rel.weight, kind=rel.kind.value, evidence_ids=rel.evidence_ids)
        return graph
