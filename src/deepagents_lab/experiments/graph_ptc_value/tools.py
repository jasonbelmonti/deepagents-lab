"""Identical batch reads and per-trial work bounds for every arm."""
import asyncio
import json
from contextvars import copy_context
from copy import deepcopy
from datetime import date
from functools import partial
from threading import Lock
from time import perf_counter

from langchain_core.tools import tool

from .fixture import GraphData


class GraphAPI:
    def __init__(self, data: GraphData, *, max_calls=64, concurrency=4):
        self.data, self.max_calls = data, max_calls
        self.calls: list[dict] = []
        self._lock = Lock()
        self._slots = asyncio.Semaphore(concurrency)

    def execute(self, name, ids, **options):
        result, row = self._execute(name, ids, **options)
        row["delivered"] = True
        return result

    def _execute(self, name, ids, **options):
        """Record backend work separately from delivery to a read's caller."""
        started = perf_counter()
        options = deepcopy(options)
        row = {"name": name, "ids": list(ids), "options": options,
               "ok": False, "delivered": False, "response_bytes": 0}
        with self._lock:
            self.calls.append(row)
            over_budget = len(self.calls) > self.max_calls
        try:
            if over_budget:
                raise ValueError("Graph API call budget exceeded.")
            if not 1 <= len(ids) <= 64 or len(ids) != len(set(ids)) or any(i not in self.data.profiles for i in ids):
                raise ValueError("Use 1–64 distinct known person IDs per batch.")
            if name in ("neighbors", "contacts"):
                since = options["since"]
                if date.fromisoformat(since).isoformat() != since:
                    raise ValueError("Use YYYY-MM-DD dates.")
            if name == "neighbors":
                result = [dict(e) for e in self.data.edges if e["source"] in ids
                          and e["kind"] == options["kind"] and e["last_seen"] >= since]
            elif name == "profiles":
                fields = options["fields"]
                if not fields or not set(fields) <= {"topic", "name"}:
                    raise ValueError("Choose topic and/or name fields.")
                result = [{"person_id": i, **{f: self.data.profiles[i][f] for f in fields}} for i in ids]
            elif name == "contacts":
                result = [{"person_id": i, "last_contact": self.data.contacts[i]} for i in ids
                          if self.data.contacts.get(i, "") >= since]
            else:
                raise ValueError("Unknown graph API operation.")
            row.update(ok=True, records=len(result), response_bytes=len(json.dumps(result, separators=(",", ":")).encode()))
            return result, row
        except Exception as error:
            row["error_type"] = type(error).__name__
            raise
        finally:
            row["elapsed_seconds"] = perf_counter() - started

    async def read(self, name, ids, **options):
        await self._slots.acquire()
        try:
            work = asyncio.get_running_loop().run_in_executor(
                None, partial(copy_context().run, self._execute, name, ids, **options))
        except BaseException:
            self._slots.release()
            raise
        # The worker owns the slot: cancelling its caller cannot stop a thread.
        work.add_done_callback(self._read_finished)
        result, row = await asyncio.shield(work)
        # No await between this mark and return: cancelled reads never mark it.
        row["delivered"] = True
        return result

    def _read_finished(self, work):
        self._slots.release()
        if not work.cancelled():
            work.exception()  # Observe errors even when the caller has left.

    def tools(self):
        # QuickJS renders only the first description line in its PTC reference.
        # Adjacent literals keep the complete contract on one model-visible line.
        @tool(description=(
            "All outgoing edges for 1–64 distinct known person_ids, filtered by kind "
            "(default collaborated) and inclusive YYYY-MM-DD since. "
            "Returns an array of objects with source, target, kind, last_seen. "
            "source is the queried ID; target is the outgoing neighbor; last_seen is YYYY-MM-DD. "
            "No truncation or pagination. Batch IDs freely."
        ))
        async def get_neighbors(person_ids: list[str], since: str, kind: str = "collaborated") -> list[dict]:
            return await self.read("neighbors", person_ids, since=since, kind=kind)

        @tool(description=(
            "Profiles for 1–64 distinct known person_ids. Select topic and/or name with fields "
            "(default [topic]). Returns an array of objects with person_id and the selected "
            "string fields; person_id is always returned. No truncation or pagination."
        ))
        async def get_profiles(person_ids: list[str], fields: list[str] = ["topic"]) -> list[dict]:
            return await self.read("profiles", person_ids, fields=fields)

        @tool(description=(
            "Your contacts since inclusive YYYY-MM-DD for 1–64 distinct known person_ids. "
            "Returns an array of objects with person_id, last_contact (YYYY-MM-DD). "
            "An absent ID has not been contacted in that period. No truncation or pagination."
        ))
        async def get_contact_history(person_ids: list[str], since: str) -> list[dict]:
            return await self.read("contacts", person_ids, since=since)

        return [get_neighbors, get_profiles, get_contact_history]
