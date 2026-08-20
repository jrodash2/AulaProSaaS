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
