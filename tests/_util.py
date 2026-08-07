"""Shared test helpers: locate the repo, load JSON, import the skill scripts."""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "skills", "daily-brief", "scripts")
SCHEMA_PATH = os.path.join(REPO, "schemas", "daily-brief.schema.json")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def load_json(*parts):
    with open(os.path.join(REPO, *parts)) as f:
        return json.load(f)


def schema():
    return load_json("schemas", "daily-brief.schema.json")
