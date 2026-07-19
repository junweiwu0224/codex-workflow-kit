# Payment Callback Completion Requirements

The callback endpoint is not ready to ship until all of the following are
demonstrably complete:

1. It rejects a callback whose HMAC signature cannot be verified before any
   event is processed.
2. It rejects callback URLs outside the configured provider allowlist.
3. It prevents replay of an already processed provider event identifier.
4. The completion review cites test evidence for each rejection path and does
   not claim success when evidence is absent.
