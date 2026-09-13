"""Task specification shared by all arms; no live solution program."""
import json

from .config import ARMS, Config, Scenario


def prompt_for(case: Scenario, root: str, arm: str, config: Config) -> str:
    if arm not in ARMS:
        raise ValueError("Unknown arm.")
    if case.kind == "lookup":
        task = f'Return the topic of person {root} as JSON [{{"person_id":"{root}","topic":"..."}}].'
    else:
        task = f"""Find up to {case.limit} warm-introduction candidates for {root}.
Eligible paths: directed collaborated edges with last_seen >= {case.edge_since},
2 through {case.depth} hops, no repeated person within a path. Exclude the root
and all its direct neighbors under that same edge/date filter. Candidates must
have topic {json.dumps(case.topic)} and no contact since {case.contact_since}.
A connector is the first person after the root in an eligible path. Count distinct
connectors, not paths; require at least {case.min_connectors}. For each candidate
and connector retain the shortest path, breaking equal-length ties by the
lexicographic sequence of IDs. Order these representative paths by connector ID.
Rank candidates by connector count descending, then shortest path hop count
ascending, then person_id ascending. Return only the top {case.limit} as JSON:
[{{"person_id":"...","connectors":2,"paths":[["root","connector","candidate"],...]}}].
Search completely within the specified hop limit; do not sample candidates.
Return [] if none qualify. An API/error budget failure is not an empty answer.
"""
    common = f"""
Use only graph reads{', and eval' if arm != 'ordinary' else ''}. Do not use planning,
subagents, filesystem or unrelated tools. Batch up to 64 IDs per API call and
parallelize independent calls when useful (backend concurrency {config.concurrency}).
Backend filtering and profile field selection are available to every arm.
The total graph API budget is {config.max_tool_calls} calls. IDs are opaque;
discover them through returned edges. All graph data is fixed for this run.
Final response must be only the requested JSON, no markdown or explanation.
"""
    routes = {
        "ordinary": "Use get_neighbors, get_profiles and get_contact_history as ordinary model tool calls.",
        "compute": """Use graph APIs as ordinary model tool calls. You may use eval for
JavaScript computation on returned data; eval has no tools bridge. Within this
invocation, variables persist between eval calls. Code's last expression is its
result; JSON.stringify is useful. Computation is optional, not required.""",
        "ptc": """Use eval to call graph APIs from JavaScript: tools.getNeighbors,
tools.getProfiles and tools.getContactHistory. Argument keys remain snake_case;
each returns a native array; await calls. Write your own program to solve the
task. Variables persist between eval calls in this invocation. Return only the
requested answer from eval using JSON.stringify as the last expression, then
repeat it as the final answer. Do not log intermediate records. No top-level return.""",
    }
    return task + common + routes[arm]
