import json
import re
from pathlib import Path

from eval.harness import load_suite, validate_suite


ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "eval/suites/v4.2-routing-baseline.json"
SCHEMA_PATH = ROOT / "governance/eval-suite.schema.json"
CATALOG_PATH = ROOT / "catalog/components.yaml"


def _matches_type(value, expected):
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda: isinstance(value, bool),
        "null": lambda: value is None,
    }[expected]()


def _schema_errors(value, schema, path="$"):
    errors = []
    if "type" in schema and not _matches_type(value, schema["type"]):
        return [f"{path}: wrong type"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: does not match const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in enum")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than minLength")
    if isinstance(value, int) and not isinstance(value, bool) and value < schema.get("minimum", value):
        errors.append(f"{path}: below minimum")
    if isinstance(value, dict):
        required = schema.get("required", [])
        errors.extend(f"{path}: missing {key}" for key in required if key not in value)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}: unexpected {key}" for key in value if key not in properties)
        for key, child in value.items():
            if key in properties:
                errors.extend(_schema_errors(child, properties[key], f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than minItems")
        if "items" in schema:
            for index, child in enumerate(value):
                errors.extend(_schema_errors(child, schema["items"], f"{path}[{index}]"))
        if "contains" in schema and not any(not _schema_errors(child, schema["contains"], path) for child in value):
            errors.append(f"{path}: contains constraint not met")
    return errors


def _catalog_skill_names():
    text = CATALOG_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^  - name: ([a-z0-9-]+)$", text, flags=re.MULTILINE))


def test_v42_routing_baseline_conforms_to_declared_schema():
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert _schema_errors(suite, schema) == []
    assert validate_suite(suite) == []
    assert load_suite(SUITE_PATH) == suite


def test_v42_routing_baseline_has_independent_frozen_sample_shape():
    suite = load_suite(SUITE_PATH)
    cases = suite["cases"]
    assert 30 <= len(cases) <= 50
    held_out = [case for case in cases if case["split"] == "held_out"]
    assert len(held_out) / len(cases) == 0.4
    assert len({case["case_id"] for case in cases}) == len(cases)
    normalized_prompts = {" ".join(case["prompt"].split()).casefold() for case in cases}
    assert len(normalized_prompts) == len(cases)
    assert suite["repetitions"] == 3
    assert "not an execution report or promotion evidence" in suite["description"]


def test_v42_routing_baseline_covers_every_packaged_skill_and_controls():
    cases = load_suite(SUITE_PATH)["cases"]
    positive = [case for case in cases if case["expected_route"] != "native"]
    controls = [case for case in cases if case["expected_route"] == "native"]
    expected_skills = _catalog_skill_names()
    assert {case["expected_route"] for case in positive} == expected_skills
    for skill in expected_skills:
        skill_cases = [case for case in positive if case["expected_route"] == skill]
        assert {case["split"] for case in skill_cases} == {"train", "held_out"}
        assert all(any(item == {"type": "route_suggested", "skill": skill} for item in case["assertions"]) for case in skill_cases)
    assert len(controls) >= 10
    assert {case["split"] for case in controls} == {"train", "held_out"}
    assert all(any(item == {"type": "route_suggested", "skill": "native"} for item in case["assertions"]) for case in controls)
