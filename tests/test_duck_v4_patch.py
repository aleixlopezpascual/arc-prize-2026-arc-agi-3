import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import py_compile

def test_dry_run_enhancements_v4():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v4/apply_enhancements_v4.py")
        assert patch_script.exists(), "apply_enhancements_v4.py must exist"

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Verify segmentation has is_border and compiles
        seg_file = dest_root / "inference/utils/segmentation.py"
        seg_code = seg_file.read_text()
        assert "is_border" in seg_code
        assert "centroid" in seg_code
        assert "bbox" in seg_code
        py_compile.compile(str(seg_file), doraise=True)

        # Verify python_tool_sandbox has candidate_clicks and object_at and solved_memory
        sandbox_file = dest_root / "inference/agent/python_tool_sandbox.py"
        sandbox_code = sandbox_file.read_text()
        assert "def candidate_clicks" in sandbox_code
        assert "def object_at" in sandbox_code
        assert "solved_memory" in sandbox_code
        py_compile.compile(str(sandbox_file), doraise=True)

        # Verify tool_agent records solved memory into runtime state WITHOUT prompt mutation
        agent_file = dest_root / "inference/agent/tool_agent.py"
        agent_code = agent_file.read_text()
        assert "_cleared_level_memories" in agent_code
        assert "Knowledge from cleared levels:" not in agent_code  # MUST NOT BE IN PROMPTS!
        py_compile.compile(str(agent_file), doraise=True)

        # Verify prompts.py documents candidate_clicks
        prompts_file = dest_root / "inference/agent/prompts.py"
        prompts_code = prompts_file.read_text()
        assert "candidate_clicks" in prompts_code
        assert "object_at" in prompts_code
        py_compile.compile(str(prompts_file), doraise=True)
