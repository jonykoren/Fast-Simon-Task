import json
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from google.cloud import datastore

app = FastAPI(title="Fast Simon Simple Database")

client = datastore.Client()
KIND = "AppState"
KEY_NAME = "state"

DEFAULT_STATE = {"variables": {}, "value_counts": {}, "undo_stack": [], "redo_stack": []}


@contextmanager
def transactional_state():
    """Load state, yield it for mutation, save it back — all inside one Datastore transaction."""
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


@app.get("/set", response_class=PlainTextResponse)
def set_var(name: str, value: str):
    with transactional_state() as state:
        old = state["variables"].get(name)
        _dec(state, old)
        state["variables"][name] = value
        _inc(state, value)
        state["undo_stack"].append({"name": name, "old": old, "new": value})
        state["redo_stack"] = []
    return f"{name} = {value}"


@app.get("/get", response_class=PlainTextResponse)
def get_var(name: str):
    with transactional_state() as state:
        value = state["variables"].get(name)
    return value if value is not None else "None"


@app.get("/unset", response_class=PlainTextResponse)
def unset_var(name: str):
    with transactional_state() as state:
        old = state["variables"].get(name)
        _dec(state, old)
        state["variables"].pop(name, None)
        state["undo_stack"].append({"name": name, "old": old, "new": None})
        state["redo_stack"] = []
    return f"{name} = None"


@app.get("/numequalto", response_class=PlainTextResponse)
def numequalto(value: str):
    with transactional_state() as state:
        count = state["value_counts"].get(value, 0)
    return str(count)


@app.get("/undo", response_class=PlainTextResponse)
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


@app.get("/redo", response_class=PlainTextResponse)
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


@app.get("/end", response_class=PlainTextResponse)
def end():
    key = client.key(KIND, KEY_NAME)
    with client.transaction():
        client.delete(key)
    return "CLEANED"
