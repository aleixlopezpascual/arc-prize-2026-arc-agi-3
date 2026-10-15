import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import py_compile

def test_dry_run_enhancements_v7():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v7/apply_enhancements_v7.py")
        assert patch_script.exists(), "apply_enhancements_v7.py must exist"

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # 1. Verify fable_layer_core.py was written and compiles
        fable_core = dest_root / "inference/agent/fable_layer_core.py"
        assert fable_core.exists()
        py_compile.compile(str(fable_core), doraise=True)

        # 2. Verify segmentation compiles and has is_border
        seg_file = dest_root / "inference/utils/segmentation.py"
        seg_code = seg_file.read_text()
        assert "is_border" in seg_code
        assert "centroid" in seg_code
        assert "bbox" in seg_code
        py_compile.compile(str(seg_file), doraise=True)

        # 3. Verify python_tool_sandbox compiles and has bfs_path, candidate_clicks, object_at
        sandbox_file = dest_root / "inference/agent/python_tool_sandbox.py"
        sandbox_code = sandbox_file.read_text()
        assert "def bfs_path" in sandbox_code
        assert "def candidate_clicks" in sandbox_code
        assert "def object_at" in sandbox_code
        assert "solved_memory" in sandbox_code
        py_compile.compile(str(sandbox_file), doraise=True)

        # 4. Verify tool_agent compiles and has Fable layer methods + null safety
        agent_file = dest_root / "inference/agent/tool_agent.py"
        agent_code = agent_file.read_text()
        assert "ARC3_FABLE_LAYER" in agent_code
        assert "_fl_opener_lines" in agent_code
        assert "if current_frame_payload is not None:" in agent_code
        py_compile.compile(str(agent_file), doraise=True)
