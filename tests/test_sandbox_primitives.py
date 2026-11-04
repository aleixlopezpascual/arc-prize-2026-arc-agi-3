from src.perception.sandbox_primitives import (
    candidate_clicks,
    candidate_goals,
    detect_budget_helper,
    detect_indicators,
    object_at,
)


def test_candidate_clicks_filtering():
  nodes = [
      {
          "id": 0,
          "color": "B",
          "pixels": 10,
          "centroid": [0, 5],
          "bbox": [0, 0, 0, 9],
          "is_border": True,
      },
      {
          "id": 1,
          "color": "R",
          "pixels": 4,
          "centroid": [5, 5],
          "bbox": [4, 4, 5, 5],
          "is_border": False,
      },
      {
          "id": 2,
          "color": "G",
          "pixels": 1,
          "centroid": [2, 2],
          "bbox": [2, 2, 2, 2],
          "is_border": False,
      },
  ]
  # By default, exclude_border drops B
  targets = candidate_clicks(nodes)
  assert len(targets) == 2
  assert targets[0]["id"] == 1
  assert targets[1]["id"] == 2

  # Filter by color
  r_targets = candidate_clicks(nodes, color="R")
  assert len(r_targets) == 1
  assert r_targets[0]["color"] == "R"

  # Filter by min_size
  large_targets = candidate_clicks(nodes, min_size=2)
  assert len(large_targets) == 1
  assert large_targets[0]["pixels"] == 4


def test_candidate_goals():
  nodes = [
      {
          "id": 0,
          "color": "B",
          "pixels": 50,
          "centroid": [0, 0],
          "bbox": [0, 0, 10, 5],
          "is_border": True,
      },  # border
      {
          "id": 1,
          "color": "W",
          "pixels": 20,
          "centroid": [10, 10],
          "bbox": [10, 10, 15, 15],
          "is_border": False,
      },  # large common
      {
          "id": 2,
          "color": "W",
          "pixels": 20,
          "centroid": [20, 20],
          "bbox": [20, 20, 25, 25],
          "is_border": False,
      },  # large common
      {
          "id": 3,
          "color": "Y",
          "pixels": 1,
          "centroid": [30, 30],
          "bbox": [30, 30, 30, 30],
          "is_border": False,
      },  # unique color, 1 pixel target!
      {
          "id": 4,
          "color": "R",
          "pixels": 4,
          "centroid": [40, 40],
          "bbox": [40, 40, 41, 41],
          "is_border": False,
      },  # rare color, 2x2 socket
  ]
  goals = candidate_goals(nodes)
  assert len(goals) == 4
  # Yellow single pixel should be top ranked goal
  assert goals[0]["id"] == 3
  assert goals[0]["color"] == "Y"
  assert goals[0]["pixels"] == 1
  assert goals[0]["goal_score"] > goals[1]["goal_score"]
  # Rare red 2x2 socket should be ranked second
  assert goals[1]["id"] == 4
  assert goals[1]["color"] == "R"


def test_object_at_lookup():
  nodes = [
      {
          "id": 1,
          "color": "R",
          "pixels": 4,
          "bbox": [4, 4, 5, 5],
          "is_border": False,
      },
  ]
  assert object_at(nodes, 4, 4)["id"] == 1
  assert object_at(nodes, 5, 5)["id"] == 1
  assert object_at(nodes, 6, 6) is None
  assert object_at(nodes, -1, 0) is None


def test_primitives_empty_or_none():
  assert candidate_clicks(None) == []
  assert candidate_clicks([]) == []
  assert candidate_goals(None) == []
  assert candidate_goals([]) == []
  assert object_at(None, 0, 0) is None
  assert object_at([], 0, 0) is None


def test_sandbox_diagnostic_helpers_safe_empty():
  assert detect_indicators(None, None) == []
  assert detect_budget_helper([]) is None


def test_sandbox_detect_indicators():
  before = [[0] * 64 for _ in range(64)]
  after = [[0] * 64 for _ in range(64)]
  # Main moving cluster
  for r in range(20, 25):
    for c in range(20, 25):
      before[r][c] = 1
      after[r][c + 1] = 1
  # Distant indicator
  for r in range(5, 7):
    for c in range(5, 7):
      before[r][c] = 2
      after[r][c] = 3

  res = detect_indicators(before, after)
  assert len(res) == 1
  assert res[0]["size"] == 4


def test_solve_toggle_exact():
  from src.perception.sandbox_primitives import solve_toggle
  # Button 0 toggles cell 0 (mask 1)
  # Button 1 toggles cells 0 and 1 (mask 3)
  # Button 2 toggles cell 1 (mask 2)
  # Target: turn on cell 1 only (target 2)
  res = solve_toggle([1, 3, 2], target=2)
  assert res["solvable"] is True
  assert res["indices"] == [2] or len(res["indices"]) == 1
  assert res["clicks"] == 1
  assert res["minimal"] is True


def test_solve_toggle_unsolvable():
  from src.perception.sandbox_primitives import solve_toggle
  # Parity conflict: only even bits togglable, odd bit required
  res = solve_toggle([2, 4], target=1)
  assert res["solvable"] is False
  assert res["indices"] is None

