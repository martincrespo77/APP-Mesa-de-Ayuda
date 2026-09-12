/**
 * Wrapper de fetch: adjunta el JWT guardado en localStorage y centraliza
 * el manejo de 401 (token vencido o inválido) limpiando la sesión.
 */

function obtenerToken() {
    return localStorage.getItem("token");
}

function decodificarPayload(token) {
    try {
        const payload = token.split(".")[1];
        const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}

function tokenValido() {
    const token = obtenerToken();
    if (!token) return false;
    const payload = decodificarPayload(token);
    return Boolean(payload && payload.exp && payload.exp * 1000 > Date.now());
}

function cerrarSesion() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}

function exigirSesion() {
    if (!tokenValido()) {
        cerrarSesion();
        return false;
    }
    return true;
}

async function apiFetch(ruta, opciones = {}) {
    const token = obtenerToken();
    const headers = new Headers(opciones.headers || {});
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const respuesta = await fetch(ruta, { ...opciones, headers });
    if (respuesta.status === 401) {
        cerrarSesion();
        throw new Error("La sesión expiró. Iniciá sesión nuevamente.");
    }
    return respuesta;
}

async function apiFetchJson(ruta, opciones = {}) {
    const headers = new Headers(opciones.headers || {});
    headers.set("Content-Type", "application/json");
    const respuesta = await apiFetch(ruta, { ...opciones, headers });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
        const mensaje = (datos && datos.detail) || "Ocurrió un error inesperado.";
        throw new Error(mensaje);
    }
    return datos;
}
