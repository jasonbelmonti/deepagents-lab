"""Transparent offline SQL recipe. Never supplied to live agents."""

from .domain import Question


REFERENCE_SQL = """
WITH RECURSIVE
settings AS (
    SELECT ?::VARCHAR AS user_id, ?::VARCHAR AS job_id,
           ?::DATE AS as_of, ?::DATE AS cutoff, ?::INTEGER AS max_hops
),
eligible AS (
    SELECT r.* FROM relationships r CROSS JOIN settings s
    WHERE r.kind IN ('collaborated', 'mentor')
      AND r.observed_at BETWEEN s.cutoff AND s.as_of
),
paths AS (
    SELECT [s.user_id] AS path, []::VARCHAR[] AS evidence_ids,
           5 AS bottleneck_strength, s.as_of AS oldest_evidence_at, 0 AS hops
    FROM settings s
    UNION ALL
    SELECT list_append(p.path, r.target_id), list_append(p.evidence_ids, r.evidence_id),
           least(p.bottleneck_strength, r.strength),
           least(p.oldest_evidence_at, r.observed_at), p.hops + 1
    FROM paths p JOIN eligible r ON r.source_id = list_last(p.path)
    CROSS JOIN settings s
    WHERE p.hops < s.max_hops AND NOT list_contains(p.path, r.target_id)
),
candidates AS (
    SELECT p.path[2] AS connector_id, list_last(p.path) AS target_id,
           p.path, p.evidence_ids, e.evidence_id AS employment_evidence_id,
           p.bottleneck_strength, p.hops, p.oldest_evidence_at
    FROM paths p
    JOIN employment e ON e.person_id = list_last(p.path)
    CROSS JOIN settings s
    JOIN jobs j ON j.job_id = s.job_id AND j.company_id = e.company_id AND j.team = e.team
    WHERE p.hops > 0 AND e.starts_at <= s.as_of AND (e.ends_at IS NULL OR e.ends_at > s.as_of)
),
diverse AS (
    SELECT * FROM candidates
    QUALIFY row_number() OVER (
        PARTITION BY connector_id ORDER BY bottleneck_strength DESC, hops,
        oldest_evidence_at DESC, array_to_string(path, '>'), employment_evidence_id
    ) = 1
)
SELECT * FROM diverse
ORDER BY bottleneck_strength DESC, hops, oldest_evidence_at DESC,
         array_to_string(path, '>'), employment_evidence_id
LIMIT ?
""".strip()


def reference_parameters(question: Question) -> list:
    return [question.user_id, question.job_id, question.as_of, question.cutoff,
            question.max_hops, question.top_k]


def named_rows(result: dict) -> list[dict]:
    return [dict(zip(result["columns"], row, strict=True)) for row in result["rows"]]
