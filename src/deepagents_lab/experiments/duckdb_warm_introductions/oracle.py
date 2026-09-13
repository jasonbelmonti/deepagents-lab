"""Independent Python traversal; never executes the reference or model SQL."""

from collections import defaultdict
from datetime import date

from .domain import Network, Question


def expected_routes(network: Network, question: Question) -> dict:
    jobs = {job[0]: job for job in network.jobs}
    _, company, team, _ = jobs[question.job_id]
    targets = defaultdict(list)
    for employment in network.employment:
        if (employment.company_id == company and employment.team == team
                and employment.starts_at <= question.as_of
                and (employment.ends_at is None or employment.ends_at > question.as_of)):
            targets[employment.person_id].append(employment.evidence_id)
    adjacency = defaultdict(list)
    for edge in network.relationships:
        if (edge.kind in {"collaborated", "mentor"}
                and question.cutoff <= edge.observed_at <= question.as_of):
            adjacency[edge.source_id].append(edge)
    candidates = []

    def walk(path, evidence, strength, oldest):
        if len(path) > 1:
            for employment_id in targets[path[-1]]:
                candidates.append({
                    "connector_id": path[1], "target_id": path[-1], "path": path,
                    "evidence_ids": evidence, "employment_evidence_id": employment_id,
                    "bottleneck_strength": strength, "hops": len(path) - 1,
                    "oldest_evidence_at": oldest,
                })
        if len(path) - 1 == question.max_hops:
            return
        for edge in adjacency[path[-1]]:
            if edge.target_id not in path:
                walk(path + [edge.target_id], evidence + [edge.evidence_id],
                     min(strength, edge.strength), min(oldest, edge.observed_at))

    walk([question.user_id], [], 5, question.as_of)

    def ranking(route):
        return (-route["bottleneck_strength"], route["hops"],
                -date.fromisoformat(route["oldest_evidence_at"]).toordinal(),
                ">".join(route["path"]), route["employment_evidence_id"])

    selected = {}
    for route in sorted(candidates, key=ranking):
        selected.setdefault(route["connector_id"], route)
    return {"routes": list(selected.values())[:question.top_k]}
