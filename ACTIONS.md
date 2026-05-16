# PlaudNotes — Open Actions

## Open

| # | Actie | Status | Bron | Eigenaar |
|---|---|---|---|---|
| 1 | Vraag 2 + 3 uit research-sessie definitief beantwoorden aan gebruiker (upload-MCP + retrigger-transcriptie) | pending | `prompts/2026-05-17_plaud_mcp_upload_retrigger_research.md` | Claude (volgende sessie) |
| 2 | Gebruikersakkoord ontvangen op 4 scope-vragen (tools-set, file_type detectie, chunk-size, branch-strategie) | pending | sessie-MD | Gebruiker |
| 3 | Implementeren `upload_recording()` in `plaud_client.py` (4-staps multipart presigned-S3 flow) | pending | sessie-MD §Reverse-engineering | Claude (na akkoord) |
| 4 | Implementeren `retry_transcription()` in `plaud_client.py` (POST `/ai/polish-transcation` met `force_failed`) | pending | sessie-MD §Reverse-engineering | Claude (na akkoord) |
| 5 | Eventueel `get_task_status()` als 3e tool | scope-vraag | sessie-MD | Gebruiker beslist |
| 6 | Branch `feat/upload-and-retrigger` aanmaken, MCP-tools registreren in `server.py`, README updaten, PR | pending | sessie-MD | Claude (na akkoord) |

## Geparkeerd

| # | Actie | Status | Bron | Reden parkeren |
|---|---|---|---|---|
| P1 | Bluetooth-download Mac/Windows ↔ NotePin (BLE reverse engineering) | parked | sessie-MD §A | 3-7 dagen werk + brittle; USB-C alternatief triviaal |
| P2 | Hybride: MCP-tool `import_from_notepin(volume_path)` die USB-mount detecteert en via upload-flow naar cloud upload | parked | sessie-MD §A | Pas overwegen ná upload-flow werkt |

## Klaar

(leeg)
