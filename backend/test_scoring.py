"""
Tests for scoring.py

Run:
    cd backend && source .venv/bin/activate && python test_scoring.py
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

# Ensure the backend directory is on the path
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Patch DB_PATH to a temp file so tests don't pollute the real database
# ---------------------------------------------------------------------------
import scoring as _scoring_module

_tmp_dir = tempfile.mkdtemp()
_scoring_module.DB_PATH = Path(_tmp_dir) / "test_results.db"

from scoring import (
    calculate_scores,
    determine_type,
    get_axis_averages,
    get_result,
    init_db,
    save_result,
)

init_db()

PASS = "PASS"
FAIL = "FAIL"
_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [{PASS}] {name}")
    else:
        msg = f"  [{FAIL}] {name}" + (f" — {detail}" if detail else "")
        print(msg)
        _failures.append(name)


# ---------------------------------------------------------------------------
# Test 1: calculate_scores with known answers
# ---------------------------------------------------------------------------
print("\n--- Test 1: calculate_scores ---")

# All A answers
# q001 A: {independence:3, social:-1, curiosity:1, action:-1}
# q002 A: {independence:2, social:-1, curiosity:3, action:-1}
# q003 A: {independence:-1, social:3, curiosity:0, action:1}
# q004 A: {independence:2, social:-1, curiosity:0, action:2}
# q005 A: {independence:2, social:-1, curiosity:3, action:-1}
# Raw: independence=3+2-1+2+2=8, social=-1-1+3-1-1=-1, curiosity=1+3+0+0+3=7, action=-1-1+1+2-1=0
# axis_max = 15 for all
# independence = round(8/15*100)=53, social = round(-1/15*100)=round(-6.67)=-7 → clamp 0
# curiosity = round(7/15*100)=round(46.67)=47, action = round(0/15*100)=0
all_A_scores = calculate_scores(["A", "A", "A", "A", "A"])
check("all-A independence=53", all_A_scores["independence"] == 53, str(all_A_scores))
check("all-A social clamped to 0", all_A_scores["social"] == 0, str(all_A_scores))
check("all-A curiosity=47", all_A_scores["curiosity"] == 47, str(all_A_scores))
check("all-A action=0", all_A_scores["action"] == 0, str(all_A_scores))

# All D answers
# q001 D: {independence:-1, social:3, curiosity:0, action:1}
# q002 D: {independence:1, social:-1, curiosity:0, action:3}
# q003 D: {independence:2, social:-2, curiosity:1, action:0}
# q004 D: {independence:1, social:-1, curiosity:0, action:3}
# q005 D: {independence:1, social:0, curiosity:1, action:2}
# Raw: independence=-1+1+2+1+1=4, social=3-1-2-1+0=-1, curiosity=0+0+1+0+1=2, action=1+3+0+3+2=9
# independence=round(4/15*100)=27, social=clamp(0), curiosity=round(2/15*100)=13, action=round(9/15*100)=60
all_D_scores = calculate_scores(["D", "D", "D", "D", "D"])
check("all-D independence=27", all_D_scores["independence"] == 27, str(all_D_scores))
check("all-D social clamped to 0", all_D_scores["social"] == 0, str(all_D_scores))
check("all-D curiosity=13", all_D_scores["curiosity"] == 13, str(all_D_scores))
check("all-D action=60", all_D_scores["action"] == 60, str(all_D_scores))

# With None answer (skipped)
partial_scores = calculate_scores(["A", None, None, None, None])
check("partial answers returns dict with all axes", set(partial_scores.keys()) == {"independence", "social", "curiosity", "action"}, str(partial_scores))

# All None answers — all zeros
none_scores = calculate_scores([None, None, None, None, None])
check("all-None scores all zero", all(v == 0 for v in none_scores.values()), str(none_scores))

# ---------------------------------------------------------------------------
# Test 2: determine_type — each of the 4 types
# ---------------------------------------------------------------------------
print("\n--- Test 2: determine_type ---")

# explorer: curiosity > 60 AND social < 50
explorer_scores = {"independence": 50, "social": 30, "curiosity": 70, "action": 50}
t = determine_type(explorer_scores)
check("explorer type matched", t["id"] == "explorer", f"got {t['id']}")

# connector: social > 60
connector_scores = {"independence": 50, "social": 70, "curiosity": 50, "action": 50}
t = determine_type(connector_scores)
check("connector type matched", t["id"] == "connector", f"got {t['id']}")

# achiever: action > 60 (and social not > 60 to avoid connector matching first)
achiever_scores = {"independence": 50, "social": 50, "curiosity": 50, "action": 70}
t = determine_type(achiever_scores)
check("achiever type matched", t["id"] == "achiever", f"got {t['id']}")

# balanced: no strong axis
balanced_scores = {"independence": 50, "social": 50, "curiosity": 50, "action": 50}
t = determine_type(balanced_scores)
check("balanced fallback matched", t["id"] == "balanced", f"got {t['id']}")

# Edge: high curiosity but social >= 50 → not explorer → check connector/achiever/balanced
edge_scores = {"independence": 50, "social": 50, "curiosity": 80, "action": 50}
t = determine_type(edge_scores)
check("high curiosity but social=50 not explorer", t["id"] != "explorer", f"got {t['id']}")

# connector takes priority over achiever when social > 60 AND action > 60
both_scores = {"independence": 50, "social": 70, "curiosity": 50, "action": 70}
t = determine_type(both_scores)
check("connector before achiever (order matters)", t["id"] == "connector", f"got {t['id']}")

# ---------------------------------------------------------------------------
# Test 3: save_result + get_result roundtrip
# ---------------------------------------------------------------------------
print("\n--- Test 3: save_result + get_result roundtrip ---")

rid = "test-result-001"
answers = ["A", "B", "C", "D", "A"]
scores = {"independence": 60, "social": 40, "curiosity": 55, "action": 45}
type_id = "explorer"

save_result(rid, answers, scores, type_id)
sr = get_result(rid)

check("result not None", sr is not None)
check("result_id matches", sr.result_id == rid)
check("type_id matches", sr.type_id == type_id)
check("type_name populated", len(sr.type_name) > 0, sr.type_name)
check("description populated", len(sr.description) > 0)
check("one_liner populated", len(sr.one_liner) > 0)
check("good_match is list", isinstance(sr.good_match, list))
check("bad_match is list", isinstance(sr.bad_match, list))
check("footer_question populated", len(sr.footer_question) > 0)
check("scores match", sr.scores == scores, str(sr.scores))
check("raw_answers match", sr.raw_answers == answers, str(sr.raw_answers))
check("questions is list of 5", isinstance(sr.questions, list) and len(sr.questions) == 5, str(len(sr.questions)))
check("axis_comparisons has all axes", set(sr.axis_comparisons.keys()) == set(scores.keys()), str(sr.axis_comparisons))

# Not-found returns None
missing = get_result("nonexistent-id-xyz")
check("missing result returns None", missing is None)

# ---------------------------------------------------------------------------
# Test 4: get_axis_averages with multiple stored results
# ---------------------------------------------------------------------------
print("\n--- Test 4: get_axis_averages ---")

# Save two more results
save_result(
    "test-result-002",
    ["B", "B", "B", "B", "B"],
    {"independence": 40, "social": 60, "curiosity": 35, "action": 55},
    "connector",
)
save_result(
    "test-result-003",
    ["C", "C", "C", "C", "C"],
    {"independence": 50, "social": 50, "curiosity": 50, "action": 50},
    "balanced",
)

avgs = get_axis_averages()
check("averages has all axes", set(avgs.keys()) == {"independence", "social", "curiosity", "action"}, str(avgs))

# 3 results: independence = [60, 40, 50] → avg = 50.0
expected_indep = (60 + 40 + 50) / 3
check(
    f"independence avg ≈ {expected_indep:.2f}",
    abs(avgs["independence"] - expected_indep) < 0.01,
    f"got {avgs['independence']}",
)

# social = [40, 60, 50] → avg = 50.0
expected_social = (40 + 60 + 50) / 3
check(
    f"social avg ≈ {expected_social:.2f}",
    abs(avgs["social"] - expected_social) < 0.01,
    f"got {avgs['social']}",
)

# Axis comparison for test-result-001 (independence=60, avg=50): diff = +10
sr_updated = get_result(rid)
check(
    "axis_comparison independence=+10",
    sr_updated.axis_comparisons["independence"] == 10,
    str(sr_updated.axis_comparisons),
)
check(
    "axis_comparison social=-10",
    sr_updated.axis_comparisons["social"] == -10,
    str(sr_updated.axis_comparisons),
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"RESULT: {len(_failures)} test(s) FAILED: {', '.join(_failures)}")
    sys.exit(1)
else:
    print("RESULT: All tests PASSED")
