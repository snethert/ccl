"""Use the qualified class graph; namespace prerequisites initialize on target."""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def source():
    return (HERE.parent/'ready/graph.lisp').read_text()
