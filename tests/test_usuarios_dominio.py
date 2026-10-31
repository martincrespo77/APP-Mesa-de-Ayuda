"""Tests de dominio del módulo `app/usuarios/`: la jerarquía polimórfica por rol.

Cada clase de test es la especificación de un rol según la matriz de roles
del enunciado: lo que ese rol PUEDE hacer y lo que NO PUEDE hacer. Las
preguntas (`puede_cerrar`, `puede_derivar`, ...) se hacen sobre tickets
reales (propio/ajeno, asignado/no asignado), porque muchas respuestas
dependen de la relación entre el usuario y el requerimiento.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.compartido.excepciones import DatoInvalidoError
from app.requerimientos.dominio import (
    CategoriaIncidente,
    Incidente,
    Requerimiento,
    UrgenciaIncidente,
)
from app.supervision.excepciones import RolNoSupervisableError, SupervisionNoPermitidaError
from app.usuarios.dominio import (
    Email,
    Empleado,
    FabricaUsuarios,
    Operador,
    Solicitante,
    Supervisor,
    Tecnico,
    Usuario,
)
from app.usuarios.excepciones import (
    CredencialesInvalidasError,
    EmailCorporativoRequeridoError,
    SuscripcionRequeridaError,
    UsuarioYaActivoError,
    UsuarioYaInactivoError,
)
from tests.actores import UN_SERVICIO, un_operador, un_solicitante, un_supervisor, un_tecnico
from tests.fakes import FakeRepositorioRequerimientos

PreguntaSobreTicket = Callable[[Usuario, Requerimiento], bool]


def _ticket_de(solicitante_id: uuid.UUID) -> Incidente:
    return Incidente(
        titulo="Sin internet",
        descripcion="No navega desde ayer.",
        solicitante_id=solicitante_id,
        urgencia=UrgenciaIncidente.IMPORTANTE,
        categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
        servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        pasos_reproduccion="Reiniciar el router.",
    )


def _ticket_asignado_a(tecnico: Tecnico) -> Incidente:
    ticket = _ticket_de(uuid.uuid4())
    operador = un_operador()
    ticket.iniciar_analisis(operador)
    ticket.asignar_tecnico(tecnico, operador)
    return ticket


def _verificador(password_correcta: str) -> Callable[[str, str], bool]:
    """Simula el verificador bcrypt de infraestructura."""
    return lambda password, _hash: password == password_correcta


# Preguntas de la matriz de roles sobre un ticket, con un id legible para pytest.
INICIAR_ANALISIS = pytest.param(lambda u, r: u.puede_iniciar_analisis(r), id="iniciar_analisis")
ASIGNAR_TECNICO = pytest.param(lambda u, r: u.puede_asignar_tecnico(r), id="asignar_tecnico")
INICIAR_PROGRESO = pytest.param(lambda u, r: u.puede_iniciar_progreso(r), id="iniciar_progreso")
RESOLVER = pytest.param(lambda u, r: u.puede_resolver(r), id="resolver")
CERRAR = pytest.param(lambda u, r: u.puede_cerrar(r), id="cerrar")
CANCELAR = pytest.param(lambda u, r: u.puede_cancelar(r), id="cancelar")
COMENTAR = pytest.param(lambda u, r: u.puede_comentar(r), id="comentar")
DERIVAR = pytest.param(lambda u, r: u.puede_derivar(r), id="derivar")
VER = pytest.param(lambda u, r: u.puede_ver(r), id="ver")


class TestEmail:
    def test_se_normaliza_a_minusculas_y_sin_espacios(self) -> None:
        # Act
        email = Email("  Ana.Perez@Comunicarlos.Com.Ar ")

        # Assert
        assert str(email) == "ana.perez@comunicarlos.com.ar"

    def test_dos_emails_con_distinta_capitalizacion_son_iguales(self) -> None:
        # Assert
        assert Email("Lucia@Mail.com") == Email("lucia@mail.com")

    def test_formato_invalido_lanza_dato_invalido(self) -> None:
        # Act & Assert: es un DominioError (HTTP 422), no un ValueError suelto (500)
        with pytest.raises(DatoInvalidoError):
            Email("correo-invalido")

    def test_no_texto_lanza_type_error(self) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Email(123)  # type: ignore[arg-type]

    def test_sabe_si_pertenece_a_un_dominio(self) -> None:
        # Assert
        assert Email("ana@comunicarlos.com.ar").pertenece_al_dominio("comunicarlos.com.ar")
        assert not Email("ana@gmail.com").pertenece_al_dominio("comunicarlos.com.ar")


class TestFabricaUsuarios:
    @pytest.mark.parametrize(
        ("rol", "clase", "email", "servicios"),
        [
            (RolUsuario.SOLICITANTE, Solicitante, "ana@gmail.com", UN_SERVICIO),
            (RolUsuario.OPERADOR, Operador, "ana@comunicarlos.com.ar", None),
            (RolUsuario.TECNICO, Tecnico, "ana@comunicarlos.com.ar", None),
            (RolUsuario.SUPERVISOR, Supervisor, "ana@comunicarlos.com.ar", None),
        ],
    )
    def test_crea_la_subclase_correspondiente_al_rol(
        self,
        rol: RolUsuario,
        clase: type[Usuario],
        email: str,
        servicios: frozenset[ServicioComunicarlos] | None,
    ) -> None:
        # Act
        usuario = FabricaUsuarios.crear(
            rol,
            nombre_completo="Ana",
            email=email,
            password_hash="hash",
            servicios_suscriptos=servicios,
        )

        # Assert
        assert type(usuario) is clase
        assert usuario.rol == rol

    def test_rol_invalido_lanza_type_error(self) -> None:
        # Act & Assert: se pasa un str en lugar de un RolUsuario
        with pytest.raises(TypeError):
            FabricaUsuarios.crear("OPERADOR", nombre_completo="Ana")  # type: ignore[arg-type]


class TestCuenta:
    """Comportamiento de cuenta común a todos los roles."""

    def test_nace_activo_con_id_y_fecha_y_sin_ultimo_acceso(self) -> None:
        # Act
        usuario = un_operador()

        # Assert
        assert usuario.activo is True
        assert isinstance(usuario.id, uuid.UUID)
        assert usuario.fecha_creacion.tzinfo is not None
        assert usuario.ultimo_acceso is None

    def test_nombre_vacio_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Operador("   ", "ana@comunicarlos.com.ar", "hash")

    def test_password_hash_vacio_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Operador("Ana", "ana@comunicarlos.com.ar", "   ")

    def test_desactivar_y_reactivar(self) -> None:
        # Arrange
        usuario = un_operador()

        # Act & Assert
        usuario.desactivar()
        assert not usuario.activo
        usuario.activar()
        assert usuario.activo

    def test_desactivar_usuario_ya_inactivo_lanza_error(self) -> None:
        # Arrange
        usuario = un_operador(activo=False)

        # Act & Assert
        with pytest.raises(UsuarioYaInactivoError):
            usuario.desactivar()

    def test_activar_usuario_ya_activo_lanza_error(self) -> None:
        # Act & Assert
        with pytest.raises(UsuarioYaActivoError):
            un_operador().activar()

    def test_el_hash_de_contrasena_se_conserva_byte_a_byte(self) -> None:
        # Act: un hash nunca se normaliza (recortarlo lo invalidaría)
        usuario = Operador("Ana", "ana@comunicarlos.com.ar", " hash-con-espacios ")

        # Assert
        assert usuario.password_hash == " hash-con-espacios "

    def test_cambiar_password_hash(self) -> None:
        # Arrange
        usuario = un_operador()

        # Act
        usuario.cambiar_password_hash("nuevo-hash-bcrypt")

        # Assert
        assert usuario.password_hash == "nuevo-hash-bcrypt"

    def test_registrar_acceso_fija_ultimo_acceso(self) -> None:
        # Arrange
        usuario = un_operador()
        antes = datetime.now(UTC)

        # Act
        usuario.registrar_acceso()

        # Assert
        assert usuario.ultimo_acceso is not None
        assert usuario.ultimo_acceso >= antes


class TestAutenticar:
    def test_password_correcta_autentica_y_registra_el_acceso(self) -> None:
        # Arrange
        usuario = un_operador()

        # Act
        usuario.autenticar("secreta", _verificador("secreta"))

        # Assert
        assert usuario.ultimo_acceso is not None

    def test_password_incorrecta_lanza_credenciales_invalidas(self) -> None:
        # Arrange
        usuario = un_operador()

        # Act & Assert
        with pytest.raises(CredencialesInvalidasError):
            usuario.autenticar("otra", _verificador("secreta"))
        assert usuario.ultimo_acceso is None

    def test_usuario_desactivado_no_puede_autenticarse(self) -> None:
        # Arrange
        usuario = un_operador(activo=False)

        # Act & Assert: aunque la contraseña sea correcta
        with pytest.raises(CredencialesInvalidasError):
            usuario.autenticar("secreta", _verificador("secreta"))


class TestSolicitante:
    """Cliente: opera solo sobre sus propios tickets."""

    @pytest.fixture
    def solicitante(self) -> Solicitante:
        return un_solicitante()

    def test_puede_usar_cualquier_email(self) -> None:
        # Act
        solicitante = un_solicitante(email="ana@gmail.com")

        # Assert
        assert solicitante.email == "ana@gmail.com"

    def test_debe_estar_suscripto_a_al_menos_un_servicio(self) -> None:
        # Act & Assert
        with pytest.raises(SuscripcionRequeridaError):
            Solicitante("Ana", "ana@gmail.com", "hash")

    def test_conserva_sus_servicios_suscriptos(self, solicitante: Solicitante) -> None:
        # Assert
        assert solicitante.servicios_suscriptos == UN_SERVICIO

    @pytest.mark.parametrize("pregunta", [VER, COMENTAR, CERRAR, CANCELAR])
    def test_puede_operar_sobre_su_propio_ticket(
        self, solicitante: Solicitante, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert pregunta(solicitante, _ticket_de(solicitante.id))

    @pytest.mark.parametrize("pregunta", [VER, COMENTAR, CERRAR, CANCELAR])
    def test_no_puede_operar_sobre_un_ticket_ajeno(
        self, solicitante: Solicitante, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert not pregunta(solicitante, _ticket_de(uuid.uuid4()))

    def test_solo_obtiene_sus_propios_tickets_del_repositorio(
        self, solicitante: Solicitante
    ) -> None:
        # Arrange
        repositorio = FakeRepositorioRequerimientos()
        propio, ajeno = _ticket_de(solicitante.id), _ticket_de(uuid.uuid4())
        repositorio.guardar(propio)
        repositorio.guardar(ajeno)

        # Act
        visibles = solicitante.requerimientos_visibles(repositorio)

        # Assert
        assert [r.id for r in visibles] == [propio.id]

    def test_solo_puede_cancelar_mientras_el_ticket_esta_abierto(
        self, solicitante: Solicitante
    ) -> None:
        # Arrange
        ticket = _ticket_de(solicitante.id)
        ticket.iniciar_analisis(un_operador())

        # Assert
        assert not solicitante.puede_cancelar(ticket)

    @pytest.mark.parametrize(
        "pregunta", [INICIAR_ANALISIS, ASIGNAR_TECNICO, INICIAR_PROGRESO, RESOLVER, DERIVAR]
    )
    def test_no_puede_gestionar_ni_trabajar_tickets(
        self, solicitante: Solicitante, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert: ni siquiera sobre los propios
        assert not pregunta(solicitante, _ticket_de(solicitante.id))

    def test_su_comentario_no_reabre_un_ticket_resuelto(self, solicitante: Solicitante) -> None:
        # Assert
        assert not solicitante.reabre_al_comentar()

    def test_no_es_personal_de_la_cooperativa(self, solicitante: Solicitante) -> None:
        # Assert
        assert not solicitante.puede_recibir_requerimientos()
        assert not solicitante.puede_consultar_tecnicos()
        assert not solicitante.es_supervisable()
        assert not solicitante.puede_administrar_usuarios()
        assert not solicitante.puede_administrar_supervisiones()
        assert not solicitante.recibe_notificaciones()

    def test_no_puede_supervisar(self, solicitante: Solicitante) -> None:
        # Act & Assert
        with pytest.raises(SupervisionNoPermitidaError):
            solicitante.supervisar(un_operador())


class TestEmpleado:
    """Lo común a Operador, Técnico y Supervisor."""

    @pytest.mark.parametrize("clase", [Operador, Tecnico, Supervisor])
    def test_requiere_email_corporativo(self, clase: type[Empleado]) -> None:
        # Act & Assert
        with pytest.raises(EmailCorporativoRequeridoError):
            clase("Ana", "ana@gmail.com", "hash")

    @pytest.mark.parametrize("clase", [Operador, Tecnico, Supervisor])
    def test_no_puede_tener_servicios_suscriptos(self, clase: type[Empleado]) -> None:
        # Act & Assert: solo el Solicitante es cliente de la cooperativa
        with pytest.raises(SuscripcionRequeridaError):
            clase("Ana", "ana@comunicarlos.com.ar", "hash", servicios_suscriptos=UN_SERVICIO)

    @pytest.mark.parametrize("empleado", [un_operador(), un_tecnico(), un_supervisor()])
    def test_ve_cualquier_ticket(self, empleado: Empleado) -> None:
        # Assert
        assert empleado.puede_ver(_ticket_de(uuid.uuid4()))

    @pytest.mark.parametrize("empleado", [un_operador(), un_tecnico(), un_supervisor()])
    def test_obtiene_la_bandeja_completa_del_repositorio(self, empleado: Empleado) -> None:
        # Arrange
        repositorio = FakeRepositorioRequerimientos()
        for _ in range(2):
            repositorio.guardar(_ticket_de(uuid.uuid4()))

        # Act & Assert
        assert len(empleado.requerimientos_visibles(repositorio)) == 2

    @pytest.mark.parametrize("clase", [Operador, Tecnico, Supervisor])
    def test_puede_consultar_tecnicos(self, clase: type[Empleado]) -> None:
        # Assert: para asignar (Operador/Supervisor) o derivar (Técnico)
        assert clase("Ana", "ana@comunicarlos.com.ar", "hash").puede_consultar_tecnicos()


class TestOperador:
    """Mesa de entrada: triage, asignación y seguimiento; no trabaja tickets."""

    @pytest.fixture
    def operador(self) -> Operador:
        return un_operador()

    @pytest.mark.parametrize(
        "pregunta", [INICIAR_ANALISIS, ASIGNAR_TECNICO, CERRAR, CANCELAR, COMENTAR]
    )
    def test_puede_gestionar_cualquier_ticket(
        self, operador: Operador, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert pregunta(operador, _ticket_de(uuid.uuid4()))

    @pytest.mark.parametrize("pregunta", [INICIAR_PROGRESO, RESOLVER, DERIVAR])
    def test_no_puede_trabajar_tecnicamente_un_ticket(
        self, operador: Operador, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert not pregunta(operador, _ticket_de(uuid.uuid4()))

    def test_su_comentario_reabre_un_ticket_resuelto(self, operador: Operador) -> None:
        # Assert
        assert operador.reabre_al_comentar()

    def test_consulta_tecnicos_para_asignar(self, operador: Operador) -> None:
        # Assert
        assert operador.puede_consultar_tecnicos()

    def test_es_supervisable(self, operador: Operador) -> None:
        # Assert
        assert operador.es_supervisable()

    def test_no_recibe_tickets_ni_administra(self, operador: Operador) -> None:
        # Assert
        assert not operador.puede_recibir_requerimientos()
        assert not operador.puede_administrar_usuarios()
        assert not operador.puede_administrar_supervisiones()
        assert not operador.recibe_notificaciones()


class TestTecnico:
    """Trabaja los tickets que tiene asignados; todo su poder depende de eso."""

    @pytest.fixture
    def tecnico(self) -> Tecnico:
        return un_tecnico()

    @pytest.mark.parametrize("pregunta", [INICIAR_PROGRESO, RESOLVER, COMENTAR, DERIVAR])
    def test_puede_trabajar_el_ticket_que_tiene_asignado(
        self, tecnico: Tecnico, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert pregunta(tecnico, _ticket_asignado_a(tecnico))

    @pytest.mark.parametrize("pregunta", [INICIAR_PROGRESO, RESOLVER, COMENTAR, DERIVAR])
    def test_no_puede_trabajar_un_ticket_asignado_a_otro(
        self, tecnico: Tecnico, pregunta: PreguntaSobreTicket
    ) -> None:
        # Arrange
        ticket = _ticket_asignado_a(un_tecnico(email="otro@comunicarlos.com.ar"))

        # Assert
        assert not pregunta(tecnico, ticket)

    @pytest.mark.parametrize("pregunta", [INICIAR_ANALISIS, ASIGNAR_TECNICO, CERRAR, CANCELAR])
    def test_no_puede_gestionar_tickets_ni_siquiera_los_suyos(
        self, tecnico: Tecnico, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert not pregunta(tecnico, _ticket_asignado_a(tecnico))

    def test_su_comentario_reabre_un_ticket_resuelto(self, tecnico: Tecnico) -> None:
        # Assert
        assert tecnico.reabre_al_comentar()

    def test_puede_recibir_tickets_mientras_esta_activo(self, tecnico: Tecnico) -> None:
        # Assert
        assert tecnico.puede_recibir_requerimientos()

    def test_desactivado_no_puede_recibir_tickets(self) -> None:
        # Arrange
        tecnico = un_tecnico(activo=False)

        # Assert
        assert not tecnico.puede_recibir_requerimientos()

    def test_consulta_tecnicos_para_derivar(self, tecnico: Tecnico) -> None:
        # Assert
        assert tecnico.puede_consultar_tecnicos()

    def test_es_supervisable(self, tecnico: Tecnico) -> None:
        # Assert
        assert tecnico.es_supervisable()

    def test_no_administra_ni_recibe_notificaciones(self, tecnico: Tecnico) -> None:
        # Assert
        assert not tecnico.puede_administrar_usuarios()
        assert not tecnico.puede_administrar_supervisiones()
        assert not tecnico.recibe_notificaciones()


class TestSupervisor:
    """Autoridad: cualquier transición, administración y auditoría."""

    @pytest.fixture
    def supervisor(self) -> Supervisor:
        return un_supervisor()

    @pytest.mark.parametrize(
        "pregunta",
        [INICIAR_ANALISIS, ASIGNAR_TECNICO, INICIAR_PROGRESO, RESOLVER, CERRAR, CANCELAR],
    )
    def test_puede_ejecutar_cualquier_transicion_sin_ser_el_asignado(
        self, supervisor: Supervisor, pregunta: PreguntaSobreTicket
    ) -> None:
        # Arrange
        ticket = _ticket_asignado_a(un_tecnico())

        # Assert
        assert pregunta(supervisor, ticket)

    @pytest.mark.parametrize("pregunta", [COMENTAR, DERIVAR])
    def test_no_comenta_ni_deriva(
        self, supervisor: Supervisor, pregunta: PreguntaSobreTicket
    ) -> None:
        # Assert
        assert not pregunta(supervisor, _ticket_asignado_a(un_tecnico()))

    def test_administra_usuarios_y_supervisiones(self, supervisor: Supervisor) -> None:
        # Assert
        assert supervisor.puede_administrar_usuarios()
        assert supervisor.puede_administrar_supervisiones()

    def test_recibe_notificaciones(self, supervisor: Supervisor) -> None:
        # Assert
        assert supervisor.recibe_notificaciones()

    def test_no_recibe_tickets_ni_es_supervisable(self, supervisor: Supervisor) -> None:
        # Assert
        assert not supervisor.puede_recibir_requerimientos()
        assert not supervisor.es_supervisable()

    @pytest.mark.parametrize("empleado", [un_operador(), un_tecnico()])
    def test_puede_supervisar_operadores_y_tecnicos(
        self, supervisor: Supervisor, empleado: Empleado
    ) -> None:
        # Act
        relacion = supervisor.supervisar(empleado)

        # Assert
        assert relacion.supervisor_id == supervisor.id
        assert relacion.supervisado_id == empleado.id

    @pytest.mark.parametrize(
        "usuario",
        [
            pytest.param(un_solicitante(), id="solicitante"),
            pytest.param(un_supervisor(email="otra@comunicarlos.com.ar"), id="supervisor"),
        ],
    )
    def test_no_puede_supervisar_a_quien_no_es_supervisable(
        self, supervisor: Supervisor, usuario: Usuario
    ) -> None:
        # Act & Assert
        with pytest.raises(RolNoSupervisableError):
            supervisor.supervisar(usuario)

    @pytest.mark.parametrize("no_supervisor", [un_operador(), un_tecnico()])
    def test_ningun_otro_rol_puede_supervisar(self, no_supervisor: Usuario) -> None:
        # Act & Assert
        with pytest.raises(SupervisionNoPermitidaError):
            no_supervisor.supervisar(un_tecnico(email="otro@comunicarlos.com.ar"))


class TestCambiarRol:
    def test_devuelve_el_mismo_usuario_encarnado_en_el_nuevo_rol(self) -> None:
        # Arrange
        operador = un_operador()

        # Act
        supervisor = operador.cambiar_rol(RolUsuario.SUPERVISOR)

        # Assert: otra clase, misma identidad y datos
        assert isinstance(supervisor, Supervisor)
        assert supervisor.id == operador.id
        assert supervisor.email == operador.email
        assert supervisor.puede_administrar_usuarios()

    def test_no_muta_la_instancia_original(self) -> None:
        # Arrange
        operador = un_operador()

        # Act
        operador.cambiar_rol(RolUsuario.SUPERVISOR)

        # Assert
        assert isinstance(operador, Operador)
        assert operador.rol == RolUsuario.OPERADOR

    def test_ascender_solicitante_con_email_no_corporativo_lanza_error(self) -> None:
        # Arrange: Solicitante con email personal, válido para su rol actual
        solicitante = un_solicitante(email="ana@gmail.com")

        # Act & Assert: no puede pasar a Operador sin antes tener email corporativo
        with pytest.raises(EmailCorporativoRequeridoError):
            solicitante.cambiar_rol(RolUsuario.OPERADOR)

    def test_ascender_solicitante_con_servicios_suscriptos_lanza_error(self) -> None:
        # Arrange: email ya corporativo, pero conserva servicios suscriptos de Solicitante
        solicitante = un_solicitante(email="ana@comunicarlos.com.ar")

        # Act & Assert: un empleado no puede tener servicios suscriptos
        with pytest.raises(SuscripcionRequeridaError):
            solicitante.cambiar_rol(RolUsuario.OPERADOR)

    def test_un_empleado_no_puede_pasar_a_solicitante_sin_servicios(self) -> None:
        # Act & Assert
        with pytest.raises(SuscripcionRequeridaError):
            un_operador().cambiar_rol(RolUsuario.SOLICITANTE)
