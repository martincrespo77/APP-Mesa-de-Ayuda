/**
 * Portal web — Fase 1 (Solicitante): perfil del usuario actual, alta de
 * Incidente/Solicitud filtrada por servicios suscriptos, y listado/detalle
 * de los propios requerimientos con las únicas transiciones que la matriz
 * de roles habilita a este rol (cancelar propio ABIERTO, confirmar cierre
 * de un RESUELTO, comentar). El resto de las acciones de ciclo de vida
 * (asignar, iniciar progreso, derivar, resolver, etc.) quedan fuera de
 * este rol y se suman en las fases 2 a 4 del portal web.
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

let serviciosSuscriptos = [];

function filtrarSelectoresServicio() {
    // El backend no valida hoy el cruce servicio <-> servicios_suscriptos
    // (ver PLAN_DESARROLLO_4_ROLES.md, Fase 1): esto es una restricción de
    // UX para evitar tickets ilógicos, no una protección contra un 400.
    if (serviciosSuscriptos.length === 0) return;
    SELECTORES_SERVICIO.forEach((idSelect) => {
        const select = document.getElementById(idSelect);
        let primeraVisible = null;
        [...select.options].forEach((opcion) => {
            const suscripto = serviciosSuscriptos.includes(opcion.value);
            opcion.hidden = !suscripto;
            opcion.disabled = !suscripto;
            if (suscripto && !primeraVisible) primeraVisible = opcion.value;
        });
        if (primeraVisible) select.value = primeraVisible;
    });
}

async function cargarPerfil() {
    try {
        const usuario = await apiFetchJson("/usuarios/me");
        document.getElementById("usuario-nombre").textContent = usuario.nombre_completo;
        document.getElementById("usuario-rol").textContent = usuario.rol;
        serviciosSuscriptos = usuario.servicios_suscriptos ?? [];
        filtrarSelectoresServicio();
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

function renderizarTicket(ticket) {
    const div = document.createElement("div");
    div.className = "ticket";
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

function ticketPasaFiltro(ticket) {
    if (filtroEstadoActivo === "todos") return true;
    const esFinal = ESTADOS_FINALES.has(ticket.estado);
    return filtroEstadoActivo === "finalizados" ? esFinal : !esFinal;
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

// -- Modal de detalle --------------------------------------------------------------

const modal = document.getElementById("modal-detalle");
const botonCancelarTicket = document.getElementById("boton-cancelar-ticket");
const botonConfirmarCierre = document.getElementById("boton-confirmar-cierre");
const errorDetalle = document.getElementById("error-detalle");
const bloqueComentario = document.getElementById("bloque-comentario");
const comentarioTexto = document.getElementById("comentario-texto");
const botonComentar = document.getElementById("boton-comentar");

let ticketActualId = null;

function filaDetalle(etiqueta, valor) {
    return `<div class="detalle-fila"><span>${etiqueta}</span><span>${valor}</span></div>`;
}

function mostrarDetalle(ticket) {
    ticketActualId = ticket.id;
    errorDetalle.hidden = true;
    // El dominio (Requerimiento.cancelar/cerrar) solo habilita al Solicitante
    // a cancelar un ticket propio en ABIERTO o dar conformidad sobre uno
    // RESUELTO — las demás transiciones quedan reservadas al cliente de
    // escritorio (Operador/Técnico/Supervisor).
    botonCancelarTicket.hidden = ticket.estado !== "ABIERTO";
    botonConfirmarCierre.hidden = ticket.estado !== "RESUELTO";
    bloqueComentario.hidden = ESTADOS_SIN_COMENTARIOS.has(ticket.estado);
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
        filas.push(filaDetalle("Técnico asignado", ticket.tecnico_asignado_id));
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
