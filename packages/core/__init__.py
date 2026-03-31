# Compatibility shim — allows 'from packages.core.X' imports to work
# while core's source lives at packages/core/core/X.
# Remove this when all packages are restructured.

import importlib
import sys
import os

# Add packages/core to sys.path so 'from core.X' works for core's internal imports
_core_dir = os.path.dirname(__file__)
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)

# Re-export submodules so 'from packages.core.schemas' etc still work
from core import schemas, terraform, dag, registry, validation, iam_mappings, auto_provision  # noqa: F401, E402
