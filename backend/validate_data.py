"""
Validates data files for the exhibition diagnostic system.
Checks questions.json, active.json, and types.json for correctness.
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

REQUIRED_AXES = {"independence", "social", "curiosity", "action"}
REQUIRED_OPTIONS = {"A", "B", "C", "D"}
REQUIRED_QUESTION_FIELDS = {"id", "text", "summary", "options", "scoring"}
REQUIRED_TYPE_FIELDS = {
    "id", "name", "description", "one_liner",
    "good_match", "bad_match", "footer_question", "condition"
}


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_questions(data: dict) -> list[str]:
    errors = []
    questions = data.get("questions")

    if not isinstance(questions, list):
        return ["questions.json: 'questions' must be a list"]
    if len(questions) == 0:
        return ["questions.json: 'questions' list is empty"]

    seen_ids = set()
    for i, q in enumerate(questions):
        prefix = f"questions[{i}] (id={q.get('id', '<missing>')})"

        # Required top-level fields
        missing_fields = REQUIRED_QUESTION_FIELDS - set(q.keys())
        if missing_fields:
            errors.append(f"{prefix}: missing fields: {sorted(missing_fields)}")

        # Duplicate IDs
        qid = q.get("id")
        if qid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{qid}'")
        elif qid:
            seen_ids.add(qid)

        # Options
        options = q.get("options", {})
        missing_opts = REQUIRED_OPTIONS - set(options.keys())
        if missing_opts:
            errors.append(f"{prefix}: options missing keys: {sorted(missing_opts)}")

        # Scoring
        scoring = q.get("scoring", {})
        missing_scoring_opts = REQUIRED_OPTIONS - set(scoring.keys())
        if missing_scoring_opts:
            errors.append(
                f"{prefix}: scoring missing option keys: {sorted(missing_scoring_opts)}"
            )
        for opt, axes in scoring.items():
            if not isinstance(axes, dict):
                errors.append(f"{prefix}: scoring[{opt}] must be a dict")
                continue
            missing_axes = REQUIRED_AXES - set(axes.keys())
            if missing_axes:
                errors.append(
                    f"{prefix}: scoring[{opt}] missing axes: {sorted(missing_axes)}"
                )
            for axis, val in axes.items():
                if not isinstance(val, (int, float)):
                    errors.append(
                        f"{prefix}: scoring[{opt}][{axis}] must be numeric, got {type(val).__name__}"
                    )

    return errors


def validate_active(data: dict, valid_question_ids: set[str]) -> list[str]:
    errors = []
    active_ids = data.get("active_ids")

    if not isinstance(active_ids, list):
        return ["active.json: 'active_ids' must be a list"]

    for qid in active_ids:
        if qid not in valid_question_ids:
            errors.append(
                f"active.json: '{qid}' not found in questions.json"
            )

    if "updated_at" not in data:
        errors.append("active.json: missing 'updated_at' field")

    return errors


def validate_types(data: dict) -> list[str]:
    errors = []

    # Check axis_max
    axis_max = data.get("axis_max", {})
    if not isinstance(axis_max, dict):
        errors.append("types.json: 'axis_max' must be a dict")
    else:
        missing_axes = REQUIRED_AXES - set(axis_max.keys())
        if missing_axes:
            errors.append(
                f"types.json: axis_max missing axes: {sorted(missing_axes)}"
            )
        for axis, val in axis_max.items():
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(
                    f"types.json: axis_max[{axis}] must be a positive number"
                )

    # Check default_type
    if "default_type" not in data:
        errors.append("types.json: missing 'default_type'")

    # Check types list
    types = data.get("types")
    if not isinstance(types, list):
        return errors + ["types.json: 'types' must be a list"]

    seen_ids = set()
    default_type = data.get("default_type")
    found_default = False

    for i, t in enumerate(types):
        prefix = f"types[{i}] (id={t.get('id', '<missing>')})"

        missing_fields = REQUIRED_TYPE_FIELDS - set(t.keys())
        if missing_fields:
            errors.append(f"{prefix}: missing fields: {sorted(missing_fields)}")

        tid = t.get("id")
        if tid in seen_ids:
            errors.append(f"{prefix}: duplicate id '{tid}'")
        elif tid:
            seen_ids.add(tid)

        if tid == default_type:
            found_default = True
            if t.get("condition") is not None:
                errors.append(
                    f"{prefix}: default type must have condition=null"
                )

        # good_match and bad_match must be lists
        for field in ("good_match", "bad_match"):
            val = t.get(field)
            if val is not None and not isinstance(val, list):
                errors.append(f"{prefix}: '{field}' must be a list")

    if default_type and not found_default:
        errors.append(
            f"types.json: default_type '{default_type}' not found in types list"
        )

    return errors


def main() -> None:
    errors: list[str] = []

    # Load files
    try:
        questions_data = load_json("questions.json")
    except Exception as e:
        print(f"ERROR loading questions.json: {e}")
        sys.exit(1)

    try:
        active_data = load_json("active.json")
    except Exception as e:
        print(f"ERROR loading active.json: {e}")
        sys.exit(1)

    try:
        types_data = load_json("types.json")
    except Exception as e:
        print(f"ERROR loading types.json: {e}")
        sys.exit(1)

    # Validate
    errors += validate_questions(questions_data)

    valid_ids = {q["id"] for q in questions_data.get("questions", []) if "id" in q}
    errors += validate_active(active_data, valid_ids)
    errors += validate_types(types_data)

    if errors:
        print("Validation FAILED. Errors found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✅ All data valid")


if __name__ == "__main__":
    main()
