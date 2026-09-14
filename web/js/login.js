/**
 * Login vía /usuarios/login: el endpoint espera OAuth2PasswordRequestForm
 * (form-urlencoded, campo "username" = email), no JSON. El registro vía
 * /usuarios/registro es JSON normal (usa apiFetchJson de api.js) y, si sale
 * bien, inicia sesión automáticamente con las mismas credenciales.
 */

if (tokenValido()) {
    window.location.href = "app.html";
}

async function iniciarSesion(email, password) {
    const cuerpo = new URLSearchParams();
    cuerpo.set("username", email);
    cuerpo.set("password", password);

    const respuesta = await fetch("/usuarios/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: cuerpo,
    });
    if (!respuesta.ok) {
        throw new Error("Email o contraseña incorrectos.");
    }
    const datos = await respuesta.json();
    localStorage.setItem("token", datos.access_token);
}

document.getElementById("form-login").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const boton = evento.submitter;
    const errorEl = document.getElementById("error-login");
    errorEl.hidden = true;
    boton.disabled = true;

    try {
        await iniciarSesion(
            document.getElementById("email").value,
            document.getElementById("password").value,
        );
        window.location.href = "app.html";
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.hidden = false;
    } finally {
        boton.disabled = false;
    }
});

// -- Alternar entre Iniciar sesión y Registrarse --------------------------------

const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");

document.getElementById("link-ir-a-registro").addEventListener("click", (evento) => {
    evento.preventDefault();
    formLogin.hidden = true;
    formRegistro.hidden = false;
});

document.getElementById("link-ir-a-login").addEventListener("click", (evento) => {
    evento.preventDefault();
    formRegistro.hidden = true;
    formLogin.hidden = false;
});

// -- Registro (auto-servicio, siempre crea un Solicitante) ----------------------

formRegistro.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const boton = evento.submitter;
    const errorEl = document.getElementById("error-registro");
    errorEl.hidden = true;

    const email = document.getElementById("registro-email").value;
    const password = document.getElementById("registro-password").value;
    const passwordConfirmar = document.getElementById("registro-password-confirmar").value;
    const servicios = [...document.querySelectorAll('input[name="registro-servicio"]:checked')].map(
        (input) => input.value,
    );

    if (password !== passwordConfirmar) {
        errorEl.textContent = "Las contraseñas no coinciden.";
        errorEl.hidden = false;
        return;
    }
    if (servicios.length === 0) {
        errorEl.textContent = "Elegí al menos un servicio contratado.";
        errorEl.hidden = false;
        return;
    }

    boton.disabled = true;
    try {
        await apiFetchJson("/usuarios/registro", {
            method: "POST",
            body: JSON.stringify({
                nombre_completo: document.getElementById("registro-nombre").value,
                email,
                password,
                servicios_suscriptos: servicios,
            }),
        });
        // Cuenta creada y activa de inmediato: inicia sesión sin pedirle
        // las credenciales de nuevo.
        await iniciarSesion(email, password);
        window.location.href = "app.html";
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.hidden = false;
    } finally {
        boton.disabled = false;
    }
});
