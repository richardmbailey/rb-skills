"""Shared typed runtime for the RB constrained execution skills."""

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0"

# Install first-release verification-mode enforcement before workflow imports bind
# deterministic_assessment_findings from the policy module.
from .verification import install_policy_guard as _install_policy_guard

_install_policy_guard()
del _install_policy_guard
