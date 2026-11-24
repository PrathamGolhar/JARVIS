# JARVIS Engineering Instructions

JARVIS is a modular, general-purpose personal AI assistant. Preserve its local-first/hybrid operation and provider abstraction. Treat source and tests as evidence; product claims and documentation do not prove a capability.

## Engineering principles
- Keep JARVIS interactions and user-facing outputs in English.
- Prefer minimal, modular changes; avoid mass rewrites and unnecessary dependencies.
- Preserve existing behavior and interfaces unless the task requires a change.
- Never weaken security, authentication, authorization, permission, or confirmation boundaries. Sensitive actions require appropriate approval.
- Avoid silent fallbacks and success-shaped responses; surface errors using established patterns.

## Investigation
- Trace the actual execution path before describing or changing behavior.
- Inspect relevant source, configuration, and tests. Use targeted searches and direct reads; avoid unrelated repository material.
- Distinguish verified behavior from intended, documented, or untested behavior. Do not invent capabilities or implementation status.

## Implementation and verification
- Make the smallest effective change and follow local patterns.
- Run the smallest relevant existing tests and checks. Report exact commands and observed results; identify untested behavior. Never claim success without evidence.
- Update directly related documentation when behavior or setup changes materially.

## Documentation
- Use README.md as the project entry point; ARCHITECTURE.md for an overview; API.md and SECURITY.md for their respective domains.
- Verify documentation against source and tests. Treat historical audits, plans, and backlogs as evidence of past state, not current truth.
