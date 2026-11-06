import shutil
import subprocess
from pathlib import Path

import pytest

TESTS = Path(__file__).parent


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
@pytest.mark.parametrize("test_file", ["reader.test.mjs", "selection.test.mjs"])
def test_the_javascript_helpers(test_file):
    result = subprocess.run(["node", "--test", str(TESTS / test_file)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
