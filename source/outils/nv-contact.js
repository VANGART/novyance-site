/* Novyance · formulaires de contact du site statique.
   Remplace le formulaire de contact Shopify : envoie les champs « contact[...] » à la fonction Supabase « contact ».
   Les pages qui gèrent déjà leur envoi (demande d'exemple) appellent preventDefault avant nous : on ne touche à rien. */
(function () {
  var MERCI = {
    "f-call": "ok3"
  };
  [].forEach.call(document.querySelectorAll("form[data-nv-contact]"), function (f) {
    f.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      var piege = f.querySelector('[name="_gotcha"]');
      e.preventDefault();
      if (piege && piege.value) return;
      var champs = {};
      [].forEach.call(f.elements, function (c) {
        var m = c.name && c.name.match(/^contact\[(.+)\]$/);
        if (m && c.value) champs[m[1]] = c.value;
      });
      var bouton = f.querySelector("button[type=submit],button:not([type])");
      if (bouton) bouton.disabled = true;
      var erreur = f.querySelector("[data-err]");
      if (erreur) erreur.hidden = true;
      fetch(f.action, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ formulaire: f.id, page: location.pathname, champs: champs }) })
        .then(function (r) { if (!r.ok) throw new Error("erreur"); f.reset(); montrer(f, true); })
        .catch(function () { montrer(f, false); })
        .then(function () { if (bouton) bouton.disabled = false; });
    });
  });
  function montrer(f, ok) {
    var cible = ok && MERCI[f.id] && document.getElementById(MERCI[f.id]);
    if (cible) { cible.hidden = false; return; }
    var m = f.querySelector(".nv-retour") || f.appendChild(document.createElement("div"));
    m.className = "ok-msg nv-retour" + (ok ? "" : " err");
    m.setAttribute("role", ok ? "status" : "alert");
    m.textContent = ok ? "Demande reçue. Aurélien vous répond très vite, par mail."
      : "Une erreur s'est produite. Vérifiez votre adresse email, ou écrivez à contact@novyance.fr.";
  }
})();
