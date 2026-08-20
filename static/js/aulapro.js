(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const mobileBreakpoint = 991;

  const themeButton = document.getElementById("themeToggle");
  const updateThemeIcon = () => {
    if (!themeButton) return;
    const dark = root.dataset.theme === "dark";
    themeButton.innerHTML = dark
      ? '<i class="bi bi-sun"></i>'
      : '<i class="bi bi-moon-stars"></i>';
    themeButton.setAttribute("aria-label", dark ? "Activar modo claro" : "Activar modo oscuro");
  };

  themeButton?.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("aulapro-theme", root.dataset.theme);
    updateThemeIcon();
  });
  updateThemeIcon();

  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarClose = document.getElementById("sidebarClose");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");

  const setMobileSidebar = (open) => {
    body.classList.toggle("sidebar-open", open);
    sidebarBackdrop?.classList.toggle("visible", open);
    sidebarToggle?.setAttribute("aria-expanded", String(open));
  };

  if (localStorage.getItem("aulapro-sidebar") === "collapsed" && innerWidth > mobileBreakpoint) {
    body.classList.add("sidebar-collapsed");
    sidebarToggle?.setAttribute("aria-expanded", "false");
  }

  sidebarToggle?.addEventListener("click", () => {
    if (innerWidth <= mobileBreakpoint) {
      setMobileSidebar(!body.classList.contains("sidebar-open"));
      return;
    }
    body.classList.toggle("sidebar-collapsed");
    const collapsed = body.classList.contains("sidebar-collapsed");
    localStorage.setItem("aulapro-sidebar", collapsed ? "collapsed" : "expanded");
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  });

  sidebarClose?.addEventListener("click", () => setMobileSidebar(false));
  sidebarBackdrop?.addEventListener("click", () => setMobileSidebar(false));
  window.addEventListener("resize", () => {
    if (innerWidth > mobileBreakpoint) setMobileSidebar(false);
  });

  document.querySelectorAll("[data-submenu]").forEach((button) => {
    const submenuId = button.dataset.submenu;
    const submenu = document.getElementById(submenuId);
    const storageKey = `aulapro-submenu-${submenuId}`;
    const shouldOpen = localStorage.getItem(storageKey) === "open" || Boolean(submenu?.querySelector("a[aria-current='page']"));
    button.setAttribute("aria-controls", submenuId);
    button.setAttribute("aria-expanded", String(shouldOpen));
    submenu?.classList.toggle("open", shouldOpen);
    button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      submenu?.classList.toggle("open", open);
      localStorage.setItem(storageKey, open ? "open" : "closed");
    });
  });

  const passwordToggle = document.getElementById("passwordToggle");
  passwordToggle?.addEventListener("click", () => {
    const input = document.getElementById("id_password");
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    passwordToggle.innerHTML = show
      ? '<i class="bi bi-eye-slash"></i>'
      : '<i class="bi bi-eye"></i>';
    passwordToggle.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
  });

  document.querySelectorAll(".toast").forEach((element) => {
    if (window.bootstrap?.Toast) bootstrap.Toast.getOrCreateInstance(element).show();
  });

  const progress = document.getElementById("navigationProgress");
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link || link.target === "_blank" || link.hasAttribute("download") || link.href.startsWith("#")) return;
    if (new URL(link.href, location.href).origin !== location.origin) return;
    progress?.classList.add("loading");
  });
  document.addEventListener("submit", () => progress?.classList.add("loading"));
  window.addEventListener("pageshow", () => progress?.classList.remove("loading"));

  const settingsButtons = document.querySelectorAll("[data-settings-tab]");
  const settingsPanels = document.querySelectorAll("[data-settings-panel]");
  settingsButtons.forEach((button) => {
    button.addEventListener("click", () => {
      settingsButtons.forEach((item) => item.classList.toggle("active", item === button));
      settingsPanels.forEach((panel) => panel.classList.toggle("active", panel.dataset.settingsPanel === button.dataset.settingsTab));
    });
  });
  const errorPanel = document.querySelector("[data-settings-panel] .field-error")?.closest("[data-settings-panel]");
  if (errorPanel) document.querySelector(`[data-settings-tab="${errorPanel.dataset.settingsPanel}"]`)?.click();

  document.querySelectorAll(".logo-uploader input[type='file']").forEach((input) => {
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      const preview = input.closest(".logo-uploader")?.querySelector(".logo-preview");
      if (!file || !preview || !file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.addEventListener("load", () => {
        preview.innerHTML = `<img src="${reader.result}" alt="Vista previa del logo">`;
      });
      reader.readAsDataURL(file);
    });
  });

  document.querySelectorAll("input[type='color']").forEach((input) => {
    const swatch = document.querySelector(`[data-color-swatch="${input.id}"]`);
    const output = document.querySelector(`[data-color-output="${input.id}"]`);
    const brandPreview = document.querySelector("[data-brand-preview]");
    const refresh = () => {
      if (swatch) swatch.style.backgroundColor = input.value;
      if (output) output.textContent = input.value.toUpperCase();
      if (brandPreview && input.name === "color_primario") brandPreview.style.setProperty("--preview-primary", input.value);
    };
    swatch?.addEventListener("click", () => input.click());
    input.addEventListener("input", refresh);
    refresh();
  });

  const confirmModalElement = document.getElementById("confirmModal");
  const confirmButton = document.getElementById("confirmModalAction");
  let pendingForm = null;
  document.querySelectorAll("[data-confirm]").forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      if (!window.bootstrap?.Modal || !confirmModalElement) return;
      event.preventDefault();
      pendingForm = trigger.closest("form");
      document.getElementById("confirmModalTitle").textContent = trigger.dataset.confirmTitle || "Confirmar acción";
      document.getElementById("confirmModalMessage").textContent = trigger.dataset.confirm;
      bootstrap.Modal.getOrCreateInstance(confirmModalElement).show();
    });
  });
  confirmButton?.addEventListener("click", () => pendingForm?.submit());

  if (window.bootstrap?.Tooltip) {
    const sidebarTooltips = [...document.querySelectorAll(".sidebar .nav-item[title]")].map(
      (element) => new bootstrap.Tooltip(element, { placement: "right", trigger: "hover focus" }),
    );
    const syncTooltips = () => {
      const enabled = body.classList.contains("sidebar-collapsed") && innerWidth > mobileBreakpoint;
      sidebarTooltips.forEach((tooltip) => (enabled ? tooltip.enable() : tooltip.disable()));
    };
    new MutationObserver(syncTooltips).observe(body, { attributes: true, attributeFilter: ["class"] });
    window.addEventListener("resize", syncTooltips);
    syncTooltips();
  }
})();
