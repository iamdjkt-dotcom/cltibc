# HTML templates for the CLTIBC website.
# Placeholders use {{key}} and are filled by render() in server.py.

# Recreation of the CLTIBC seal: gold ring, interlocked monogram, caption.
# Caption colour follows --logo-ink so it stays legible on umber (hero) and cream.
LOGO_SVG = """<svg class="seal" viewBox="0 0 420 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Centre for LexTax and IBC seal">
  <defs>
    <linearGradient id="sealGold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#c9a961"/>
      <stop offset=".5" stop-color="#a8843c"/>
      <stop offset="1" stop-color="#8a6c2f"/>
    </linearGradient>
  </defs>
  <circle class="seal-ring" cx="210" cy="210" r="188" fill="none" stroke="url(#sealGold)" stroke-width="9" stroke-linecap="round"/>
  <g class="seal-mono">
    <text x="210" y="212" text-anchor="middle" font-family="'Playfair Display', Georgia, serif"
          font-size="118" font-weight="600" fill="url(#sealGold)"
          textLength="290" lengthAdjust="spacingAndGlyphs">CLTIBC</text>
  </g>
  <g class="seal-caption" font-family="'EB Garamond', Georgia, serif" fill="var(--logo-ink, #384959)">
    <text x="210" y="292" text-anchor="middle" font-size="35" letter-spacing="2">CENTRE <tspan font-style="italic" font-size="31">for</tspan></text>
    <text x="210" y="332" text-anchor="middle" font-size="35" letter-spacing="2">LEXTAX <tspan font-style="italic" font-size="31">and</tspan> IBC</text>
  </g>
</svg>"""

# Small mark for the top bar (ring + monogram only).
MARK_SVG = """<svg class="brand-mark" viewBox="0 0 420 420" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="210" cy="210" r="186" fill="none" stroke="#b08d45" stroke-width="16"/>
  <text x="210" y="248" text-anchor="middle" font-family="'Playfair Display', Georgia, serif"
        font-size="112" font-weight="600" fill="#b08d45"
        textLength="280" lengthAdjust="spacingAndGlyphs">CLTIBC</text>
</svg>"""

# Small ring-and-dot flourish used as a soft divider between sections.
DIVIDER = """<div class="flourish" aria-hidden="true"><svg viewBox="0 0 120 24" xmlns="http://www.w3.org/2000/svg">
  <line x1="0" y1="12" x2="44" y2="12" stroke="#c9a961" stroke-width="1"/>
  <circle cx="60" cy="12" r="7" fill="none" stroke="#a8843c" stroke-width="1.5"/>
  <circle cx="60" cy="12" r="2" fill="#a8843c"/>
  <line x1="76" y1="12" x2="120" y2="12" stroke="#c9a961" stroke-width="1"/>
</svg></div>"""

BASE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}} — Centre for LexTax &amp; IBC</title>
{{meta}}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500;1,600&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css?v=14">
<style>{{theme_css}}</style>
</head>
<body>
<header class="topbar" id="topbar">
  <div class="wrap topbar-inner">
    <a class="brand" href="/">{{brand_mark}}<span>Centre for LexTax &amp; IBC</span></a>
    <button class="nav-toggle" id="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">
      <span></span><span></span><span></span>
    </button>
    <nav class="nav" id="site-nav">{{nav}}</nav>
  </div>
</header>
<main>{{content}}</main>
<footer class="footer">
  <div class="wrap footer-grid">
    <div>
      <p class="footer-brand">Centre for LexTax &amp; IBC</p>
      <p class="footer-desc">{{footer_desc}}</p>
    </div>
    <div>
      <p class="footer-head">Explore</p>
      <ul class="footer-links">
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/journal">Journal</a></li>
        <li><a href="/blog">Blog</a></li>
        <li><a href="/events">Events</a></li>
        <li><a href="/team">Team</a></li>
        <li><a href="/contact">Contact</a></li>
      </ul>
    </div>
    <div>
      <p class="footer-head">Connect</p>
      <div class="social-links">{{social}}</div>
      <p class="footer-head" style="margin-top:22px">Management</p>
      <a class="admin-link" href="/admin">Admin Portal</a>
    </div>
  </div>
  <div class="wrap footer-bottom">
    <span class="footer-copy">{{uni_footer}}&copy; 2026 Centre for LexTax &amp; IBC, MNLU Mumbai.</span>
    <span class="footer-motto">Research &middot; Training &middot; Policy</span>
  </div>
</footer>
<script src="/static/app.js?v=14" defer></script>
</body>
</html>"""

HOME = """
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <div class="hero-affil seq seq-1">{{uni_mark}}<span class="eyebrow eyebrow-light">{{hero_kicker}}</span></div>
      <h1 class="hero-title seq seq-2">{{hero_title}}</h1>
      <p class="hero-sub seq seq-3">{{hero_sub}}</p>
      <div class="hero-actions seq seq-4">
        <a class="btn btn-primary" href="/journal#submissions">Submit to Journal</a>
        <a class="btn btn-ghost" href="/about">Learn more</a>
      </div>
    </div>
    <div class="hero-logo">{{logo}}</div>
  </div>
</section>

<section class="offerings">
  <div class="wrap offer-grid">
    <article class="offering" data-reveal>
      <span class="eyebrow">The Journal</span>
      <h3><a href="/journal">Indian Review of Taxation and Insolvency Law</a></h3>
      <p>{{card_journal}}</p>
      <a class="textlink" href="/journal#submissions">Submission guidelines</a>
    </article>
    <article class="offering" data-reveal>
      <span class="eyebrow">The Blog</span>
      <h3><a href="/blog">The JurisFiscus Blog</a></h3>
      <p>{{card_blog}}</p>
      <a class="textlink" href="/blog#submissions">Submission guidelines</a>
    </article>
    <article class="offering" data-reveal>
      <span class="eyebrow">Our People</span>
      <h3><a href="/team">Expert Leadership</a></h3>
      <p>{{card_team}}</p>
      <a class="textlink" href="/team">Meet the team</a>
    </article>
  </div>
</section>

"""  +  """

<section class="pull" data-reveal>
  <div class="wrap pull-inner">
    <p class="pull-quote">{{about_lede}}</p>
    <a class="textlink" href="/about">About the Centre</a>
  </div>
</section>

{{journal_latest}}
{{latest}}

<section class="cta" data-reveal>
  <div class="wrap cta-inner">
    <div>
      <h2 class="cta-title">{{cta_title}}</h2>
      <p class="cta-text">{{cta_text}}</p>
    </div>
    <a class="btn btn-dark" href="/contact">Get in touch</a>
  </div>
</section>
"""

LATEST_SECTION = """
<section class="section">
  <div class="wrap">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">Latest</span>
      <h2>Recent from the Blog</h2>
    </div>
    <div class="post-grid">{{posts}}</div>
  </div>
</section>
"""

JOURNAL_LATEST_SECTION = """
<section class="section">
  <div class="wrap">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">The Review</span>
      <h2>From the Journal</h2>
    </div>
    <div class="post-grid">{{articles}}</div>
  </div>
</section>
"""

ABOUT = """
<section class="page-hero">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Our Centre &middot; Vision &middot; Mission</span>
    <h1 class="seq seq-2">About the Centre</h1>
  </div>
</section>
<section class="section">
  <div class="wrap narrow-wide">
    <p class="pull-quote" data-reveal>{{about_lede}}</p>
    <div class="prose about-prose" data-reveal>{{about_body}}</div>
  </div>
</section>
"""  +  """
<section class="section creed">
  <div class="wrap creed-grid">
    <div class="creed-item" data-reveal>
      <span class="eyebrow">Our Vision</span>
      <p>{{vision}}</p>
    </div>
    <div class="creed-item" data-reveal>
      <span class="eyebrow">Our Mission</span>
      <p>{{mission}}</p>
    </div>
  </div>
</section>
"""

JOURNAL = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">The Flagship Publication</span>
    <h1 class="seq seq-2">Indian Review of Taxation and Insolvency Law</h1>
    <p class="page-hero-sub seq seq-3">Under the aegis of the Centre for LexTax &amp; IBC</p>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">Scholarship</span>
      <h2>Articles &amp; Papers</h2>
    </div>
    <div class="post-grid">{{articles}}</div>
  </div>
</section>
"""  +  """
<section class="section" id="submissions">
  <div class="wrap narrow">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">Call for Papers</span>
      <h2>Submission Guidelines</h2>
    </div>
    <div class="prose" data-reveal>{{journal_guidelines}}</div>
  </div>
</section>
"""

BLOG = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Commentary &amp; Analysis</span>
    <h1 class="seq seq-2">The JurisFiscus Blog</h1>
    <p class="page-hero-sub seq seq-3">Short-form commentary on tax law and the Insolvency &amp; Bankruptcy Code</p>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="post-grid">{{posts}}</div>
  </div>
</section>
"""  +  """
<section class="section" id="submissions">
  <div class="wrap narrow">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">Contribute</span>
      <h2>Write for the Blog</h2>
    </div>
    <div class="prose" data-reveal>{{blog_guidelines}}</div>
  </div>
</section>
"""

POST_PAGE = """
<section class="page-hero page-hero-left">
  <div class="wrap narrow">
    <span class="eyebrow eyebrow-light seq seq-1">The JurisFiscus Blog</span>
    <h1 class="post-title seq seq-2">{{title}}</h1>
    <p class="page-hero-sub seq seq-3">{{author}} &middot; {{date}}</p>
    <div class="post-stats seq seq-4">{{stats}}</div>
  </div>
</section>
<section class="section">
  <div class="wrap narrow">
    {{cover}}
    <div class="prose post-body">{{body}}</div>
    <p class="backlink"><a class="textlink textlink-back" href="/blog">All posts</a></p>
  </div>
</section>
"""

EVENTS = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Lectures &middot; Workshops &middot; Conferences</span>
    <h1 class="seq seq-2">Events</h1>
    <p class="page-hero-sub seq seq-3">Engagements hosted and organised by the Centre</p>
  </div>
</section>
<section class="section">
  <div class="wrap">{{events}}</div>
</section>
"""

TEAM = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Our People</span>
    <h1 class="seq seq-2">The Team</h1>
    <p class="page-hero-sub seq seq-3">Distinguished faculty, patrons, and student members dedicated to legal excellence</p>
  </div>
</section>
<section class="section">
  <div class="wrap">{{groups}}</div>
</section>
"""

CONTACT = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Enquiries &middot; Collaborations &middot; Submissions</span>
    <h1 class="seq seq-2">Contact Us</h1>
  </div>
</section>
<section class="section">
  <div class="wrap contact-grid">
    <div data-reveal>
      <div class="sec-head">
        <span class="eyebrow">The Centre</span>
        <h2>Reach the Centre</h2>
      </div>
      <div class="prose">
        <p>{{contact_address}}</p>
        <p><strong>Email:</strong> <a href="mailto:{{contact_email}}">{{contact_email}}</a></p>
        <p>For journal and blog submissions, please consult the respective <a href="/journal#submissions">journal</a> and <a href="/blog#submissions">blog</a> guidelines before writing to us.</p>
      </div>
    </div>
    <div data-reveal>
      <div class="sec-head">
        <span class="eyebrow">Write to Us</span>
        <h2>Send a Message</h2>
      </div>
      {{flash}}
      <form method="post" action="/contact" class="form">
        <label>Name<input type="text" name="name" required maxlength="120"></label>
        <label>Email<input type="email" name="email" required maxlength="200"></label>
        <label>Subject<input type="text" name="subject" required maxlength="200"></label>
        <label>Message<textarea name="message" rows="6" required maxlength="5000"></textarea></label>
        <button class="btn btn-primary" type="submit">Send message</button>
      </form>
    </div>
  </div>
</section>
"""

LOGIN = """
<section class="section login-section">
  <div class="login-card">
    <span class="eyebrow">Restricted Access</span>
    <h1>Admin Portal</h1>
    <p class="login-note">This area is reserved for the Centre&rsquo;s administrator.</p>
    {{flash}}
    <form method="post" action="/admin/login" class="form">
      <label>Password<input type="password" name="password" required autofocus></label>
      <button class="btn btn-primary btn-block" type="submit">Sign in</button>
    </form>
  </div>
</section>
"""

ADMIN = """
<section class="admin">
  <div class="wrap admin-grid">
    <aside class="admin-side">
      <p class="admin-side-head">Manage</p>
      <nav class="admin-nav">
        <a href="/admin?tab=site" class="{{active_site}}">Site Content</a>
        <a href="/admin?tab=sections" class="{{active_sections}}">Custom Sections</a>
        <a href="/admin?tab=pages" class="{{active_pages}}">Pages &amp; Menu</a>
        <a href="/admin?tab=blog" class="{{active_blog}}">Blog Posts</a>
        <a href="/admin?tab=journal" class="{{active_journal}}">Journal Articles</a>
        <a href="/admin?tab=events" class="{{active_events}}">Events &amp; Photos</a>
        <a href="/admin?tab=team" class="{{active_team}}">Team Members</a>
        <a href="/admin?tab=messages" class="{{active_messages}}">Messages {{msg_badge}}</a>
        <a href="/admin?tab=settings" class="{{active_settings}}">Settings</a>
      </nav>
      <form method="post" action="/admin/logout">{{csrf}}<button class="btn btn-ghost btn-block" type="submit">Sign out</button></form>
    </aside>
    <div class="admin-main">
      {{flash}}
      {{panel}}
    </div>
  </div>
</section>
<script src="/static/admin.js?v=1" defer></script>
"""


SUBMISSIONS = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <span class="eyebrow eyebrow-light seq seq-1">Write for the Centre</span>
    <h1 class="seq seq-2">Submission Guidelines</h1>
    <p class="page-hero-sub seq seq-3">{{intro}}</p>
  </div>
</section>
<section class="section">
  <div class="wrap narrow">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">The Journal</span>
      <h2>Indian Review of Taxation and Insolvency Law</h2>
    </div>
    <div class="prose" data-reveal>{{journal_guidelines}}</div>
  </div>
</section>
<section class="section">
  <div class="wrap narrow">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">The Blog</span>
      <h2>The JurisFiscus Blog</h2>
    </div>
    <div class="prose" data-reveal>{{blog_guidelines}}</div>
  </div>
</section>
{{files}}
"""

CUSTOM_PAGE = """
<section class="page-hero page-hero-left">
  <div class="wrap">
    <h1 class="seq seq-1">{{title}}</h1>
  </div>
</section>
<section class="section">
  <div class="wrap narrow-wide">
    <div class="prose" data-reveal>{{body}}</div>
  </div>
</section>
"""
