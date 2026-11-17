# Security policy

## Scope

This repository is an **internship prototype**. It is not an official airport system, it is not
deployed in production, and it comes with no support guarantee.

| Version | Supported |
| --- | --- |
| `main` (latest commit) | best effort |

In scope:

- the API (`backend/api_service/`): JWT validation, role checks, intent routing, rate limiting;
- the retrieval service (`rag_service/`): PDF ingestion, document upload and replacement;
- the frontend (`frontend/`) and the Keycloak realm and theme (`keycloak/`);
- any secret, personal data or third-party document published by mistake, including in history.

Out of scope: Keycloak, Chroma, the LLM providers and other dependencies (report to their
maintainers), and the known limits listed in the [README](README.md#limitations) (Keycloak in
`start-dev` mode over HTTP, in-process rate limit).

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting: **Security** tab, then
**Report a vulnerability**. Include the affected file or commit, steps to reproduce and the expected
impact. Do not paste a full secret value: its location is enough.

This is a personal project: replies are best effort, with no guaranteed delay.

## Notes for users

- Never commit a `.env` file; only the `*.env.example` templates are tracked.
- `AUTH_DISABLED` is for local development only and is forced to `false` in Compose.
- Only index documents you have the right to use; source documents and the vector index are not
  part of this repository (see [`rag_service/data/README.md`](rag_service/data/README.md)).
