# CLTIBC Website — Centre for LexTax & IBC, MNLU Mumbai

Production-grade website with a private admin portal. Zero dependencies — runs
on the Python 3 that ships with macOS (and any Linux host).

## Run it

```
cd "/Users/deepak/claude ME/cltibc-website"
python3 server.py
```

Open **http://localhost:8452** — admin portal at **/admin**.
On a brand-new install the server prints a randomly generated admin password
to the console (change it in Admin → Settings).

## What the admin portal controls (everything)

| Tab | Controls |
|---|---|
| Site Content | Every line of copy (hero, cards, about, guidelines, contact, footer), logo upload, SEO description, social links, theme colours, submission downloads |
| Custom Sections | Add your own sections to any page (top or bottom slot, ordered, draftable) |
| Pages & Menu | Create whole new pages at `/p/<slug>`; rename/reorder/hide any menu item |
| Blog Posts | Full CRUD, markdown body, cover image, drafts |
| Journal Articles | Full CRUD, PDF upload, cover image, drafts |
| Events & Photos | Full CRUD with photo galleries |
| Team Members | Full CRUD with a drag-and-zoom circular photo cropper |
| Messages | Contact-form inbox |
| Settings | Change password; **Edit History** — every save keeps the last 15 versions per content file, restorable in one click |

Blog posts and journal papers show **live view counts** (per open) and a
**like button** (one per browser).

## Security posture

- PBKDF2 password hashing (200k rounds), HMAC-signed session cookies
  (HttpOnly, SameSite=Strict), CSRF tokens on every state-changing form.
- Login rate limiting: 5 failures locks the address for 15 minutes.
- All admin routes enforced server-side; every user string HTML-escaped;
  markdown renderer escapes before formatting (no raw HTML injection).
- Uploads: extension whitelist (images/PDF/DOCX), size caps, random filenames,
  served with `nosniff`; path-traversal guarded on all file serving.
- Security headers: CSP, X-Frame-Options DENY, Referrer-Policy, nosniff.
- Errors never leak stack traces — they log privately to `data/error.log`.
- `data/` and `uploads/` are `.gitignore`d (secrets never enter version control).

## Deployment — PythonAnywhere (recommended, free)

Vercel/Netlify will NOT work: they wipe the filesystem, which destroys the
admin portal's saved content. Use a host with a persistent disk.

1. Create a free account at https://www.pythonanywhere.com (Beginner plan).
2. Open a Bash console there and run:
   `git clone https://github.com/iamdjkt-dotcom/cltibc.git`
3. (Optional — carries over existing content.) Upload your latest
   `cltibc-backup-*.zip` (Files tab), then in the console:
   `cd cltibc && unzip -o ~/cltibc-backup-*.zip && cp -r cltibc-content/data cltibc-content/uploads . && rm -r cltibc-content`
   Backups intentionally do NOT contain the password — you set that in step 4.
4. **Set the admin password on the server** (do this every fresh deploy):
   `cd ~/cltibc && python3 server.py --set-password "your-chosen-password"`
5. Web tab → Add a new web app → Manual configuration → latest Python 3.
6. Set "Source code" to `/home/<username>/cltibc`, then edit the WSGI
   configuration file to exactly:

   ```python
   import os, sys
   os.environ["CLTIBC_SECURE"] = "1"
   sys.path.insert(0, "/home/<username>/cltibc")
   from wsgi import application
   ```

7. Reload the web app. The site is live at `https://<username>.pythonanywhere.com`
   with HTTPS already on; sign in at /admin with the password from step 4.
8. Set the public address in Admin → Site Content → "Public Site Address".
9. To publish future code updates: `cd ~/cltibc && git pull`, then Reload.
   Content backups: download `data/` + `uploads/` from the Files tab.

**Forgot the deployed password / "incorrect password"?** The password never
travels in git or backups by design, so a fresh server has its own. Just run
step 4 again on the host to set a known one, then Reload.

## Where things live

| Path | What |
|---|---|
| `server.py` | The whole application |
| `templates.py` | Page HTML |
| `static/` | Stylesheet + scripts |
| `data/*.json` | All content (this is the database) |
| `data/history/` | Automatic version history of every edit |
| `data/config.json` | Password hash + signing secret — never share |
| `uploads/` | PDFs and photos |

**Backup = copy `data/` and `uploads/`.**
