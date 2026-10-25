# PROMPTS.md: where the AI was wrong and what I did

I used Claude (Anthropic) to plan and write most of this project. These are real problems I hit, with what I did about each.

## 1. Packages installed in the wrong place
- **What happened:** I pasted four setup commands at once. Activating the virtual environment failed because PowerShell blocks scripts, but the pip install ran anyway, so packages went into my main Python and `requirements.txt` listed packages I did not need.
- **What I did:** I allowed scripts for my user with `Set-ExecutionPolicy`, deleted `.venv` and `requirements.txt`, recreated the environment, and reinstalled. I now paste commands one at a time.
- **How I checked:** the prompt showed `(.venv)` and `pip freeze` listed only Flask, gunicorn, pytest and their dependencies.

## 2. `.gitignore` did not work, so `.venv` went to GitHub
- **What happened:** my `.gitignore` lines had spaces in front of them after pasting, so Git did not match `.venv/` and committed thousands of files.
- **What I did:** I rewrote the file with `Set-Content`, ran `git rm -r --cached .venv`, and committed again.
- **How I checked:** `git ls-files` listed only my own files, and later `git status` stopped showing `.venv`, `uploads/` and `trustvault.db`.

## 3. Templates folder nested inside itself
- **What happened:** my HTML files ended up in `templates/templates/templates/...`, so Flask raised `TemplateNotFound: login.html`.
- **What I did:** I listed the files with `Get-ChildItem -Recurse`, moved the four HTML files into a temporary folder, deleted the messy folder, created a clean `templates` folder, and moved the files back.
- **How I checked:** `dir templates` showed exactly four files and the login page loaded.

## 4. `app.py` lost its ending after an edit
- **What happened:** when I replaced the dashboard function, the code below it was deleted too (upload, download, and the lines that start the server). `python app.py` exited immediately with no error.
- **What I did:** I looked at the end of the file, saw it stopped at the dashboard function, and replaced `app.py` with a complete version.
- **How I checked:** the terminal showed `Running on http://127.0.0.1:5000` and upload and download worked again.

## 5. Four modules were in `.venv`, not in the project, so they were missing from GitHub
- **What happened:** `audit.py`, `audit_views.py`, `db.py` and `schema.sql` had been created inside the `.venv` folder. The app ran on my computer, but Git ignores `.venv`, so the live site would have crashed on missing files. `git add audit.py` failed with `pathspec did not match any files`.
- **What I did:** I printed `audit.__file__` and `db.__file__` with Python and searched for the files, found them in `.venv`, moved them next to `app.py`, and pushed.
- **How I checked:** a loop over the nine required files printed OK for every one, and the Render deploy started.

## 6. The tamper demo script failed
- **What happened:** the first `tamper_demo.py` raised `sqlite3.OperationalError: no such table: audit`.
- **What I did:** I changed it to use `DB_PATH` from `db.py` and to print the database path it opens, and to stop with a message if the audit table is missing.
- **How I checked:** after the change the script forged an audit record, the Verification page showed the red tampering card, and `python tamper_demo.py restore` turned it green again.

## 7. A dashboard tile that did nothing
- **What happened:** the "Share securely" tile only scrolled the page, so clicking it looked broken.
- **What I did:** I changed it to open the Share page for the newest document, and show a message if there are no documents.
- **How I checked:** I clicked the tile and the Share page opened.

## 8. A mockup claimed features I do not have
- **What happened:** my design mockup said "end-to-end encryption" and "Cloud Backup". TrustVault does neither, so the first interface the AI built must not repeat those claims.
- **What I did:** the Security Status panel shows only facts from my own data: audit chain state, owner-only access, active share links and fingerprinted files. The README lists encryption at rest as not done.