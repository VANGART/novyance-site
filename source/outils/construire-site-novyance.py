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
    "theme-v18/templates/page.sites.liquid": "/pages/site-internet",
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
    dest = sortie / url.strip("/") / "index.html" if url != "/" else sortie / "index.html"
    # anti-spam : chaque formulaire de contact reçoit le champ piège « _gotcha » s'il n'en a pas (la fonction contact l'ignore si rempli)
    piege = '<div style="position:absolute;left:-9999px" aria-hidden="true"><label>Ne pas remplir<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></div>'
    contenu = re.sub(r"(<form\b[^>]*data-nv-contact[^>]*>)(.*?)(</form>)",
                     lambda m: m.group(0) if "_gotcha" in m.group(2) else m.group(1) + m.group(2) + piege + m.group(3), contenu, flags=re.S)
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


def pages_sites(sortie):
    """Pages « site internet » par métier et par ville : gabarit page.sites + textes de seo/sites/*.json."""
    fichiers = sorted((RACINE / "seo/sites").glob("*.json"))
    donnees = [json.loads(f.read_text(encoding="utf-8")) for f in fichiers]
    e = html.escape
    def liens(d):
        def groupe(titre, type_):
            autres = [x for x in donnees if x["type"] == type_ and x["url"] != d["url"]]
            if not autres:
                return ""
            return '<div><h3>%s</h3><ul>%s</ul></div>' % (titre, "".join('<li><a href="%s">%s</a></li>' % (x["url"], e(x["lien"])) for x in autres))
        return ('<section class="voisins"><div class="wrap"><h2>Les autres pages<span class="dot">.</span></h2><div class="voisins-g">%s%s'
                '<div><h3>L\'offre complète</h3><ul><li><a href="/pages/site-internet">Sites internet dès 490 €</a></li><li><a href="/">Prospection à la commission</a></li></ul></div>'
                '</div></div></section>') % (groupe("Par métier", "metier"), groupe("Par ville", "ville"))
    urls = []
    for d in donnees:
        url = d["url"]
        t = liquid(lire("theme-v18/templates/page.sites.liquid"), url)
        sec = lambda c: re.search(r'<section class="%s".*?</section>' % c, t, flags=re.S).group(0)
        devis = re.search(r'<div class="devis".*?</p>\s*</div>', t, flags=re.S).group(0)
        x = d["exemple"]
        top = ('<section class="top"><div class="wrap"><div><p class="kick">%s</p><h1>%s<span class="dot">.</span></h1>'
               '<p class="lead">%s</p><div class="acts"><a href="#devis" class="btn">Demander un devis sous 24 h</a>'
               '<a href="tel:+33786523681" class="btn ghost">07 86 52 36 81</a></div><p class="pour">%s</p></div>%s</div></section>'
               % (e(d["kick"]), e(d["h1"]), e(d["lead"]), d["pour"], devis))
        bas = "".join('<div><b>%s%s</b>%s</div>' % (e(a), ' <span class="pin">4</span>' if i == 2 else "", e(b)) for i, (a, b) in enumerate(x["bas"]))
        ex = ('<section class="ex" id="exemple"><div class="wrap"><h2>%s<span class="dot">.</span></h2><p class="lead">%s</p><div class="ex-grid"><div>'
              '<div class="nav-b" aria-hidden="true"><div class="barre"><i></i><i></i><i></i><span class="url">%s</span></div><div class="site">'
              '<div class="site-h"><b>%s</b><span><span class="pin">2</span><span class="site-tel">%s</span></span></div>'
              '<div class="site-hero"><div class="txt"><h4><span class="pin" style="margin-left:0">1</span>%s</h4><p>%s</p>'
              '<p class="zone"><span class="pin" style="margin-left:0">3</span>%s</p><span class="cta">%s</span></div><div class="bois"></div></div>'
              '<div class="site-bas">%s</div></div></div><p class="fictif">Exemple fictif : %s n\'existe pas.</p></div><ol class="notes">%s</ol></div></div></section>'
              % (e(d["exemple_h2"]), e(d["exemple_lead"]), e(x["url"]), e(x["nom"]), e(x["bouton"]), e(x["h"]), e(x["p"]), e(x["zone"]), e(x["cta"]),
                 bas, e(x["nom"]), "".join('<li><b>%s</b>%s</li>' % (e(a), e(b)) for a, b in d["notes"])))
        b = d["bloc"]
        bloc = ('<section class="metier"><div class="wrap"><h2>%s<span class="dot">.</span></h2><div class="metier-g"><div class="metier-i">%s</div><ul>%s</ul></div>%s</div></section>'
                % (e(b["h2"]), "".join("<p>%s</p>" % p for p in b["intro"]), "".join('<li><b>%s</b>%s</li>' % (e(a), e(c)) for a, c in b["points"]),
                   ('<p class="sources">Sources : %s</p>' % " · ".join('<a href="%s" rel="noopener" target="_blank">%s</a>' % (e(u), e(l)) for l, u in d["sources"])) if d.get("sources") else ""))
        faq = ('<section class="faq"><div class="wrap"><h2>Les questions qu\'on nous pose<span class="dot">.</span></h2><div class="faq-l">%s</div></div></section>'
               % "".join("<details><summary>%s</summary><p>%s</p></details>" % (e(q), e(r)) for q, r in d["faq"]))
        main = top + ex + bloc + sec("jours") + sec("perim") + faq + liens(d)
        t = re.sub(r'<section class="top">.*(?=<section class="end")', lambda m: main + "\n  ", t, count=1, flags=re.S)
        t = t.replace('value="Site internet"', 'value="%s"' % e(d["demande"]))
        t = re.sub(r"<title>.*?</title>", "<title>%s</title>" % e(d["title"]), t, count=1, flags=re.S)
        for nom, val in (('name="description"', d["description"]), ('property="og:title"', d["h1"]), ('property="og:description"', d["description"])):
            t = re.sub(r'<meta %s content="[^"]*">' % re.escape(nom), '<meta %s content="%s">' % (nom, e(val)), t, count=1)
        ld = [{"@context": "https://schema.org", "@type": "Service", "name": d["title"].split(" · ")[0], "serviceType": "Création de site internet",
               "areaServed": d.get("zone_ld", "FR"), "provider": {"@type": "Organization", "name": "Novyance", "url": SITE},
               "offers": {"@type": "Offer", "price": "490", "priceCurrency": "EUR"}},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in d["faq"]]},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Sites internet", "item": SITE + "/pages/site-internet"},
                  {"@type": "ListItem", "position": 3, "name": d["lien"], "item": SITE + url}]}]
        t = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: "\n".join('<script type="application/ld+json">%s</script>' % json.dumps(o, ensure_ascii=False) for o in ld), t, count=1, flags=re.S)
        t = t.replace("</style>", CSS_SITES + "</style>", 1)
        t = t.replace("</body>", '<script src="/assets/nv-contact.js" defer></script>\n</body>', 1)
        ecrire(sortie, url, t)
        urls.append(url)
    # la page générale « Sites internet » liste aussi les pages métier et ville
    general = sortie / "pages/site-internet/index.html"
    if general.exists() and donnees:
        g = general.read_text(encoding="utf-8")
        g = g.replace('<section class="end"', liens({"url": "/pages/site-internet"}) + '\n  <section class="end"', 1).replace("</style>", CSS_SITES + "</style>", 1)
        general.write_text(g, encoding="utf-8")
    return urls


LEGALES = {
    "/pages/cgv": ("seo/legal/cgv.html", "Conditions générales de vente · Novyance",
                   "Conditions générales de vente de Novyance : prospection à la commission, sites internet, outils sur mesure. Prix, paiement, engagement, données."),
    "/pages/confidentialite": ("seo/legal/confidentialite.html", "Politique de confidentialité · Novyance",
                               "Quelles données Novyance collecte, pourquoi, combien de temps, qui y a accès, et comment exercer vos droits."),
}


def pages_legales(sortie):
    """CGV et confidentialité : textes de seo/legal, habillés comme la page « Sites internet »."""
    urls = []
    for url, (src, titre, desc) in LEGALES.items():
        t = liquid(lire("theme-v18/templates/page.sites.liquid"), url)
        t = re.sub(r"<main>.*</main>", lambda m: '<main><section class="legal"><div class="wrap">%s</div></section></main>' % lire(src), t, count=1, flags=re.S)
        t = re.sub(r"<title>.*?</title>", "<title>%s</title>" % html.escape(titre), t, count=1, flags=re.S)
        for nom, val in (('name="description"', desc), ('property="og:title"', titre), ('property="og:description"', desc)):
            t = re.sub(r'<meta %s content="[^"]*">' % re.escape(nom), '<meta %s content="%s">' % (nom, html.escape(val)), t, count=1)
        t = re.sub(r'<script type="application/ld\+json">.*?</script>', "", t, count=1, flags=re.S)
        t = t.replace("</style>", CSS_LEGAL + "</style>", 1)
        ecrire(sortie, url, t)
        urls.append(url)
    return urls


CSS_LEGAL = """
.legal{padding:clamp(48px,7vw,96px) 0 clamp(64px,8vw,112px)}
.legal .wrap{max-width:820px}
.legal h1{font-size:clamp(36px,5vw,60px)}
.legal .maj{color:var(--muted);margin-top:14px;font-size:15px}
.legal h2{font-size:clamp(22px,2.4vw,28px);margin:44px 0 12px}
.legal p,.legal li{color:var(--ink);max-width:70ch}
.legal p+p{margin-top:12px}
.legal ul{padding-left:20px;margin:10px 0 0}
.legal li{margin-bottom:8px}
"""


CSS_SITES = """
.metier{padding:clamp(64px,9vw,120px) 0 0}
.metier-g{display:grid;grid-template-columns:.9fr 1.1fr;gap:clamp(28px,5vw,64px);margin-top:36px;align-items:start}
.metier-i p{color:var(--muted);margin-bottom:16px;max-width:52ch}
.metier ul{list-style:none;margin:0;padding:0;border-top:2px solid var(--ink2)}
.metier li{padding:16px 0;border-bottom:1px solid var(--line);color:var(--muted)}
.metier li b{display:block;color:var(--ink2);font-weight:600;margin-bottom:2px}
.sources{margin-top:28px;font-size:13px;color:var(--muted)}
.voisins{padding:0 0 clamp(64px,9vw,112px)}
.voisins-g{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:28px}
.voisins h3{font-size:16px;margin-bottom:10px}
.voisins ul{list-style:none;margin:0;padding:0}
.voisins li{padding:6px 0}
.voisins a{text-decoration:none;border-bottom:1px solid var(--line)}
.voisins a:hover{color:var(--accent-d);border-color:var(--accent)}
@media (max-width:860px){.metier-g,.voisins-g{grid-template-columns:1fr}}
"""


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
    urls += pages_sites(sortie)
    urls += pages_legales(sortie)
    liste = articles(tout)
    ecrire(sortie, "/blogs/blog", page_blog(liste))
    urls.append("/blogs/blog")
    for a in liste:
        ecrire(sortie, "/blogs/blog/" + a["handle"], page_article(a, liste))
        urls.append("/blogs/blog/" + a["handle"])
    (sortie / "sitemap.xml").write_text(plan_du_site(urls), encoding="utf-8")
    (sortie / "robots.txt").write_text("User-agent: *\nAllow: /\nDisallow: /pages/exemple\nDisallow: /pages/recommande\nSitemap: %s/sitemap.xml\n" % SITE, encoding="utf-8")
    (sortie / "404.html").write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><link rel="icon" href="/assets/nv-favicon-48.png"><title>Page introuvable · Novyance</title>'
                                     '<p style="font:18px system-ui;padding:12vh 24px;text-align:center">Cette page n\'existe pas. <a href="/">Retour à l\'accueil</a></p>', encoding="utf-8")
    if (RACINE / "outils/CNAME-novyance").exists():
        shutil.copy(RACINE / "outils/CNAME-novyance", sortie / "CNAME")
    (sortie / ".nojekyll").write_text("", encoding="utf-8")
    reste = [str(m) for p in sortie.rglob("*.html") for m in re.findall(r"\{\{.*?\}\}|\{%.*?%\}", p.read_text(encoding="utf-8")) if "<" not in m][:10]
    print("Pages : %d · articles publiés : %d · Liquid restant : %s" % (len(PAGES) + len(LIVE) + 1, len(liste), reste or "aucun"))


if __name__ == "__main__":
    main()
