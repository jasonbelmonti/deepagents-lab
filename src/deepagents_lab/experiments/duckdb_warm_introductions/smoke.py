"""Provider-free recipes that grade actual SQL/interpreter outputs."""

import json
from xml.etree import ElementTree

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from .domain import Question
from .reference import REFERENCE_SQL, named_rows, reference_parameters


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def program(question: Question, *, inject_error: bool = False) -> str:
    query = json.dumps({"sql": REFERENCE_SQL, "parameters": reference_parameters(question)})
    recovery = """
var failed = await tools.queryDuckdb({sql: 'SELECT nonexistent_column FROM people'});
if (failed.ok !== false) throw new Error('Expected a recoverable SQL error');
""" if inject_error else ""
    return f"""
var schema = await tools.duckdbSchema({{}});
if (!schema.ok) throw new Error(schema.error);
{recovery}
var result = await tools.queryDuckdb({query});
if (!result.ok) throw new Error(result.error);
var routes = result.rows.map(row => Object.fromEntries(
    result.columns.map((name, i) => [name, row[i]])
));
JSON.stringify({{routes}});
""".strip()


def scripted_model(arm: str, question: Question, expected: dict, *, inject_error: bool = False):
    def call(name, args, identifier):
        return {"name": name, "args": args, "id": identifier, "type": "tool_call"}

    if arm == "interpreter":
        messages = [AIMessage(content="", tool_calls=[
            call("eval", {"code": program(question, inject_error=inject_error)}, "eval-1"),
        ])]
    elif arm == "ordinary":
        query = call("query_duckdb", {
            "sql": REFERENCE_SQL, "parameters": reference_parameters(question),
        }, "query-1")
        schema = call("duckdb_schema", {}, "schema-1")
        if inject_error:
            messages = [AIMessage(content="", tool_calls=[schema, call(
                "query_duckdb", {"sql": "SELECT nonexistent_column FROM people"}, "bad-query",
            )]), AIMessage(content="", tool_calls=[query])]
        else:
            # The ordinary arm may batch calls and solve the task in one SQL query.
            messages = [AIMessage(content="", tool_calls=[schema, query])]
    else:
        raise ValueError(arm)
    return ScriptedModel(responses=[*messages, AIMessage(content=json.dumps(expected))])


def executed_answer(record: dict) -> dict:
    """Do not accept canned final model text as proof that the recipe worked."""
    for message in reversed(record["messages"]):
        if message["type"] != "tool" or message.get("status") == "error":
            continue
        if record["arm"] == "interpreter" and message.get("name") == "eval":
            envelope = ElementTree.fromstring(message["content"])
            if envelope.tag != "result":
                raise AssertionError(message["content"])
            return json.loads(envelope.text)
        if record["arm"] == "ordinary" and message.get("name") == "query_duckdb":
            result = json.loads(message["content"])
            if result["ok"]:
                return {"routes": named_rows(result)}
    raise AssertionError("No successful recipe result was returned by the assigned tool transport")
