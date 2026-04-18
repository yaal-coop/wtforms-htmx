/*
 * Auto-submit the htmx toggle form when the switch changes. Loaded
 * unconditionally (ie. even when htmx is disabled) so the user can
 * always toggle it back on.
 */
document.addEventListener("change", (evt) => {
  const input = evt.target;
  if (
    input.matches('#htmx-toggle-form input[type="checkbox"]')
  ) {
    input.closest("form").submit();
  }
});
