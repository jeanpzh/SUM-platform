# PDF ingestion dashboard concepts

Design exploration for administrative staff of the proposed SUM academic assistant (FISI / UNMSM). Generated with Product Design ideation and built-in Image Gen, grounded in [DESIGN.md](../../DESIGN.md), [ARQUITECTURA.md](../../ARQUITECTURA.md), and [service separation](../../docs/separacion-servicios.md).

## Scope

Three independent horizontal alternatives of one focused dashboard screen, 1440 × 1024 target. Mock operational data, anchored to 2026-10-02. These are visual references, not a working upload system.

The documentation identifies administrators as people and indexer workers as background processes. No separate human worker permissions are specified.

## Responsive behavior for implementation

- At 1024px and above: 256px sidebar; fluid main workspace. Upload workbench and job/detail columns fit within remaining width.
- At 768–1023px: compact navigation; upload, source metadata, and processing details stack in reading order.
- Below 768px: menu replaces sidebar; full-width single column with 16px horizontal padding and 24px gaps. File picker precedes metadata and jobs. Tables become readable grouped rows; no page-wide horizontal overflow.
- File selection works by keyboard and touch as well as drag-and-drop. Touch controls are at least 44px high, primary action 48px.
- Use visible focus states, text plus color for job status, labeled inputs and an announced processing status. Reduced motion disables entry choreography.

## Workflow fidelity

Register PDF and its source/version/applicability, enqueue processing, extract text, index, validate, and publish a complete version. Upload success and published status are distinct. A failed job preserves the previous published version. Human-facing progress uses readable stage names. No undocumented upload-size limits, approval permissions, automatic normative-validity claims, or manual publication controls are introduced.

## Visual direction

Keep DESIGN.md's warm neutrals, terracotta actions, sparse amber attention, Playfair Display headings, Source Sans 3 interface text, and sidebar identity. Premium craft comes from hierarchy, spacing, restrained depth, light icons, and useful document previews. Existing design-system radii take precedence over generic large-radius skill defaults. Primary CTA count stays one per view.

Desktop reference images indicate responsive intent. The implementation has now been inspected with Playwright MCP at desktop and mobile widths; see [design-qa.md](../design-qa.md).

## Selected implementation

Option 1 is implemented at the root route of the existing React 19, TanStack Start, Tailwind CSS 4 app in `../src/routes/index.tsx`. It uses the repository's shadcn components, React Hook Form, the installed Zod 4 schema, and focused hooks for PDF file selection and indexing job state. Bulk file submission, job monitoring, cancellation, and retry now call the current ingestion backend through a server proxy. Each PDF receives an independent job. The library and retrieval views remain local samples; see [the application README](../README.md).

## Visual QA notes

These are generated concept images, not exact font or brand assets. Mesa de ingesta uses more serif UI text than specified and includes a generated crest; use the documented sans-serif UI and approved wordmark when implementing. Registro de fuentes includes a blue processing marker and a terracotta wordmark; implementation should use the documented warm palette and neutral wordmark. Document thumbnails, metadata, job times and page counts are illustrative, not verified source evidence.
