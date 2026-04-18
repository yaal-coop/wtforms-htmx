/* Drag-to-reorder bridge between Sortable.js and a wtforms-htmx
   HiddenField wired with ``.triggers(target, list_reorder, on="change")``.

   Picks up any element carrying ``data-sortable-fieldlist`` (typically
   the FieldList's <ul>). On drop, builds a comma-separated permutation
   string from the children's ``data-index`` attributes (their original
   indices before this drag), writes it into the input whose id is
   ``data-sortable-target``, then dispatches a ``change`` event so htmx
   posts and the dispatcher invokes ``list_reorder`` server-side.

   ``htmx.onLoad`` is invoked for the initial DOM and every htmx swap, so
   newly-rendered FieldList containers (post-add, post-remove,
   post-reorder) are re-bound automatically. ``_sortableInited`` guards
   against double-binding when the same node survives a swap. */
(function () {
  function init(el) {
    if (el._sortableInited) return;
    el._sortableInited = true;
    Sortable.create(el, {
      handle: ".drag-handle",
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen",
      dragClass: "sortable-drag",
      onEnd: function (evt) {
        var children = evt.to.children;
        var order = [];
        for (var i = 0; i < children.length; i++) {
          var idx = children[i].dataset.index;
          if (idx !== undefined) order.push(idx);
        }
        var targetId = evt.to.dataset.sortableTarget;
        if (!targetId) return;
        var input = document.getElementById(targetId);
        if (!input) return;
        input.value = order.join(",");
        input.dispatchEvent(new Event("change", { bubbles: true }));
      },
    });
  }

  function scan(root) {
    (root || document)
      .querySelectorAll("[data-sortable-fieldlist]")
      .forEach(init);
  }

  // Register for future htmx swaps (post-add, post-remove, post-reorder).
  if (window.htmx && typeof window.htmx.onLoad === "function") {
    window.htmx.onLoad(scan);
  }
  // Scan the current DOM as well: when hx-boost navigates here and
  // ``head-support`` injects this script post-swap, ``htmx.onLoad`` won't
  // re-fire for already-swapped nodes; an explicit scan picks them up.
  // The ``_sortableInited`` guard makes this safe to call multiple times.
  if (document.readyState !== "loading") {
    scan(document);
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      scan(document);
    });
  }
})();
