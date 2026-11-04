import py_compile
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.search.bfs_path import bfs_path


def test_bfs_path_straight_and_obstacles():
    # Straight line
    path = bfs_path((0, 0), (0, 3))
    assert path == ["RIGHT", "RIGHT", "RIGHT"]

    # Simple obstacle
    path = bfs_path((0, 0), (2, 0), blocked={(1, 0)})
    assert path is not None
    assert len(path) == 4  # e.g. RIGHT, DOWN, DOWN, LEFT
    assert "DOWN" in path

    # Already at goal
    assert bfs_path((5, 5), (5, 5)) == []

    # Unreachable goal
    assert bfs_path((0, 0), (2, 0), blocked={(0, 1), (1, 0)}) is None

    # Invalid input
    assert bfs_path(None, (1, 1)) is None
    assert bfs_path((0, 0), None) is None

def test_bfs_path_step_distance():
    # Step 2 grid
    path = bfs_path((0, 0), (0, 4), step=2)
    assert path == ["RIGHT", "RIGHT"]

def test_dry_run_enhancements_v5():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v5/apply_enhancements_v5.py")
        assert patch_script.exists(), "apply_enhancements_v5.py must exist"

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Verify segmentation compiles
        seg_file = dest_root / "inference/utils/segmentation.py"
        py_compile.compile(str(seg_file), doraise=True)

        # Verify python_tool_sandbox has bfs_path and compiles
        sandbox_file = dest_root / "inference/agent/python_tool_sandbox.py"
        sandbox_code = sandbox_file.read_text()
        assert "def bfs_path" in sandbox_code
        assert "def candidate_clicks" in sandbox_code
        py_compile.compile(str(sandbox_file), doraise=True)

        # Verify tool_agent has null-safe current_frame_payload check and compiles
        agent_file = dest_root / "inference/agent/tool_agent.py"
        agent_code = agent_file.read_text()
        assert "if current_frame_payload is not None:" in agent_code
        assert "solved_memory" in agent_code
        py_compile.compile(str(agent_file), doraise=True)

        # Verify prompts.py documents bfs_path and compiles
        prompts_file = dest_root / "inference/agent/prompts.py"
        prompts_code = prompts_file.read_text()
        assert "bfs_path" in prompts_code
        py_compile.compile(str(prompts_file), doraise=True)
