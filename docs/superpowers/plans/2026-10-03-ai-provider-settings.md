# AI provider Settings extension

Authorized by the user's request to implement the reference modal and add Groq, following the approved admin RAG architecture.

## Design

Settings manages named, enabled provider connections with priority, URL, secret key and an explicit model allowlist. Native LangChain integrations serve Ollama, OpenAI, Anthropic, Gemini and Groq. Custom uses an OpenAI-compatible chat interface. The user clarified the scope to these six principal options. Google uses Gemini API-key authentication; Vertex IAM is outside this extension. Priority controls catalog ordering, never silent failover.

Backend owns connection metadata and immutable revisions. API keys are encrypted with a separate persistent Fernet key, never returned to public endpoints. SQLAlchemy Core expressions implement all new Python SQL. Cloud endpoints are fixed; local/custom endpoints require a server host allowlist. Queued runs pin a connection ID and revision, and only an authenticated internal run-context endpoint resolves the matching secret. A disabled or edited connection does not rewrite existing runs. Catalog is bounded and rebuilt per request; per-run registries avoid shared mutable credentials.

Models require tool calling and structured tool output; manually configured capabilities remain a deployment responsibility. Explicit input/output tariffs and effective date support existing cost estimates; zero rates must be deliberately entered. Existing environment models remain supported and visibly distinct from Settings connections.

## Execution

1. Extend validated contracts; add Groq dependency and native registry integration.
2. Add provider revisions migration and encrypted Core repository; test validation, redaction, updates and pinned revisions.
3. Add authenticated management routes, catalog composition and internal runtime resolution. Carry revision through chat/run request and audit view.
4. Implement accessible responsive Settings dialog matching the reference, with provider tiles, model chips, edit, enable/disable, errors and saving states.
5. Document deployment, quotas and provider setup; verify Python, browser and UI build without paid cloud calls.
