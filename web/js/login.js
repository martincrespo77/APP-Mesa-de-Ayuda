/**
 * Login vía /usuarios/login: el endpoint espera OAuth2PasswordRequestForm
 * (form-urlencoded, campo "username" = email), no JSON.
 */

if (tokenValido()) {
    window.location.href = "app.html";
}

document.getElementById("form-login").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const boton = evento.submitter;
    const errorEl = document.getElementById("error-login");
    errorEl.hidden = true;
    boton.disabled = true;

    const cuerpo = new URLSearchParams();
    cuerpo.set("username", document.getElementById("email").value);
    cuerpo.set("password", document.getElementById("password").value);

    try {
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
        window.location.href = "app.html";
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.hidden = false;
    } finally {
        boton.disabled = false;
    }
});
