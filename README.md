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

## Deployment (when going public)

1. Copy the whole folder to a Python host (PythonAnywhere, Render, a small VPS).
2. Put it behind HTTPS (the host usually provides this).
3. Run with `CLTIBC_SECURE=1 python3 server.py` — this turns on the `Secure`
   cookie flag and HSTS. **Never expose /admin over plain HTTP.**
4. Set your public address in Admin → Site Content → "Public Site Address"
   so link previews (OG tags) work.
5. Back up `data/` + `uploads/` — that's 100% of the site's content.

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
