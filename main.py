import json
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from google.cloud import datastore

app = FastAPI(title="Fast Simon Simple Database")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    missing = [
        str(err["loc"][-1])
        for err in exc.errors()
        if err["type"] in ("missing", "value_error")
    ]
    if missing:
        return PlainTextResponse(
            f"Error: missing or invalid parameter(s): {', '.join(missing)}",
            status_code=400,
        )
    return PlainTextResponse("Error: invalid request.", status_code=400)


_client: datastore.Client | None = None
KIND = "AppState"
KEY_NAME = "state"

DEFAULT_STATE = {"variables": {}, "value_counts": {}, "undo_stack": [], "redo_stack": []}


def get_client() -> datastore.Client:
    global _client
    if _client is None:
        _client = datastore.Client()
    return _client


@contextmanager
def transactional_state():
    """Load state, yield it for mutation, save it back — all inside one Datastore transaction."""
    client = get_client()
    key = client.key(KIND, KEY_NAME)
    with client.transaction():
        entity = client.get(key)
        state = json.loads(entity["state_json"]) if entity else json.loads(json.dumps(DEFAULT_STATE))
        yield state
        new_entity = datastore.Entity(key=key, exclude_from_indexes=("state_json",))
        new_entity["state_json"] = json.dumps(state)
        client.put(new_entity)


def _inc(state: dict, value: Optional[str]) -> None:
    if value is None:
        return
    state["value_counts"][value] = state["value_counts"].get(value, 0) + 1


def _dec(state: dict, value: Optional[str]) -> None:
    if value is None:
        return
    counts = state["value_counts"]
    if value in counts:
        counts[value] -= 1
        if counts[value] <= 0:
            del counts[value]


@app.get("/", response_class=PlainTextResponse)
def hello_world():
    return "Hello, World!"


@app.get("/set", response_class=PlainTextResponse, summary="Set a variable")
def set_var(name: str, value: str):
    with transactional_state() as state:
        old = state["variables"].get(name)
        _dec(state, old)
        state["variables"][name] = value
        _inc(state, value)
        state["undo_stack"].append({"name": name, "old": old, "new": value})
        state["redo_stack"] = []
    return f"{name} = {value}"


@app.get("/get", response_class=PlainTextResponse, summary="Get a variable's value")
def get_var(name: str):
    with transactional_state() as state:
        value = state["variables"].get(name)
    return value if value is not None else "None"


@app.get("/unset", response_class=PlainTextResponse, summary="Unset a variable")
def unset_var(name: str):
    with transactional_state() as state:
        old = state["variables"].get(name)
        _dec(state, old)
        state["variables"].pop(name, None)
        state["undo_stack"].append({"name": name, "old": old, "new": None})
        state["redo_stack"] = []
    return f"{name} = None"


@app.get("/numequalto", response_class=PlainTextResponse, summary="Count variables equal to a value")
def numequalto(value: str):
    with transactional_state() as state:
        count = state["value_counts"].get(value, 0)
    return str(count)


@app.get("/undo", response_class=PlainTextResponse, summary="Undo the last SET/UNSET")
def undo():
    with transactional_state() as state:
        if not state["undo_stack"]:
            return "NO COMMANDS"
        action = state["undo_stack"].pop()
        name, old, new = action["name"], action["old"], action["new"]
        _dec(state, new)
        if old is None:
            state["variables"].pop(name, None)
        else:
            state["variables"][name] = old
        _inc(state, old)
        state["redo_stack"].append(action)
    return f"{name} = {old if old is not None else 'None'}"


@app.get("/redo", response_class=PlainTextResponse, summary="Redo the last undone command")
def redo():
    with transactional_state() as state:
        if not state["redo_stack"]:
            return "NO COMMANDS"
        action = state["redo_stack"].pop()
        name, old, new = action["name"], action["old"], action["new"]
        _dec(state, old)
        if new is None:
            state["variables"].pop(name, None)
        else:
            state["variables"][name] = new
        _inc(state, new)
        state["undo_stack"].append(action)
    return f"{name} = {new if new is not None else 'None'}"


@app.get("/end", response_class=PlainTextResponse, summary="Clear all data")
def end():
    client = get_client()
    key = client.key(KIND, KEY_NAME)
    with client.transaction():
        client.delete(key)
    return "CLEANED"
