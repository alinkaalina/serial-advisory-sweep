# Security Model

## Threat Mitigation

- **Commit-Pinned Fetch Restriction**: `record_bulletin` enforces a strict regular expression requiring a 40-character hexadecimal Git commit SHA and verifies the SHA-256 digest of the raw response bytes before parsing.
- **Prompt Injection Containment**: External bulletin text is serialized inside a structured JSON envelope and evaluated under strict non-instruction rules. Any ambiguity or out-of-spec formatting triggers an `UNRESOLVED` state or transaction abort.
- **Evidence Grounding**: Both leader and validator executions verify that the extracted `evidence` field is an exact verbatim substring of the source document text (`10..500` characters), while requiring exact equality on the extracted interval coverage structure.
- 
