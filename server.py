#!/usr/bin/env python3
"""
Centre for LexTax & IBC (CLTIBC) — website + admin portal.
Zero dependencies: runs on the macOS system Python 3.

    python3 server.py            # http://localhost:8452
    PORT=9000 python3 server.py  # custom port

Content lives in data/*.json, files in uploads/. Admin at /admin.
"""
import cgi
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import threading
import time
import urllib.parse
from datetime import date
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import templates as T

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
UPLOAD_DIR = os.path.join(ROOT, "uploads")
STATIC_DIR = os.path.join(ROOT, "static")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOC_EXTS = {".pdf", ".docx"}
SESSION_HOURS = 12
MAX_BODY = 30_000_000          # absolute request-size ceiling
SECURE_MODE = os.environ.get("CLTIBC_SECURE") == "1"   # set to 1 behind HTTPS

# login rate limiting: 5 failures locks an address out for 15 minutes
LOGIN_FAILS = {}
LOGIN_LOCK = threading.Lock()
MAX_FAILS, LOCKOUT_SECONDS = 5, 900

NAV_DEFAULTS = [("/", "Home", 10), ("/about", "About", 20), ("/journal", "Journal", 30),
                ("/blog", "Blog", 40), ("/submissions", "Submissions", 50),
                ("/events", "Events", 60), ("/team", "Team", 70), ("/contact", "Contact", 80)]


def nav_items():
    """Menu = built-in pages (label/order/visibility editable) + custom pages."""
    stored = {n["url"]: n for n in _load("nav.json", [])}
    items = []
    for url, label, order in NAV_DEFAULTS:
        o = stored.get(url, {})
        items.append({"url": url, "label": o.get("label") or label,
                      "order": o.get("order", order), "visible": o.get("visible", True),
                      "builtin": True})
    for p in _load("pages.json", []):
        if p.get("published") and p.get("in_nav"):
            url = "/p/%s" % p["slug"]
            o = stored.get(url, {})
            items.append({"url": url, "label": o.get("label") or p["title"],
                          "order": o.get("order", p.get("order", 90)),
                          "visible": o.get("visible", True), "builtin": False})
    return sorted(items, key=lambda n: n["order"])

TEAM_CATEGORIES = ["Patrons & Advisors", "Faculty", "Student Editorial Board", "Student Team"]

# Every piece of site copy is editable in Admin -> Site Content; these are the defaults.
SITE_DEFAULTS = {
    "logo": "",
    "hero_kicker": "Maharashtra National Law University Mumbai",
    "hero_title": "Advancing Scholarship, Training, and Policy Discourse in Tax Law & Insolvency",
    "hero_sub": ("CLTIBC serves as a platform for interdisciplinary engagement by bringing together "
                 "academia, professionals, policymakers, regulators, and students to critically engage "
                 "with contemporary legal and regulatory developments."),
    "card_journal": ("Our flagship peer-reviewed journal dedicated to advancing scholarship "
                     "at the intersection of taxation and insolvency law."),
    "card_blog": ("Short-form commentary, analysis, and opinion on recent developments in "
                  "tax law and the Insolvency & Bankruptcy Code."),
    "card_team": "Our centre is led by distinguished faculty and patrons dedicated to legal excellence.",
    "cta_title": "Collaborate with the Centre",
    "cta_text": ("We welcome speaking engagements, research collaborations, and contributions "
                 "from academics, practitioners, and students across India."),
    "about_lede": ("The Centre for LexTax & IBC (CLTIBC) at Maharashtra National Law University, Mumbai "
                   "is a specialised academic and research centre established to promote advanced study, "
                   "research, and capacity building in the fields of taxation laws, fiscal policy, and "
                   "Insolvency and Bankruptcy Law."),
    "about_body": ("The Centre serves as a platform for interdisciplinary engagement by bringing together "
                   "academia, professionals, policymakers, regulators, and students to critically engage "
                   "with contemporary legal and regulatory developments.\n\n"
                   "Through its flagship publication, the *Indian Review of Taxation and Insolvency Law*, "
                   "the *JurisFiscus Blog*, and a calendar of lectures, workshops, and conferences, the "
                   "Centre seeks to contribute meaningfully to the development of tax and insolvency "
                   "jurisprudence in India."),
    "vision": "To be a premier global hub for excellence in legislative policy research in taxation and insolvency law.",
    "mission": ("To foster rigorous scholarship, professional training, and informed policy discourse by "
                "connecting academia, practitioners, regulators, and students."),
    "journal_guidelines": (
        "The Review invites original, unpublished manuscripts from academics, practitioners, and students "
        "on themes at the intersection of taxation, fiscal policy, and insolvency law.\n\n"
        "- **Categories:** Long Articles (5,000-8,000 words), Short Articles (3,000-5,000 words), "
        "Case Comments & Legislative Notes (1,500-3,000 words).\n"
        "- **Format:** Microsoft Word (.docx), Times New Roman 12/1.5 line spacing, footnotes in Bluebook (21st ed.).\n"
        "- **Review:** All submissions undergo double-blind peer review. Co-authorship up to two authors is permitted.\n"
        "- **How to submit:** Email your manuscript with a 250-word abstract and a separate cover letter "
        "(name, affiliation, contact) to cltibc@mnlumumbai.edu.in with the subject line \"Journal Submission\".\n\n"
        "Accepted papers are published on this page under the Centre's aegis."),
    "blog_guidelines": (
        "We accept guest posts of 1,200-2,500 words offering timely analysis of judgments, regulatory "
        "developments, and policy debates in tax and insolvency law. Hyperlink all sources; footnotes are discouraged.\n\n"
        "Email submissions to cltibc@mnlumumbai.edu.in with the subject line \"Blog Submission\". "
        "The editorial team responds within 10 working days."),
    "contact_address": ("Centre for LexTax & IBC\nMaharashtra National Law University, Mumbai\n"
                        "Powai, Mumbai - 400076, Maharashtra, India"),
    "contact_email": "cltibc@mnlumumbai.edu.in",
    "footer_desc": ("A specialised academic and research centre at Maharashtra National Law University, "
                    "Mumbai, established to promote advanced study, research, and capacity building in "
                    "taxation laws, fiscal policy, and Insolvency and Bankruptcy Law."),
    "submissions_intro": ("The Centre welcomes contributions to both of its publications. Review the "
                          "guidelines below before submitting, and write to us with any questions."),
    "submission_files": [],
    "seo_description": ("Centre for LexTax & IBC (CLTIBC), Maharashtra National Law University Mumbai — "
                        "research, training and policy discourse in tax law and insolvency."),
    "site_url": "",
    "social_linkedin": "",
    "social_instagram": "",
    "theme_ink": "#384959",
    "theme_band": "#BDDDFC",
    "theme_accent": "#6A89A7",
    "theme_bright": "#88BDF2",
}


def site():
    stored = _load("site.json", {})
    merged = dict(SITE_DEFAULTS)
    merged.update({k: v for k, v in stored.items() if v or k == "logo"})
    return merged


# ---------------------------------------------------------------- storage

def _load(name, default):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


HISTORY_DIR = os.path.join(DATA_DIR, "history")
HISTORY_KEEP = 15
SNAPSHOT_FILES = {"site.json", "blog.json", "journal.json", "events.json",
                  "team.json", "sections.json", "pages.json", "nav.json"}


def _snapshot(name):
    """Keep the previous version of a content file so edits can be undone."""
    src = os.path.join(DATA_DIR, name)
    if not os.path.exists(src) or name not in SNAPSHOT_FILES:
        return
    os.makedirs(HISTORY_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    with open(src, "rb") as f:
        data = f.read()
    with open(os.path.join(HISTORY_DIR, "%s.%s" % (name, stamp)), "wb") as f:
        f.write(data)
    snaps = sorted(f for f in os.listdir(HISTORY_DIR) if f.startswith(name + "."))
    for old in snaps[:-HISTORY_KEEP]:
        os.remove(os.path.join(HISTORY_DIR, old))


def _save(name, obj):
    path = os.path.join(DATA_DIR, name)
    _snapshot(name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # first run: generate a random password instead of shipping a default
    password = secrets.token_urlsafe(10)
    salt = secrets.token_hex(16)
    cfg = {
        "secret": secrets.token_hex(32),
        "salt": salt,
        "password_hash": hash_password(password, salt),
    }
    _save("config.json", cfg)
    print("=" * 60)
    print("  FIRST RUN — your admin password is:  %s" % password)
    print("  Change it after signing in: Admin -> Settings.")
    print("=" * 60)
    return cfg


CONFIG = load_config()


# ---------------------------------------------------------------- helpers

def esc(s):
    return html.escape(str(s or ""), quote=True)


def render(template, **kw):
    out = template
    for key, val in kw.items():
        out = out.replace("{{%s}}" % key, str(val))
    return out


def _shade(hexcol, factor):
    try:
        h = hexcol.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return hexcol
    clamp = lambda c: max(0, min(255, int(c * factor)))
    return "#%02x%02x%02x" % (clamp(r), clamp(g), clamp(b))


def theme_css(s):
    ink, band = s["theme_ink"], s["theme_band"]
    accent, bright = s["theme_accent"], s["theme_bright"]
    try:
        h = ink.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        r, g, b = 56, 73, 89
    return (":root{--umber:%s;--umber-deep:%s;--ink:%s;--gold:%s;--gold-deep:%s;"
            "--gold-pale:%s;--ice:%s;--hairline:rgba(%d,%d,%d,.22);"
            "--hairline-soft:rgba(%d,%d,%d,.12);}"
            % (ink, _shade(ink, .74), _shade(ink, .92), accent, _shade(accent, .76),
               bright, band, r, g, b, r, g, b))


def page(title, content, active="", meta_desc="", og_image=""):
    s = site()
    nav = "".join(
        '<a href="%s" class="%s">%s</a>'
        % (n["url"], "active" if n["url"] == active else "", esc(n["label"]))
        for n in nav_items() if n["visible"]
    )
    desc = esc(meta_desc or s["seo_description"])
    meta = '<meta name="description" content="%s">' % desc
    meta += '<meta property="og:title" content="%s">' % esc(title)
    meta += '<meta property="og:description" content="%s">' % desc
    base_url = s["site_url"].rstrip("/")
    if base_url and og_image:
        meta += '<meta property="og:image" content="%s%s">' % (esc(base_url), esc(og_image))
    social = ""
    if s["social_linkedin"]:
        social += '<a href="%s" target="_blank" rel="noopener">LinkedIn</a>' % esc(s["social_linkedin"])
    if s["social_instagram"]:
        social += '<a href="%s" target="_blank" rel="noopener">Instagram</a>' % esc(s["social_instagram"])
    social += '<a href="mailto:%s">Email</a>' % esc(s["contact_email"])
    return render(T.BASE, title=esc(title), nav=nav, content=content, meta=meta,
                  theme_css=theme_css(s), social=social,
                  brand_mark=T.MARK_SVG, footer_desc=esc(s["footer_desc"]))


def md_to_html(text):
    """Minimal, safe markdown: headings, bold/italic, links, lists, quotes, paragraphs."""
    text = esc(text).replace("\r\n", "\n")

    def inline(s):
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        s = re.sub(r"\[(.+?)\]\((https?://[^)\s]+)\)",
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        return s

    out = []
    para, bullets, quote = [], [], []

    def flush():
        if bullets:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(b) for b in bullets))
            bullets.clear()
        if quote:
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(quote)))
            quote.clear()
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            para.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            flush()
        elif stripped.startswith("## "):
            flush()
            out.append("<h3>%s</h3>" % inline(stripped[3:]))
        elif stripped.startswith("# "):
            flush()
            out.append("<h2>%s</h2>" % inline(stripped[2:]))
        elif stripped.startswith(("- ", "* ")):
            if para or quote:
                flush()
            bullets.append(stripped[2:])
        elif stripped.startswith("&gt;"):
            if para or bullets:
                flush()
            quote.append(stripped[4:].strip())
        else:
            if bullets or quote:
                flush()
            para.append(stripped)
    flush()
    return "\n".join(out)


def excerpt(text, limit=220):
    plain = re.sub(r"[#*>\[\]()]", "", text or "").strip().replace("\n", " ")
    plain = re.sub(r"\s+", " ", plain)
    return plain[:limit] + ("…" if len(plain) > limit else "")


def fmt_date(iso):
    try:
        y, m, d = iso.split("-")
        return date(int(y), int(m), int(d)).strftime("%d %B %Y")
    except Exception:
        return iso or ""


def safe_filename(name):
    base = os.path.basename(name or "file")
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base).strip("-.") or "file"
    return secrets.token_hex(4) + "-" + base[:80]


def new_id():
    return secrets.token_hex(8)


# ---------------------------------------------------------------- sessions

def make_session_cookie():
    expiry = str(int(time.time()) + SESSION_HOURS * 3600)
    sig = hmac.new(CONFIG["secret"].encode(), ("session:" + expiry).encode(), "sha256").hexdigest()
    return expiry + "." + sig


def session_valid(cookie_val):
    if not cookie_val or "." not in cookie_val:
        return False
    expiry, sig = cookie_val.split(".", 1)
    if not expiry.isdigit() or int(expiry) < time.time():
        return False
    expected = hmac.new(CONFIG["secret"].encode(), ("session:" + expiry).encode(), "sha256").hexdigest()
    return hmac.compare_digest(sig, expected)


def csrf_token(cookie_val):
    return hmac.new(CONFIG["secret"].encode(), ("csrf:" + cookie_val).encode(), "sha256").hexdigest()


# ---------------------------------------------------------------- public rendering

def blog_item_html(p):
    return card_html("blog", p)


def published(items):
    return sorted([i for i in items if i.get("published")], key=lambda i: i.get("date", ""), reverse=True)


PAGE_NAMES = ["home", "about", "journal", "blog", "submissions", "events", "team", "contact"]
SLOT_LABELS = {"top": "Below the page header", "bottom": "At the end of the page"}

# ---------------------------------------------------------------- view/like stats

STATS_LOCK = threading.Lock()


def get_stats(item_id):
    return _load("stats.json", {}).get(item_id, {"views": 0, "likes": 0})


def bump_view(item_id):
    with STATS_LOCK:
        stats = _load("stats.json", {})
        entry = stats.setdefault(item_id, {"views": 0, "likes": 0})
        entry["views"] += 1
        _save("stats.json", stats)


def change_like(item_id, delta):
    with STATS_LOCK:
        stats = _load("stats.json", {})
        entry = stats.setdefault(item_id, {"views": 0, "likes": 0})
        entry["likes"] = max(0, entry["likes"] + delta)
        _save("stats.json", stats)
        return entry["likes"]


EYE_SVG = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>')
HEART_SVG = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"/></svg>')


def read_minutes(text):
    return max(1, round(len((text or "").split()) / 200))


def stats_bar(item_id):
    st = get_stats(item_id)
    return ('<div class="post-card-foot">'
            '<span class="stat">%s<span>%d</span></span>'
            '<button class="like-btn" type="button" data-id="%s" aria-label="Like this">'
            '%s<span class="like-count">%d</span></button></div>'
            % (EYE_SVG, st["views"], item_id, HEART_SVG, st["likes"]))


def card_html(kind, item):
    if kind == "blog":
        href = "/blog/%s" % item["id"]
        meta = "%s &middot; %d min read" % (fmt_date(item["date"]), read_minutes(item["body"]))
    else:
        href = ("/journal/read/%s" % item["id"]) if item.get("pdf") else "/journal#submissions"
        meta = "%s &middot; %s" % (esc(item["authors"]), esc(item.get("issue") or fmt_date(item["date"])))
    style = ""
    if item.get("image"):
        style = " style=\"background-image:url('/uploads/%s')\"" % esc(item["image"])
    return ('<article class="post-card%s" data-reveal%s>'
            '<a class="post-card-link" href="%s"><span class="sr-only">%s</span></a>'
            '<p class="post-card-meta">%s</p>'
            '<h3 class="post-card-title">%s</h3>'
            '%s</article>'
            % (" no-image" if not item.get("image") else "", style, href,
               esc(item["title"]), meta, esc(item["title"]), stats_bar(item["id"])))


def custom_sections_html(page_name, slot):
    secs = [s for s in _load("sections.json", [])
            if s.get("page") == page_name and s.get("slot", "bottom") == slot and s.get("published")]
    secs.sort(key=lambda s: s.get("order", 99))
    out = []
    for s in secs:
        eyebrow = '<span class="eyebrow">%s</span>' % esc(s["eyebrow"]) if s.get("eyebrow") else ""
        image = ('<img class="custom-img" src="/uploads/%s" alt="%s" loading="lazy">'
                 % (esc(s["image"]), esc(s["title"]))) if s.get("image") else ""
        out.append(
            '<section class="section custom-section"><div class="wrap narrow-wide">'
            '<div class="sec-head" data-reveal>%s<h2>%s</h2></div>'
            '<div class="prose" data-reveal>%s</div>%s</div></section>'
            % (eyebrow, esc(s["title"]), md_to_html(s.get("body", "")), image)
        )
    return "".join(out)


def with_custom(page_name, body):
    """Splice admin-defined sections into a rendered page: 'top' goes right
    after the first section (the page header), 'bottom' after everything."""
    top = custom_sections_html(page_name, "top")
    if top:
        body = body.replace("</section>", "</section>" + top, 1)
    return body + custom_sections_html(page_name, "bottom")


def home_page():
    s = site()
    posts = published(_load("blog.json", []))[:3]
    latest = ""
    if posts:
        latest = render(T.LATEST_SECTION, posts="".join(blog_item_html(p) for p in posts))
    if s["logo"]:
        logo = ('<div class="logo-badge seq seq-2"><img src="/uploads/%s" '
                'alt="Centre for LexTax and IBC logo"></div>' % esc(s["logo"]))
    else:
        logo = T.LOGO_SVG
    articles = published(_load("journal.json", []))[:2]
    journal_latest = ""
    if articles:
        rows = "".join(card_html("journal", a) for a in articles)
        journal_latest = render(T.JOURNAL_LATEST_SECTION, articles=rows)
    body = render(T.HOME, latest=latest, logo=logo, journal_latest=journal_latest,
                  hero_kicker=esc(s["hero_kicker"]), hero_title=esc(s["hero_title"]),
                  hero_sub=esc(s["hero_sub"]), about_lede=esc(s["about_lede"]),
                  card_journal=esc(s["card_journal"]), card_blog=esc(s["card_blog"]),
                  card_team=esc(s["card_team"]),
                  cta_title=esc(s["cta_title"]), cta_text=esc(s["cta_text"]))
    return page("Home", with_custom("home", body), active="/")


def blog_page():
    posts = published(_load("blog.json", []))
    body = "".join(blog_item_html(p) for p in posts) or \
        '<div class="empty">Posts are on their way. The editorial team is reviewing the first submissions.</div>'
    return page("The JurisFiscus Blog",
                with_custom("blog", render(T.BLOG, posts=body,
                                           blog_guidelines=md_to_html(site()["blog_guidelines"]))),
                active="/blog")


def post_page(post_id):
    posts = _load("blog.json", [])
    post = next((p for p in posts if p["id"] == post_id and p.get("published")), None)
    if not post:
        return None
    bump_view(post_id)
    cover = ('<img class="post-cover" src="/uploads/%s" alt="">' % esc(post["image"])) \
        if post.get("image") else ""
    body = render(T.POST_PAGE, title=esc(post["title"]), author=esc(post["author"]),
                  date="%s &middot; %d min read" % (fmt_date(post["date"]), read_minutes(post["body"])),
                  cover=cover, stats=stats_bar(post_id), body=md_to_html(post["body"]))
    return page(post["title"], body, active="/blog")


def journal_page():
    articles = published(_load("journal.json", []))
    rows = [card_html("journal", a) for a in articles]
    body = "".join(rows) or \
        '<div class="empty">The inaugural issue is under preparation. Accepted papers will appear here.</div>'
    return page("Indian Review of Taxation and Insolvency Law",
                with_custom("journal", render(T.JOURNAL, articles=body,
                                              journal_guidelines=md_to_html(site()["journal_guidelines"]))),
                active="/journal")


def events_page():
    events = sorted(_load("events.json", []), key=lambda e: e.get("date", ""), reverse=True)
    rows = []
    for e in events:
        photos = "".join('<img src="/uploads/%s" alt="%s" loading="lazy">' % (esc(f), esc(e["title"]))
                         for f in e.get("photos", []))
        photos_html = '<div class="photo-grid">%s</div>' % photos if photos else ""
        rows.append(
            '<article class="event" data-reveal><p class="entry-meta">%s</p>'
            '<h3 class="event-title">%s</h3>'
            '<div class="prose">%s</div>%s</article>'
            % (fmt_date(e["date"]), esc(e["title"]), md_to_html(e.get("description", "")), photos_html)
        )
    body = "".join(rows) or \
        '<div class="empty">Upcoming lectures, workshops, and conferences will be announced here.</div>'
    return page("Events", with_custom("events", render(T.EVENTS, events=body)), active="/events")


def team_page():
    members = _load("team.json", [])
    groups_html = []
    for cat in TEAM_CATEGORIES:
        group = sorted([m for m in members if m.get("category") == cat],
                       key=lambda m: (m.get("order", 99), m.get("name", "")))
        if not group:
            continue
        cards = []
        for m in group:
            if m.get("photo"):
                avatar = '<img src="/uploads/%s" alt="%s">' % (esc(m["photo"]), esc(m["name"]))
            else:
                initials = "".join(w[0] for w in m["name"].split()[:2]).upper()
                avatar = '<div class="avatar-fallback">%s</div>' % esc(initials)
            bio = '<p class="bio">%s</p>' % esc(m["bio"]) if m.get("bio") else ""
            cards.append('<div class="member" data-reveal>%s<h4>%s</h4><p class="role">%s</p>%s</div>'
                         % (avatar, esc(m["name"]), esc(m["role"]), bio))
        groups_html.append('<div class="team-group"><div class="sec-head"><h2>%s</h2></div>'
                           '<div class="team-grid">%s</div></div>' % (esc(cat), "".join(cards)))
    body = "".join(groups_html) or \
        '<div class="empty">Profiles of our patrons, faculty, and student team will appear here shortly.</div>'
    return page("The Team", with_custom("team", render(T.TEAM, groups=body)), active="/team")


def submissions_page():
    s = site()
    files_html = ""
    if s["submission_files"]:
        rows = "".join(
            '<li><a href="/uploads/%s" target="_blank">%s</a></li>'
            % (esc(f["file"]), esc(f["name"])) for f in s["submission_files"])
        files_html = ('<section class="section"><div class="wrap narrow">'
                      '<div class="sec-head" data-reveal><span class="eyebrow">Downloads</span>'
                      '<h2>Templates &amp; Documents</h2></div>'
                      '<ul class="prose download-list" data-reveal>%s</ul></div></section>' % rows)
    body = render(T.SUBMISSIONS, intro=esc(s["submissions_intro"]),
                  journal_guidelines=md_to_html(s["journal_guidelines"]),
                  blog_guidelines=md_to_html(s["blog_guidelines"]),
                  files=files_html)
    return page("Submission Guidelines", with_custom("submissions", body), active="/submissions")


def custom_page(slug):
    p = next((x for x in _load("pages.json", [])
              if x["slug"] == slug and x.get("published")), None)
    if not p:
        return None
    body = render(T.CUSTOM_PAGE, title=esc(p["title"]), body=md_to_html(p.get("body", "")))
    return page(p["title"], body, active="/p/%s" % slug)


def contact_page(flash=""):
    s = site()
    address = esc(s["contact_address"]).replace("\n", "<br>")
    return page("Contact", with_custom("contact",
                                       render(T.CONTACT, flash=flash, contact_address=address,
                                              contact_email=esc(s["contact_email"]))), active="/contact")


def about_page():
    s = site()
    body = render(T.ABOUT, vision=esc(s["vision"]), mission=esc(s["mission"]),
                  about_lede=esc(s["about_lede"]), about_body=md_to_html(s["about_body"]))
    return page("About", with_custom("about", body), active="/about")


def flash_box(msg, error=False):
    if not msg:
        return ""
    return '<div class="flash %s">%s</div>' % ("flash-error" if error else "", esc(msg))


# ---------------------------------------------------------------- admin panels

def csrf_field(token):
    return '<input type="hidden" name="csrf" value="%s">' % token


def admin_page(tab, token, flash=""):
    messages = _load("messages.json", [])
    badge = '<span class="badge">%d</span>' % len(messages) if messages else ""
    panels = {"site": panel_site, "sections": panel_sections, "pages": panel_pages,
              "blog": panel_blog, "journal": panel_journal, "events": panel_events,
              "team": panel_team, "messages": panel_messages, "settings": panel_settings}
    tab = tab if tab in panels else "blog"
    actives = {"active_%s" % name: ("active" if name == tab else "") for name in panels}
    body = render(T.ADMIN, panel=panels[tab](token), flash=flash,
                  msg_badge=badge, csrf=csrf_field(token), **actives)
    return page("Admin", body)


def _item_row(kind, item, token, label, sub):
    pill = "" if item.get("published", True) else '<span class="draft-pill">Draft</span>'
    return (
        '<div class="admin-row"><div class="admin-row-info"><strong>%s%s</strong><span>%s</span></div>'
        '<div class="admin-row-actions">'
        '<a class="btn btn-ghost btn-small" href="/admin?tab=%s&amp;edit=%s">Edit</a>'
        '<form method="post" action="/admin/%s/delete" '
        'onsubmit="return confirm(\'Delete this item permanently?\')">%s'
        '<input type="hidden" name="id" value="%s">'
        '<button class="btn btn-danger btn-small" type="submit">Delete</button></form>'
        '</div></div>'
        % (esc(label), pill, esc(sub), kind, item["id"], kind, csrf_field(token), item["id"])
    )


def panel_blog(token, edit_id=None):
    posts = sorted(_load("blog.json", []), key=lambda p: p.get("date", ""), reverse=True)
    editing = next((p for p in posts if p["id"] == edit_id), None) or {}
    rows = "".join(_item_row("blog", p, token, p["title"],
                             "%s · %s" % (p["author"], fmt_date(p["date"]))) for p in posts) \
        or '<div class="empty">No posts yet.</div>'
    checked = "checked" if editing.get("published", True) else ""
    current_img = ('<p class="help-text">Current cover: <a href="/uploads/%s" target="_blank">%s</a> '
                   '(uploading a new one replaces it)</p>' % (esc(editing["image"]), esc(editing["image"]))) \
        if editing.get("image") else ""
    return (
        '<div class="admin-panel"><h2>%s</h2>'
        '<p class="help-text">Workflow: a submission arrives by email &rarr; you review it &rarr; paste the final text here and publish. '
        'Formatting: blank line between paragraphs; <code>## Heading</code>, <code>**bold**</code>, <code>*italic*</code>, '
        '<code>- bullet</code>, <code>[link text](https://…)</code>.</p>'
        '<form method="post" action="/admin/blog/save" class="form" enctype="multipart/form-data">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Title<input type="text" name="title" required value="%s"></label>'
        '<label>Author<input type="text" name="author" required value="%s" placeholder="e.g. Aditi Sharma, NLU Delhi"></label>'
        '<label>Date<input type="date" name="date" required value="%s"></label>'
        '<label>Body<textarea name="body" rows="14" required>%s</textarea></label>'
        '<label>Cover Image (shown behind the title on the blog page; wide photos work best)'
        '<input type="file" name="image" accept="image/*"></label>%s'
        '<label class="checkbox"><input type="checkbox" name="published" %s> Published (visible on the website)</label>'
        '<button class="btn btn-primary" type="submit">Save Post</button></form></div>'
        '<div class="admin-panel"><h2>All Posts</h2><div class="admin-list">%s</div></div>'
        % ("Edit Post" if editing else "Add Blog Post", csrf_field(token),
           editing.get("id", ""), esc(editing.get("title", "")), esc(editing.get("author", "")),
           editing.get("date", date.today().isoformat()), esc(editing.get("body", "")),
           current_img, checked, rows)
    )


def panel_journal(token, edit_id=None):
    articles = sorted(_load("journal.json", []), key=lambda a: a.get("date", ""), reverse=True)
    editing = next((a for a in articles if a["id"] == edit_id), None) or {}
    rows = "".join(_item_row("journal", a, token, a["title"],
                             "%s · %s" % (a["authors"], a.get("issue") or fmt_date(a["date"])))
                   for a in articles) or '<div class="empty">No articles yet.</div>'
    checked = "checked" if editing.get("published", True) else ""
    current_pdf = ('<p class="help-text">Current file: <a href="/uploads/%s" target="_blank">%s</a> '
                   '(uploading a new PDF replaces it)</p>' % (esc(editing["pdf"]), esc(editing["pdf"]))) \
        if editing.get("pdf") else ""
    return (
        '<div class="admin-panel"><h2>%s</h2>'
        '<p class="help-text">Publish accepted papers here. Upload the final PDF; readers download it from the Journal page.</p>'
        '<form method="post" action="/admin/journal/save" class="form" enctype="multipart/form-data">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Title<input type="text" name="title" required value="%s"></label>'
        '<label>Author(s)<input type="text" name="authors" required value="%s"></label>'
        '<label>Volume / Issue (optional)<input type="text" name="issue" value="%s" placeholder="e.g. Vol. 1, Issue 1 (2026)"></label>'
        '<label>Date<input type="date" name="date" required value="%s"></label>'
        '<label>Abstract<textarea name="abstract" rows="5">%s</textarea></label>'
        '<label>Paper PDF<input type="file" name="pdf" accept=".pdf"></label>%s'
        '<label>Cover Image (shown behind the title on the journal page)'
        '<input type="file" name="image" accept="image/*"></label>'
        '<label class="checkbox"><input type="checkbox" name="published" %s> Published (visible on the website)</label>'
        '<button class="btn btn-primary" type="submit">Save Article</button></form></div>'
        '<div class="admin-panel"><h2>All Articles</h2><div class="admin-list">%s</div></div>'
        % ("Edit Article" if editing else "Add Journal Article", csrf_field(token),
           editing.get("id", ""), esc(editing.get("title", "")), esc(editing.get("authors", "")),
           esc(editing.get("issue", "")), editing.get("date", date.today().isoformat()),
           esc(editing.get("abstract", "")), current_pdf, checked, rows)
    )


def panel_events(token, edit_id=None):
    events = sorted(_load("events.json", []), key=lambda e: e.get("date", ""), reverse=True)
    editing = next((e for e in events if e["id"] == edit_id), None) or {}
    rows = "".join(_item_row("events", e, token, e["title"],
                             "%s · %d photo(s)" % (fmt_date(e["date"]), len(e.get("photos", []))))
                   for e in events) or '<div class="empty">No events yet.</div>'
    photos_html = ""
    if editing.get("photos"):
        thumbs = "".join(
            '<div class="admin-photo"><img src="/uploads/%s">'
            '<form method="post" action="/admin/events/photo-delete" '
            'onsubmit="return confirm(\'Remove this photo?\')">%s'
            '<input type="hidden" name="id" value="%s"><input type="hidden" name="photo" value="%s">'
            '<button class="btn btn-danger btn-small" type="submit">&times;</button></form></div>'
            % (esc(f), csrf_field(token), editing["id"], esc(f)) for f in editing["photos"]
        )
        photos_html = '<p class="help-text">Current photos:</p><div class="admin-photos">%s</div>' % thumbs
    return (
        '<div class="admin-panel"><h2>%s</h2>'
        '<p class="help-text">Add the event first, then attach photos (JPG/PNG, you can select several at once).</p>'
        '<form method="post" action="/admin/events/save" class="form" enctype="multipart/form-data">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Event Title<input type="text" name="title" required value="%s"></label>'
        '<label>Date<input type="date" name="date" required value="%s"></label>'
        '<label>Description<textarea name="description" rows="6">%s</textarea></label>'
        '<label>Add Photos<input type="file" name="photos" accept="image/*" multiple></label>'
        '<button class="btn btn-primary" type="submit">Save Event</button></form>%s</div>'
        '<div class="admin-panel"><h2>All Events</h2><div class="admin-list">%s</div></div>'
        % ("Edit Event" if editing else "Add Event", csrf_field(token),
           editing.get("id", ""), esc(editing.get("title", "")),
           editing.get("date", date.today().isoformat()),
           esc(editing.get("description", "")), photos_html, rows)
    )


def panel_team(token, edit_id=None):
    members = _load("team.json", [])
    editing = next((m for m in members if m["id"] == edit_id), None) or {}
    rows = "".join(_item_row("team", m, token, m["name"],
                             "%s · %s" % (m["role"], m["category"])) for m in members) \
        or '<div class="empty">No team members yet.</div>'
    options = "".join('<option value="%s" %s>%s</option>'
                      % (c, "selected" if editing.get("category") == c else "", c)
                      for c in TEAM_CATEGORIES)
    current_photo = ('<p class="help-text">Current photo: %s (uploading a new one replaces it)</p>'
                     % esc(editing["photo"])) if editing.get("photo") else ""
    return (
        '<div class="admin-panel"><h2>%s</h2>'
        '<form method="post" action="/admin/team/save" class="form" enctype="multipart/form-data" id="team-form">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Full Name<input type="text" name="name" required value="%s"></label>'
        '<label>Role / Designation<input type="text" name="role" required value="%s" placeholder="e.g. Faculty Convenor"></label>'
        '<label>Category<select name="category">%s</select></label>'
        '<label>Short Bio (optional)<textarea name="bio" rows="3">%s</textarea></label>'
        '<label>Display Order (lower appears first)<input type="number" name="order" value="%s" min="1" max="99"></label>'
        '<label>Photo<input type="file" name="photo" id="team-photo" accept="image/*"></label>'
        '<div id="crop-box" hidden style="margin-bottom:18px">'
        '<p class="help-text">Drag the photo to centre the face; use the slider to zoom. '
        'The circle shows exactly what visitors will see.</p>'
        '<canvas id="crop-canvas" width="600" height="600" '
        'style="width:260px;height:260px;border-radius:50%%;cursor:grab;touch-action:none;'
        'border:1px solid #cadbeb;background:#fff"></canvas>'
        '<input type="range" id="crop-zoom" min="1" max="3" step="0.01" value="1" '
        'style="width:260px;display:block;margin-top:10px"></div>%s'
        '<button class="btn btn-primary" type="submit">Save Member</button></form></div>'
        '<div class="admin-panel"><h2>All Members</h2><div class="admin-list">%s</div></div>'
        % ("Edit Member" if editing else "Add Team Member", csrf_field(token),
           editing.get("id", ""), esc(editing.get("name", "")), esc(editing.get("role", "")),
           options, esc(editing.get("bio", "")), editing.get("order", 10), current_photo, rows)
    )


def panel_pages(token, edit_id=None):
    # menu editor
    nav_rows = []
    for i, n in enumerate(nav_items()):
        nav_rows.append(
            '<div class="nav-edit-row">'
            '<input type="hidden" name="url__%d" value="%s">'
            '<input type="text" name="label__%d" value="%s" aria-label="Menu label">'
            '<input type="number" name="order__%d" value="%d" min="1" max="99" aria-label="Order">'
            '<label class="checkbox"><input type="checkbox" name="visible__%d" %s> Show</label>'
            '<span class="help-text">%s</span></div>'
            % (i, esc(n["url"]), i, esc(n["label"]), i, n["order"], i,
               "checked" if n["visible"] else "", esc(n["url"])))
    menu_panel = (
        '<div class="admin-panel"><h2>Menu</h2>'
        '<p class="help-text">Rename, reorder (lower number = further left), or hide any menu item. '
        'Custom pages appear here once "Show in menu" is ticked on the page.</p>'
        '<form method="post" action="/admin/nav/save" class="form">%s%s'
        '<button class="btn btn-primary" type="submit">Save Menu</button></form></div>'
        % (csrf_field(token), "".join(nav_rows)))

    # custom pages CRUD
    pages = _load("pages.json", [])
    editing = next((x for x in pages if x["id"] == edit_id), None) or {}
    rows = "".join(_item_row("pages", x, token, x["title"], "/p/%s" % x["slug"])
                   for x in pages) or '<div class="empty">No custom pages yet.</div>'
    checked = "checked" if editing.get("published", True) else ""
    in_nav = "checked" if editing.get("in_nav", True) else ""
    form_panel = (
        '<div class="admin-panel"><h2>%s</h2>'
        '<p class="help-text">A custom page gets its own address (shown in the list below) and can '
        'be added to the menu. Body supports the usual formatting.</p>'
        '<form method="post" action="/admin/pages/save" class="form">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Page Title<input type="text" name="title" required value="%s"></label>'
        '<label>Address Slug (letters, numbers, hyphens; e.g. "advisory-board")'
        '<input type="text" name="slug" value="%s" pattern="[a-z0-9-]*" placeholder="auto-generated from the title"></label>'
        '<label>Body<textarea name="body" rows="12" required>%s</textarea></label>'
        '<label class="checkbox"><input type="checkbox" name="in_nav" %s> Show in menu</label>'
        '<label class="checkbox"><input type="checkbox" name="published" %s> Published</label>'
        '<button class="btn btn-primary" type="submit">Save Page</button></form></div>'
        '<div class="admin-panel"><h2>All Custom Pages</h2><div class="admin-list">%s</div></div>'
        % ("Edit Page" if editing else "Add Custom Page", csrf_field(token),
           editing.get("id", ""), esc(editing.get("title", "")), esc(editing.get("slug", "")),
           esc(editing.get("body", "")), in_nav, checked, rows))
    return menu_panel + form_panel


def panel_sections(token, edit_id=None):
    secs = _load("sections.json", [])
    editing = next((x for x in secs if x["id"] == edit_id), None) or {}
    rows = "".join(_item_row("sections", x, token, x["title"],
                             "%s page · %s" % (x.get("page", "?").title(),
                                               SLOT_LABELS.get(x.get("slot", "bottom"), "")))
                   for x in secs) or '<div class="empty">No custom sections yet.</div>'
    page_opts = "".join('<option value="%s" %s>%s</option>'
                        % (p, "selected" if editing.get("page") == p else "", p.title())
                        for p in PAGE_NAMES)
    slot_opts = "".join('<option value="%s" %s>%s</option>'
                        % (v, "selected" if editing.get("slot", "bottom") == v else "", label)
                        for v, label in SLOT_LABELS.items())
    checked = "checked" if editing.get("published", True) else ""
    current_img = ('<p class="help-text">Current image: <a href="/uploads/%s" target="_blank">%s</a> '
                   '(uploading a new one replaces it)</p>' % (esc(editing["image"]), esc(editing["image"]))) \
        if editing.get("image") else ""
    return (
        '<div class="admin-panel"><h2>%s</h2>'
        '<p class="help-text">Add your own section to any page — an announcement, a call for papers, '
        'an initiative, anything. Pick the page and where it should sit; lower Display Order appears first '
        'when several sections share a spot. Body supports the usual formatting '
        '(<code>## heading</code>, <code>**bold**</code>, <code>- bullet</code>, links).</p>'
        '<form method="post" action="/admin/sections/save" class="form" enctype="multipart/form-data">%s'
        '<input type="hidden" name="id" value="%s">'
        '<label>Section Heading<input type="text" name="title" required value="%s"></label>'
        '<label>Small Label Above Heading (optional)<input type="text" name="eyebrow" value="%s" placeholder="e.g. Announcement"></label>'
        '<label>Show On Page<select name="page">%s</select></label>'
        '<label>Position<select name="slot">%s</select></label>'
        '<label>Display Order (lower appears first)<input type="number" name="order" value="%s" min="1" max="99"></label>'
        '<label>Body<textarea name="body" rows="8" required>%s</textarea></label>'
        '<label>Image (optional, shown below the text)<input type="file" name="image" accept="image/*"></label>%s'
        '<label class="checkbox"><input type="checkbox" name="published" %s> Published (visible on the website)</label>'
        '<button class="btn btn-primary" type="submit">Save Section</button></form></div>'
        '<div class="admin-panel"><h2>All Custom Sections</h2><div class="admin-list">%s</div></div>'
        % ("Edit Section" if editing else "Add Custom Section", csrf_field(token),
           editing.get("id", ""), esc(editing.get("title", "")), esc(editing.get("eyebrow", "")),
           page_opts, slot_opts, editing.get("order", 10), esc(editing.get("body", "")),
           current_img, checked, rows)
    )


def panel_site(token, edit_id=None):
    s = site()

    def field(label, name, rows=None, help_note=""):
        note = '<p class="help-text">%s</p>' % help_note if help_note else ""
        if rows:
            return ('<label>%s<textarea name="%s" rows="%d">%s</textarea></label>%s'
                    % (label, name, rows, esc(s[name]), note))
        return ('<label>%s<input type="text" name="%s" value="%s"></label>%s'
                % (label, name, esc(s[name]), note))

    logo_preview = ('<img class="logo-preview" src="/uploads/%s" alt="Current logo">' % esc(s["logo"])) \
        if s["logo"] else '<p class="help-text">No logo uploaded yet — the built-in CLTIBC seal is shown.</p>'
    remove_logo = ('<label class="checkbox"><input type="checkbox" name="remove_logo"> '
                   'Remove uploaded logo and use the built-in seal</label>') if s["logo"] else ""
    return (
        '<div class="admin-panel"><h2>Site Content</h2>'
        '<p class="help-text">Everything on the public pages is edited here. Leave a field as-is to keep '
        'the current text. Long fields accept the same formatting as blog posts '
        '(blank line = new paragraph, <code>**bold**</code>, <code>- bullet</code>).</p>'
        '<form method="post" action="/admin/site/save" class="form" enctype="multipart/form-data">%s'

        '<h3 class="form-section">Logo</h3>%s'
        '<label>Upload Logo (PNG/JPG, square, transparent background works best)'
        '<input type="file" name="logo" accept="image/*"></label>%s'

        '<h3 class="form-section">Homepage Hero</h3>%s%s%s'
        '<h3 class="form-section">Homepage Cards</h3>%s%s%s'
        '<h3 class="form-section">Homepage Call-to-Action Band</h3>%s%s'
        '<h3 class="form-section">About Page</h3>%s%s%s%s'
        '<h3 class="form-section">Submissions Page</h3>%s%s%s'
        '<h3 class="form-section">Contact &amp; Footer</h3>%s%s%s'
        '<h3 class="form-section">Search &amp; Social (SEO)</h3>%s%s%s%s'
        '<h3 class="form-section">Theme Colours</h3>'
        '<p class="help-text">Changes recolour the whole site instantly. '
        'Ink is used for text and buttons; band for page headers.</p>'
        '<div class="color-row">%s%s%s%s</div>'
        '<button class="btn btn-primary" type="submit">Save Site Content</button></form></div>'
        '%s'
        % (csrf_field(token), logo_preview, remove_logo,
           field("Hero Badge Line", "hero_kicker"),
           field("Hero Headline", "hero_title", rows=3),
           field("Hero Paragraph", "hero_sub", rows=4),
           field("Journal Card Text", "card_journal", rows=3),
           field("Blog Card Text", "card_blog", rows=3),
           field("Team Card Text", "card_team", rows=3),
           field("CTA Heading", "cta_title"),
           field("CTA Text", "cta_text", rows=3),
           field("Opening Paragraph (large serif)", "about_lede", rows=4),
           field("Main Text", "about_body", rows=8),
           field("Vision Statement", "vision", rows=3),
           field("Mission Statement", "mission", rows=3),
           field("Submissions Page Introduction", "submissions_intro", rows=3),
           field("Journal Submission Guidelines", "journal_guidelines", rows=10),
           field("Blog Submission Guidelines", "blog_guidelines", rows=6),
           field("Postal Address (one line per line)", "contact_address", rows=4),
           field("Contact Email", "contact_email"),
           field("Footer Description", "footer_desc", rows=4),
           field("Meta Description (what search engines show)", "seo_description", rows=3),
           field("Public Site Address (once live, e.g. https://cltibc.in — used for link previews)", "site_url"),
           field("LinkedIn URL", "social_linkedin"),
           field("Instagram URL", "social_instagram"),
           color_input("Ink", "theme_ink", s), color_input("Header Band", "theme_band", s),
           color_input("Accent", "theme_accent", s), color_input("Bright Accent", "theme_bright", s),
           attachments_panel(token, s))
    )


def color_input(label, name, s):
    return ('<label class="color-field">%s<input type="color" name="%s" value="%s"></label>'
            % (label, name, esc(s[name])))


def attachments_panel(token, s):
    rows = "".join(
        '<div class="admin-row"><div class="admin-row-info"><strong>%s</strong></div>'
        '<div class="admin-row-actions">'
        '<a class="btn btn-ghost btn-small" href="/uploads/%s" target="_blank">View</a>'
        '<form method="post" action="/admin/site/attachment-delete" '
        'onsubmit="return confirm(\'Remove this download?\')">%s'
        '<input type="hidden" name="file" value="%s">'
        '<button class="btn btn-danger btn-small" type="submit">Delete</button></form>'
        '</div></div>'
        % (esc(f["name"]), esc(f["file"]), csrf_field(token), esc(f["file"]))
        for f in s["submission_files"]) or '<div class="empty">No downloads yet.</div>'
    return (
        '<div class="admin-panel"><h2>Submission Downloads</h2>'
        '<p class="help-text">PDF or Word templates offered on the Submissions page '
        '(cover-letter formats, style guides, and so on).</p>'
        '<form method="post" action="/admin/site/attachment-add" class="form" enctype="multipart/form-data">%s'
        '<label>Add Files<input type="file" name="attachments" accept=".pdf,.docx" multiple></label>'
        '<button class="btn btn-primary" type="submit">Upload</button></form>'
        '<div class="admin-list" style="margin-top:18px">%s</div></div>'
        % (csrf_field(token), rows)
    )


def panel_messages(token, edit_id=None):
    messages = _load("messages.json", [])
    items = "".join(
        '<div class="msg-item"><div class="msg-head"><strong>%s &lt;%s&gt; — %s</strong>'
        '<span>%s</span></div><p class="msg-body">%s</p>'
        '<form method="post" action="/admin/messages/delete" style="margin-top:10px">%s'
        '<input type="hidden" name="id" value="%s">'
        '<button class="btn btn-danger btn-small" type="submit">Delete</button></form></div>'
        % (esc(m["name"]), esc(m["email"]), esc(m["subject"]), esc(m.get("received", "")),
           esc(m["message"]), csrf_field(token), m["id"])
        for m in reversed(messages)
    ) or '<div class="empty">No messages from the contact form yet.</div>'
    return '<div class="admin-panel"><h2>Contact Form Messages</h2>%s</div>' % items


FILE_LABELS = {"site.json": "Site content", "blog.json": "Blog posts",
               "journal.json": "Journal articles", "events.json": "Events",
               "team.json": "Team members", "sections.json": "Custom sections",
               "pages.json": "Custom pages", "nav.json": "Menu"}


def panel_settings(token, edit_id=None):
    snaps = sorted(os.listdir(HISTORY_DIR), reverse=True) if os.path.isdir(HISTORY_DIR) else []
    rows = []
    for snap in snaps[:40]:
        base = snap.split(".json.")[0] + ".json"
        stamp = snap.rsplit(".", 1)[-1]
        try:
            when = "%s-%s-%s %s:%s" % (stamp[0:4], stamp[4:6], stamp[6:8], stamp[9:11], stamp[11:13])
        except IndexError:
            when = stamp
        rows.append(
            '<div class="admin-row"><div class="admin-row-info"><strong>%s</strong>'
            '<span>saved %s</span></div><div class="admin-row-actions">'
            '<form method="post" action="/admin/restore" '
            'onsubmit="return confirm(\'Restore this version? The current state is saved to history first.\')">%s'
            '<input type="hidden" name="snap" value="%s">'
            '<button class="btn btn-ghost btn-small" type="submit">Restore</button></form>'
            '</div></div>'
            % (FILE_LABELS.get(base, base), when, csrf_field(token), esc(snap)))
    history = "".join(rows) or '<div class="empty">Every content edit will be listed here, restorable.</div>'
    return (
        '<div class="admin-panel"><h2>Change Admin Password</h2>'
        '<p class="help-text">You are the only person with access to this portal. '
        'Use a strong password you do not use anywhere else.</p>'
        '<form method="post" action="/admin/password" class="form">%s'
        '<label>Current Password<input type="password" name="current" required></label>'
        '<label>New Password (min 10 characters)<input type="password" name="new1" required minlength="10"></label>'
        '<label>Repeat New Password<input type="password" name="new2" required minlength="10"></label>'
        '<button class="btn btn-primary" type="submit">Update Password</button></form></div>'
        '<div class="admin-panel"><h2>Edit History</h2>'
        '<p class="help-text">The last %d versions of each content file are kept automatically. '
        'Restoring never destroys anything — the current version is itself saved first.</p>'
        '<div class="admin-list">%s</div></div>'
        % (csrf_field(token), HISTORY_KEEP, history)
    )


PANEL_EDITORS = {"blog": panel_blog, "journal": panel_journal, "events": panel_events,
                 "team": panel_team, "sections": panel_sections, "pages": panel_pages}


# ---------------------------------------------------------------- HTTP handler

class Handler(BaseHTTPRequestHandler):
    server_version = "CLTIBC/1.0"

    # ---- plumbing

    CSP = ("default-src 'self'; img-src 'self' data:; "
           "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
           "font-src https://fonts.gstatic.com; script-src 'self'; "
           "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")

    def respond(self, body, status=200, content_type="text/html; charset=utf-8", extra_headers=None):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", self.CSP)
        if SECURE_MODE:
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, extra_headers=None):
        self.send_response(303)
        self.send_header("Location", location)
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()

    def not_found(self):
        body = page("Not Found", '<section class="section"><div class="wrap narrow">'
                    '<h1>Page not found</h1><p style="margin-top:12px">'
                    '<a href="/">Return to the homepage</a></p></div></section>')
        self.respond(body, status=404)

    def session_cookie(self):
        c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return c["cltibc_session"].value if "cltibc_session" in c else ""

    def is_admin(self):
        return session_valid(self.session_cookie())

    def parse_form(self):
        """Returns (fields dict, files dict-of-lists) for urlencoded or multipart POSTs."""
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY:
            raise ValueError("request too large")
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            fs = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                  environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype})
            fields, files = {}, {}
            for key in fs.keys():
                for item in fs[key] if isinstance(fs[key], list) else [fs[key]]:
                    if item.filename:
                        files.setdefault(key, []).append((item.filename, item.file.read()))
                    else:
                        fields[key] = item.value
            return fields, files
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(min(length, 2_000_000)).decode("utf-8", "replace")
        parsed = urllib.parse.parse_qs(raw, keep_blank_values=True)
        return {k: v[0] for k, v in parsed.items()}, {}

    def save_upload(self, filename, content, allowed_exts):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_exts or not content or len(content) > 25_000_000:
            return None
        fname = safe_filename(filename)
        with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
            f.write(content)
        return fname

    def serve_file(self, directory, relpath):
        full = os.path.realpath(os.path.join(directory, relpath))
        if not full.startswith(os.path.realpath(directory) + os.sep) or not os.path.isfile(full):
            return self.not_found()
        ctypes = {".css": "text/css", ".js": "text/javascript",
                  ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
                  ".pdf": "application/pdf", ".svg": "image/svg+xml"}
        ext = os.path.splitext(full)[1].lower()
        ctype = ctypes.get(ext, "application/octet-stream")
        # CSS/JS change during design work — keep them fresh; media can cache longer.
        cache = "no-cache" if ext in (".css", ".js") else "public, max-age=3600"
        with open(full, "rb") as f:
            self.respond(f.read(), content_type=ctype,
                         extra_headers=[("Cache-Control", cache)])

    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def handle_safely(self, method):
        """Run a request handler; on failure log privately, show a plain error page."""
        try:
            method()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            import traceback
            try:
                with open(os.path.join(DATA_DIR, "error.log"), "a", encoding="utf-8") as f:
                    f.write("[%s] %s %s\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                                  self.command, self.path,
                                                  traceback.format_exc()))
            except OSError:
                pass
            try:
                self.respond(page("Error", '<section class="section"><div class="wrap narrow">'
                                  '<h1>Something went wrong</h1><p style="margin-top:12px">'
                                  'The problem has been recorded. <a href="/">Return home</a>.</p>'
                                  '</div></section>'), status=500)
            except Exception:
                pass

    # ---- GET

    def do_GET(self):
        self.handle_safely(self._do_get)

    def _do_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path.rstrip("/") or "/", urllib.parse.parse_qs(parsed.query)

        if path == "/":
            return self.respond(home_page())
        if path == "/about":
            return self.respond(about_page())
        if path == "/journal":
            return self.respond(journal_page())
        if path == "/blog":
            return self.respond(blog_page())
        if path.startswith("/blog/"):
            body = post_page(path.split("/")[2])
            return self.respond(body) if body else self.not_found()
        if path.startswith("/journal/read/"):
            art_id = path.split("/")[3]
            art = next((a for a in _load("journal.json", [])
                        if a["id"] == art_id and a.get("published") and a.get("pdf")), None)
            if not art:
                return self.not_found()
            bump_view(art_id)
            return self.redirect("/uploads/%s" % art["pdf"])
        if path == "/submissions":
            return self.respond(submissions_page())
        if path.startswith("/p/"):
            body = custom_page(path[3:])
            return self.respond(body) if body else self.not_found()
        if path == "/events":
            return self.respond(events_page())
        if path == "/team":
            return self.respond(team_page())
        if path == "/contact":
            sent = "sent" in query
            flash = flash_box("Thank you — your message has been received.") if sent else ""
            return self.respond(contact_page(flash))
        if path.startswith("/static/"):
            return self.serve_file(STATIC_DIR, path[len("/static/"):])
        if path.startswith("/uploads/"):
            return self.serve_file(UPLOAD_DIR, path[len("/uploads/"):])

        if path == "/admin":
            if not self.is_admin():
                flash = ""
                if "failed" in query:
                    flash = flash_box("Incorrect password.", error=True)
                elif "locked" in query:
                    flash = flash_box("Too many attempts. Try again in 15 minutes.", error=True)
                return self.respond(page("Admin Sign In", render(T.LOGIN, flash=flash)))
            token = csrf_token(self.session_cookie())
            tab = (query.get("tab") or ["blog"])[0]
            edit_id = (query.get("edit") or [None])[0]
            if edit_id and tab in PANEL_EDITORS:
                messages = _load("messages.json", [])
                badge = '<span class="badge">%d</span>' % len(messages) if messages else ""
                actives = {"active_%s" % n: ("active" if n == tab else "")
                           for n in ["site", "sections", "pages", "blog", "journal",
                                     "events", "team", "messages", "settings"]}
                body = render(T.ADMIN, panel=PANEL_EDITORS[tab](token, edit_id), flash="",
                              msg_badge=badge, csrf=csrf_field(token), **actives)
                return self.respond(page("Admin", body))
            saved = flash_box("Saved.") if "saved" in query else ""
            return self.respond(admin_page(tab, token, flash=saved))

        return self.not_found()

    # ---- POST

    def do_POST(self):
        self.handle_safely(self._do_post)

    def _do_post(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")

        if path == "/api/like":
            fields, _ = self.parse_form()
            item_id = fields.get("id", "")[:32]
            known = any(i["id"] == item_id
                        for i in _load("blog.json", []) + _load("journal.json", []))
            if not known:
                return self.respond('{"error":"unknown"}', status=404,
                                    content_type="application/json")
            delta = -1 if fields.get("action") == "unlike" else 1
            likes = change_like(item_id, delta)
            return self.respond(json.dumps({"likes": likes}),
                                content_type="application/json")

        if path == "/contact":
            fields, _ = self.parse_form()
            if all(fields.get(k, "").strip() for k in ("name", "email", "subject", "message")):
                messages = _load("messages.json", [])
                messages.append({
                    "id": new_id(),
                    "name": fields["name"][:120], "email": fields["email"][:200],
                    "subject": fields["subject"][:200], "message": fields["message"][:5000],
                    "received": time.strftime("%Y-%m-%d %H:%M"),
                })
                _save("messages.json", messages)
            return self.redirect("/contact?sent=1")

        if path == "/admin/login":
            ip = self.client_address[0]
            now = time.time()
            with LOGIN_LOCK:
                fails, until = LOGIN_FAILS.get(ip, (0, 0))
                if fails >= MAX_FAILS and now < until:
                    return self.redirect("/admin?locked=1")
            fields, _ = self.parse_form()
            attempt = hash_password(fields.get("password", ""), CONFIG["salt"])
            if hmac.compare_digest(attempt, CONFIG["password_hash"]):
                with LOGIN_LOCK:
                    LOGIN_FAILS.pop(ip, None)
                cookie_val = make_session_cookie()
                secure = "; Secure" if SECURE_MODE else ""
                return self.redirect("/admin", extra_headers=[
                    ("Set-Cookie", "cltibc_session=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d%s"
                     % (cookie_val, SESSION_HOURS * 3600, secure))])
            with LOGIN_LOCK:
                fails, _ = LOGIN_FAILS.get(ip, (0, 0))
                LOGIN_FAILS[ip] = (fails + 1, now + LOCKOUT_SECONDS)
            time.sleep(1.5)  # slow down guessing
            return self.redirect("/admin?failed=1")

        # everything below requires a valid admin session + CSRF token
        if not self.is_admin():
            return self.redirect("/admin")
        fields, files = self.parse_form()
        if not hmac.compare_digest(fields.get("csrf", ""), csrf_token(self.session_cookie())):
            return self.respond("Invalid request token. Go back and retry.", status=403,
                                content_type="text/plain")

        if path == "/admin/logout":
            return self.redirect("/admin", extra_headers=[
                ("Set-Cookie", "cltibc_session=; Path=/; HttpOnly; Max-Age=0")])

        if path == "/admin/password":
            attempt = hash_password(fields.get("current", ""), CONFIG["salt"])
            new1, new2 = fields.get("new1", ""), fields.get("new2", "")
            if not hmac.compare_digest(attempt, CONFIG["password_hash"]) or new1 != new2 or len(new1) < 10:
                return self.redirect("/admin?tab=settings")
            CONFIG["salt"] = secrets.token_hex(16)
            CONFIG["password_hash"] = hash_password(new1, CONFIG["salt"])
            _save("config.json", CONFIG)
            return self.redirect("/admin?tab=settings&saved=1")

        if path == "/admin/site/save":
            stored = _load("site.json", {})
            for key in SITE_DEFAULTS:
                if key != "logo" and key in fields:
                    stored[key] = fields[key].strip()
            if files.get("logo"):
                saved = self.save_upload(*files["logo"][0], IMAGE_EXTS)
                if saved:
                    stored["logo"] = saved
            elif "remove_logo" in fields:
                stored["logo"] = ""
            _save("site.json", stored)
            return self.redirect("/admin?tab=site&saved=1")

        if path == "/admin/nav/save":
            entries = []
            i = 0
            while "url__%d" % i in fields:
                entries.append({
                    "url": fields["url__%d" % i][:200],
                    "label": fields.get("label__%d" % i, "").strip()[:60],
                    "order": int(fields.get("order__%d" % i) or 50),
                    "visible": ("visible__%d" % i) in fields,
                })
                i += 1
            if entries:
                _save("nav.json", entries)
            return self.redirect("/admin?tab=pages&saved=1")

        if path == "/admin/pages/save":
            title = fields.get("title", "").strip()
            slug = re.sub(r"[^a-z0-9-]", "-", (fields.get("slug") or title).lower()).strip("-")
            slug = re.sub(r"-+", "-", slug)[:60] or new_id()
            items = _load("pages.json", [])
            # keep slugs unique across other pages
            if any(p["slug"] == slug and p["id"] != fields.get("id") for p in items):
                slug = "%s-%s" % (slug, new_id()[:4])
            return self.crud_save("pages.json", "pages", {
                "title": title,
                "slug": slug,
                "body": fields.get("body", ""),
                "in_nav": "in_nav" in fields,
                "published": "published" in fields,
            }, fields.get("id"))

        if path == "/admin/site/attachment-add":
            stored = _load("site.json", {})
            existing = stored.get("submission_files", [])
            for fname, content in files.get("attachments", []):
                saved = self.save_upload(fname, content, DOC_EXTS)
                if saved:
                    existing.append({"name": os.path.basename(fname)[:80], "file": saved})
            stored["submission_files"] = existing
            _save("site.json", stored)
            return self.redirect("/admin?tab=site&saved=1")

        if path == "/admin/site/attachment-delete":
            stored = _load("site.json", {})
            stored["submission_files"] = [f for f in stored.get("submission_files", [])
                                          if f["file"] != fields.get("file")]
            _save("site.json", stored)
            return self.redirect("/admin?tab=site&saved=1")

        if path == "/admin/restore":
            snap = fields.get("snap", "")
            if not re.fullmatch(r"[a-z]+\.json\.\d{8}-\d{6}", snap):
                return self.redirect("/admin?tab=settings")
            src = os.path.join(HISTORY_DIR, snap)
            if not os.path.exists(src):
                return self.redirect("/admin?tab=settings")
            target = snap.split(".json.")[0] + ".json"
            with open(src, "r", encoding="utf-8") as f:
                content = json.load(f)
            _save(target, content)   # snapshots current state first
            return self.redirect("/admin?tab=settings&saved=1")

        if path == "/admin/sections/save":
            extra = {
                "title": fields.get("title", "").strip(),
                "eyebrow": fields.get("eyebrow", "").strip(),
                "page": fields.get("page") if fields.get("page") in PAGE_NAMES else "home",
                "slot": fields.get("slot") if fields.get("slot") in SLOT_LABELS else "bottom",
                "order": int(fields.get("order") or 10),
                "body": fields.get("body", ""),
                "published": "published" in fields,
            }
            items = _load("sections.json", [])
            existing = next((x for x in items if x["id"] == fields.get("id")), None)
            if files.get("image"):
                saved = self.save_upload(*files["image"][0], IMAGE_EXTS)
                if saved:
                    extra["image"] = saved
            elif existing:
                extra["image"] = existing.get("image", "")
            return self.crud_save("sections.json", "sections", extra, fields.get("id"))

        if path == "/admin/blog/save":
            extra = {
                "title": fields.get("title", "").strip(),
                "author": fields.get("author", "").strip(),
                "date": fields.get("date", date.today().isoformat()),
                "body": fields.get("body", ""),
                "published": "published" in fields,
            }
            existing = next((p for p in _load("blog.json", [])
                             if p["id"] == fields.get("id")), None)
            if files.get("image"):
                saved = self.save_upload(*files["image"][0], IMAGE_EXTS)
                if saved:
                    extra["image"] = saved
            elif existing:
                extra["image"] = existing.get("image", "")
            return self.crud_save("blog.json", "blog", extra, fields.get("id"))

        if path == "/admin/journal/save":
            extra = {
                "title": fields.get("title", "").strip(),
                "authors": fields.get("authors", "").strip(),
                "issue": fields.get("issue", "").strip(),
                "date": fields.get("date", date.today().isoformat()),
                "abstract": fields.get("abstract", ""),
                "published": "published" in fields,
            }
            existing = next((a for a in _load("journal.json", [])
                             if a["id"] == fields.get("id")), None)
            if files.get("pdf"):
                saved = self.save_upload(*files["pdf"][0], DOC_EXTS)
                if saved:
                    extra["pdf"] = saved
            elif existing:
                extra["pdf"] = existing.get("pdf", "")
            if files.get("image"):
                saved = self.save_upload(*files["image"][0], IMAGE_EXTS)
                if saved:
                    extra["image"] = saved
            elif existing:
                extra["image"] = existing.get("image", "")
            return self.crud_save("journal.json", "journal", extra, fields.get("id"))

        if path == "/admin/events/save":
            new_photos = [self.save_upload(fn, content, IMAGE_EXTS)
                          for fn, content in files.get("photos", [])]
            new_photos = [p for p in new_photos if p]
            items = _load("events.json", [])
            existing = next((e for e in items if e["id"] == fields.get("id")), None)
            photos = (existing.get("photos", []) if existing else []) + new_photos
            return self.crud_save("events.json", "events", {
                "title": fields.get("title", "").strip(),
                "date": fields.get("date", date.today().isoformat()),
                "description": fields.get("description", ""),
                "photos": photos,
            }, fields.get("id"))

        if path == "/admin/events/photo-delete":
            items = _load("events.json", [])
            for e in items:
                if e["id"] == fields.get("id"):
                    e["photos"] = [p for p in e.get("photos", []) if p != fields.get("photo")]
            _save("events.json", items)
            return self.redirect("/admin?tab=events&edit=%s" % fields.get("id", ""))

        if path == "/admin/team/save":
            extra = {
                "name": fields.get("name", "").strip(),
                "role": fields.get("role", "").strip(),
                "category": fields.get("category", TEAM_CATEGORIES[0]),
                "bio": fields.get("bio", "").strip(),
                "order": int(fields.get("order") or 10),
            }
            items = _load("team.json", [])
            existing = next((m for m in items if m["id"] == fields.get("id")), None)
            if files.get("photo"):
                saved = self.save_upload(*files["photo"][0], IMAGE_EXTS)
                if saved:
                    extra["photo"] = saved
            elif existing:
                extra["photo"] = existing.get("photo", "")
            return self.crud_save("team.json", "team", extra, fields.get("id"))

        if path in ("/admin/blog/delete", "/admin/journal/delete",
                    "/admin/events/delete", "/admin/team/delete",
                    "/admin/messages/delete", "/admin/sections/delete",
                    "/admin/pages/delete"):
            kind = path.split("/")[2]
            fname = {"blog": "blog.json", "journal": "journal.json", "events": "events.json",
                     "team": "team.json", "messages": "messages.json",
                     "sections": "sections.json", "pages": "pages.json"}[kind]
            items = [i for i in _load(fname, []) if i["id"] != fields.get("id")]
            _save(fname, items)
            return self.redirect("/admin?tab=%s&saved=1" % kind)

        return self.not_found()

    def crud_save(self, fname, tab, data, item_id):
        if not data.get("title") and not data.get("name"):
            return self.redirect("/admin?tab=%s" % tab)
        items = _load(fname, [])
        existing = next((i for i in items if i["id"] == item_id), None)
        if existing:
            existing.update(data)
        else:
            data["id"] = new_id()
            items.append(data)
        _save(fname, items)
        return self.redirect("/admin?tab=%s&saved=1" % tab)


# ---------------------------------------------------------------- backups

BACKUP_KEEP = 10
BACKUP_EVERY = 24 * 3600


def backup_dir():
    """Prefer a folder inside Google Drive (if Drive for desktop is installed),
    else fall back to ~/CLTIBC-backups on this Mac."""
    import glob
    for drive in sorted(glob.glob(os.path.expanduser(
            "~/Library/CloudStorage/GoogleDrive-*/My Drive"))):
        return os.path.join(drive, "CLTIBC backups")
    return os.path.expanduser("~/CLTIBC-backups")


def run_backup():
    import shutil
    import tempfile
    target = backup_dir()
    os.makedirs(target, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    with tempfile.TemporaryDirectory() as tmp:
        staging = os.path.join(tmp, "cltibc-content")
        os.makedirs(staging)
        for src in (DATA_DIR, UPLOAD_DIR):
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(staging, os.path.basename(src)))
        archive = shutil.make_archive(os.path.join(tmp, "cltibc-backup-" + stamp),
                                      "zip", tmp, "cltibc-content")
        final = os.path.join(target, os.path.basename(archive))
        shutil.move(archive, final)
    old = sorted(f for f in os.listdir(target)
                 if f.startswith("cltibc-backup-") and f.endswith(".zip"))
    for name in old[:-BACKUP_KEEP]:
        os.remove(os.path.join(target, name))
    return final


def backup_loop():
    while True:
        try:
            path = run_backup()
            print("Backup saved: %s" % path)
        except Exception as exc:
            print("Backup failed: %s" % exc)
        time.sleep(BACKUP_EVERY)


def main():
    import sys
    if "--backup" in sys.argv:
        print("Backup saved: %s" % run_backup())
        return
    threading.Thread(target=backup_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8452"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("CLTIBC website running at http://localhost:%d  (admin: /admin)" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()
