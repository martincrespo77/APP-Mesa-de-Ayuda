/**
 * Portal web — Fases 1 a 4 (Solicitante, Operador, Técnico y Supervisor):
 * perfil del usuario actual, alta de Incidente/Solicitud filtrada por
 * servicios suscriptos, y un listado/detalle de requerimientos cuyas
 * pestañas, filtros y acciones se adaptan al rol según la Matriz de
 * Permisos de CLAUDE.md. Las funciones `puede*(ticket)` son la única
 * fuente de verdad de qué botón mostrar; el backend vuelve a validar cada
 * transición de todos modos (Information Expert en las entidades de
 * dominio), así que ocultar un botón acá es una ayuda de UX, no el
 * control de acceso real.
 *
 * También incluye, para Supervisor, la administración de usuarios
 * (crear, cambiar rol, activar/desactivar) — capacidad de negocio
 * separada de "administrar supervisiones" (pestaña Equipo supervisado):
 * una vincula a alguien ya existente como supervisado propio, la otra
 * da de alta cuentas nuevas o les cambia el rol.
 */

if (!exigirSesion()) {
    // exigirSesion() ya redirigió a index.html.
    throw new Error("Sesión no válida.");
}

const ETIQUETAS_ESTADO = {
    ABIERTO: "Abierto",
    EN_ANALISIS: "En análisis",
    EN_PROGRESO: "En progreso",
    RESUELTO: "Resuelto",
    CERRADO: "Cerrado",
    CANCELADO: "Cancelado",
};

const ETIQUETAS_URGENCIA = { MENOR: "Menor", IMPORTANTE: "Importante", CRITICO: "Crítico" };

const ETIQUETAS_CATEGORIA_INCIDENTE = {
    SERVICIO_INACCESIBLE: "Servicio inaccesible",
    BLOQUEO_SIM: "Bloqueo de SIM",
    PERDIDA_O_DESTRUCCION_DE_EQUIPO: "Pérdida o destrucción de equipo",
};

const ETIQUETAS_CATEGORIA_SOLICITUD = {
    ALTA_SERVICIO: "Alta de servicio",
    BAJA_SERVICIO: "Baja de servicio",
};

const ETIQUETAS_SERVICIO = {
    TELEFONIA_CELULAR: "Telefonía celular",
    INTERNET_BANDA_ANCHA: "Internet de banda ancha",
    TELEVISION: "Televisión",
};

const ETIQUETAS_EVENTO = {
    CREACION: "Creación",
    CAMBIO_ESTADO: "Cambio de estado",
    ASIGNACION: "Asignación de técnico",
    RESOLUCION: "Resolución",
    CIERRE: "Cierre",
    CANCELACION: "Cancelación",
    COMENTARIO: "Comentario",
    DERIVACION: "Derivación a otro técnico",
    REAPERTURA: "Reapertura",
};

const ESTADOS_SIN_COMENTARIOS = new Set(["CERRADO", "CANCELADO"]);
const ESTADOS_FINALES = new Set(["CERRADO", "CANCELADO"]);
const SELECTORES_SERVICIO = ["servicio-incidente", "servicio-solicitud"];

function formatearFecha(iso) {
    return new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

// -- Perfil del usuario actual ------------------------------------------------

let usuarioActual = null;
let rolActual = null;
let tecnicosCache = [];
let usuariosCache = []; // Fase 4 (Supervisor): GET /usuarios completo, para resolver nombres.
let notificacionesCache = [];
let supervisadosCache = [];

const ROLES_BANDEJA_GENERAL_SIMPLE = new Set(["OPERADOR", "SUPERVISOR"]);
const ROLES_LISTAN_TECNICOS = new Set(["OPERADOR", "TECNICO", "SUPERVISOR"]);

// Fase 3 (Técnico): "Mis asignaciones" es la vista por defecto; "Todos los
// tickets" reutiliza los mismos filtros avanzados de la bandeja de Operador.
let vistaTecnico = "mis-asignaciones";

function filtrarSelectoresServicio() {
    // El backend no valida hoy el cruce servicio <-> servicios_suscriptos
    // (ver PLAN_DESARROLLO_4_ROLES.md, Fase 1): esto es una restricción de
    // UX para evitar tickets ilógicos, no una protección contra un 400.
    const suscriptos = usuarioActual?.servicios_suscriptos ?? [];
    if (suscriptos.length === 0) return;
    SELECTORES_SERVICIO.forEach((idSelect) => {
        const select = document.getElementById(idSelect);
        let primeraVisible = null;
        [...select.options].forEach((opcion) => {
            const suscripto = suscriptos.includes(opcion.value);
            opcion.hidden = !suscripto;
            opcion.disabled = !suscripto;
            if (suscripto && !primeraVisible) primeraVisible = opcion.value;
        });
        if (primeraVisible) select.value = primeraVisible;
    });
}

function tituloSegunVistaTecnico() {
    return vistaTecnico === "mis-asignaciones" ? "Mis asignaciones" : "Todos los tickets";
}

function aplicarRolAInterfaz() {
    // Fase 2 (Operador, y Supervisor hasta que la Fase 4 le dé su propio
    // panel): bandeja general con filtros avanzados, siempre "todos".
    // Fase 3 (Técnico): "Mis asignaciones" por defecto + toggle a "Todos
    // los tickets", que sí reutiliza esos mismos filtros avanzados.
    const esBandejaSimple = ROLES_BANDEJA_GENERAL_SIMPLE.has(rolActual);
    const esTecnico = rolActual === "TECNICO";

    let tituloListado = "Mis requerimientos";
    if (esBandejaSimple) tituloListado = "Bandeja general";
    if (esTecnico) tituloListado = tituloSegunVistaTecnico();

    document.getElementById("pestana-boton-listado").textContent = tituloListado;
    document.getElementById("listado-titulo").textContent = tituloListado;

    document.getElementById("filtro-estado").hidden = esBandejaSimple || esTecnico;
    document.getElementById("vista-tecnico").hidden = !esTecnico;
    document.getElementById("filtros-avanzados").hidden = !(
        esBandejaSimple ||
        (esTecnico && vistaTecnico === "todos")
    );

    // Fase 4 (Supervisor): pestañas propias de Notificaciones y Equipo
    // supervisado, más el panel de métricas sobre el listado general.
    const esSupervisor = rolActual === "SUPERVISOR";
    document.getElementById("pestana-boton-notificaciones").hidden = !esSupervisor;
    document.getElementById("pestana-boton-equipo").hidden = !esSupervisor;
    document.getElementById("pestana-boton-usuarios").hidden = !esSupervisor;
    document.getElementById("panel-metricas").hidden = !esSupervisor;

    botonCancelarTicket.textContent =
        rolActual === "SOLICITANTE" ? "Cancelar ticket" : "Cancelar / Desestimar";
}

async function cargarTecnicos() {
    if (!ROLES_LISTAN_TECNICOS.has(rolActual)) return;
    try {
        tecnicosCache = await apiFetchJson("/usuarios/tecnicos");
    } catch {
        tecnicosCache = [];
    }
}

function nombreUsuario(usuarioId) {
    return usuariosCache.find((u) => u.id === usuarioId)?.nombre_completo ?? usuarioId;
}

function actualizarBadgeNotificaciones() {
    const noLeidas = notificacionesCache.filter((n) => !n.leida).length;
    const boton = document.getElementById("pestana-boton-notificaciones");
    boton.textContent = noLeidas > 0 ? `Notificaciones (${noLeidas})` : "Notificaciones";
}

async function cargarUsuariosTodos() {
    if (rolActual !== "SUPERVISOR") return;
    usuariosCache = await apiFetchJson("/usuarios");
}

async function cargarNotificaciones() {
    if (rolActual !== "SUPERVISOR") return;
    notificacionesCache = await apiFetchJson("/notificaciones");
    notificacionesCache.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    actualizarBadgeNotificaciones();
}

async function cargarSupervisados() {
    if (rolActual !== "SUPERVISOR") return;
    supervisadosCache = await apiFetchJson("/supervisiones");
}

async function cargarPerfil() {
    try {
        const usuario = await apiFetchJson("/usuarios/me");
        usuarioActual = usuario;
        rolActual = usuario.rol;
        document.getElementById("usuario-nombre").textContent = usuario.nombre_completo;
        document.getElementById("usuario-rol").textContent = usuario.rol;
        filtrarSelectoresServicio();
        aplicarRolAInterfaz();
        await cargarTecnicos();
        try {
            await cargarUsuariosTodos();
        } catch {
            // No bloqueante: la caché queda vacía hasta que se reintente
            // (por ejemplo, al abrir la pestaña de Usuarios).
        }
        try {
            await cargarNotificaciones();
        } catch {
            // No bloqueante: el badge queda en 0 hasta que se reintente
            // (por ejemplo, al abrir la pestaña de Notificaciones).
        }
    } catch {
        // apiFetch ya redirige a login si fue un 401; cualquier otro error
        // deja el encabezado en su placeholder, no es bloqueante para el resto.
    }
}

document.getElementById("boton-salir").addEventListener("click", cerrarSesion);

// -- Pestañas ------------------------------------------------------------------

const pestanas = document.querySelectorAll(".pestana");
const secciones = {
    nuevo: document.getElementById("pestana-nuevo"),
    listado: document.getElementById("pestana-listado"),
    notificaciones: document.getElementById("pestana-notificaciones"),
    equipo: document.getElementById("pestana-equipo"),
    usuarios: document.getElementById("pestana-usuarios"),
};

function mostrarPestana(nombre) {
    pestanas.forEach((boton) => boton.classList.toggle("activa", boton.dataset.pestana === nombre));
    Object.entries(secciones).forEach(([clave, el]) => {
        el.hidden = clave !== nombre;
    });
    if (nombre === "listado") cargarListado();
    if (nombre === "notificaciones") cargarYRenderizarNotificaciones();
    if (nombre === "equipo") cargarYRenderizarEquipo();
    if (nombre === "usuarios") cargarYRenderizarUsuarios();
}

pestanas.forEach((boton) => {
    boton.addEventListener("click", () => mostrarPestana(boton.dataset.pestana));
});

// -- Formulario de creación ------------------------------------------------------

const selectorTipo = document.getElementById("tipo");
const camposIncidente = document.getElementById("campos-incidente");
const camposSolicitud = document.getElementById("campos-solicitud");

function actualizarCamposPorTipo() {
    const esIncidente = selectorTipo.value === "INCIDENTE";
    camposIncidente.hidden = !esIncidente;
    camposSolicitud.hidden = esIncidente;
}

selectorTipo.addEventListener("change", actualizarCamposPorTipo);
actualizarCamposPorTipo();

document.getElementById("form-nuevo").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const boton = evento.submitter;
    const errorEl = document.getElementById("error-nuevo");
    const exitoEl = document.getElementById("exito-nuevo");
    errorEl.hidden = true;
    exitoEl.hidden = true;
    boton.disabled = true;

    const titulo = document.getElementById("titulo").value;
    const descripcion = document.getElementById("descripcion").value;

    let cuerpo;
    if (selectorTipo.value === "INCIDENTE") {
        cuerpo = {
            tipo: "INCIDENTE",
            titulo,
            descripcion,
            urgencia: document.getElementById("urgencia").value,
            categoria: document.getElementById("categoria-incidente").value,
            servicio: document.getElementById("servicio-incidente").value,
            pasos_reproduccion: document.getElementById("pasos_reproduccion").value,
        };
    } else {
        cuerpo = {
            tipo: "SOLICITUD",
            titulo,
            descripcion,
            categoria: document.getElementById("categoria-solicitud").value,
            servicio: document.getElementById("servicio-solicitud").value,
        };
    }

    try {
        await apiFetchJson("/requerimientos", { method: "POST", body: JSON.stringify(cuerpo) });
        exitoEl.textContent = "Requerimiento creado correctamente.";
        exitoEl.hidden = false;
        evento.target.reset();
        actualizarCamposPorTipo();
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.hidden = false;
    } finally {
        boton.disabled = false;
    }
});

// -- Listado y detalle -----------------------------------------------------------

const listaTickets = document.getElementById("lista-tickets");
const errorListado = document.getElementById("error-listado");

function metaEspecifica(ticket) {
    if (ticket.tipo === "INCIDENTE") {
        return `Urgencia: ${ETIQUETAS_URGENCIA[ticket.urgencia] ?? ticket.urgencia}`;
    }
    return `Categoría: ${ETIQUETAS_CATEGORIA_SOLICITUD[ticket.categoria] ?? ticket.categoria}`;
}

function requiereAtencionUrgente(ticket) {
    // Fase 2: resaltado de advertencia para incidentes CRITICO abiertos o
    // sin técnico asignado todavía (matriz de Operador/Supervisor).
    if (ticket.tipo !== "INCIDENTE" || ticket.urgencia !== "CRITICO") return false;
    return ticket.estado === "ABIERTO" || !ticket.tecnico_asignado_id;
}

function renderizarTicket(ticket) {
    const div = document.createElement("div");
    div.className = "ticket";
    if (requiereAtencionUrgente(ticket)) div.classList.add("ticket-alerta");
    div.innerHTML = `
        <div class="ticket-encabezado">
            <div>
                <div class="ticket-titulo">${ticket.titulo}</div>
                <div class="ticket-meta">${metaEspecifica(ticket)} · Creado: ${formatearFecha(ticket.fecha_creacion)}</div>
            </div>
            <span class="badge badge-${ticket.estado}">${ETIQUETAS_ESTADO[ticket.estado] ?? ticket.estado}</span>
        </div>
    `;
    div.addEventListener("click", () => mostrarDetalle(ticket));
    return div;
}

let ticketsCache = [];
let filtroEstadoActivo = "todos";

const selectFiltroEstado = document.getElementById("filtro-avanzado-estado");
const selectFiltroUrgencia = document.getElementById("filtro-avanzado-urgencia");
const selectFiltroServicio = document.getElementById("filtro-avanzado-servicio");

function ticketPasaFiltroSimple(ticket) {
    if (filtroEstadoActivo === "todos") return true;
    const esFinal = ESTADOS_FINALES.has(ticket.estado);
    return filtroEstadoActivo === "finalizados" ? esFinal : !esFinal;
}

function ticketPasaFiltrosAvanzados(ticket) {
    if (selectFiltroEstado.value && ticket.estado !== selectFiltroEstado.value) return false;
    if (selectFiltroUrgencia.value && ticket.urgencia !== selectFiltroUrgencia.value) return false;
    if (selectFiltroServicio.value && ticket.servicio !== selectFiltroServicio.value) return false;
    return true;
}

function ticketPasaFiltro(ticket) {
    if (rolActual === "TECNICO") {
        return vistaTecnico === "mis-asignaciones"
            ? esTecnicoAsignado(ticket)
            : ticketPasaFiltrosAvanzados(ticket);
    }
    return ROLES_BANDEJA_GENERAL_SIMPLE.has(rolActual)
        ? ticketPasaFiltrosAvanzados(ticket)
        : ticketPasaFiltroSimple(ticket);
}

function actualizarMetricas() {
    if (rolActual !== "SUPERVISOR") return;
    // Métricas del Panel Global: se calculan sobre TODOS los tickets, no
    // sobre el subconjunto que dejan pasar los filtros avanzados vigentes.
    document.getElementById("metrica-abiertos").textContent = ticketsCache.filter(
        (t) => t.estado === "ABIERTO",
    ).length;
    document.getElementById("metrica-criticos").textContent = ticketsCache.filter(
        (t) => t.tipo === "INCIDENTE" && t.urgencia === "CRITICO",
    ).length;
    document.getElementById("metrica-resueltos").textContent = ticketsCache.filter(
        (t) => t.estado === "RESUELTO",
    ).length;
}

function renderizarListado() {
    actualizarMetricas();
    listaTickets.innerHTML = "";
    if (ticketsCache.length === 0) {
        listaTickets.innerHTML = '<p class="vacio">Todavía no cargaste ningún requerimiento.</p>';
        return;
    }
    const visibles = ticketsCache.filter(ticketPasaFiltro);
    if (visibles.length === 0) {
        listaTickets.innerHTML = '<p class="vacio">No hay requerimientos que coincidan con el filtro.</p>';
        return;
    }
    visibles.forEach((ticket) => listaTickets.appendChild(renderizarTicket(ticket)));
}

async function cargarListado() {
    errorListado.hidden = true;
    listaTickets.innerHTML = '<p class="vacio">Cargando…</p>';
    try {
        const tickets = await apiFetchJson("/requerimientos");
        tickets.sort((a, b) => new Date(b.fecha_creacion) - new Date(a.fecha_creacion));
        ticketsCache = tickets;
        renderizarListado();
    } catch (error) {
        listaTickets.innerHTML = "";
        errorListado.textContent = error.message;
        errorListado.hidden = false;
    }
}

document.getElementById("boton-refrescar").addEventListener("click", cargarListado);

document.querySelectorAll("#filtro-estado .chip").forEach((boton) => {
    boton.addEventListener("click", () => {
        filtroEstadoActivo = boton.dataset.filtro;
        document
            .querySelectorAll("#filtro-estado .chip")
            .forEach((otro) => otro.classList.toggle("activa", otro === boton));
        renderizarListado();
    });
});

[selectFiltroEstado, selectFiltroUrgencia, selectFiltroServicio].forEach((select) => {
    select.addEventListener("change", renderizarListado);
});

document.querySelectorAll("#vista-tecnico .chip").forEach((boton) => {
    boton.addEventListener("click", () => {
        vistaTecnico = boton.dataset.vista;
        document
            .querySelectorAll("#vista-tecnico .chip")
            .forEach((otro) => otro.classList.toggle("activa", otro === boton));
        const tituloListado = tituloSegunVistaTecnico();
        document.getElementById("pestana-boton-listado").textContent = tituloListado;
        document.getElementById("listado-titulo").textContent = tituloListado;
        document.getElementById("filtros-avanzados").hidden = vistaTecnico !== "todos";
        renderizarListado();
    });
});

// -- Modal de detalle --------------------------------------------------------------

const modal = document.getElementById("modal-detalle");
const botonIniciarAnalisis = document.getElementById("boton-iniciar-analisis");
const botonIniciarProgreso = document.getElementById("boton-iniciar-progreso");
const botonCancelarTicket = document.getElementById("boton-cancelar-ticket");
const botonConfirmarCierre = document.getElementById("boton-confirmar-cierre");
const bloqueAsignarTecnico = document.getElementById("bloque-asignar-tecnico");
const selectAsignarTecnico = document.getElementById("asignar-tecnico-select");
const botonAsignarTecnico = document.getElementById("boton-asignar-tecnico");
const bloqueDerivar = document.getElementById("bloque-derivar");
const selectDerivarTecnico = document.getElementById("derivar-tecnico-select");
const botonDerivar = document.getElementById("boton-derivar");
const bloqueResolver = document.getElementById("bloque-resolver");
const resolverNota = document.getElementById("resolver-nota");
const botonResolver = document.getElementById("boton-resolver");
const errorDetalle = document.getElementById("error-detalle");
const bloqueComentario = document.getElementById("bloque-comentario");
const comentarioTexto = document.getElementById("comentario-texto");
const botonComentar = document.getElementById("boton-comentar");

let ticketActualId = null;

// -- Matriz de Permisos (CLAUDE.md) aplicada a botones del detalle --------------
// Ocultar acá es solo UX: cada transición vuelve a validarse en el dominio.

function esDueño(ticket) {
    return usuarioActual != null && ticket.solicitante_id === usuarioActual.id;
}

function esTecnicoAsignado(ticket) {
    return usuarioActual != null && ticket.tecnico_asignado_id === usuarioActual.id;
}

function puedeIniciarAnalisis(ticket) {
    return (rolActual === "OPERADOR" || rolActual === "SUPERVISOR") && ticket.estado === "ABIERTO";
}

function puedeAsignarTecnico(ticket) {
    return (
        (rolActual === "OPERADOR" || rolActual === "SUPERVISOR") &&
        ticket.estado === "EN_ANALISIS" &&
        !ticket.tecnico_asignado_id
    );
}

function puedeIniciarProgreso(ticket) {
    if (ticket.estado !== "EN_ANALISIS" || !ticket.tecnico_asignado_id) return false;
    if (rolActual === "TECNICO") return esTecnicoAsignado(ticket);
    return rolActual === "SUPERVISOR";
}

function puedeResolver(ticket) {
    if (ticket.estado !== "EN_PROGRESO") return false;
    if (rolActual === "TECNICO") return esTecnicoAsignado(ticket);
    return rolActual === "SUPERVISOR";
}

function hayOtroTecnicoDisponible() {
    return tecnicosCache.some((tecnico) => tecnico.id !== usuarioActual?.id);
}

function puedeDerivar(ticket) {
    // Solo el técnico actualmente asignado deriva (Supervisor no: no es
    // "interconsulta" si lo decide alguien fuera del circuito técnico).
    // Sin otro técnico activo no hay a quién derivar: ocultar el bloque en
    // vez de mostrar un <select> vacío.
    return (
        rolActual === "TECNICO" &&
        esTecnicoAsignado(ticket) &&
        ["EN_ANALISIS", "EN_PROGRESO"].includes(ticket.estado) &&
        hayOtroTecnicoDisponible()
    );
}

function puedeCancelar(ticket) {
    if (rolActual === "SOLICITANTE") return esDueño(ticket) && ticket.estado === "ABIERTO";
    if (rolActual === "OPERADOR" || rolActual === "SUPERVISOR") {
        return ["ABIERTO", "EN_ANALISIS", "EN_PROGRESO"].includes(ticket.estado);
    }
    return false;
}

function puedeCerrar(ticket) {
    if (ticket.estado !== "RESUELTO") return false;
    if (rolActual === "SOLICITANTE") return esDueño(ticket);
    return rolActual === "OPERADOR" || rolActual === "SUPERVISOR";
}

function puedeComentar(ticket) {
    if (ESTADOS_SIN_COMENTARIOS.has(ticket.estado)) return false;
    if (rolActual === "SOLICITANTE") return esDueño(ticket);
    if (rolActual === "OPERADOR") return true;
    if (rolActual === "TECNICO") return esTecnicoAsignado(ticket);
    return false; // SUPERVISOR nunca comenta (matriz de roles).
}

function filaDetalle(etiqueta, valor) {
    return `<div class="detalle-fila"><span>${etiqueta}</span><span>${valor}</span></div>`;
}

function opcionesTecnicos(excluirId) {
    return tecnicosCache
        .filter((tecnico) => tecnico.id !== excluirId)
        .map((tecnico) => `<option value="${tecnico.id}">${tecnico.nombre_completo}</option>`)
        .join("");
}

function poblarSelectTecnicos() {
    selectAsignarTecnico.innerHTML = opcionesTecnicos(null);
}

function poblarSelectDerivar() {
    // El dominio rechaza derivar al mismo técnico ya asignado.
    selectDerivarTecnico.innerHTML = opcionesTecnicos(usuarioActual?.id);
}

function mostrarDetalle(ticket) {
    ticketActualId = ticket.id;
    errorDetalle.hidden = true;

    botonIniciarAnalisis.hidden = !puedeIniciarAnalisis(ticket);
    botonIniciarProgreso.hidden = !puedeIniciarProgreso(ticket);
    botonCancelarTicket.hidden = !puedeCancelar(ticket);
    botonConfirmarCierre.hidden = !puedeCerrar(ticket);

    bloqueAsignarTecnico.hidden = !puedeAsignarTecnico(ticket);
    if (!bloqueAsignarTecnico.hidden) poblarSelectTecnicos();

    bloqueDerivar.hidden = !puedeDerivar(ticket);
    if (!bloqueDerivar.hidden) poblarSelectDerivar();

    bloqueResolver.hidden = !puedeResolver(ticket);
    resolverNota.value = "";

    bloqueComentario.hidden = !puedeComentar(ticket);
    comentarioTexto.value = "";

    document.getElementById("detalle-titulo").textContent = ticket.titulo;

    const filas = [
        filaDetalle("Tipo", ticket.tipo === "INCIDENTE" ? "Incidente" : "Solicitud"),
        filaDetalle(
            "Estado",
            `<span class="badge badge-${ticket.estado}">${ETIQUETAS_ESTADO[ticket.estado] ?? ticket.estado}</span>`,
        ),
        filaDetalle("Descripción", ticket.descripcion),
    ];

    if (ticket.tipo === "INCIDENTE") {
        filas.push(
            filaDetalle("Urgencia", ETIQUETAS_URGENCIA[ticket.urgencia] ?? ticket.urgencia),
            filaDetalle(
                "Categoría",
                ETIQUETAS_CATEGORIA_INCIDENTE[ticket.categoria] ?? ticket.categoria,
            ),
            filaDetalle("Servicio", ETIQUETAS_SERVICIO[ticket.servicio] ?? ticket.servicio),
            filaDetalle("Pasos de reproducción", ticket.pasos_reproduccion),
        );
    } else {
        filas.push(
            filaDetalle(
                "Categoría",
                ETIQUETAS_CATEGORIA_SOLICITUD[ticket.categoria] ?? ticket.categoria,
            ),
            filaDetalle("Servicio", ETIQUETAS_SERVICIO[ticket.servicio] ?? ticket.servicio),
        );
    }

    if (ticket.tecnico_asignado_id) {
        const tecnico = tecnicosCache.find((t) => t.id === ticket.tecnico_asignado_id);
        filas.push(filaDetalle("Técnico asignado", tecnico?.nombre_completo ?? ticket.tecnico_asignado_id));
    }
    if (ticket.nota_resolucion) {
        filas.push(filaDetalle("Nota de resolución", ticket.nota_resolucion));
    }

    document.getElementById("detalle-cuerpo").innerHTML = filas.join("");

    const historial = [...ticket.historial]
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
        .map(
            (evento) => `
                <div class="historial-evento">
                    <span class="tipo">${ETIQUETAS_EVENTO[evento.tipo_evento] ?? evento.tipo_evento}</span>
                    · <span class="fecha">${formatearFecha(evento.timestamp)}</span>
                    <div>${evento.detalle}</div>
                </div>
            `,
        )
        .join("");
    document.getElementById("detalle-historial").innerHTML = historial;

    modal.hidden = false;
}

document.getElementById("boton-cerrar-modal").addEventListener("click", () => {
    modal.hidden = true;
});
modal.addEventListener("click", (evento) => {
    if (evento.target === modal) modal.hidden = true;
});

async function ejecutarAccionTicket(accion, mensajeConfirmacion, boton) {
    if (!window.confirm(mensajeConfirmacion)) return;
    errorDetalle.hidden = true;
    boton.disabled = true;
    try {
        const actualizado = await apiFetchJson(`/requerimientos/${ticketActualId}/${accion}`, {
            method: "POST",
        });
        mostrarDetalle(actualizado);
        cargarListado();
    } catch (error) {
        errorDetalle.textContent = error.message;
        errorDetalle.hidden = false;
    } finally {
        boton.disabled = false;
    }
}

botonIniciarAnalisis.addEventListener("click", () =>
    ejecutarAccionTicket(
        "iniciar-analisis",
        "¿Iniciar el análisis de este ticket?",
        botonIniciarAnalisis,
    ),
);

botonAsignarTecnico.addEventListener("click", async () => {
    const tecnicoId = selectAsignarTecnico.value;
    if (!tecnicoId) return;
    errorDetalle.hidden = true;
    botonAsignarTecnico.disabled = true;
    try {
        const actualizado = await apiFetchJson(`/requerimientos/${ticketActualId}/asignar-tecnico`, {
            method: "POST",
            body: JSON.stringify({ tecnico_id: tecnicoId }),
        });
        mostrarDetalle(actualizado);
        cargarListado();
    } catch (error) {
        errorDetalle.textContent = error.message;
        errorDetalle.hidden = false;
    } finally {
        botonAsignarTecnico.disabled = false;
    }
});

botonIniciarProgreso.addEventListener("click", () =>
    ejecutarAccionTicket(
        "iniciar-progreso",
        "¿Iniciar el progreso de este ticket?",
        botonIniciarProgreso,
    ),
);

botonDerivar.addEventListener("click", async () => {
    const tecnicoDestinoId = selectDerivarTecnico.value;
    if (!tecnicoDestinoId) return;
    if (!window.confirm("¿Derivar este ticket a otro técnico (interconsulta)?")) return;
    errorDetalle.hidden = true;
    botonDerivar.disabled = true;
    try {
        const actualizado = await apiFetchJson(`/requerimientos/${ticketActualId}/derivar`, {
            method: "POST",
            body: JSON.stringify({ tecnico_destino_id: tecnicoDestinoId }),
        });
        mostrarDetalle(actualizado);
        cargarListado();
    } catch (error) {
        errorDetalle.textContent = error.message;
        errorDetalle.hidden = false;
    } finally {
        botonDerivar.disabled = false;
    }
});

botonResolver.addEventListener("click", async () => {
    const nota = resolverNota.value.trim();
    if (!nota) {
        errorDetalle.textContent = "La nota de resolución es obligatoria.";
        errorDetalle.hidden = false;
        return;
    }
    if (!window.confirm("¿Marcar este ticket como resuelto?")) return;
    errorDetalle.hidden = true;
    botonResolver.disabled = true;
    try {
        const actualizado = await apiFetchJson(`/requerimientos/${ticketActualId}/resolver`, {
            method: "POST",
            body: JSON.stringify({ nota_resolucion: nota }),
        });
        mostrarDetalle(actualizado);
        cargarListado();
    } catch (error) {
        errorDetalle.textContent = error.message;
        errorDetalle.hidden = false;
    } finally {
        botonResolver.disabled = false;
    }
});

botonCancelarTicket.addEventListener("click", () =>
    ejecutarAccionTicket(
        "cancelar",
        "¿Cancelar este ticket? La acción no se puede deshacer.",
        botonCancelarTicket,
    ),
);

botonConfirmarCierre.addEventListener("click", () =>
    ejecutarAccionTicket(
        "cerrar",
        "¿Confirmar el cierre de este ticket?",
        botonConfirmarCierre,
    ),
);

botonComentar.addEventListener("click", async () => {
    const texto = comentarioTexto.value.trim();
    if (!texto) return;
    errorDetalle.hidden = true;
    botonComentar.disabled = true;
    try {
        await apiFetchJson(`/requerimientos/${ticketActualId}/comentarios`, {
            method: "POST",
            body: JSON.stringify({ texto }),
        });
        // El endpoint de comentarios solo devuelve el comentario creado, no
        // el ticket: hay que releerlo para reflejar el nuevo evento en el
        // historial y un eventual estado tras la reapertura automática.
        const actualizado = await apiFetchJson(`/requerimientos/${ticketActualId}`);
        mostrarDetalle(actualizado);
        cargarListado();
    } catch (error) {
        errorDetalle.textContent = error.message;
        errorDetalle.hidden = false;
    } finally {
        botonComentar.disabled = false;
    }
});

// -- Notificaciones y Equipo supervisado (Fase 4, Supervisor) ------------------

const listaNotificaciones = document.getElementById("lista-notificaciones");
const errorNotificaciones = document.getElementById("error-notificaciones");

function renderizarNotificacion(notificacion) {
    const div = document.createElement("div");
    div.className = "ticket";
    if (!notificacion.leida) div.classList.add("ticket-alerta");
    div.innerHTML = `
        <div class="ticket-encabezado">
            <div>
                <div class="ticket-titulo">${ETIQUETAS_EVENTO[notificacion.tipo_evento] ?? notificacion.tipo_evento} — ${nombreUsuario(notificacion.empleado_supervisado_id)}</div>
                <div class="ticket-meta">${notificacion.detalle} · ${formatearFecha(notificacion.timestamp)}</div>
            </div>
        </div>
        <div style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button type="button" class="secundario boton-ver-ticket">Ver ticket</button>
            ${notificacion.leida ? "" : '<button type="button" class="boton-marcar-leida">Marcar como leída</button>'}
        </div>
    `;
    div.querySelector(".boton-ver-ticket").addEventListener("click", async () => {
        try {
            const ticket = await apiFetchJson(`/requerimientos/${notificacion.requerimiento_id}`);
            mostrarDetalle(ticket);
        } catch (error) {
            errorNotificaciones.textContent = error.message;
            errorNotificaciones.hidden = false;
        }
    });
    const botonLeida = div.querySelector(".boton-marcar-leida");
    if (botonLeida) {
        botonLeida.addEventListener("click", async () => {
            botonLeida.disabled = true;
            try {
                await apiFetchJson(`/notificaciones/${notificacion.id}/leida`, { method: "PATCH" });
                notificacion.leida = true;
                actualizarBadgeNotificaciones();
                renderizarNotificaciones();
            } catch (error) {
                errorNotificaciones.textContent = error.message;
                errorNotificaciones.hidden = false;
                botonLeida.disabled = false;
            }
        });
    }
    return div;
}

function renderizarNotificaciones() {
    listaNotificaciones.innerHTML = "";
    if (notificacionesCache.length === 0) {
        listaNotificaciones.innerHTML = '<p class="vacio">No hay notificaciones todavía.</p>';
        return;
    }
    notificacionesCache.forEach((n) => listaNotificaciones.appendChild(renderizarNotificacion(n)));
}

async function cargarYRenderizarNotificaciones() {
    errorNotificaciones.hidden = true;
    listaNotificaciones.innerHTML = '<p class="vacio">Cargando…</p>';
    try {
        await cargarNotificaciones();
        renderizarNotificaciones();
    } catch (error) {
        listaNotificaciones.innerHTML = "";
        errorNotificaciones.textContent = error.message;
        errorNotificaciones.hidden = false;
    }
}

document.getElementById("boton-refrescar-notificaciones").addEventListener(
    "click",
    cargarYRenderizarNotificaciones,
);

const listaEquipo = document.getElementById("lista-equipo");
const errorEquipo = document.getElementById("error-equipo");
const selectNuevoSupervisado = document.getElementById("select-nuevo-supervisado");
const botonAgregarSupervisado = document.getElementById("boton-agregar-supervisado");

const ROLES_SUPERVISABLES = new Set(["OPERADOR", "TECNICO"]);

function renderizarEquipo() {
    listaEquipo.innerHTML = "";
    if (supervisadosCache.length === 0) {
        listaEquipo.innerHTML = '<p class="vacio">Todavía no supervisás a nadie.</p>';
        return;
    }
    supervisadosCache.forEach((relacion) => {
        const usuario = usuariosCache.find((u) => u.id === relacion.supervisado_id);
        const div = document.createElement("div");
        div.className = "ticket";
        div.innerHTML = `
            <div class="ticket-encabezado">
                <div>
                    <div class="ticket-titulo">${usuario?.nombre_completo ?? relacion.supervisado_id}</div>
                    <div class="ticket-meta">${usuario?.rol ?? ""} · Supervisado desde: ${formatearFecha(relacion.fecha_asignacion)}</div>
                </div>
                <button type="button" class="secundario boton-quitar-supervisado">Quitar</button>
            </div>
        `;
        div.querySelector(".boton-quitar-supervisado").addEventListener("click", async () => {
            if (!window.confirm(`¿Dejar de supervisar a ${usuario?.nombre_completo ?? "este usuario"}?`)) return;
            errorEquipo.hidden = true;
            try {
                await apiFetchJson(`/supervisiones/${relacion.supervisado_id}`, { method: "DELETE" });
                await cargarYRenderizarEquipo();
            } catch (error) {
                errorEquipo.textContent = error.message;
                errorEquipo.hidden = false;
            }
        });
        listaEquipo.appendChild(div);
    });
}

function poblarSelectNuevoSupervisado() {
    const yaSupervisados = new Set(supervisadosCache.map((r) => r.supervisado_id));
    const candidatos = usuariosCache.filter(
        (u) => ROLES_SUPERVISABLES.has(u.rol) && u.activo && !yaSupervisados.has(u.id),
    );
    selectNuevoSupervisado.innerHTML = candidatos
        .map((u) => `<option value="${u.id}">${u.nombre_completo} (${u.rol})</option>`)
        .join("");
}

async function cargarYRenderizarEquipo() {
    errorEquipo.hidden = true;
    listaEquipo.innerHTML = '<p class="vacio">Cargando…</p>';
    try {
        await cargarSupervisados();
        renderizarEquipo();
        poblarSelectNuevoSupervisado();
    } catch (error) {
        listaEquipo.innerHTML = "";
        errorEquipo.textContent = error.message;
        errorEquipo.hidden = false;
    }
}

botonAgregarSupervisado.addEventListener("click", async () => {
    const supervisadoId = selectNuevoSupervisado.value;
    if (!supervisadoId) return;
    errorEquipo.hidden = true;
    botonAgregarSupervisado.disabled = true;
    try {
        await apiFetchJson("/supervisiones", {
            method: "POST",
            body: JSON.stringify({ supervisado_id: supervisadoId }),
        });
        await cargarYRenderizarEquipo();
    } catch (error) {
        errorEquipo.textContent = error.message;
        errorEquipo.hidden = false;
    } finally {
        botonAgregarSupervisado.disabled = false;
    }
});

// -- Administrar usuarios (Supervisor) ------------------------------------------

const ROLES_CON_EMAIL_CORPORATIVO = new Set(["OPERADOR", "TECNICO", "SUPERVISOR"]);
const ETIQUETAS_ROL = {
    SOLICITANTE: "Solicitante",
    OPERADOR: "Operador",
    TECNICO: "Técnico",
    SUPERVISOR: "Supervisor",
};

const formCrearUsuario = document.getElementById("form-crear-usuario");
const selectNuevoUsuarioRol = document.getElementById("nuevo-usuario-rol");
const bloqueNuevoUsuarioServicios = document.getElementById("nuevo-usuario-servicios");
const hintNuevoUsuarioEmail = document.getElementById("nuevo-usuario-hint-email");
const errorCrearUsuario = document.getElementById("error-crear-usuario");
const exitoCrearUsuario = document.getElementById("exito-crear-usuario");
const listaUsuarios = document.getElementById("lista-usuarios");
const errorUsuarios = document.getElementById("error-usuarios");

function actualizarFormularioSegunRol() {
    const rol = selectNuevoUsuarioRol.value;
    bloqueNuevoUsuarioServicios.hidden = rol !== "SOLICITANTE";
    hintNuevoUsuarioEmail.hidden = !ROLES_CON_EMAIL_CORPORATIVO.has(rol);
}

selectNuevoUsuarioRol.addEventListener("change", actualizarFormularioSegunRol);
actualizarFormularioSegunRol();

formCrearUsuario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const boton = evento.submitter;
    errorCrearUsuario.hidden = true;
    exitoCrearUsuario.hidden = true;
    boton.disabled = true;

    const rol = selectNuevoUsuarioRol.value;
    const servicios =
        rol === "SOLICITANTE"
            ? [...document.querySelectorAll('input[name="nuevo-usuario-servicio"]:checked')].map(
                  (input) => input.value,
              )
            : [];

    try {
        await apiFetchJson("/usuarios", {
            method: "POST",
            body: JSON.stringify({
                nombre_completo: document.getElementById("nuevo-usuario-nombre").value,
                email: document.getElementById("nuevo-usuario-email").value,
                password: document.getElementById("nuevo-usuario-password").value,
                rol,
                servicios_suscriptos: servicios,
            }),
        });
        exitoCrearUsuario.textContent = "Usuario creado correctamente.";
        exitoCrearUsuario.hidden = false;
        evento.target.reset();
        actualizarFormularioSegunRol();
        await cargarYRenderizarUsuarios();
        await cargarTecnicos(); // por si el usuario creado es un Técnico nuevo
    } catch (error) {
        errorCrearUsuario.textContent = error.message;
        errorCrearUsuario.hidden = false;
    } finally {
        boton.disabled = false;
    }
});

function renderizarUsuarioAdmin(usuario) {
    const div = document.createElement("div");
    div.className = "ticket";
    div.innerHTML = `
        <div class="ticket-encabezado">
            <div>
                <div class="ticket-titulo">${usuario.nombre_completo}</div>
                <div class="ticket-meta">${usuario.email}</div>
            </div>
            <span class="badge ${usuario.activo ? "badge-ACTIVO" : "badge-INACTIVO"}">
                ${usuario.activo ? "Activo" : "Inactivo"}
            </span>
        </div>
        <div class="fila" style="margin-top: 12px; align-items: flex-end;">
            <div>
                <label>Rol</label>
                <select class="select-cambiar-rol">
                    ${Object.entries(ETIQUETAS_ROL)
                        .map(
                            ([valor, etiqueta]) =>
                                `<option value="${valor}" ${valor === usuario.rol ? "selected" : ""}>${etiqueta}</option>`,
                        )
                        .join("")}
                </select>
            </div>
            <div style="display: flex; gap: 10px;">
                <button type="button" class="secundario boton-guardar-rol">Cambiar rol</button>
                <button type="button" class="secundario boton-activar-desactivar">
                    ${usuario.activo ? "Desactivar" : "Activar"}
                </button>
            </div>
        </div>
    `;

    div.querySelector(".boton-guardar-rol").addEventListener("click", async (evento) => {
        const nuevoRol = div.querySelector(".select-cambiar-rol").value;
        if (nuevoRol === usuario.rol) return;
        if (
            !window.confirm(
                `¿Cambiar el rol de ${usuario.nombre_completo} de ${ETIQUETAS_ROL[usuario.rol]} a ${ETIQUETAS_ROL[nuevoRol]}?`,
            )
        ) {
            return;
        }
        errorUsuarios.hidden = true;
        evento.target.disabled = true;
        try {
            await apiFetchJson(`/usuarios/${usuario.id}/rol`, {
                method: "PATCH",
                body: JSON.stringify({ nuevo_rol: nuevoRol }),
            });
            await cargarYRenderizarUsuarios();
            await cargarTecnicos();
        } catch (error) {
            errorUsuarios.textContent = error.message;
            errorUsuarios.hidden = false;
            evento.target.disabled = false;
        }
    });

    div.querySelector(".boton-activar-desactivar").addEventListener("click", async (evento) => {
        const accion = usuario.activo ? "desactivar" : "activar";
        if (!window.confirm(`¿${usuario.activo ? "Desactivar" : "Activar"} a ${usuario.nombre_completo}?`)) {
            return;
        }
        errorUsuarios.hidden = true;
        evento.target.disabled = true;
        try {
            await apiFetchJson(`/usuarios/${usuario.id}/${accion}`, { method: "PATCH" });
            await cargarYRenderizarUsuarios();
            await cargarTecnicos();
        } catch (error) {
            errorUsuarios.textContent = error.message;
            errorUsuarios.hidden = false;
            evento.target.disabled = false;
        }
    });

    return div;
}

function renderizarUsuariosAdmin() {
    listaUsuarios.innerHTML = "";
    if (usuariosCache.length === 0) {
        listaUsuarios.innerHTML = '<p class="vacio">No hay usuarios para mostrar.</p>';
        return;
    }
    usuariosCache.forEach((u) => listaUsuarios.appendChild(renderizarUsuarioAdmin(u)));
}

async function cargarYRenderizarUsuarios() {
    errorUsuarios.hidden = true;
    listaUsuarios.innerHTML = '<p class="vacio">Cargando…</p>';
    try {
        await cargarUsuariosTodos();
        renderizarUsuariosAdmin();
    } catch (error) {
        listaUsuarios.innerHTML = "";
        errorUsuarios.textContent = error.message;
        errorUsuarios.hidden = false;
    }
}

document.getElementById("boton-refrescar-usuarios").addEventListener("click", cargarYRenderizarUsuarios);

// -- Inicio ---------------------------------------------------------------------

cargarPerfil();
