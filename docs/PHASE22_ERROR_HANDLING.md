# Phase 22 — API Error Response Hardening

## Goal

Make unexpected API failures observable and safe at the HTTP boundary.

## Behavior

The request logging middleware now catches unexpected exceptions, logs them as HTTP 500 requests, and returns a generic JSON response containing the request ID.

Example shape:

```json
{
  "detail": "Internal server error",
  "request_id": "..."
}
```

The response also includes the same value in `X-Request-ID`.

## Why

Previously, an unexpected exception was logged but re-raised before the middleware could attach its request ID to the response. That made it harder to correlate a user's 500 error with the server log.

The response intentionally does not expose the underlying exception message, which can contain implementation details or sensitive information.

Expected application errors such as normal FastAPI `HTTPException` responses continue through the existing API handling path.
