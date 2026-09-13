"""Handwritten offline recipes ONLY. Never supplied to a live agent."""
import json
from dataclasses import asdict

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from .fixture import make_graph
from .oracle import expected_answer
from .tools import GraphAPI

# Breadth-first path enumeration over API responses, independent of the Python
# oracle's depth-first full-fixture enumeration. Used to exercise real QuickJS.
COMPUTE_JS = """
var adjacency = new Map();
for (var e of edges) {
  if (!adjacency.has(e.source)) adjacency.set(e.source, new Set());
  adjacency.get(e.source).add(e.target);
}
var direct = adjacency.get(root) || new Set();
var excluded = new Set(contacts.map(p => p.person_id));
var topics = new Map(profiles.map(p => [p.person_id, p.topic]));
var paths = [[root]], candidates = new Map();
function better(a, b) { return a.length < b.length || (a.length === b.length && JSON.stringify(a) < JSON.stringify(b)); }
for (var index = 0; index < paths.length; index++) {
  var path = paths[index], person = path[path.length - 1];
  if (path.length >= 3 && !direct.has(person) && !excluded.has(person) && topics.get(person) === q.topic) {
    if (!candidates.has(person)) candidates.set(person, new Map());
    var options = candidates.get(person), prior = options.get(path[1]);
    if (!prior || better(path, prior)) options.set(path[1], path);
  }
  if (path.length <= q.depth) {
    for (var target of adjacency.get(person) || []) {
      if (!path.includes(target)) paths.push([...path, target]);
    }
  }
}
var answer = [...candidates].filter(([id, options]) => options.size >= q.min_connectors)
  .map(([id, options]) => ({person_id: id, connectors: options.size,
    paths: [...options].sort((a,b) => a[0].localeCompare(b[0])).map(x => x[1])}));
answer.sort((a,b) => b.connectors - a.connectors ||
  Math.min(...a.paths.map(p => p.length)) - Math.min(...b.paths.map(p => p.length)) ||
  a.person_id.localeCompare(b.person_id));
JSON.stringify(answer.slice(0, q.limit));
"""

GATHER_JS = """
var edges = [], seen = new Set(), frontier = [root];
for (var depth = 0; depth < q.depth && frontier.length; depth++) {
  var batch = await tools.getNeighbors({person_ids: frontier, since: q.edge_since});
  edges.push(...batch);
  frontier.forEach(id => seen.add(id));
  frontier = [...new Set(batch.map(e => e.target))].filter(id => !seen.has(id));
}
var ids = [...new Set(edges.map(e => e.target))].filter(id => id !== root);
var profiles = [], contacts = [];
if (ids.length) [profiles, contacts] = await Promise.all([
  tools.getProfiles({person_ids: ids, fields: ['topic']}),
  tools.getContactHistory({person_ids: ids, since: q.contact_since})
]);
"""


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def message(requests, index):
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": f"call-{index}-{i}", "type": "tool_call"}
        for i, (name, args) in enumerate(requests)
    ])


def scripted_model(config, case, seed, arm):
    """Precompute a script to verify plumbing; do not interpret its speed as value."""
    data = make_graph(seed, case.width)
    prefix = f"var root = {json.dumps(data.root)}; var q = {json.dumps(asdict(case))};\n"
    expected = expected_answer(data, case)
    if arm == "ptc":
        code = (f"JSON.stringify(await tools.getProfiles({{person_ids:[root],fields:['topic']}}));"
                if case.kind == "lookup" else GATHER_JS + COMPUTE_JS)
        responses = [message([("eval", {"code": prefix + code})], 0)]
    elif case.kind == "lookup":
        responses = [message([("get_profiles", {"person_ids": [data.root], "fields": ["topic"]})], 0)]
    else:
        reference = GraphAPI(data)
        responses, edges, seen, frontier = [], [], set(), [data.root]
        for depth in range(case.depth):
            if not frontier:
                break
            args = dict(person_ids=frontier, since=case.edge_since, kind="collaborated")
            responses.append(message([("get_neighbors", args)], depth))
            batch = reference.execute("neighbors", frontier, since=case.edge_since, kind="collaborated")
            edges.extend(batch)
            seen.update(frontier)
            frontier = sorted({e["target"] for e in batch} - seen)
        ids = sorted({e["target"] for e in edges} - {data.root})
        profiles, contacts = [], []
        if ids:
            responses.append(message([
                ("get_profiles", dict(person_ids=ids, fields=["topic"])),
                ("get_contact_history", dict(person_ids=ids, since=case.contact_since)),
            ], len(responses)))
            profiles = reference.execute("profiles", ids, fields=["topic"])
            contacts = reference.execute("contacts", ids, since=case.contact_since)
        if arm == "compute":
            declarations = "\n".join(f"var {name} = {json.dumps(value)};" for name, value in (
                ("edges", edges), ("profiles", profiles), ("contacts", contacts)))
            responses.append(message([("eval", {"code": prefix + declarations + COMPUTE_JS})], len(responses)))
    responses.append(AIMessage(content=json.dumps(expected)))
    return ScriptedModel(responses=responses)
