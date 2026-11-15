"""Shared setup for the tests: make the repo's modules importable from tests/."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "tools")):
    if p not in sys.path: sys.path.insert(0, p)
