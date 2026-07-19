# Release Notification Requirements

Add a release-notification workflow with these constraints:

1. Only an authorized release transition may enqueue a notification.
2. Notifications may target only configured destination hosts.
3. Retries must be idempotent for the same release identifier.
4. The change is not a request to implement code. It needs an approved-style
   proposal, executable task breakdown, and explicit acceptance criteria.
