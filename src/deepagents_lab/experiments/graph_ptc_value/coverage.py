"""Require sufficient read evidence, without forcing one call sequence or count."""
from .oracle import structural_candidates


def sufficient_reads(api, case, expected):
    data = api.data
    calls = [row for row in api.calls if row["ok"] and row["delivered"]]
    profiles = {i for row in calls if row["name"] == "profiles" and "topic" in row["options"]["fields"] for i in row["ids"]}
    if case.kind == "lookup":
        return data.root in profiles
    contact_reads = [row for row in calls if row["name"] == "contacts"]
    contacts = {i for row in contact_reads
                if row["options"]["since"] <= case.contact_since for i in row["ids"]}
    # A returned recent contact proves exclusion even from a narrower query.
    # Empty results prove absence only over the query's actual date coverage.
    recent_contacts = {i for row in contact_reads for i in row["ids"]
                       if data.contacts.get(i, "") >= max(row["options"]["since"], case.contact_since)}
    expanded = {i for row in calls if row["name"] == "neighbors"
                and row["options"]["kind"] == "collaborated"
                and row["options"]["since"] <= case.edge_since for i in row["ids"]}
    first_hops = {e["target"] for e in data.edges if e["source"] == data.root
                  and e["kind"] == "collaborated" and e["last_seen"] >= case.edge_since} - {data.root}
    if data.root in expanded and len(first_hops) < case.min_connectors:
        return True  # No candidate can have enough distinct first-hop connectors.
    frontier, required = {data.root}, set()
    for _ in range(case.depth):
        required.update(frontier)
        frontier = {e["target"] for e in data.edges if e["source"] in frontier
                    and e["kind"] == "collaborated" and e["last_seen"] >= case.edge_since} - required
    if not required <= expanded:
        return False
    for row in structural_candidates(data, case):
        person = row["person_id"]
        excluded = (person in profiles and data.profiles[person]["topic"] != case.topic) or person in recent_contacts
        if not excluded and not (person in profiles and person in contacts):
            return False
        # Once the exact top K is established, lower-ranked candidates can be
        # pruned without fetching their profiles/history. Empty answers cannot.
        if len(expected) == case.limit and person == expected[-1]["person_id"]:
            break
    return True
