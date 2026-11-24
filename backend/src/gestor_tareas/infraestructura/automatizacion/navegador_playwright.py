"""Adaptador del navegador con Playwright (Chromium, ventana visible).

Rellena el formulario "Oportunidades -> Acciones -> Crear" de Digital Desktop y se
para antes de guardar: guardar lo decide el caso de uso tras preguntar en la página.

Playwright es una dependencia opcional (extra "automatizador"): solo se importa al
abrir el navegador, así que el backend normal y la CI no la necesitan. Este módulo
no tiene tests (abriría un navegador real); su frontera se prueba con dobles.
Los ids del DOM llevan un sufijo de ventana variable: se buscan por prefijo.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gestor_tareas.aplicacion.oportunidad.puertos import AutomatizacionFallidaError, CanalEjecucion
from gestor_tareas.dominio.oportunidad.entidades import (
    Asignacion,
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
    DatosFormulario,
)

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Locator, Page, Playwright

TIMEOUT_MS = 20_000
ESPERA_INICIO_SESION_SEGUNDOS = 300  # 5 minutos, como el script original

_JS_TEXTO_EN_PANTALLA = """t => {
    const W=innerWidth, H=innerHeight;
    const els=[...document.querySelectorAll('span,a,div,p,label,li')].filter(e=>{
        if (e.innerText===undefined || e.innerText.trim()!==t) return false;
        const r=e.getBoundingClientRect();
        if (r.width<2 || r.height<2 || r.left<0 || r.top<0 || r.right>W || r.bottom>H) return false;
        const top=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
        return top && (top===e || e.contains(top) || top.contains(e));
    });
    if (!els.length) return null;
    const r=els[0].getBoundingClientRect();
    return {x:r.left+r.width/2, y:r.top+r.height/2};
}"""

_JS_BOTON_ACTIVO = (
    "p => { const b=[...document.querySelectorAll(`[id^='${p}windowBody']`)]"
    ".find(e=>e.offsetParent!==null); return b && !b.disabled; }"
)

_JS_FILA_NOTION = """prj => {
    const el=[...document.querySelectorAll('*')].find(e=>e.childElementCount===0 && e.textContent.trim()===prj);
    let row=el; for(let i=0;i<12&&row;i++){ if(row.getAttribute && row.getAttribute('role')==='row') break;
      if(row.matches && row.matches('.notion-table-view-row,.notion-collection-item')) break; row=row.parentElement; }
    return (row||el.parentElement).innerText;
}"""

_JS_PERFIL_ACTIVO = """n => { const p=document.querySelector('#atd-panel-user'); if(!p) return false;
    const c=p.cloneNode(true); c.querySelectorAll('#accordion-accesos').forEach(e=>e.remove());
    return c.innerText.includes(n); }"""

_JS_FILAS_VISIBLES = "() => [...document.querySelectorAll('tr')].filter(t=>t.offsetParent!==null).map(t=>t.innerText)"

_JS_REVALIDAR_DIALOGO = """p => { const s=[...document.querySelectorAll(`select[id^='${p}windowBody']`)]
    .find(x=>x.closest('.ui-dialog') && x.closest('.ui-dialog').offsetParent!==null);
    if (s && window.jQuery) jQuery(s).trigger('change'); }"""

_JS_OTRA_OPCION = (
    "p => { const s=[...document.querySelectorAll(`select[id^='${p}windowBody']`)]"
    ".find(x=>x.closest('.ui-dialog')&&x.closest('.ui-dialog').offsetParent!==null);"
    " return s ? [...s.options].map(o=>o.text.trim()).filter(t=>t)[0] : null; }"
)

_JS_ESTADO_DIALOGO = """([c,q]) => { const d=[...document.querySelectorAll('.ui-dialog')].find(x=>x.offsetParent!==null);
    const s=d && d.querySelector(`select[id^='${c}windowBody']`), i=d && d.querySelector(`[id^='${q}windowBody']`);
    return {opcion: s ? s.options[s.selectedIndex]?.text.trim() : null, pct: i ? i.value : null}; }"""

# Área MS3 (solo existe tras añadir el tipo de servicio MS3): su contenedor "chosen"
# mide 0 px de ancho, así que si el clic falla se elige en el <select> de debajo.
_JS_ELEGIR_EN_SELECT = """([p,t]) => { for (const s of document.querySelectorAll(`select[id^='${p}windowBody']`)) {
    const o=[...s.options].find(x=>x.text.trim()===t); if (!o) continue;
    s.value=o.value; s.dispatchEvent(new Event('change', {bubbles:true}));
    if (window.jQuery) jQuery(s).trigger('liszt:updated').trigger('chosen:updated');
    return true; } return false; }"""

_JS_ETIQUETAS_CHOSEN = """p => [...document.querySelectorAll(`[id^='${p}windowBody'][id$='_chzn'] .chzn-single span`)]
    .map(e=>e.textContent.trim())"""

_JS_RESUMEN = """ms3 => {
  const v=p=>{const e=[...document.querySelectorAll(`[id^='${p}windowBody']`)].find(x=>x.offsetParent!==null||x.tagName==='SELECT'); if(!e) return '';
    if(e.tagName==='SELECT') return [...e.selectedOptions].map(o=>o.text).join(', '); return e.value;};
  const ck=p=>{const e=document.querySelector(`[id^='${p}windowBody']`); return e&&e.checked?'Sí':'No';};
  const tabla=t=>{const h=[...document.querySelectorAll('.ui-accordion-header')].find(e=>e.offsetParent!==null&&e.innerText.trim()===t);
    if(!h) return []; return [...h.nextElementSibling.querySelectorAll('tbody tr')].map(r=>[...r.querySelectorAll('td')].map(td=>{
      const i=td.querySelector('input'); return (i?i.value:td.innerText).trim();}).filter(Boolean).join(' | ')).filter(Boolean);};
  return [
    'Nombre: '+v('iptNombreG'), 'Observaciones: '+v('observacionesG'),
    'Cliente: '+v('comboClienteChosenG'), 'Grupo: '+v('comboEmpresaGrupoAtSistemasG'), 'Tipos: '+v('comboTipoG'),
    'ENS No: '+ck('radioNoEns'), 'RGPD No: '+ck('radioNoRgpd'),
    'Responsable: '+v('comboComercialG'),
    ...(ms3 ? ['Responsable de Operaciones: '+v('comboRespOperacionesG'), 'Responsable técnico: '+v('comboRespTecnicoG')] : []),
    'Segmentación: '+v('comboSegmentacionG'), ...(ms3 ? ['Área MS3: '+v('comboAreaMs3')] : []),
    'Fase: '+v('comboFaseG'), 'No genera pipeline: '+ck('noGeneraPipeline'),
    'Fecha límite: '+v('fechaLimiteG'), 'Probabilidad: '+v('probabilidadG'), 'Fecha inicio: '+v('fechaEstimadaG'),
    'Tipos de servicio: '+JSON.stringify(tabla('Tipos de servicio a crear')),
    'Líneas de negocio: '+JSON.stringify(tabla('Líneas de Negocio')),
    'Comunidades: '+JSON.stringify(tabla('Comunidades')),
  ].join('\\n');
}"""


class NavegadorPlaywright:
    """Implementa ``NavegadorOportunidades`` con la API síncrona de Playwright.

    Todos sus métodos se llaman desde el mismo hilo de trabajo (la API síncrona
    de Playwright no admite cambiar de hilo).
    """

    def __init__(
        self,
        configuracion: ConfiguracionAltaOportunidad,
        directorio_perfil: Path,
        espera_inicio_sesion_segundos: int = ESPERA_INICIO_SESION_SEGUNDOS,
    ) -> None:
        self._c = configuracion
        self._directorio_perfil = directorio_perfil
        self._espera_inicio_sesion = espera_inicio_sesion_segundos
        self._playwright: Playwright | None = None
        self._contexto: BrowserContext | None = None
        self._pagina: Page | None = None
        self._formulario_ms3 = False  # el resumen añade los campos propios de AXAS MS3

    # --- Ciclo de vida ------------------------------------------------------------
    def abrir(self) -> None:
        from playwright.sync_api import sync_playwright

        self._directorio_perfil.mkdir(parents=True, exist_ok=True)
        # Solo hay un alta a la vez: un bloqueo que quede es de un cierre brusco.
        for bloqueo in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            (self._directorio_perfil / bloqueo).unlink(missing_ok=True)
        self._playwright = sync_playwright().start()
        try:
            self._contexto = self._playwright.chromium.launch_persistent_context(
                str(self._directorio_perfil),
                headless=False,
                viewport={"width": 1400, "height": 900},
                locale="es-ES",
            )
        except Exception as error:
            raise AutomatizacionFallidaError(
                "No se pudo abrir el navegador. Comprueba que WSLg está activo "
                f"(DISPLAY=:0 y /tmp/.X11-unix montado en el servicio): {error}"
            ) from error
        self._contexto.set_default_timeout(TIMEOUT_MS)

    def cerrar(self) -> None:
        try:
            if self._contexto is not None:
                self._contexto.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
            self._contexto = self._playwright = self._pagina = None

    # --- Notion -------------------------------------------------------------------
    def buscar_descripcion(self, prj: str, canal: CanalEjecucion) -> str:
        pagina = self._ctx().new_page()
        pagina.goto(self._c.url_notion)
        self._esperar_inicio_sesion(
            pagina,
            lambda: self._c.titulo_pagina_notion in pagina.title(),
            "Inicia sesión en Notion en la ventana del navegador.",
            canal,
        )
        try:
            pagina.get_by_text(prj, exact=True).first.wait_for(timeout=30_000)
            texto = pagina.evaluate(_JS_FILA_NOTION, prj)
        except Exception as error:
            raise AutomatizacionFallidaError(
                f"No encontré la descripción de {prj} en Notion. Escríbela en el formulario."
            ) from error
        finally:
            pagina.close()
        lineas = [linea.strip() for linea in str(texto).splitlines()]
        lineas = [linea for linea in lineas if linea and linea != prj]
        if not lineas:
            raise AutomatizacionFallidaError(
                f"No encontré la descripción de {prj} en Notion. Escríbela en el formulario."
            )
        canal.informar(f"Descripción encontrada en Notion: {lineas[0]}")
        return lineas[0]

    # --- Digital Desktop ------------------------------------------------------------
    def iniciar_sesion(self, canal: CanalEjecucion) -> None:
        contexto = self._ctx()
        pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
        self._pagina = pagina
        pagina.goto(self._c.url_digital_desktop)
        if "Forbidden" in pagina.title():
            raise AutomatizacionFallidaError(
                "Digital Desktop responde 'Forbidden': conecta la VPN."
            )
        self._esperar_inicio_sesion(
            pagina,
            lambda: (
                pagina.locator("input[type=password]:visible").count() == 0
                and pagina.get_by_text("Accesos permitidos").count() > 0
            ),
            "Inicia sesión en Digital Desktop en la ventana del navegador.",
            canal,
        )
        canal.informar("Sesión iniciada en Digital Desktop")

    def cambiar_perfil(self, perfil: str, canal: CanalEjecucion) -> None:
        """Avatar -> panel de usuario -> "Accesos permitidos" -> enlace del perfil."""
        pagina = self._pag()
        panel = pagina.locator("#atd-panel-user")
        enlace = panel.locator("a[href*='accederConUsuarioDelegado']", has_text=perfil)
        avatar = pagina.locator("#fotoPerfilUsuario")

        def perfil_activo() -> bool:
            return bool(pagina.evaluate(_JS_PERFIL_ACTIVO, perfil))

        avatar.wait_for(timeout=TIMEOUT_MS)
        if perfil_activo():
            canal.informar(f"Perfil activo: {perfil}")
            return
        if not panel.is_visible():
            avatar.click()
            panel.wait_for(state="visible", timeout=TIMEOUT_MS)
            pagina.wait_for_timeout(300)
        if not enlace.first.is_visible():
            panel.locator("h3", has_text="Accesos permitidos").click()
            pagina.wait_for_timeout(700)
        if enlace.count():
            enlace.first.click()
            pagina.wait_for_load_state("networkidle")
            pagina.wait_for_timeout(2500)
        if panel.is_visible():
            avatar.click()
            pagina.wait_for_timeout(300)
        if perfil_activo():
            canal.informar(f"Perfil cambiado a {perfil}")
        else:
            canal.pedir_intervencion(
                f"No pude confirmar el cambio al perfil de {perfil}. Cámbialo tú a mano en "
                "el navegador y pulsa «Continuar»."
            )
            canal.informar(f"Perfil confirmado a mano: {perfil}")

    def existe_oportunidad(self, cliente: str, cliente_busqueda: str, texto: str) -> bool:
        """Abre Oportunidades, busca por el cliente y mira si alguna fila contiene el texto."""
        pagina = self._pag()
        self._clic_texto_en_pantalla("Oportunidades")
        self._vis("buscarwindowBody").wait_for()
        self._chosen("comboClienteChosenB", cliente, buscar=cliente_busqueda)
        self._vis("buscarwindowBody").click()
        pagina.wait_for_timeout(3000)
        filas = pagina.evaluate(_JS_FILAS_VISIBLES)
        return any(texto in fila for fila in filas)

    def rellenar(self, datos: DatosFormulario, canal: CanalEjecucion) -> None:
        """Variante ANES."""
        pagina = self._pag()
        c = self._c
        self._formulario_ms3 = False
        self._abrir_formulario(canal)

        # 1. Datos de la oportunidad
        self._nombre_y_casillas(datos)
        self._chosen("comboClienteChosenG", c.cliente, buscar=c.cliente_busqueda)
        self._chosen("comboEmpresaGrupoAtSistemasG", c.grupo)
        self._chosen("comboTipoG", c.tipo)
        pagina.keyboard.press("Escape")
        canal.informar("Datos de la oportunidad")

        # 2. Personas de contactos
        self._abrir_seccion("Personas de contactos")
        self._chosen("comboComercialG", c.perfil)
        canal.informar("Responsable")

        # 3. Más datos
        self._segmentacion(c.segmentacion, canal)

        # 4. Avance
        self._avance(datos, c.fase, c.probabilidad, canal)

        # 5. Tipos de servicio
        self._tipo_servicio(datos, c.tipo_servicio, canal)

        # 6. Líneas de negocio. 7. Fabricantes: nada. 8. Comunidades
        self._lineas_y_comunidades(c.lineas_negocio, c.comunidades, canal)

    def rellenar_axas_ms3(
        self,
        datos: DatosFormulario,
        configuracion: ConfiguracionAxasMs3,
        canal: CanalEjecucion,
    ) -> None:
        """Variante AXAS MS3: grupo antes que cliente, tres responsables y Área MS3."""
        pagina = self._pag()
        m = configuracion
        self._formulario_ms3 = True
        self._abrir_formulario(canal)

        # 1. Datos de la oportunidad (el grupo corporativo antes que el cliente)
        self._nombre_y_casillas(datos)
        self._chosen("comboEmpresaGrupoAtSistemasG", m.grupo)
        self._chosen("comboClienteChosenG", m.cliente, buscar=m.cliente_busqueda)
        self._chosen("comboTipoG", m.tipo)
        pagina.keyboard.press("Escape")
        canal.informar("Datos de la oportunidad")

        # 2. Personas de contactos (Responsable y Responsable técnico cargan al escribir)
        self._abrir_seccion("Personas de contactos")
        self._chosen("comboComercialG", m.perfil, buscar=m.responsable_busqueda)
        self._chosen("comboRespOperacionesG", m.responsable_operaciones)
        self._chosen(
            "comboRespTecnicoG", m.responsable_tecnico, buscar=m.responsable_tecnico_busqueda
        )
        canal.informar("Responsables")

        # 3. Más datos
        self._segmentacion(m.segmentacion, canal)

        # 4. Avance
        self._avance(datos, m.fase, m.probabilidad, canal)

        # 5. Tipos de servicio y, ya con el tipo MS3 añadido, el Área MS3
        self._tipo_servicio(datos, m.tipo_servicio, canal)
        self._area_ms3(m.area_ms3, canal)

        # 6. Líneas de negocio. 7. Fabricantes: nada. 8. Comunidades
        self._lineas_y_comunidades(m.lineas_negocio, m.comunidades, canal)

    def resumen_formulario(self) -> str:
        return str(self._pag().evaluate(_JS_RESUMEN, self._formulario_ms3))

    def guardar(self) -> bytes:
        pagina = self._pag()
        boton = self._vis("guardarwindowBody")
        boton.scroll_into_view_if_needed()
        boton.click()
        pagina.wait_for_timeout(4000)
        return pagina.screenshot(full_page=True)

    # --- Pasos internos -------------------------------------------------------------
    def _abrir_formulario(self, canal: CanalEjecucion) -> None:
        """Pestaña BÚSQUEDA -> hover en "Acciones" -> "Crear"."""
        pagina = self._pag()
        acciones = pagina.locator("button:visible", has_text=re.compile(r"^\s*Acciones\s*$")).last
        acciones.scroll_into_view_if_needed()
        acciones.hover()
        pagina.wait_for_timeout(600)
        self._vis("nuevaOportunidadwindowBody").click()
        self._vis("iptNombreG").wait_for(timeout=TIMEOUT_MS)
        canal.informar("Formulario de alta abierto")

    def _nombre_y_casillas(self, datos: DatosFormulario) -> None:
        self._escribir("iptNombreG", datos.nombre)
        self._escribir("observacionesG", datos.observaciones)
        self._vis("radioNoEns").check()
        self._vis("radioNoRgpd").check()

    def _segmentacion(self, segmentacion: str, canal: CanalEjecucion) -> None:
        self._abrir_seccion("Más datos")
        self._chosen("comboSegmentacionG", segmentacion)
        canal.informar("Segmentación")

    def _avance(
        self, datos: DatosFormulario, fase: str, probabilidad: str, canal: CanalEjecucion
    ) -> None:
        self._abrir_seccion("Avance")
        self._chosen("comboFaseG", fase)
        casilla = self._vis("noGeneraPipeline")
        if casilla.is_checked():
            casilla.uncheck()
        self._escribir("fechaLimiteG", datos.fecha_limite)
        self._escribir("probabilidadG", probabilidad)
        self._escribir("fechaEstimadaG", datos.fecha_inicio)
        canal.informar("Avance")

    def _lineas_y_comunidades(
        self,
        lineas_negocio: tuple[Asignacion, ...],
        comunidades: tuple[Asignacion, ...],
        canal: CanalEjecucion,
    ) -> None:
        self._abrir_seccion("Líneas de Negocio")
        for linea in lineas_negocio:
            self._anadir_en_dialogo(
                "aniadirLineaNegocio",
                "comboLineaNegG",
                linea.nombre,
                "dedicacionLineaNegocio",
                linea.porcentaje,
                "aceptarPopupLineasNegocio",
                canal,
            )
        self._abrir_seccion("Comunidades")
        for comunidad in comunidades:
            self._anadir_en_dialogo(
                "aniadirComunidad",
                "comboComunidadesG",
                comunidad.nombre,
                "dedicacionComunidad",
                comunidad.porcentaje,
                "aceptarPopupComunidad",
                canal,
            )

    def _area_ms3(self, area: str, canal: CanalEjecucion) -> None:
        """Más datos -> Área MS3 (sin sufijo "G"; aparece tras añadir el tipo MS3)."""
        from playwright.sync_api import Error as ErrorPlaywright

        pagina = self._pag()
        prefijo = "comboAreaMs3"
        self._abrir_seccion("Más datos")
        try:
            pagina.locator(f'select[id^="{prefijo}windowBody"]').first.wait_for(
                state="attached", timeout=TIMEOUT_MS
            )
            # Con ancho 0 el clic normal suele fallar: se prueba rápido y, si no, por JS.
            contenedor = pagina.locator(f'[id^="{prefijo}windowBody"][id$="_chzn"]').first
            if contenedor.is_visible():
                self._chosen(prefijo, area)
        except ErrorPlaywright:
            pass
        if area not in pagina.evaluate(_JS_ETIQUETAS_CHOSEN, prefijo):
            pagina.evaluate(_JS_ELEGIR_EN_SELECT, [prefijo, area])
            pagina.wait_for_timeout(400)
        if area in pagina.evaluate(_JS_ETIQUETAS_CHOSEN, prefijo):
            canal.informar(f"Área MS3: {area}")
            return
        canal.pedir_intervencion(
            f"No pude elegir «{area}» en Área MS3 (sección «Más datos»). Elígelo tú en el "
            "navegador y pulsa «Continuar»."
        )
        canal.informar(f"Área MS3 elegida a mano: {area}")

    def _tipo_servicio(
        self, datos: DatosFormulario, tipo_servicio: str, canal: CanalEjecucion
    ) -> None:
        self._abrir_seccion("Tipos de servicio a crear")
        self._vis("nuevoTipoServicio").click()
        self._vis("duracionTipoServicio").wait_for(timeout=TIMEOUT_MS)
        self._chosen("comboTipoServicioG", tipo_servicio)
        self._escribir("duracionTipoServicio", datos.duracion)
        self._escribir("multi_importeG", datos.importe)
        self._escribir("multi_costeG", datos.coste)
        self._vis("radioNoColaboraDUnit").check()
        self._escribir("duracionTipoServicio", datos.duracion)  # re-dispara la validación
        if not self._boton_activo("aceptarPopupTiposServicios"):
            self._escribir("multi_importeG", datos.importe)
            self._escribir("multi_costeG", datos.coste)
            self._vis("radioNoColaboraDUnit").click()
            self._escribir("duracionTipoServicio", datos.duracion)
        if self._boton_activo("aceptarPopupTiposServicios", 6000):
            self._vis("aceptarPopupTiposServicios").click()
            self._pag().wait_for_timeout(1000)
            canal.informar("Tipo de servicio añadido")
        else:
            canal.pedir_intervencion(
                "El botón «Añadir» del tipo de servicio sigue desactivado. Revísalo en el "
                "navegador, púlsalo tú y luego pulsa «Continuar»."
            )
            canal.informar("Tipo de servicio añadido a mano")

    def _anadir_en_dialogo(
        self,
        boton_abrir: str,
        combo: str,
        opcion: str,
        campo_pct: str,
        pct: str,
        boton_aceptar: str,
        canal: CanalEjecucion,
    ) -> None:
        """Líneas de negocio / comunidades: opción, % de asignación y "Añadir"."""
        pagina = self._pag()
        boton = self._vis(boton_abrir)
        boton.scroll_into_view_if_needed()
        boton.click()
        self._vis(campo_pct).wait_for(timeout=TIMEOUT_MS)

        self._chosen(combo, opcion)

        campo = self._vis(campo_pct)
        campo.click()
        campo.fill("")
        campo.press_sequentially(pct, delay=50)
        campo.dispatch_event("keyup")
        campo.dispatch_event("change")
        campo.press("Tab")
        pagina.wait_for_timeout(400)

        # La ventana valida en el "change" del desplegable: se re-dispara con el % ya escrito.
        pagina.evaluate(_JS_REVALIDAR_DIALOGO, combo)
        pagina.wait_for_timeout(400)

        if not self._boton_activo(boton_aceptar):
            otra = pagina.evaluate(_JS_OTRA_OPCION, combo)
            if otra and otra != opcion:
                self._chosen(combo, otra)
            self._chosen(combo, opcion)

        estado = pagina.evaluate(_JS_ESTADO_DIALOGO, [combo, campo_pct])
        if estado["opcion"] != opcion or str(estado["pct"]).strip() != pct:
            canal.informar(f"Aviso: la ventana tiene {estado} y se esperaba {opcion} / {pct}")
        if not self._boton_activo(boton_aceptar, 6000):
            canal.pedir_intervencion(
                f"El botón «Añadir» ({opcion}) sigue desactivado. Revísalo en el navegador, "
                "púlsalo tú y luego pulsa «Continuar»."
            )
            canal.informar(f"Añadido a mano: {opcion} ({pct} %)")
            return
        self._vis(boton_aceptar).click()
        pagina.wait_for_timeout(1000)
        canal.informar(f"Añadido: {opcion} ({pct} %)")

    def _esperar_inicio_sesion(
        self, pagina: Page, comprobar: Callable[[], bool], mensaje: str, canal: CanalEjecucion
    ) -> None:
        if comprobar():
            return
        canal.mostrar_espera_inicio_sesion(
            f"{mensaje} Se continúa solo en cuanto se detecte que has entrado "
            f"(tienes {self._espera_inicio_sesion // 60} minutos)."
        )
        try:
            for _ in range(self._espera_inicio_sesion):
                pagina.wait_for_timeout(1000)
                if comprobar():
                    return
        finally:
            canal.ocultar_espera()
        raise AutomatizacionFallidaError("No se detectó el inicio de sesión. Abortado.")

    def _clic_texto_en_pantalla(self, texto: str) -> None:
        """Clic en el elemento con ese texto exacto que esté DENTRO de la pantalla
        (en el escritorio hay copias ocultas fuera del viewport)."""
        pagina = self._pag()
        posicion: Any = None
        for _ in range(TIMEOUT_MS // 500):
            posicion = pagina.evaluate(_JS_TEXTO_EN_PANTALLA, texto)
            if posicion:
                break
            pagina.wait_for_timeout(500)
        if not posicion:
            raise AutomatizacionFallidaError(f"No encuentro en pantalla el texto '{texto}'.")
        pagina.mouse.click(posicion["x"], posicion["y"])

    def _vis(self, prefijo_id: str, sufijo: str = "") -> Locator:
        """Elemento visible cuyo id empieza por el prefijo (con "windowBody")."""
        if "windowBody" not in prefijo_id:
            prefijo_id += "windowBody"
        selector = f'[id^="{prefijo_id}"]' + (f'[id$="{sufijo}"]' if sufijo else "")
        return self._pag().locator(f"{selector}:visible").first

    def _chosen(self, prefijo_select: str, opcion: str, buscar: str | None = None) -> None:
        """Elige la opción (texto exacto) en un desplegable "chosen"."""
        pagina = self._pag()
        contenedor = self._vis(prefijo_select, "_chzn")
        contenedor.scroll_into_view_if_needed()
        contenedor.locator(".chzn-single, .chzn-choices").first.click()
        if buscar:
            pagina.keyboard.type(buscar, delay=40)
        elemento = contenedor.locator("li.active-result").filter(
            has_text=re.compile(rf"^\s*{re.escape(opcion)}\s*$")
        )
        elemento.first.wait_for(state="attached", timeout=TIMEOUT_MS)
        elemento.first.scroll_into_view_if_needed()
        elemento.first.click()
        pagina.wait_for_timeout(400)

    def _escribir(self, prefijo_id: str, texto: str) -> None:
        """Escribe como un usuario y sale con Tab (algunos campos validan al perder el foco)."""
        campo = self._vis(prefijo_id)
        campo.scroll_into_view_if_needed()
        campo.click()
        campo.press("Control+A")
        campo.press("Delete")
        campo.press_sequentially(texto, delay=30)
        campo.press("Tab")
        self._pag().wait_for_timeout(300)

    def _abrir_seccion(self, titulo: str) -> None:
        cabecera = self._pag().locator(".ui-accordion-header:visible", has_text=titulo).first
        cabecera.scroll_into_view_if_needed()
        expandida = cabecera.get_attribute("aria-expanded") == "true"
        if not expandida and "ui-state-active" not in (cabecera.get_attribute("class") or ""):
            cabecera.click()
            self._pag().wait_for_timeout(500)

    def _boton_activo(self, prefijo_id: str, timeout: int = 4000) -> bool:
        from playwright.sync_api import TimeoutError as TimeoutPlaywright

        try:
            self._pag().wait_for_function(_JS_BOTON_ACTIVO, arg=prefijo_id, timeout=timeout)
        except TimeoutPlaywright:
            return False
        return True

    def _ctx(self) -> BrowserContext:
        if self._contexto is None:
            raise AutomatizacionFallidaError("El navegador no está abierto.")
        return self._contexto

    def _pag(self) -> Page:
        if self._pagina is None:
            raise AutomatizacionFallidaError("No hay ninguna página de Digital Desktop abierta.")
        return self._pagina


def fabrica_navegador_playwright(
    directorio_perfil: Path,
) -> Callable[[ConfiguracionAltaOportunidad], NavegadorPlaywright]:
    def fabricar(configuracion: ConfiguracionAltaOportunidad) -> NavegadorPlaywright:
        return NavegadorPlaywright(configuracion, directorio_perfil)

    return fabricar
