/**
 * Portal web — Fases 1 y 2 (Solicitante y Operador): perfil del usuario
 * actual, alta de Incidente/Solicitud filtrada por servicios suscriptos, y
 * un listado/detalle de requerimientos cuyas pestañas, filtros y acciones
 * se adaptan al rol según la Matriz de Permisos de CLAUDE.md. Las
 * funciones `puede*(ticket)` son la única fuente de verdad de qué botón
 * mostrar; el backend vuelve a validar cada transición de todos modos
 * (Information Expert en las entidades de dominio), así que ocultar un
 * botón acá es una ayuda de UX, no el control de acceso real.
 * Lo específico de Técnico (mis asignaciones, derivar, resolver) y de
 * Supervisor (notificaciones, equipo supervisado, panel global) se suma
 * en las fases 3 y 4.
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

const ROLES_CON_BANDEJA_GENERAL = new Set(["OPERADOR", "TECNICO", "SUPERVISOR"]);
const ROLES_LISTAN_TECNICOS = new Set(["OPERADOR", "TECNICO", "SUPERVISOR"]);

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

function aplicarRolAInterfaz() {
    // Fase 2 (Operador): bandeja general con filtros avanzados. Técnico y
    // Supervisor comparten esta misma vista genérica hasta que sus fases
    // (3 y 4) agreguen sus pantallas propias (mis asignaciones, panel, etc.).
    const esBandejaGeneral = ROLES_CON_BANDEJA_GENERAL.has(rolActual);
    const tituloListado = esBandejaGeneral ? "Bandeja general" : "Mis requerimientos";
    document.getElementById("pestana-boton-listado").textContent = tituloListado;
    document.getElementById("listado-titulo").textContent = tituloListado;
    document.getElementById("filtro-estado").hidden = esBandejaGeneral;
    document.getElementById("filtros-avanzados").hidden = !esBandejaGeneral;

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
};

function mostrarPestana(nombre) {
    pestanas.forEach((boton) => boton.classList.toggle("activa", boton.dataset.pestana === nombre));
    Object.entries(secciones).forEach(([clave, el]) => {
        el.hidden = clave !== nombre;
    });
    if (nombre === "listado") cargarListado();
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
    return ROLES_CON_BANDEJA_GENERAL.has(rolActual)
        ? ticketPasaFiltrosAvanzados(ticket)
        : ticketPasaFiltroSimple(ticket);
}

function renderizarListado() {
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

// -- Modal de detalle --------------------------------------------------------------

const modal = document.getElementById("modal-detalle");
const botonIniciarAnalisis = document.getElementById("boton-iniciar-analisis");
const botonCancelarTicket = document.getElementById("boton-cancelar-ticket");
const botonConfirmarCierre = document.getElementById("boton-confirmar-cierre");
const bloqueAsignarTecnico = document.getElementById("bloque-asignar-tecnico");
const selectAsignarTecnico = document.getElementById("asignar-tecnico-select");
const botonAsignarTecnico = document.getElementById("boton-asignar-tecnico");
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

function poblarSelectTecnicos() {
    selectAsignarTecnico.innerHTML = tecnicosCache
        .map((tecnico) => `<option value="${tecnico.id}">${tecnico.nombre_completo}</option>`)
        .join("");
}

function mostrarDetalle(ticket) {
    ticketActualId = ticket.id;
    errorDetalle.hidden = true;

    botonIniciarAnalisis.hidden = !puedeIniciarAnalisis(ticket);
    botonCancelarTicket.hidden = !puedeCancelar(ticket);
    botonConfirmarCierre.hidden = !puedeCerrar(ticket);

    bloqueAsignarTecnico.hidden = !puedeAsignarTecnico(ticket);
    if (!bloqueAsignarTecnico.hidden) poblarSelectTecnicos();

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

// -- Inicio ---------------------------------------------------------------------

cargarPerfil();
