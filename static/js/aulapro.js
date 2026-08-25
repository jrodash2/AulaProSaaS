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

if (window.AulaProCuiUrl) {
  const cui = document.getElementById("id_alumno-cui");
  const feedback = document.getElementById("cuiFeedback");
  cui?.addEventListener("blur", async () => {
    if (!cui.value) { feedback.textContent = "Se registrará con identificación pendiente."; return; }
    const response = await fetch(`${window.AulaProCuiUrl}?cui=${encodeURIComponent(cui.value)}`);
    const data = await response.json();
    feedback.innerHTML = data.disponible ? '<span class="text-success">✓ CUI disponible</span>' : `Este alumno ya está registrado: <a href="${data.alumno.url}">${data.alumno.nombre}</a>`;
  });
}

if (window.AulaProInscripcionOpciones) {
  const chain = [
    ["id_inscripcion-ciclo", "id_inscripcion-oferta_academica", "ciclo", "Seleccione oferta"],
    ["id_inscripcion-oferta_academica", "id_inscripcion-grado", "oferta", "Seleccione grado"],
    ["id_inscripcion-grado", "id_inscripcion-seccion", "grado", "Seleccione sección"],
  ];
  chain.forEach(([sourceId, targetId, key, label]) => document.getElementById(sourceId)?.addEventListener("change", async event => {
    const target = document.getElementById(targetId); target.disabled = true;
    const response = await fetch(`${window.AulaProInscripcionOpciones}?${key}=${encodeURIComponent(event.target.value)}`);
    const data = await response.json(); target.innerHTML = `<option value="">${label}</option>` + data.resultados.map(x => `<option value="${x.id}">${x.nombre}</option>`).join(""); target.disabled = false;
  }));
}

if (window.AulaProDocenteOpciones) {
  const chain = [
    ["id_ciclo", "id_oferta_academica", "ciclo", "Seleccione oferta"],
    ["id_oferta_academica", "id_grado", "oferta", "Seleccione grado"],
    ["id_grado", "id_seccion", "grado", "Seleccione sección", "secciones"],
    ["id_grado", "id_curso", "grado", "Seleccione curso", "cursos"],
  ];
  chain.forEach(([sourceId,targetId,key,label,tipo]) => document.getElementById(sourceId)?.addEventListener("change", async event => {
    const target=document.getElementById(targetId); target.disabled=true;
    const response=await fetch(`${window.AulaProDocenteOpciones}?${key}=${encodeURIComponent(event.target.value)}${tipo ? `&tipo=${tipo}` : ""}`);
    const data=await response.json(); target.innerHTML=`<option value="">${label}</option>`+data.resultados.map(x=>`<option value="${x.id}">${x.nombre}</option>`).join(""); target.disabled=false;
  }));
}

if(window.AulaProAttendance){
 const form=document.getElementById('attendanceForm'), rows=[...document.querySelectorAll('.attendance-row')], total=window.AulaProAttendance.total;
 const refresh=()=>{const done=rows.filter(r=>r.querySelector('input:checked')?.value!=='SIN_MARCAR').length,pending=total-done,pct=total?Math.round(done*100/total):0;document.getElementById('progressCopy').textContent=`${done} / ${total} registrados`;document.getElementById('pendingCopy').textContent=`${pending} pendientes`;document.getElementById('stickyProgress').textContent=`${done} de ${total} registrados`;document.getElementById('attendanceProgress').style.width=`${pct}%`;document.getElementById('closeAttendance').disabled=pending>0};
 form?.addEventListener('change',refresh);document.getElementById('markAll')?.addEventListener('click',()=>{rows.forEach(r=>{const x=r.querySelector('input[value="PRESENTE"]');if(x&&!x.disabled)x.checked=true});refresh()});document.getElementById('studentSearch')?.addEventListener('input',e=>rows.forEach(r=>r.hidden=!r.dataset.search.includes(e.target.value.toLowerCase())));refresh();
}

document.querySelectorAll('.grade-input').forEach(input=>{let timer;input.addEventListener('input',()=>{const state=input.nextElementSibling;state.textContent='Guardando...';input.classList.remove('save-error');clearTimeout(timer);timer=setTimeout(async()=>{const data=new FormData();data.append('punteo',input.value);data.append('estado',input.value===''?'PENDIENTE':'CALIFICADO');try{const response=await fetch(input.dataset.url,{method:'POST',headers:{'X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]')?.value||document.cookie.match(/csrftoken=([^;]+)/)?.[1]||''},body:data});const json=await response.json();if(!response.ok||!json.ok)throw new Error(json.error);state.textContent='Guardado ✓'}catch(error){state.textContent=error.message||'No se pudo guardar';input.classList.add('save-error')}},650)});input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();const all=[...document.querySelectorAll('.grade-input')],next=all[all.indexOf(input)+1];next?.focus()}})});

document.querySelectorAll('.apply-amount').forEach(input=>input.addEventListener('input',()=>{const total=[...document.querySelectorAll('.apply-amount')].reduce((sum,x)=>sum+(parseFloat(x.value)||0),0);const output=document.getElementById('appliedTotal');if(output)output.textContent=total.toFixed(2)}));

// Previene doble envío en operaciones críticas y restablece el modal compartido.
document.querySelectorAll("form").forEach(form => {
  form.addEventListener("submit", event => {
    if (form.dataset.submitting === "true") { event.preventDefault(); return; }
    if (event.submitter?.name) {
      const value = document.createElement("input");
      value.type = "hidden"; value.name = event.submitter.name; value.value = event.submitter.value;
      form.appendChild(value);
    }
    form.dataset.submitting = "true";
    form.querySelectorAll('button[type="submit"], button:not([type])').forEach(button => {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      if (!button.dataset.originalText) button.dataset.originalText = button.innerHTML;
      button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Procesando…';
    });
  });
});
const confirmModal = document.getElementById("confirmModal");
confirmModal?.addEventListener("hidden.bs.modal", () => {
  const form = document.getElementById("confirmModalForm");
  if (form) {
    form.removeAttribute("action");
    delete form.dataset.submitting;
    form.querySelectorAll("button").forEach(button => {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      if (button.dataset.originalText) button.innerHTML = button.dataset.originalText;
    });
  }
});
