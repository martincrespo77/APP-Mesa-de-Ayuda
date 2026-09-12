/**
 * Portal web: perfil del usuario actual, alta de Incidente/Solicitud y
 * listado/detalle de los propios requerimientos. Solo lectura de estado
 * (sin transiciones): las acciones de gestión del ciclo de vida quedan en
 * el cliente de escritorio, según la matriz de roles del backend.
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

const ETIQUETAS_SEVERIDAD = { BAJA: "Baja", MEDIA: "Media", ALTA: "Alta", CRITICA: "Crítica" };

const ETIQUETAS_CATEGORIA = {
    NUEVO_SERVICIO: "Nuevo servicio",
    CAMBIO_ABONO: "Cambio de abono",
    CONSULTA_ADMINISTRATIVA: "Consulta administrativa",
    FACTURACION: "Facturación",
};

const ETIQUETAS_EVENTO = {
    CREACION: "Creación",
    CAMBIO_ESTADO: "Cambio de estado",
    ASIGNACION: "Asignación de técnico",
    RESOLUCION: "Resolución",
    CIERRE: "Cierre",
    CANCELACION: "Cancelación",
};

function formatearFecha(iso) {
    return new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

// -- Perfil del usuario actual ------------------------------------------------

async function cargarPerfil() {
    try {
        const usuario = await apiFetchJson("/usuarios/me");
        document.getElementById("usuario-nombre").textContent = usuario.nombre_completo;
        document.getElementById("usuario-rol").textContent = usuario.rol;
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
            severidad: document.getElementById("severidad").value,
            pasos_reproduccion: document.getElementById("pasos_reproduccion").value,
            servicio_afectado: document.getElementById("servicio_afectado").value,
        };
    } else {
        const fechaLimite = document.getElementById("fecha_limite").value;
        cuerpo = {
            tipo: "SOLICITUD",
            titulo,
            descripcion,
            categoria: document.getElementById("categoria").value,
            fecha_limite: fechaLimite ? new Date(fechaLimite).toISOString() : null,
            impacto_estimado: document.getElementById("impacto_estimado").value,
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
        return `Severidad: ${ETIQUETAS_SEVERIDAD[ticket.severidad] ?? ticket.severidad}`;
    }
    return `Categoría: ${ETIQUETAS_CATEGORIA[ticket.categoria] ?? ticket.categoria}`;
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

async function cargarListado() {
    errorListado.hidden = true;
    listaTickets.innerHTML = '<p class="vacio">Cargando…</p>';
    try {
        const tickets = await apiFetchJson("/requerimientos");
        tickets.sort((a, b) => new Date(b.fecha_creacion) - new Date(a.fecha_creacion));
        listaTickets.innerHTML = "";
        if (tickets.length === 0) {
            listaTickets.innerHTML = '<p class="vacio">Todavía no cargaste ningún requerimiento.</p>';
            return;
        }
        tickets.forEach((ticket) => listaTickets.appendChild(renderizarTicket(ticket)));
    } catch (error) {
        listaTickets.innerHTML = "";
        errorListado.textContent = error.message;
        errorListado.hidden = false;
    }
}

document.getElementById("boton-refrescar").addEventListener("click", cargarListado);

// -- Modal de detalle --------------------------------------------------------------

const modal = document.getElementById("modal-detalle");

function filaDetalle(etiqueta, valor) {
    return `<div class="detalle-fila"><span>${etiqueta}</span><span>${valor}</span></div>`;
}

function mostrarDetalle(ticket) {
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
            filaDetalle("Severidad", ETIQUETAS_SEVERIDAD[ticket.severidad] ?? ticket.severidad),
            filaDetalle("Servicio afectado", ticket.servicio_afectado),
            filaDetalle("Pasos de reproducción", ticket.pasos_reproduccion),
        );
    } else {
        filas.push(
            filaDetalle("Categoría", ETIQUETAS_CATEGORIA[ticket.categoria] ?? ticket.categoria),
            filaDetalle("Fecha límite", formatearFecha(ticket.fecha_limite)),
            filaDetalle("Impacto estimado", ticket.impacto_estimado),
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

// -- Inicio ---------------------------------------------------------------------

cargarPerfil();
