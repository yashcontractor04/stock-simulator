// The only script of my own. Frontend, built by Fable.
// Admin pages carry a CSRF token in a <meta> tag. HTMX must send it with every
// request it makes, so the server can tell my clicks from another site's.
document.addEventListener("htmx:configRequest", (event) => {
  const token = document.querySelector('meta[name="csrf-token"]');
  if (token) event.detail.headers["X-CSRF-Token"] = token.content;
});
