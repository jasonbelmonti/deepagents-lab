"""Require sufficient read evidence, without forcing one call sequence or count."""
from .oracle import structural_candidates


def sufficient_reads(api, case, expected):
    data = api.data
    calls = [row for row in api.calls if row["ok"]]
    profiles = {i for row in calls if row["name"] == "profiles" and "topic" in row["options"]["fields"] for i in row["ids"]}
    if case.kind == "lookup":
        return data.root in profiles
    contacts = {i for row in calls if row["name"] == "contacts"
                and row["options"]["since"] <= case.contact_since for i in row["ids"]}
    expanded = {i for row in calls if row["name"] == "neighbors"
                and row["options"]["kind"] == "collaborated"
                and row["options"]["since"] <= case.edge_since for i in row["ids"]}
    frontier, required = {data.root}, set()
    for _ in range(case.depth):
        required.update(frontier)
        frontier = {e["target"] for e in data.edges if e["source"] in frontier
                    and e["kind"] == "collaborated" and e["last_seen"] >= case.edge_since} - required
    if not required <= expanded:
        return False
    for row in structural_candidates(data, case):
        person = row["person_id"]
        excluded = (person in profiles and data.profiles[person]["topic"] != case.topic) or (
            person in contacts and data.contacts.get(person, "") >= case.contact_since)
        if not excluded and not (person in profiles and person in contacts):
            return False
        # Once the exact top K is established, lower-ranked candidates can be
        # pruned without fetching their profiles/history. Empty answers cannot.
        if len(expected) == case.limit and person == expected[-1]["person_id"]:
            break
    return True
