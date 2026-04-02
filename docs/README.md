# NetCloud Manager API Documentation

This directory contains consolidated documentation for the Cradlepoint NetCloud Manager (NCM) API.
It is maintained by both humans and AI through a reflexion workflow — when the AI discovers
new patterns, corrections, or best practices while building applications, it updates these docs
and the steering rules automatically.

## Structure

- `api-overview.md` — API basics, authentication, base URLs, rate limiting
- `api-v2-endpoints.md` — All v2 endpoint reference with fields, filters, methods
- `api-v3-endpoints.md` — All v3 endpoint reference (JSON:API format)
- `api-configuration.md` — Device and group configuration via API (diffs, PUT/PATCH, _id_ fields)
- `api-webhooks.md` — Webhook setup, alert push destinations, payload examples
- `api-deprecations.md` — Deprecated endpoints and fields with dates
- `ncm-sdk-reference.md` — Python NCM SDK usage patterns and method reference
- `common-patterns.md` — Reusable code patterns, error handling, pagination
- `known-issues.md` — Discovered issues, gotchas, and workarounds (AI-maintained)
- `CHANGELOG.md` — Log of documentation updates made by the reflexion system

## Source

Primary source: [https://developer.cradlepoint.com/documentation](https://developer.cradlepoint.com/documentation)
