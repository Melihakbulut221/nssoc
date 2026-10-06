"""Recheck only saved native positives; no HDL rerun here."""
from pathlib import Path
import runpy
def test_saved_selected_positive_canonical_schema():
    runpy.run_path(str(Path(__file__).resolve().parent/'read_targeted_positive02.py'),run_name='__main__')
