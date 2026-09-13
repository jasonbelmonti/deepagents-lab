"""Shared task semantics; only the tool transport differs between arms."""

from .domain import Question


COMMON_SYSTEM = """
Find evidence-backed introduction routes in a synthetic social network stored in DuckDB.
Inspect its schema, then query the data. SQL may do the entire search/ranking in one
query, including recursive CTEs and window functions. You may also use several queries.
Both schema and query tools return {ok: true, columns, rows} or {ok: false, error}.
Always check ok; correct failed SQL within the budget. Do not treat errors as no routes.
Use only the experiment's database tools via the assigned transport. Do not use task,
filesystem tools, or write_todos. Final response must be the requested JSON object
without Markdown fences or commentary. Do not invent people, relationships or evidence.
""".strip()

TRANSPORT = {
    "ordinary": "Call duckdb_schema and query_duckdb directly for all database work.",
    "interpreter": """Use eval for all database work. Inside JavaScript, call
await tools.duckdbSchema({}) and await tools.queryDuckdb({sql: '...', parameters: []}).
These return native objects; do not JSON.parse them. Use SQL for joins and aggregation,
JavaScript for orchestration and shaping compact results. Return JSON.stringify(...)
as the final expression of eval. You may use several eval calls if needed.""",
}


def task_prompt(question: Question) -> str:
    return f"""
Who can {question.user_id} approach for an introduction into job {question.job_id}?
Use the job's exact company_id and team. Return up to {question.top_k} distinct first
connectors, ranked using the following deliberately synthetic heuristic:

- Follow directed source_id -> target_id relationships only. Never reverse an edge.
- Only kind 'collaborated' or 'mentor' is eligible; shared affiliation is insufficient.
- Every edge's observed_at must be in [{question.cutoff}, {question.as_of}], inclusive.
- Paths start with {question.user_id}, contain 1–{question.max_hops} edges, and never
  repeat a person. Direct contacts are eligible: their connector is also their target.
- The target must have matching employment with starts_at <= {question.as_of} and
  ends_at NULL or > {question.as_of}. An end date is exclusive. Intermediates may
  work anywhere. Each employment row carries its own evidence_id.
- Compute bottleneck_strength = the minimum edge strength, hops = number of edges,
  and oldest_evidence_at = minimum edge observed_at along the path.
- Rank routes by bottleneck_strength descending, hops ascending, oldest_evidence_at
  descending, path IDs joined with '>' ascending, then employment evidence ID ascending.
  Keep the best route per first connector (path[1] in zero-based notation), then apply
  that same order globally and keep the first {question.top_k}. Do not reward fanout.

Return exactly {{"routes": [...]}}. Each route must contain exactly these fields:
connector_id (string), target_id (string), path (ordered person ID array including user),
evidence_ids (relationship evidence ID array in path order), employment_evidence_id
(string), bottleneck_strength (integer), hops (integer), oldest_evidence_at (YYYY-MM-DD).
An empty routes array is correct only if no eligible paths exist. Strength is an ordinal
fixture score, not a probability that an introduction will succeed.
""".strip()
