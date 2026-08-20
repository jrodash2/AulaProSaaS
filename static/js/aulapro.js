(() => {
  const root = document.documentElement;
  const shell = document.body;
  const themeButton = document.getElementById("themeToggle");
  const updateThemeIcon = () => {
    if (themeButton) themeButton.innerHTML = root.dataset.theme === "dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  };
  themeButton?.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("aulapro-theme", root.dataset.theme);
    updateThemeIcon();
  });
  updateThemeIcon();

  if (localStorage.getItem("aulapro-sidebar") === "collapsed" && innerWidth > 991) shell.classList.add("sidebar-collapsed");
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    if (innerWidth <= 991) shell.classList.toggle("sidebar-open");
    else {
      shell.classList.toggle("sidebar-collapsed");
      localStorage.setItem("aulapro-sidebar", shell.classList.contains("sidebar-collapsed") ? "collapsed" : "expanded");
    }
  });
  document.getElementById("sidebarBackdrop")?.addEventListener("click", () => shell.classList.remove("sidebar-open"));
  document.getElementById("passwordToggle")?.addEventListener("click", (event) => {
    const input = document.getElementById("id_password");
    input.type = input.type === "password" ? "text" : "password";
    event.currentTarget.innerHTML = input.type === "password" ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
  });
})();

document.addEventListener("DOMContentLoaded", () => document.getElementById("apLoadingBar")?.classList.add("done"));
document.addEventListener("click", event => {
  const link = event.target.closest("a[href]");
  if (link && link.origin === location.origin && !link.hash && !event.ctrlKey && !event.metaKey) {
    document.getElementById("apLoadingBar")?.classList.add("loading");
  }
});

document.querySelectorAll(".toast").forEach(element => bootstrap.Toast.getOrCreateInstance(element).show());
document.getElementById("confirmModal")?.addEventListener("show.bs.modal", event => {
  const trigger = event.relatedTarget;
  document.getElementById("confirmModalForm").action = trigger.dataset.confirmUrl;
  document.getElementById("confirmModalTitle").textContent = trigger.dataset.confirmTitle || "Confirmar acción";
});

if (window.AulaProOfertaOpciones) {
  const nivel = document.getElementById("id_nivel");
  const carrera = document.getElementById("id_carrera");
  const pensum = document.getElementById("id_pensum");
  const cargar = async (select, parametro, valor, etiqueta) => {
    select.disabled = true;
    const response = await fetch(`${window.AulaProOfertaOpciones}?${parametro}=${encodeURIComponent(valor)}`);
    const data = await response.json();
    select.innerHTML = `<option value="">${etiqueta}</option>` + data.resultados.map(item => `<option value="${item.id}">${item.nombre}${item.codigo_version ? ` · ${item.codigo_version} · ${item.estado}` : ""}</option>`).join("");
    select.disabled = false;
  };
  nivel?.addEventListener("change", () => cargar(carrera, "nivel", nivel.value, "Seleccione una carrera"));
  carrera?.addEventListener("change", () => cargar(pensum, "carrera", carrera.value, "Seleccione una versión de pensum"));
}
