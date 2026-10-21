"""Repository entry point; the distributable skill contains the same executable core."""
import runpy
from pathlib import Path

if __name__=='__main__':
    runpy.run_path(str(Path(__file__).parent/'skills/jianying-codex-toolkit/scripts/editkit.py'),run_name='__main__')
