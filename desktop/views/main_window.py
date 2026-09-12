"""Ventana principal: Dashboard con pestañas (doc05).

Tres pestañas: **Requerimientos** (tabla + filtros + panel de detalle con
acciones de transición), **Nuevo Requerimiento** (formulario reactivo
Incidente/Solicitud) y **Notificaciones** (historial de eventos agregado
de todos los requerimientos visibles).
"""

import uuid
from collections.abc import Callable
from datetime import UTC

from PyQt6.QtCore import QDateTime, QModelIndex, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.api_client import ClienteApi, ClienteApiError
from desktop.models import (
    CategoriaSolicitud,
    EstadoRequerimiento,
    RequerimientoDTO,
    Severidad,
    TipoRequerimiento,
    UsuarioDTO,
)
from desktop.styles import color_para_estado, color_para_severidad

_ROL_REQUERIMIENTO_ID = Qt.ItemDataRole.UserRole
_TODOS = "Todos"


class MainWindow(QTabWidget):
    """Ventana principal, ya autenticada: Requerimientos / Nuevo / Notificaciones."""

    def __init__(
        self, cliente: ClienteApi, usuario: UsuarioDTO, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._cliente = cliente
        self._usuario = usuario
        self._requerimientos: list[RequerimientoDTO] = []
        self._seleccionado: RequerimientoDTO | None = None

        self.setWindowTitle(f"Mesa de Ayuda - {usuario.nombre_completo} ({usuario.rol.value})")
        self.resize(1000, 640)

        self.addTab(self._construir_tab_requerimientos(), "Requerimientos")
        self.addTab(self._construir_tab_nuevo_requerimiento(), "Nuevo Requerimiento")
        self.addTab(self._construir_tab_notificaciones(), "Notificaciones")

        self._refrescar()

    # -- Pestaña 1: Requerimientos --------------------------------------------

    def _construir_tab_requerimientos(self) -> QWidget:
        self._campo_busqueda = QLineEdit()
        self._campo_busqueda.setPlaceholderText("Buscar por título o id…")
        self._campo_busqueda.textChanged.connect(self._aplicar_filtros)

        self._filtro_estado = QComboBox()
        self._filtro_estado.addItem(_TODOS)
        self._filtro_estado.addItems([estado.value for estado in EstadoRequerimiento])
        self._filtro_estado.currentTextChanged.connect(self._aplicar_filtros)

        self._filtro_tipo = QComboBox()
        self._filtro_tipo.addItem(_TODOS)
        self._filtro_tipo.addItems([tipo.value for tipo in TipoRequerimiento])
        self._filtro_tipo.currentTextChanged.connect(self._aplicar_filtros)

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self._refrescar)

        barra_filtros = QHBoxLayout()
        barra_filtros.addWidget(self._campo_busqueda, stretch=2)
        barra_filtros.addWidget(QLabel("Estado:"))
        barra_filtros.addWidget(self._filtro_estado)
        barra_filtros.addWidget(QLabel("Tipo:"))
        barra_filtros.addWidget(self._filtro_tipo)
        barra_filtros.addWidget(boton_actualizar)

        self._tabla = QTableWidget(0, 5)
        self._tabla.setHorizontalHeaderLabels(["Tipo", "Título", "Estado", "Solicitante", "Creado"])
        encabezado = self._tabla.horizontalHeader()
        if encabezado is not None:
            encabezado.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabla.itemSelectionChanged.connect(self._mostrar_detalle_de_la_fila_seleccionada)

        self._panel_detalle = self._construir_panel_detalle()

        divisor = QSplitter()
        divisor.addWidget(self._tabla)
        divisor.addWidget(self._panel_detalle)
        divisor.setStretchFactor(0, 2)
        divisor.setStretchFactor(1, 1)

        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.addLayout(barra_filtros)
        layout.addWidget(divisor)
        return contenedor

    def _construir_panel_detalle(self) -> QWidget:
        self._detalle_titulo = QLabel("Seleccioná un requerimiento")
        self._detalle_titulo.setObjectName("titulo")
        self._detalle_titulo.setWordWrap(True)

        self._detalle_info = QLabel()
        self._detalle_info.setWordWrap(True)

        self._detalle_historial = QListWidget()

        self._boton_iniciar_analisis = QPushButton("Iniciar análisis")
        self._boton_iniciar_analisis.clicked.connect(self._accion_iniciar_analisis)

        self._boton_asignar_tecnico = QPushButton("Asignar técnico")
        self._boton_asignar_tecnico.clicked.connect(self._accion_asignar_tecnico)

        self._boton_iniciar_progreso = QPushButton("Iniciar progreso")
        self._boton_iniciar_progreso.clicked.connect(self._accion_iniciar_progreso)

        self._boton_resolver = QPushButton("Resolver")
        self._boton_resolver.clicked.connect(self._accion_resolver)

        self._boton_cerrar = QPushButton("Cerrar")
        self._boton_cerrar.clicked.connect(self._accion_cerrar)

        self._boton_cancelar = QPushButton("Cancelar")
        self._boton_cancelar.setObjectName("botonSecundario")
        self._boton_cancelar.clicked.connect(self._accion_cancelar)

        self._botones_accion = (
            self._boton_iniciar_analisis,
            self._boton_asignar_tecnico,
            self._boton_iniciar_progreso,
            self._boton_resolver,
            self._boton_cerrar,
            self._boton_cancelar,
        )

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._detalle_titulo)
        layout.addWidget(self._detalle_info)
        layout.addWidget(QLabel("Historial:"))
        layout.addWidget(self._detalle_historial, stretch=1)
        for boton in self._botones_accion:
            layout.addWidget(boton)
        self._actualizar_botones_de_accion()
        return panel

    def _mostrar_detalle_de_la_fila_seleccionada(self) -> None:
        modelo_seleccion = self._tabla.selectionModel()
        filas: list[QModelIndex] = (
            modelo_seleccion.selectedRows() if modelo_seleccion is not None else []
        )
        if not filas:
            self._seleccionado = None
        else:
            item = self._tabla.item(filas[0].row(), 0)
            requerimiento_id = item.data(_ROL_REQUERIMIENTO_ID) if item else None
            self._seleccionado = next(
                (r for r in self._requerimientos if r.id == requerimiento_id), None
            )
        self._actualizar_panel_detalle()

    def _actualizar_panel_detalle(self) -> None:
        req = self._seleccionado
        if req is None:
            self._detalle_titulo.setText("Seleccioná un requerimiento")
            self._detalle_info.setText("")
            self._detalle_historial.clear()
            self._actualizar_botones_de_accion()
            return

        self._detalle_titulo.setText(f"{req.tipo.value}: {req.titulo}")
        lineas = [
            f"Id: {req.id}",
            f"Estado: {req.estado.value}",
            f"Descripción: {req.descripcion}",
            f"Solicitante: {req.solicitante_id}",
            f"Técnico asignado: {req.tecnico_asignado_id or '(sin asignar)'}",
        ]
        if req.tipo is TipoRequerimiento.INCIDENTE:
            lineas += [
                f"Severidad: {req.severidad.value if req.severidad else '-'}",
                f"Pasos de reproducción: {req.pasos_reproduccion}",
                f"Servicio afectado: {req.servicio_afectado}",
            ]
        else:
            lineas += [
                f"Categoría: {req.categoria.value if req.categoria else '-'}",
                f"Fecha límite: {req.fecha_limite}",
                f"Impacto estimado: {req.impacto_estimado}",
            ]
        if req.nota_resolucion:
            lineas.append(f"Nota de resolución: {req.nota_resolucion}")
        self._detalle_info.setText("\n".join(lineas))

        self._detalle_historial.clear()
        for evento in req.historial:
            texto = (
                f"[{evento.timestamp:%Y-%m-%d %H:%M}] "
                f"{evento.tipo_evento.value}: {evento.detalle}"
            )
            self._detalle_historial.addItem(QListWidgetItem(texto))

        self._actualizar_botones_de_accion()

    def _actualizar_botones_de_accion(self) -> None:
        req = self._seleccionado
        estados_visibles: dict[QPushButton, bool] = dict.fromkeys(self._botones_accion, False)
        if req is not None:
            estado = req.estado
            estados_visibles[self._boton_iniciar_analisis] = estado == EstadoRequerimiento.ABIERTO
            estados_visibles[self._boton_asignar_tecnico] = (
                estado == EstadoRequerimiento.EN_ANALISIS and req.tecnico_asignado_id is None
            )
            estados_visibles[self._boton_iniciar_progreso] = (
                estado == EstadoRequerimiento.EN_ANALISIS and req.tecnico_asignado_id is not None
            )
            estados_visibles[self._boton_resolver] = estado == EstadoRequerimiento.EN_PROGRESO
            estados_visibles[self._boton_cerrar] = estado == EstadoRequerimiento.RESUELTO
            estados_visibles[self._boton_cancelar] = estado in (
                EstadoRequerimiento.ABIERTO,
                EstadoRequerimiento.EN_ANALISIS,
                EstadoRequerimiento.EN_PROGRESO,
            )
        for boton, visible in estados_visibles.items():
            boton.setVisible(visible)

    def _accion_iniciar_analisis(self) -> None:
        self._ejecutar_accion(lambda req_id: self._cliente.iniciar_analisis(req_id))

    def _accion_asignar_tecnico(self) -> None:
        tecnico_id_texto, ok = QInputDialog.getText(
            self, "Asignar técnico", "Id (UUID) del técnico a asignar:"
        )
        if not ok or not tecnico_id_texto.strip():
            return
        try:
            tecnico_id = uuid.UUID(tecnico_id_texto.strip())
        except ValueError:
            QMessageBox.warning(self, "Id inválido", "El id del técnico debe ser un UUID válido.")
            return
        self._ejecutar_accion(lambda req_id: self._cliente.asignar_tecnico(req_id, tecnico_id))

    def _accion_iniciar_progreso(self) -> None:
        self._ejecutar_accion(lambda req_id: self._cliente.iniciar_progreso(req_id))

    def _accion_resolver(self) -> None:
        nota, ok = QInputDialog.getMultiLineText(
            self, "Resolver requerimiento", "Nota de resolución:"
        )
        if not ok or not nota.strip():
            return
        self._ejecutar_accion(lambda req_id: self._cliente.resolver(req_id, nota.strip()))

    def _accion_cerrar(self) -> None:
        self._ejecutar_accion(lambda req_id: self._cliente.cerrar(req_id))

    def _accion_cancelar(self) -> None:
        self._ejecutar_accion(lambda req_id: self._cliente.cancelar(req_id))

    def _ejecutar_accion(self, accion: Callable[[uuid.UUID], RequerimientoDTO]) -> None:
        if self._seleccionado is None:
            return
        try:
            accion(self._seleccionado.id)
        except ClienteApiError as error:
            QMessageBox.warning(self, "No se pudo completar la acción", str(error))
            return
        self._refrescar()

    # -- Pestaña 2: Nuevo Requerimiento ----------------------------------------

    def _construir_tab_nuevo_requerimiento(self) -> QWidget:
        self._nuevo_tipo = QComboBox()
        self._nuevo_tipo.addItems([tipo.value for tipo in TipoRequerimiento])
        self._nuevo_tipo.currentTextChanged.connect(self._actualizar_campos_reactivos)

        self._nuevo_titulo = QLineEdit()
        self._nuevo_descripcion = QTextEdit()
        self._nuevo_descripcion.setFixedHeight(80)

        self._grupo_incidente = QGroupBox("Datos del Incidente")
        self._nueva_severidad = QComboBox()
        self._nueva_severidad.addItems([severidad.value for severidad in Severidad])
        self._nuevos_pasos_reproduccion = QLineEdit()
        self._nuevo_servicio_afectado = QLineEdit()
        layout_incidente = QFormLayout(self._grupo_incidente)
        layout_incidente.addRow("Severidad:", self._nueva_severidad)
        layout_incidente.addRow("Pasos de reproducción:", self._nuevos_pasos_reproduccion)
        layout_incidente.addRow("Servicio afectado:", self._nuevo_servicio_afectado)

        self._grupo_solicitud = QGroupBox("Datos de la Solicitud")
        self._nueva_categoria = QComboBox()
        self._nueva_categoria.addItems([categoria.value for categoria in CategoriaSolicitud])
        self._nueva_fecha_limite = QDateTimeEdit(QDateTime.currentDateTime().addDays(7))
        self._nueva_fecha_limite.setCalendarPopup(True)
        self._nuevo_impacto_estimado = QLineEdit()
        layout_solicitud = QFormLayout(self._grupo_solicitud)
        layout_solicitud.addRow("Categoría:", self._nueva_categoria)
        layout_solicitud.addRow("Fecha límite:", self._nueva_fecha_limite)
        layout_solicitud.addRow("Impacto estimado:", self._nuevo_impacto_estimado)

        boton_crear = QPushButton("Crear requerimiento")
        boton_crear.clicked.connect(self._crear_requerimiento)

        formulario = QFormLayout()
        formulario.addRow("Tipo:", self._nuevo_tipo)
        formulario.addRow("Título:", self._nuevo_titulo)
        formulario.addRow("Descripción:", self._nuevo_descripcion)

        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.addLayout(formulario)
        layout.addWidget(self._grupo_incidente)
        layout.addWidget(self._grupo_solicitud)
        layout.addWidget(boton_crear)
        layout.addStretch(1)

        self._actualizar_campos_reactivos(self._nuevo_tipo.currentText())
        return contenedor

    def _actualizar_campos_reactivos(self, tipo_seleccionado: str) -> None:
        es_incidente = tipo_seleccionado == TipoRequerimiento.INCIDENTE.value
        self._grupo_incidente.setVisible(es_incidente)
        self._grupo_solicitud.setVisible(not es_incidente)

    def _crear_requerimiento(self) -> None:
        titulo = self._nuevo_titulo.text().strip()
        descripcion = self._nuevo_descripcion.toPlainText().strip()
        if not titulo or not descripcion:
            QMessageBox.warning(self, "Datos incompletos", "Completá título y descripción.")
            return

        try:
            if self._nuevo_tipo.currentText() == TipoRequerimiento.INCIDENTE.value:
                self._cliente.crear_incidente(
                    titulo=titulo,
                    descripcion=descripcion,
                    severidad=Severidad(self._nueva_severidad.currentText()),
                    pasos_reproduccion=self._nuevos_pasos_reproduccion.text().strip(),
                    servicio_afectado=self._nuevo_servicio_afectado.text().strip(),
                )
            else:
                fecha_limite = (
                    self._nueva_fecha_limite.dateTime().toPyDateTime().replace(tzinfo=UTC)
                )
                self._cliente.crear_solicitud(
                    titulo=titulo,
                    descripcion=descripcion,
                    categoria=CategoriaSolicitud(self._nueva_categoria.currentText()),
                    fecha_limite=fecha_limite,
                    impacto_estimado=self._nuevo_impacto_estimado.text().strip(),
                )
        except ClienteApiError as error:
            QMessageBox.warning(self, "No se pudo crear el requerimiento", str(error))
            return

        self._nuevo_titulo.clear()
        self._nuevo_descripcion.clear()
        self._nuevos_pasos_reproduccion.clear()
        self._nuevo_servicio_afectado.clear()
        self._nuevo_impacto_estimado.clear()
        QMessageBox.information(self, "Listo", "Requerimiento creado con éxito.")
        self._refrescar()
        self.setCurrentIndex(0)

    # -- Pestaña 3: Notificaciones ----------------------------------------------

    def _construir_tab_notificaciones(self) -> QWidget:
        self._lista_notificaciones = QListWidget()
        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self._refrescar)

        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.addWidget(QLabel("Historial de eventos de todos los requerimientos visibles:"))
        layout.addWidget(self._lista_notificaciones, stretch=1)
        layout.addWidget(boton_actualizar)
        return contenedor

    def _actualizar_notificaciones(self) -> None:
        self._lista_notificaciones.clear()
        eventos = [
            (evento, req)
            for req in self._requerimientos
            for evento in req.historial
        ]
        eventos.sort(key=lambda par: par[0].timestamp, reverse=True)
        for evento, req in eventos:
            texto = (
                f"[{evento.timestamp:%Y-%m-%d %H:%M}] {evento.tipo_evento.value} "
                f"en '{req.titulo}': {evento.detalle}"
            )
            self._lista_notificaciones.addItem(QListWidgetItem(texto))

    # -- Datos compartidos entre pestañas ---------------------------------------

    def _refrescar(self) -> None:
        try:
            self._requerimientos = self._cliente.listar_requerimientos()
        except ClienteApiError as error:
            QMessageBox.warning(self, "No se pudieron cargar los requerimientos", str(error))
            self._requerimientos = []
        self._aplicar_filtros()
        self._actualizar_notificaciones()

    def _aplicar_filtros(self) -> None:
        texto = self._campo_busqueda.text().strip().lower()
        estado_filtro = self._filtro_estado.currentText()
        tipo_filtro = self._filtro_tipo.currentText()

        visibles = [
            req
            for req in self._requerimientos
            if (not texto or texto in req.titulo.lower() or texto in str(req.id))
            and (estado_filtro == _TODOS or req.estado.value == estado_filtro)
            and (tipo_filtro == _TODOS or req.tipo.value == tipo_filtro)
        ]
        self._poblar_tabla(visibles)

    def _poblar_tabla(self, requerimientos: list[RequerimientoDTO]) -> None:
        id_previo = self._seleccionado.id if self._seleccionado else None
        self._tabla.setRowCount(len(requerimientos))
        fila_previa: int | None = None
        for fila, req in enumerate(requerimientos):
            item_tipo = QTableWidgetItem(req.tipo.value)
            item_tipo.setData(_ROL_REQUERIMIENTO_ID, req.id)
            self._tabla.setItem(fila, 0, item_tipo)
            self._tabla.setItem(fila, 1, QTableWidgetItem(req.titulo))

            item_estado = QTableWidgetItem(req.estado.value)
            item_estado.setForeground(Qt.GlobalColor.white)
            item_estado.setBackground(_qcolor(color_para_estado(req.estado)))
            self._tabla.setItem(fila, 2, item_estado)

            self._tabla.setItem(fila, 3, QTableWidgetItem(str(req.solicitante_id)))
            self._tabla.setItem(fila, 4, QTableWidgetItem(f"{req.fecha_creacion:%Y-%m-%d %H:%M}"))

            if req.severidad is not None:
                item_tipo.setForeground(_qcolor(color_para_severidad(req.severidad)))

            if req.id == id_previo:
                fila_previa = fila

        # Actualizamos `_seleccionado` acá directamente en vez de depender de
        # `itemSelectionChanged`: si la fila reelegida tiene el mismo índice
        # que antes, Qt no considera que la selección "cambió" y esa señal
        # nunca se dispara, dejando `_seleccionado` apuntando al DTO viejo
        # (los DTOs son inmutables: cada transición crea una instancia nueva).
        if fila_previa is not None:
            self._seleccionado = requerimientos[fila_previa]
            self._tabla.selectRow(fila_previa)
        else:
            self._seleccionado = None
        self._actualizar_panel_detalle()


def _qcolor(hexadecimal: str) -> QColor:
    return QColor(hexadecimal)
