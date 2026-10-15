import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import py_compile
from src.search.bfs_path import bfs_path

def test_bfs_path_straight_and_obstacles():
    path = bfs_path((0, 0), (0, 3))
    assert path == ["RIGHT", "RIGHT", "RIGHT"]

    path = bfs_path((0, 0), (2, 0), blocked={(1, 0)})
    assert path is not None
    assert len(path) == 4
    assert "DOWN" in path

    assert bfs_path((5, 5), (5, 5)) == []
    assert bfs_path((0, 0), (2, 0), blocked={(0, 1), (1, 0)}) is None
    assert bfs_path(None, (1, 1)) is None
    assert bfs_path((0, 0), None) is None

def test_dry_run_enhancements_v6():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v6/apply_enhancements_v6.py")
        assert patch_script.exists(), "apply_enhancements_v6.py must exist"

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Verify segmentation compiles and has is_border
        seg_file = dest_root / "inference/utils/segmentation.py"
        seg_code = seg_file.read_text()
        assert "is_border" in seg_code
        assert "centroid" in seg_code
        assert "bbox" in seg_code
        py_compile.compile(str(seg_file), doraise=True)

        # Verify python_tool_sandbox has bfs_path, candidate_clicks, object_at, solved_memory
        sandbox_file = dest_root / "inference/agent/python_tool_sandbox.py"
        sandbox_code = sandbox_file.read_text()
        assert "def bfs_path" in sandbox_code
        assert "def candidate_clicks" in sandbox_code
        assert "def object_at" in sandbox_code
        assert "solved_memory" in sandbox_code
        py_compile.compile(str(sandbox_file), doraise=True)

        # Verify tool_agent has null-safe current_frame_payload check and compiles
        agent_file = dest_root / "inference/agent/tool_agent.py"
        agent_code = agent_file.read_text()
        assert "if current_frame_payload is not None:" in agent_code
        assert "_cleared_level_memories" in agent_code
        py_compile.compile(str(agent_file), doraise=True)

        # Verify prompts.py documents bfs_path and candidate_clicks and compiles
        prompts_file = dest_root / "inference/agent/prompts.py"
        prompts_code = prompts_file.read_text()
        assert "bfs_path" in prompts_code
        assert "candidate_clicks" in prompts_code
        py_compile.compile(str(prompts_file), doraise=True)
