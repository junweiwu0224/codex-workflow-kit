"""V4.2 evaluation and lifecycle primitives.

The package deliberately has no network or Codex dependency.  Real runners
are supplied through :class:`eval.harness.RunnerAdapter`; the bundled fixture
runner exists only to exercise the harness contract in CI.
"""

from .harness import BlackBoxEvalHarness, EvalHarness, EvalError, FixtureRunner, ShadowRunner, SubprocessRunner, load_suite
from .codex_runner import (
    CodexProvider,
    CodexSubprocessRunner,
    CommandIsolationVerifier,
    IsolationRequest,
    MacOSSandboxExecLauncher,
)
from .lifecycle import CanaryScope, ComponentRecord, LifecycleManager, LifecycleError, LifecycleState, LifecycleStatus
from .resolver import resolve_catalog

__all__ = [
    "EvalHarness",
    "BlackBoxEvalHarness",
    "EvalError",
    "FixtureRunner",
    "ShadowRunner",
    "SubprocessRunner",
    "CodexProvider",
    "CodexSubprocessRunner",
    "CommandIsolationVerifier",
    "IsolationRequest",
    "MacOSSandboxExecLauncher",
    "LifecycleError",
    "LifecycleManager",
    "LifecycleState",
    "LifecycleStatus",
    "CanaryScope",
    "ComponentRecord",
    "load_suite",
    "resolve_catalog",
]
