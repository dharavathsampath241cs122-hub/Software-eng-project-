# FinScope Version 2 — Single Brief to SRS

Version 2 keeps the FinScope visual style and replaces the interview with one project brief. Two separate agents run in sequence:

1. **Requirements Gathering Agent** extracts and classifies draft requirements from the brief. If an LLM API key is configured, it can assist; otherwise, the app uses a local evidence-only fallback.
2. **SRS Generation Agent** creates an IEEE 830 style Software Requirements Specification as a Word document (`.docx`), including conceptual class, activity, use case, sequence, and state chart diagrams.

Both outputs are drafts for stakeholder review. A project brief is submitted once; the app asks no interview questions and has no answer fields.

## Run on Windows PowerShell

Open PowerShell in this `version_2` folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>. API documentation is at <http://127.0.0.1:8000/docs>. Stop the server with `Ctrl+C`.

If PowerShell blocks activation, run `python -m pip install -r requirements.txt` and `python -m uvicorn ...` without activating the environment, using `.\.venv\Scripts\python.exe -m pip ...` and `.\.venv\Scripts\python.exe -m uvicorn ...`.

## Optional LLM setup

The local fallback works without an API key. To enable LLM-assisted requirement extraction, create a `.env` file in this folder:

```text
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

Keep `.env` private and never commit API keys. Restart the server after changing it.

## Commands to learn

| Command | What it does |
| --- | --- |
| `py -m venv .venv` | Creates an isolated Python environment. |
| `.\.venv\Scripts\Activate.ps1` | Activates that environment in PowerShell. |
| `python -m pip install -r requirements.txt` | Installs the app's dependencies. |
| `python -m uvicorn app.main:app --reload` | Starts the local development server. |
| `git status` | Shows which files Git sees as changed. |
| `git add version_2` | Stages this folder (run from the `software_eng_project` Git root). |
| `git commit -m "Add single brief SRS workflow"` | Saves staged changes in a local commit. |
| `git push` | Sends committed changes to the configured GitHub remote. |

For Git commands, first change to the repository root with `cd ..` from `version_2`.
If `git remote -v` still shows the placeholder `YOUR-USERNAME`, set your actual GitHub repository URL with `git remote set-url origin https://github.com/YOUR-ACTUAL-USERNAME/software_eng_project.git` before pushing.

The `.venv` folder is local to this version and should not be committed. Generated projects and Word exports are stored under `version_2/data/`.
