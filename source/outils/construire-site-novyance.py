#!/usr/bin/env python3
"""Novyance · construit le site statique novyance.fr (hors Shopify) pour GitHub Pages.

Usage : python3 outils/construire-site-novyance.py <dossier de sortie> [--tout]

Sources : theme-v18/templates (accueil, sites, apporteurs, recommandé, exemple), puis theme/ pour le reste
(outils métier, démos, blog, extraits). Les articles viennent de seo/articles (*.json + *.html).
Sans --tout, seuls les articles dont la date de parution est passée sont publiés (reconstruire chaque jour).
Rien n'est envoyé nulle part : le script ne fait qu'écrire des fichiers dans le dossier de sortie.
"""
import datetime, html, json, re, shutil, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SITE = "https://novyance.fr"
CONTACT_URL = "https://sqxlavinbiryvmblmtse.supabase.co/functions/v1/contact"
PARIS = datetime.timezone(datetime.timedelta(hours=1))

# gabarit -> adresse (mêmes adresses que sur Shopify, pour ne rien casser)
PAGES = {
    "theme-v18/templates/index.liquid": "/",
    "theme-v18/templates/page.sites.liquid": "/pages/creation-site-internet-lyon",
    "theme-v18/templates/page.apporteurs.liquid": "/pages/apporteurs-affaires",
    "theme-v18/templates/page.recommande.liquid": "/pages/recommande",
    "theme-v18/templates/page.exemple.liquid": "/pages/exemple",
    "theme/templates/page.outils-metier.liquid": "/pages/outils-metier",
    "theme/templates/page.demo-atelier.liquid": "/pages/demo-atelier",
    "theme/templates/page.demo-commercial.liquid": "/pages/demo-commercial",
    "theme/templates/page.demo-pilotage.liquid": "/pages/demo-pilotage",
}
# pages dont le texte vit dans Shopify : copie du site en ligne (seo/live), nettoyée des scripts Shopify
LIVE = {
    "seo/live/pages_site-internet-artisan.html": "/pages/site-internet-artisan",
    "seo/live/pages_boutique-en-ligne-commercant.html": "/pages/boutique-en-ligne-commercant",
    "seo/live/pages_automatisation-ia-entreprise.html": "/pages/automatisation-ia-entreprise",
    "seo/live/pages_application-pilotage-sur-mesure.html": "/pages/application-pilotage-sur-mesure",
    "seo/live/pages_crm-sur-mesure.html": "/pages/crm-sur-mesure",
    "seo/live/pages_prospection-automatisee.html": "/pages/prospection-automatisee",
    "seo/live/pages_etude-de-cas-vangart.html": "/pages/etude-de-cas-vangart",
    "seo/live/pages_mentions-legales.html": "/pages/mentions-legales",
}
# adresses courtes -> vraie page (GitHub Pages ne fait pas de redirection : page qui renvoie aussitôt, hors plan du site)
REDIRECTIONS = {
    "/pages/site-internet": "/pages/creation-site-internet-lyon",  # lien des mails de la campagne sites (docs/CAMPAGNE-SITES.md)
}
ASSETS = ["theme/assets", "theme-v18/assets"]  # le second écrase le premier
ENTETE_FORM = ' method="post" action="%s" data-nv-contact' % CONTACT_URL


def lire(chemin):
    return (RACINE / chemin).read_text(encoding="utf-8")


def liquid(t, url, snippets=True):
    """Traduit les quelques balises Liquid utilisées par les gabarits en HTML fixe."""
    t = re.sub(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", "", t, flags=re.S)
    t = re.sub(r"\{%-?\s*(layout none|raw|endraw)\s*-?%\}", "", t)
    t = re.sub(r"\{%-?\s*assign [^%]*?-?%\}", "", t)
    if snippets:
        t = re.sub(r"\{%-?\s*render 'nv-parrainage-styles'\s*-?%\}", lambda m: liquid(lire("theme/snippets/nv-parrainage-styles.liquid"), url, False), t)
        t = re.sub(r"\{%-?\s*render 'nv-mnav'\s*-?%\}", lambda m: liquid(lire("theme/snippets/nv-mnav.liquid"), url, False), t)
    t = t.replace("{{ content_for_header }}", "")
    # gabarit « outils métier » : titre, description et adresse viennent de la page Shopify, on garde les valeurs par défaut
    t = re.sub(r"\{\{\s*page\.metafields\.[a-z_.]+\s*\|\s*default:\s*'((?:[^'\\]|\\.)*)'\s*\}\}", r"\1", t)
    t = t.replace("{{ shop.url | append: page.url | json }}", json.dumps(SITE + url)).replace("{{ shop.url }}{{ page.url }}", SITE + url)
    t = re.sub(r"\{%\s*if form\.posted_successfully\s*%\}.*?\{%\s*endif\s*%\}", "", t, flags=re.S)
    t = t.replace("{{ canonical_url }}", SITE + url)
    t = re.sub(r"\{\{\s*'([^']+)'\s*\|\s*asset_url\s*\|\s*prepend:\s*'https?:'\s*\|\s*json\s*\}\}", lambda m: json.dumps(SITE + "/assets/" + m.group(1)), t)
    t = re.sub(r"\{\{\s*'([^']+)'\s*\|\s*asset_url(?:\s*\|\s*prepend:\s*'https?:')?\s*\}\}", r"/assets/\1", t)
    t = t.replace("{{ shop.url | append: blog.url | json }}", json.dumps(SITE + "/blogs/blog"))
    # formulaires de contact Shopify -> formulaire envoyé à Supabase (voir assets/nv-contact.js)
    t = re.sub(r"\{%-?\s*form 'contact',\s*id:\s*'([^']+)'(?:,\s*class:\s*'([^']+)')?\s*-?%\}",
               lambda m: '<form id="%s"%s%s>' % (m.group(1), ' class="%s"' % m.group(2) if m.group(2) else "", ENTETE_FORM), t)
    t = re.sub(r"\{%-?\s*endform\s*-?%\}", "</form>", t)
    t = re.sub(r"\{%-?\s*if form\.posted_successfully\?\s*-?%\}.*?\{%-?\s*endif\s*-?%\}", "", t, flags=re.S)
    t = re.sub(r"\{%-?\s*if form\.errors\s*-?%\}(.*?)\{%-?\s*endif\s*-?%\}", r'<span hidden data-err>\1</span>', t, flags=re.S)
    # accueil : lien blog et mentions légales (la page « mentions-legales » Shopify n'existe pas : fenêtre intégrée)
    t = re.sub(r"\{%\s*if nvblog\.articles_count > 0\s*%\}(.*?)\{%\s*endif\s*%\}", lambda m: m.group(1).replace("{{ nvblog.url }}", "/blogs/blog"), t, flags=re.S)
    t = re.sub(r"\{%\s*if ml\.published_at.*?%\}.*?\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}", r"\1", t, flags=re.S)
    t = re.sub(r"\{%\s*if ml\.published_at[^%]*%\}.*?\{%\s*endif\s*%\}", "", t, flags=re.S)
    t = t.replace("Shopify International Ltd, Victoria Buildings, 1-2 Haddington Road, Dublin 4, D04 XN32, Irlande.",
                  "GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.")
    return t


def nettoyer(t, url):
    """Page rendue par Shopify -> HTML propre : sans scripts, métas et liens Shopify, formulaires vers Supabase."""
    def script(m):
        attrs, corps = m.group(1), m.group(2)
        return m.group(0) if ("ld+json" in attrs or "nvb" in corps) else ""
    t = re.sub(r"<script([^>]*)>(.*?)</script>", script, t, flags=re.S)
    t = re.sub(r'<link rel="ucp"[^>]*>', "", t)
    t = re.sub(r"<(?:link|meta)[^>]*(?:shopify|shopifysvc|/cdn/shopifycloud)[^>]*>", "", t)
    t = re.sub(r"<shopify-[a-z-]+[^>]*>.*?</shopify-[a-z-]+>|<shopify-[a-z-]+[^>]*/?>", "", t, flags=re.S)
    t = re.sub(r"(?:https?:)?//novyance\.fr/cdn/shop/t/\d+/assets/([^\"'?\s]+)(?:\?[^\"'\s]*)?", r"/assets/\1", t)
    t = re.sub(r'<form method="post" action="/contact[^"]*"([^>]*)>', lambda m: "<form" + m.group(1).replace(' accept-charset="UTF-8"', "") + ENTETE_FORM + ">", t)
    t = re.sub(r'<input type="hidden" name="(?:form_type|utf8)"[^>]*>', "", t)
    t = t.replace("Shopify International Ltd, Victoria Buildings, 1-2 Haddington Road, Dublin 4, D04 XN32, Irlande.",
                  "GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.")
    if "</body>" in t:
        t = t.replace("</body>", '<script src="/assets/nv-contact.js" defer></script>\n</body>', 1)
    return t


def ecrire(sortie, url, contenu):
    contenu = contenu.replace('href="/pages/site-internet"', 'href="/pages/creation-site-internet-lyon"')
    dest = sortie / url.strip("/") / "index.html" if url != "/" else sortie / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(contenu, encoding="utf-8")


def date_fr(d):
    return d.strftime("%d/%m/%Y")


def articles(tout):
    liste = []
    maintenant = datetime.datetime.now(PARIS)
    for j in sorted((RACINE / "seo/articles").glob("*.json")):
        meta = json.loads(j.read_text(encoding="utf-8"))
        corps = j.with_suffix(".html")
        if not corps.exists() or not meta.get("publishDate"):
            continue  # pas encore programmé
        d = datetime.datetime.fromisoformat(meta["publishDate"])
        if d > maintenant and not tout:
            continue
        champs = {m["key"]: m["value"] for m in meta.get("metafields", [])}
        liste.append({"handle": meta["handle"], "titre": meta["title"], "date": d, "resume": meta.get("summary", ""),
                      "titre_seo": champs.get("title_tag", meta["title"]), "desc": champs.get("description_tag", ""),
                      "corps": corps.read_text(encoding="utf-8")})
    return sorted(liste, key=lambda a: a["date"], reverse=True)


def texte(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def snippet(nom, url, **v):
    t = lire("theme/snippets/%s.liquid" % nom)
    if nom == "nv-blog-chrome":
        part = v["part"]
        t = re.sub(r"\{%\s*if part == 'header'\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}\s*$", lambda m: m.group(1) if part == "header" else m.group(2), t, flags=re.S)
        t = re.sub(r"\{%-?\s*assign ml.*?\{%\s*endif\s*%\}", "", t, flags=re.S)
    if nom == "nv-blog-head":
        t = re.sub(r"\{%-?\s*if current_page > 1\s*-?%\}.*?\{%-?\s*endif\s*-?%\}", "", t, flags=re.S)
    return liquid(t, url)


def page_article(a, tous):
    t = lire("theme/templates/article.nv.liquid")
    url = "/blogs/blog/" + a["handle"]
    desc = a["desc"] or texte(a["resume"])[:158]
    ttl = a["titre_seo"]
    ld = lambda s: json.dumps(s, ensure_ascii=False)
    t = re.sub(r"\{%-?\s*assign (desc|ttl).*?-?%\}\n?", "", t)
    t = re.sub(r"\{% render 'nv-blog-head' %\}", lambda m: snippet("nv-blog-head", url), t)
    t = re.sub(r"\{% render 'nv-blog-chrome', part: '(\w+)' %\}", lambda m: snippet("nv-blog-chrome", url, part=m.group(1)), t)
    # image de couverture : aucune dans les sources, on retombe sur l'image de partage
    t = re.sub(r"\{% if article\.image %\}(.*?)\{% else %\}(.*?)\{% endif %\}", r"\2", t, flags=re.S, count=1)
    t = re.sub(r"\{% if article\.image %\}.*?\{% endif %\}", "", t, flags=re.S)
    t = re.sub(r"\{%-? assign rel = 0 -%\}.*?(?=\{% render 'nv-blog-chrome', part: 'footer' %\}|<footer|$)", lambda m: autres(a, tous), t, count=1, flags=re.S)
    iso = a["date"].strftime("%Y-%m-%dT%H:%M:%S%z")
    iso = iso[:-2] + ":" + iso[-2:]
    rempl = {"{{ ttl }}": html.escape(ttl), "{{ ttl | escape }}": html.escape(ttl), "{{ desc | escape }}": html.escape(desc),
             "{{ shop.url }}{{ article.url }}": SITE + url, "{{ article.title }}": html.escape(a["titre"]), "{{ article.title | json }}": ld(a["titre"]),
             "{{ desc | json }}": ld(desc), "{{ blog.url }}": "/blogs/blog", "{{ article.content }}": a["corps"],
             "{{ shop.url | append: article.url | json }}": ld(SITE + url)}
    for k, v in rempl.items():
        t = t.replace(k, v)
    t = re.sub(r"\{\{\s*article\.published_at \| date: '%Y-%m-%dT%H:%M:%S%z' \| json\s*\}\}", ld(iso), t)
    t = re.sub(r"\{\{\s*article\.updated_at \| date: '%Y-%m-%dT%H:%M:%S%z' \| json\s*\}\}", ld(iso), t)
    t = re.sub(r"\{\{\s*article\.published_at \| date: '%d/%m/%Y'\s*\}\}", date_fr(a["date"]), t)
    minutes = max(1, len(texte(a["corps"]).split()) // 220)
    t = re.sub(r"\{\{\s*article\.content \| strip_html.*?\}\}", str(minutes), t)
    t = re.sub(r"\{% if article\.excerpt != blank %\}(.*?)\{% endif %\}", lambda m: m.group(1).replace("{{ article.excerpt | strip_html }}", html.escape(texte(a["resume"]))), t, flags=re.S)
    return liquid(t, url)


def autres(a, tous):
    reste = [b for b in tous if b["handle"] != a["handle"]][:3]
    if not reste:
        return ""
    cartes = "".join('<a class="post" href="/blogs/blog/%s"><small>%s</small><b>%s</b><span>%s</span><em>Lire l\'article →</em></a>'
                     % (b["handle"], date_fr(b["date"]), html.escape(b["titre"]), html.escape(" ".join(texte(b["resume"]).split()[:26]))) for b in reste)
    return '<section class="wrap wide more"><h2>À lire aussi<span class="dot">.</span></h2><div class="posts">%s</div></section>\n' % cartes


def page_blog(tous):
    t = lire("theme/templates/blog.nv.liquid")
    url = "/blogs/blog"
    t = re.sub(r"\{% render 'nv-blog-head' %\}", lambda m: snippet("nv-blog-head", url), t)
    t = re.sub(r"\{% render 'nv-blog-chrome', part: '(\w+)' %\}", lambda m: snippet("nv-blog-chrome", url, part=m.group(1)), t)
    t = re.sub(r"\{% if current_page > 1 %\}.*?\{% endif %\}", "", t, flags=re.S)
    cartes = "".join('<a class="post" href="/blogs/blog/%s"><small>%s</small><b>%s</b><span>%s</span><em>Lire l\'article →</em></a>\n'
                     % (b["handle"], date_fr(b["date"]), html.escape(b["titre"]), html.escape(" ".join(texte(b["resume"]).split()[:26]))) for b in tous)
    liste = '<div class="posts">\n%s</div>' % cartes if tous else '<p class="lead">Les premiers articles arrivent.</p>'
    t = re.sub(r"\{% paginate .*?%\}.*?\{% endpaginate %\}", lambda m: liste, t, flags=re.S)
    t = t.replace("{{ shop.url | append: blog.url | json }}", json.dumps(SITE + url)).replace("{{ shop.url }}{{ blog.url }}", SITE + url).replace("{{ blog.url }}", url).replace("{{ shop.url }}", SITE)
    return liquid(t, url)


def plan_du_site(urls):
    jour = datetime.date.today().isoformat()
    corps = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod></url>" % (SITE, u, jour) for u in urls)
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % corps


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sortie = Path(sys.argv[1]).resolve()
    tout = "--tout" in sys.argv
    if sortie == RACINE or RACINE in sortie.parents:
        sys.exit("Le dossier de sortie doit être hors du dépôt de travail.")
    for enfant in sortie.glob("*") if sortie.exists() else []:
        if enfant.name not in (".git", ".github", "source"):  # source/ = sources du site dans le dépôt novyance-site
            shutil.rmtree(enfant) if enfant.is_dir() else enfant.unlink()
    sortie.mkdir(parents=True, exist_ok=True)
    for dossier in ASSETS:
        for f in (RACINE / dossier).glob("*"):
            (sortie / "assets").mkdir(exist_ok=True)
            shutil.copy(f, sortie / "assets" / f.name)
    shutil.copy(RACINE / "outils/nv-contact.js", sortie / "assets" / "nv-contact.js")
    urls = []
    for src, url in PAGES.items():
        page = liquid(lire(src), url)
        if "</body>" in page:
            page = page.replace("</body>", '<script src="/assets/nv-contact.js" defer></script>\n</body>', 1)
        ecrire(sortie, url, page)
        if "noindex" not in page and url not in ("/pages/exemple", "/pages/recommande"):
            urls.append(url)
    for src, url in LIVE.items():
        ecrire(sortie, url, nettoyer(lire(src), url))
        urls.append(url)
    for court, cible in REDIRECTIONS.items():
        (sortie / court.strip("/")).mkdir(parents=True, exist_ok=True)
        (sortie / court.strip("/") / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>Novyance</title><meta name="robots" content="noindex">'
            '<link rel="canonical" href="%s%s"><meta http-equiv="refresh" content="0; url=%s">'
            '<script>location.replace("%s" + location.search + location.hash)</script>'
            '<p><a href="%s">Continuer vers la page</a></p>' % (SITE, cible, cible, cible, cible), encoding="utf-8")
    liste = articles(tout)
    ecrire(sortie, "/blogs/blog", page_blog(liste))
    urls.append("/blogs/blog")
    for a in liste:
        ecrire(sortie, "/blogs/blog/" + a["handle"], page_article(a, liste))
        urls.append("/blogs/blog/" + a["handle"])
    (sortie / "sitemap.xml").write_text(plan_du_site(urls), encoding="utf-8")
    (sortie / "robots.txt").write_text("User-agent: *\nAllow: /\nDisallow: /pages/exemple\nDisallow: /pages/recommande\nSitemap: %s/sitemap.xml\n" % SITE, encoding="utf-8")
    (sortie / "404.html").write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page introuvable · Novyance</title>'
                                     '<p style="font:18px system-ui;padding:12vh 24px;text-align:center">Cette page n\'existe pas. <a href="/">Retour à l\'accueil</a></p>', encoding="utf-8")
    if (RACINE / "outils/CNAME-novyance").exists():
        shutil.copy(RACINE / "outils/CNAME-novyance", sortie / "CNAME")
    (sortie / ".nojekyll").write_text("", encoding="utf-8")
    reste = [str(m) for p in sortie.rglob("*.html") for m in re.findall(r"\{\{.*?\}\}|\{%.*?%\}", p.read_text(encoding="utf-8")) if "<" not in m][:10]
    print("Pages : %d · articles publiés : %d · Liquid restant : %s" % (len(PAGES) + len(LIVE) + 1, len(liste), reste or "aucun"))


if __name__ == "__main__":
    main()
