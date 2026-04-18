document.addEventListener("click", (event) => {
  const close = event.target.closest(".alert-close");
  if (!close) return;
  const alert = close.closest(".alert");
  if (!alert) return;
  alert.remove();
  const toast = document.querySelector(".toast");
  if (toast && !toast.querySelector(".alert")) {
    toast.remove();
  }
});
