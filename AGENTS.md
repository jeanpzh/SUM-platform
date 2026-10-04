# Repository instructions

## Python database access

Write Python database queries with SQLAlchemy ORM or Core expressions (or an equivalent query builder). Use typed tables/models and `select`, `insert`, `update`, `delete`, joins and bound expressions. Do not write raw SQL strings in Python or route them through the legacy SQLAlchemy adapter. Schema migrations may remain SQL files. When changing a query, migrate the affected query to expressions; avoid unrelated rewrites.

## CodeGraph

When `.codegraph/` exists at the repository root, use `codegraph explore` (or the CodeGraph MCP tool) before grep/find or reading files to locate or understand code. Do not create an index without the user's instruction.

## Context7

Fetch current library, framework, SDK, API, CLI and cloud-service documentation with Context7. Start with `resolve-library-id`, choose the best matching library, then `query-docs` scoped to the relevant concept. This includes API syntax, configuration, migrations and library-specific debugging. Prefer it over web search for library documentation. General programming, business logic debugging, scripts and code review do not require Context7.
