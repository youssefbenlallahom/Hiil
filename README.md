# Dossier TN / Hiil

A local compliance workspace for preparing a company address-change dossier. Next.js provides the French interface; FastAPI stores dossiers and uploaded files locally, checks information, prepares downloads and optionally uses Azure OpenAI for document extraction and explanations.

## Run on another computer

Requirements: Node.js 22 and Python 3.12 (the versions used for validation).

```powershell
git clone https://github.com/youssefbenlallahom/Hiil.git
cd Hiil
npm ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
npm run dev
```

Open http://127.0.0.1:3000. `npm run dev` starts both the frontend on port 3000 and the API on port 8000. Keep the terminal running; use Ctrl+C to stop. These ports must be available.

On macOS/Linux, use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r backend/requirements.txt`, and `cp .env.example .env`; the same npm commands work.

An Azure key is **optional** for the manual workflow. The first launch creates a clearly labelled fictional Atlas Studio dossier with conflicting proposed addresses. New dossiers are empty; no extracted facts are fabricated.

## Available workflow

1. **Dashboard:** choose a company dossier, see its documents and unresolved points, or start a new address-change request.
2. **Documents:** upload PDF, PNG, JPEG or UTF-8 TXT (12 MB, 12 pages, up to 12 documents). Open a piece to review its text and original file. Enter or correct fields with a page number and source passage, then save the manual review. If a page has extracted text, its source passage must appear there; scanned-page transcription is explicitly a human review. A document with no useful fields can be marked as reviewed with an empty field list.
3. **Verification:** inspect all prepared fields, open their source pieces and resolve conflicts or missing information. Company name, identifier, current address and proposed address are the minimum fields for this draft, not a legally verified checklist. A directly declared value is distinguished from document evidence. Any new upload, extraction or manual document review clears previous dossier confirmations.
4. **Preparation:** download a printable HTML preparation sheet or a ZIP with the sheet, summary, JSON and original pieces. Conflicting values are flagged rather than silently selected. The sheet is a draft, not a completed official RNE F 005 form. Use the browser's Print menu to print the downloaded sheet or save it as PDF.
5. **Agency review:** transmit the dossier into the local officer queue. The simulated officer can request corrections with an observation, or mark the review complete. Documents are locked during review. Correction requests remain visible in the business workspace; a response must be recorded before resubmission, and the exchange stays in the history.

The assistant appears on the dashboard and is available from the help button on other screens. Without Azure it gives explicitly labelled workflow guidance based on dossier state. With Azure it answers using the dossier and the small configured source corpus.

## Optional Azure configuration

Edit `.env` locally, then restart the backend:

- `AZURE_OPENAI_BASE_URL`: HTTPS endpoint ending in `/openai/v1/`.
- `AZURE_OPENAI_API_KEY`: the resource key.
- `AZURE_OPENAI_CHAT_DEPLOYMENT`: your deployment name, supporting structured responses; scanned documents also need vision unless OCR is configured.
- Optionally set the two Azure Document Intelligence variables for scanned-page OCR.

Automated analysis sends document content to the configured Azure resource. Assistant requests send the question and relevant dossier facts. Manual review works locally without those services. Never commit `.env`, keys, uploads or real company data.

## Validation

```powershell
npm run typecheck
npm run build
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

For separate servers:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
npm run dev:web
```

After `npm run build`, `npm start` serves the production frontend and still requires the backend to be running separately.

## Data and handoff

The SQLite database and uploads live in `.local-data/` by default (`DOSSIER_DATA_DIR` overrides it). Git only transfers source code: it does not transfer your colleague's local cases, uncommitted changes or Azure configuration. To migrate cases, stop both servers and copy the entire data directory securely to the new configured location. Upload paths are relative; legacy absolute paths are resolved against the new uploads folder, including paths copied between Windows and Linux. Do not commit that data to Git.

Main code: `components/workspace.tsx` for screens, `components/document-review.tsx` for manual review, `backend/main.py` for endpoints, `backend/rules.py` for checks, `backend/drafts.py` for printable sheets and `backend/ai.py` for Azure integrations.

## Remaining scope

This is a local prototype. Company and officer views are simulated roles without authentication, authorization or tenant isolation. Shared deployment needs those controls plus protected storage and an audited workflow. The legal source corpus and complete required-document list still need domain review; the app does not validate authenticity, complete every official form field, or submit to an agency. Live Azure behavior requires credentials and deployment validation.
