# Workflow Storage Decision Constraints

The workflow records approvals, retries, rollbacks, and releases. Operators
must be able to reconstruct the history of a task after a disputed change.
Concurrent writers may add independent events, but historical records must not
be overwritten. The primary option is an append-only event log; the rejected
alternative is a mutable status row that only stores current state.
