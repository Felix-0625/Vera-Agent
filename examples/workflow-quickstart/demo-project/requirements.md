# Login rate limiting (demo requirement)

This file is the input for the workflow quickstart. It is intentionally small so
a run finishes in a few model calls.

## Goal

Limit repeated failed sign-in attempts so that brute-force guessing becomes slow,
without locking out legitimate users permanently.

## Requirements

1. After 5 failed attempts for the same account within 15 minutes, further attempts
   for that account are rejected for 15 minutes.
2. A successful sign-in resets the failure counter.
3. The rejection message must not reveal whether the account exists.
4. Administrators can see how many accounts are currently throttled.

## Open questions

- Should throttling also apply per IP address?
- Where is the failure counter stored if the service restarts?
