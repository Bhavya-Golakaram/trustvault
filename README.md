# TrustVault

Secure document sharing with a tamper-evident audit trail. Built with Python, Flask and SQLite.

Live site: https://trustvault-1-jcjo.onrender.com

## The problem

Confidential documents shared online can end up with the wrong people, with unclear permissions, and with no way to prove that the record of who did what was not edited afterwards. TrustVault gives each file a private owner-only vault, lets the owner share it with one named person under limits, and records every action in a hash-chained audit log that can be re-verified at any time.

## What works

- Register, log in and log out. Passwords are stored as salted hashes.
- Upload documents (pdf, png, jpg, jpeg, txt, docx, up to 5 MB). Each file gets a SHA-256 fingerprint and a random stored name.
- Owner-only download. Another user gets a 403 and the attempt is logged.
- Share links. The owner names the recipient's email, sets an expiry (1 hour to 7 days) and a download limit, and can revoke the link. Only a logged-in user with that exact email can use it.
- Share buttons: copy link, open in the owner's email app, and WhatsApp. TrustVault does not send email itself.
- Audit log. Every register, login, failed login, upload, download, denied download, share, revoke and password change is stored with the hash of the previous record. The Verification page re-checks the whole chain and shows a green "Chain intact" card or a red "Tampering detected" card naming the first broken record.
- Dashboard with live security status, a live chain strip, recent activity and document search.
- Account page with password change, and a recovery code for resetting a forgotten password. Failed resets are limited to 5 per 15 minutes per email.
- `tamper_demo.py` edits one audit record directly in the database so you can watch verification fail.

## How to run it

Needs Python 3.11 or newer.

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000. On Linux or macOS, activate with `source .venv/bin/activate`.

Optional environment variables: `SECRET_KEY` (set a long random value in production), `DB_PATH`, `UPLOAD_DIR`.

To see the tamper detection: register and log in, run `python tamper_demo.py`, open the Verification page (it turns red), then run `python tamper_demo.py restore`.

## How the audit chain works

Each audit record stores `hash = SHA-256(previous hash, time, actor, action, target, detail)`. Editing a record changes its hash, and changing a middle record breaks the link to the next one. `verify_chain` in `audit.py` recomputes every hash in order.

## Known limits (not finished)

- Files are not encrypted at rest.
- Share links are not emailed automatically. The owner copies the link and sends it.
- Deleting the newest audit records is not detected unless the owner saved the latest chain hash somewhere else. The chain is also not digitally signed, so someone with write access to the whole database could recompute every hash.
- Forms have no CSRF tokens, and there is no rate limit on login attempts.
- File types are checked by extension, not by content.
- Password reset works only for accounts that created a recovery code.
- On Render's free plan the disk is temporary, so accounts and files can be erased when the service restarts. This is a hosting limit.
- There are no automated tests yet.
- Subscriptions and payments are not part of this version.

## AI tools used

Claude (Anthropic) was used to plan the project and to generate and debug code. Problems found along the way are in PROMPTS.md.