"""Transparent teaching/demo risk engine. NOT a calibrated real-world risk model.
Uses max-product paths to avoid summing overlapping paths. This is a conservative
prototype scoring rule, NOT a complete input-output economic propagation model.
"""
import heapq
from app.schemas import RiskCompany

def calculate(graph, seed_nodes: list[str], severity: float | None, max_hops=4, threshold=0.005):
    if severity is None or not seed_nodes: return []
    risks:dict[str,float] = {}
    paths:dict[str,list[str]] = {}
    queue=[]
    for seed in seed_nodes:
        if seed not in graph: continue
        risks[seed]=severity; paths[seed]=[seed]
        heapq.heappush(queue, (-severity, seed, [seed]))
    while queue:
        neg, node, path=heapq.heappop(queue)
        score=-neg
        if score+1e-12 < risks.get(node,0): continue
        if len(path)-1>=max_hops: continue
        for child in graph.successors(node):
            if child in path: continue
            candidate=score*graph[node][child]['weight']
            if candidate < threshold: continue
            if candidate>risks.get(child,-1):
                risks[child]=candidate; paths[child]=path+[child]
                heapq.heappush(queue,(-candidate,child,path+[child]))
    return [RiskCompany(node_id=node,relative_risk=round(score,5),risk_index=round(score*100,2),top_paths=[paths[node]]) for node,score in sorted(risks.items(),key=lambda item:-item[1])]
