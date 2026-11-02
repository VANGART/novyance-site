/* Novyance · assistant de l'accueil et démo « Prospection ».
   Fonctionne seul. Si nv.js est chargé avant, ajoute aussi la démo « Prospection » à sa vitrine.
   Aucune IA ici : un parcours guidé. La demande finale passe par le formulaire de contact Shopify (#cf). */

/* démo Prospection dans la vitrine d'exemples (seulement avec nv.js) */
if(typeof demos !== 'undefined') demos.prospect = async (app, alive) => {
  const rows = app.querySelectorAll('.fn-r');
  await wait(300); if(!alive()) return;
  for(const r of rows){
    const bar = r.querySelector('.fn-bar i'), n = r.querySelector('b');
    bar.style.transition = 'width 1.2s cubic-bezier(.22,.61,.36,1)';
    requestAnimationFrame(() => { bar.style.width = bar.dataset.w + '%'; });
    count(n, +n.dataset.n, 1100, '');
    await wait(260); if(!alive()) return;
  }
  await wait(700); if(!alive()) return;
  gain(app);
};

/* assistant */
(() => {
  const M = id => document.getElementById(id);
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const box = M('bot'); if(!box) return;
  const msgs = M('botm'), opts = M('boto'), form = M('boti'), input = M('botin');
  const etape = M('botstep');

  // chaque besoin : ce que l'outil change, un exemple concret, et la démo à essayer
  const NEEDS = {
    planning: { label: 'Le planning', brique: 'un planning partagé, par équipe, machine ou chantier', besoin: 'Un outil pour mon atelier ou mes chantiers',
      reply: "Un planning que toute l'équipe met à jour d'un clic depuis son téléphone. Vous voyez les retards avant qu'ils coûtent, et le client est prévenu sans que vous décrochiez.",
      demo: ['/pages/demo-atelier', 'Voir un planning en vrai'] },
    chiffres: { label: 'Suivre mes chiffres', brique: 'un tableau de bord qui se remplit tout seul', besoin: 'Un tableau de bord de mes chiffres',
      reply: "Chiffre, marge, trésorerie, prévisionnel : tout arrive seul depuis votre banque et vos devis. Le 1er du mois, c'est prêt. Plus de soirée à recoller des tableurs.",
      demo: ['/pages/demo-pilotage', 'Voir un tableau de bord'] },
    devis: { label: 'Devis et relances', brique: 'devis, factures et relances automatiques', besoin: 'Prospection et suivi commercial',
      reply: "Le devis se prépare depuis un vocal en sortant du rendez-vous. Factures et relances partent au bon moment, dans votre ton. Vous validez, c'est tout.",
      demo: ['/pages/demo-commercial', 'Voir les relances'] },
    clients: { label: 'Trouver des clients', brique: 'une prospection qui tourne toute seule', besoin: 'Prospection et suivi commercial',
      reply: "Des entreprises ciblées, un message écrit pour chacune, des relances programmées. Vous ne vous occupez que de ceux qui répondent.",
      demo: ['/pages/demo-commercial', 'Voir la prospection'] },
    ia: { label: "Automatiser avec l'IA", brique: "l'automatisation de ce qui se répète, avec l'IA là où elle sert vraiment", besoin: "Automatiser une tâche avec l'IA",
      reply: "Mails triés chaque matin, comptes rendus depuis un vocal, devis dictés, relances rédigées. Rien ne part sans votre validation." },
    formia: { label: "Former mon équipe à l'IA", brique: "des ateliers pratiques pour que votre équipe se serve de l'IA dès le lendemain", besoin: "Former mon équipe à l'IA",
      reply: "Des ateliers sur vos vrais dossiers : rédiger, trier, résumer, relancer. Chacun repart avec ses modèles, prêts à servir le lendemain." },
    equipe: { label: 'Faire adopter les outils', brique: "un accompagnement pour que l'équipe adopte vraiment l'outil", besoin: "Formation ou accompagnement à l'outil",
      reply: "Le plus dur n'est pas l'outil, c'est l'habitude. Je forme l'équipe sur ses vrais dossiers et je suis l'adoption les premières semaines. La formation est incluse." },
    site: { label: 'Un site internet', brique: 'un site qui fait sonner le téléphone', besoin: 'Un site vitrine (dès 490 €)',
      reply: "Un site clair, rapide sur téléphone, relié à votre fiche Google, avec un bouton appeler bien visible. En ligne en 10 jours, et il vous appartient." },
    autre: { label: 'Autre chose', brique: "l'outil adapté à ce que vous décrivez", besoin: 'Je ne sais pas encore (diagnostic offert)',
      reply: "Noté. C'est exactement le genre de chose qu'un outil sur mesure règle : on le construit autour de votre façon de faire, pas l'inverse." }
  };
  const SIZES = ['Seul', '2 à 5', '6 à 15', '16 à 30', 'Plus de 30'];
  const TOOLS = { 'Excel': "Vos fichiers ne sont pas perdus : on les reprend pour démarrer, vous ne ressaisissez rien.",
    'Papier ou tableau blanc': "On part de vos habitudes, avec de gros boutons sur téléphone. Personne n'a besoin d'être à l'aise avec l'informatique.",
    'WhatsApp et mails': "Les infos qui se perdent dans les groupes auront enfin leur place, au même endroit pour tout le monde.",
    'Un logiciel qui ne convient pas': "On peut s'y brancher ou le remplacer, selon ce qui vous coûte le moins." };

  let step = 0, need = null, size = '', tool = '', free = '';
  const log = [];

  // toujours voir le dernier message, même quand les choix prennent de la place
  const scroll = () => { msgs.scrollTop = msgs.scrollHeight; };
  const scrollApres = () => { scroll(); requestAnimationFrame(scroll); setTimeout(scroll, 80); setTimeout(scroll, 300); };
  if('ResizeObserver' in window) new ResizeObserver(scroll).observe(opts);
  const progres = n => { if(etape) etape.textContent = n ? 'Question ' + n + ' sur 3' : 'Votre proposition'; };

  const add = (who, text, html) => {
    const d = document.createElement('div'); d.className = 'bm ' + who;
    if(html) d.innerHTML = html; else d.textContent = text;
    msgs.appendChild(d); scrollApres(); log.push((who === 'a' ? 'Novyance : ' : 'Prospect : ') + text);
    return d;
  };
  const say = async (text, delay, html) => {
    const t = document.createElement('div'); t.className = 'bm a ty'; t.innerHTML = '<i></i><i></i><i></i>';
    msgs.appendChild(t); scrollApres();
    await wait(reduce ? 0 : (delay || Math.min(1100, 300 + text.length * 9)));
    t.remove(); return add('a', text, html);
  };
  const choices = (list, cls) => {
    opts.innerHTML = ''; opts.className = 'bot-o' + (cls ? ' ' + cls : '');
    list.forEach(([label, fn]) => {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
      b.addEventListener('click', () => fn(label)); opts.appendChild(b);
    });
    scrollApres();
  };
  const raccourci = () => {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'bot-skip'; b.textContent = 'Je préfère être rappelé';
    b.addEventListener('click', () => { opts.innerHTML = ''; if(!need) need = NEEDS.autre; add('u', 'Je préfère être rappelé'); lead(true); });
    opts.appendChild(b);
  };

  const askNeed = async () => {
    step = 1; progres(1);
    await say("Bonjour, je suis Aurélien. En 3 questions, je vous dis ce que je mettrais en place chez vous.", 500);
    await say("Qu'est-ce qui vous prend le plus de temps en ce moment ?", 550);
    choices(Object.entries(NEEDS).map(([k, n]) => [n.label, l => onNeed(k, l)]), 'besoins');
    raccourci();
  };
  const onNeed = async (k, text) => {
    need = NEEDS[k]; if(k === 'autre' && text !== NEEDS.autre.label) free = text;
    opts.innerHTML = ''; add('u', text);
    await say(need.reply);
    if(need.demo) await say(need.demo[1], 300, '<a class="bot-demo" href="' + need.demo[0] + '" target="_blank" rel="noopener">' + need.demo[1] + ' ↗</a><span>Données fictives, cliquez partout.</span>');
    step = 2; progres(2);
    await say("Vous êtes combien dans l'entreprise ?", 500);
    choices(SIZES.map(s => [s, onSize]));
  };
  const onSize = async text => {
    size = text; opts.innerHTML = ''; add('u', text);
    step = 3; progres(3);
    await say(text === 'Seul' ? "Parfait, on reste simple : un outil pour vous, lisible sur téléphone."
      : "Chacun verra ce qui le concerne, et la direction garde la main sur les chiffres. Prix par entreprise, pas par personne.");
    await say("Et aujourd'hui, ça se gère comment ?", 450);
    choices(Object.keys(TOOLS).map(t => [t, onTool]));
  };
  const onTool = async text => {
    tool = text; opts.innerHTML = ''; add('u', text);
    if(TOOLS[text]) await say(TOOLS[text]);
    step = 4; progres(0);
    const site = need === NEEDS.site;
    await say('Récapitulatif', 700,
      '<div class="bot-recap"><b>Ce que je vous propose</b>' +
      '<ul><li>' + need.brique.charAt(0).toUpperCase() + need.brique.slice(1) + '</li>' +
      (site ? '<li>En ligne en 10 jours, textes écrits avec vous</li><li>Le site et le nom de domaine sont à vous</li>'
            : '<li>Première brique en place en une semaine</li><li>Branché sur ce que vous utilisez déjà</li><li>Formation de votre équipe incluse</li>') +
      '</ul><em>Mise en place à -50 % pour les 3 premiers clients.</em></div>');
    await say("Laissez-moi un moyen de vous joindre : je vous envoie une proposition adaptée sous 24 h, et on en parle 30 minutes si vous voulez. Sans engagement.", 600);
    lead(false);
  };
  const lead = rappel => {
    form.style.display = 'none'; progres(0);
    const f = document.createElement('form'); f.className = 'bot-f';
    f.innerHTML = '<input name="n" placeholder="Votre prénom et nom" required autocomplete="name">' +
      (rappel ? '' : '<input name="e" type="email" placeholder="Votre email" required autocomplete="email">') +
      '<input name="t" type="tel" placeholder="' + (rappel ? 'Votre téléphone' : 'Téléphone (facultatif)') + '"' + (rappel ? ' required' : '') + ' autocomplete="tel">' +
      (rappel ? '<input name="e" type="email" placeholder="Votre email (facultatif)" autocomplete="email">' : '') +
      '<button type="submit">' + (rappel ? 'Être rappelé sous 24 h' : 'Recevoir ma proposition') + '</button>' +
      '<small>Réponse par Aurélien lui-même, sous 24 h. Vos coordonnées servent uniquement à vous répondre.</small>';
    f.addEventListener('submit', e => { e.preventDefault(); send(f, rappel); });
    msgs.appendChild(f);
    const r = document.createElement('button'); r.type = 'button'; r.className = 'bot-r'; r.textContent = 'Recommencer';
    r.addEventListener('click', restart); msgs.appendChild(r);
    scrollApres();
    setTimeout(() => { const i = f.querySelector('input'); if(i && !matchMedia('(max-width:620px)').matches) i.focus({ preventScroll: true }); }, 350);
  };
  const send = (f, rappel) => {
    const cf = M('cf'); if(!cf) return;
    const set = (id, v) => { const el = M(id); if(el) el.value = v; };
    const tel = f.t ? f.t.value : '';
    set('nom', f.n.value); set('mail', f.e && f.e.value ? f.e.value : 'sans-email@novyance.fr');
    if(M('tel')) set('tel', tel); else set('soc', tel ? 'Tél. ' + tel : '');
    const sel = M('bes');
    if(sel){ [...sel.options].forEach(o => { if(o.text === need.besoin) sel.value = o.value; }); }
    set('msg', 'Demande via l\'assistant de l\'accueil' + (rappel ? ' (à rappeler)' : '') + '\n' +
      'Besoin : ' + need.label + (free ? ' (' + free + ')' : '') + (size ? '\nTaille : ' + size : '') + (tool ? '\nAujourd\'hui : ' + tool : '') +
      (tel ? '\nTéléphone : ' + tel : '') + '\n\n' + log.join('\n'));
    const b = f.querySelector('button'); b.disabled = true; b.textContent = 'Envoi…';
    if(cf.requestSubmit) cf.requestSubmit(); else cf.submit();
  };
  const restart = () => {
    msgs.innerHTML = ''; opts.innerHTML = ''; form.style.display = '';
    log.length = 0; need = null; size = tool = free = ''; askNeed();
  };

  /* réponse libre : sert à l'étape en cours */
  form.addEventListener('submit', e => {
    e.preventDefault();
    const v = input.value.trim(); if(!v) return; input.value = '';
    if(step === 1) onNeed('autre', v);
    else if(step === 2) onSize(v);
    else if(step === 3) onTool(v);
  });

  /* démarre quand l'assistant devient visible */
  let started = false;
  new IntersectionObserver((es, o) => es.forEach(e => {
    if(e.isIntersecting && !started){ started = true; o.disconnect(); setTimeout(askNeed, 500); }
  }), {threshold: .3}).observe(box);
})();
