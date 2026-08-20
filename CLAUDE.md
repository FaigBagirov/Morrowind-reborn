# Morrowind Sci-Fi Conversion

Docs: docs/ — Architecture (method), Canon (setting).
Read both before proposing changes.

Game: OpenMW 0.51, clean vanilla dev profile.
Mod files go in mod/. Scripts and reports go in tools/.

## Rules
- Never modify record IDs, RefIds, script bodies, or script variable names.
- Only modify display fields: names, descriptions, book text, dialogue
  responses, journal entries, GMST strings.
- Never edit Morrowind.esm, Tribunal.esm, or Bloodmoon.esm.
- All replacement text must be plain ASCII (bytes 0x00-0x7F only).
- Replacement strings must not be longer than the string they replace.
- Do not perform substitutions yourself. Write a deterministic transform
  script plus a rules table; the script performs all substitutions.
- Never modify DIAL topic IDs, general dialogue response text, greetings,
  or journal entries. Only uniquely-filtered INFO records may be rewritten.
- When rewriting an INFO record, keep at least one literal instance of the
  original topic keyword so the hyperlink still fires. Report before/after
  keyword counts for every record touched.
- Do not generate or edit NIF files.
- One system per change set. Report the diff summary before applying.

## Paths
- ESM masters: tools/input/ (copies — the real game folder is off limits)
- Mod output: mod/  (loaded by OpenMW dev profile)
- Reports: tools/reports/
- Game logs: logs/  (user copies openmw.log here after each run)
- Claude Code never launches the game. The user runs it and brings the log.