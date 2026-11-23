"""Despiece de una columna de horno en melamina.

Reglas de armado, fijas para esta primera versión:

- Los laterales van de piso a techo. Piso, techo y entrepaños entran entre ellos.
- El ancho exterior es el hueco más dos espesores.
- Las puertas de abajo son de parche: tapan el canto de los laterales.
- La tapa de arriba abre hacia arriba. No lleva cazoleta de 35 mm.
- Detrás del hueco no hay fondo. El horno a gas necesita aire.
- Ninguna pieza puede pasar de 1220 x 2440 mm, que es la hoja.
- Las medidas son del tablero, antes de pegar el canto.

El cuerpo publicado del Teka HLF 824 G es 798 x 595 x 525 mm (ancho, alto, fondo).
Esa ficha no trae el hueco del mueble. El hueco lo escribe quien usa el programa.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import ceil, hypot, isfinite

HOJA_ANCHO = 1220
HOJA_LARGO = 2440
# El despunte de la hoja se come unos 20 mm por lado. Una pieza pegada al
# límite de 1220 o 2440 no entra en la práctica.
HOLGURA_HOJA = 20
# El zoclo es pino, no melamina: el piso lo humedece.
# 20 mm y 500 mm son el punto de partida. En la sección se cambian.
# El corte del marco ya incluye el espesor.
# Al frente quedan 100 mm para el pie y el marco va atrás.
ESPESOR_PINO = 20
ANCHO_MARCO = 500
HUECO_PIE = 100
# Cada extremo del marco queda 10 mm adentro del mueble.
INSET_EXTREMO = 10
CUERPO_HORNO_ANCHO = 798
CUERPO_HORNO_ALTO = 595
CUERPO_HORNO_FONDO = 525
DENSIDAD_MELAMINA = 650  # kg/m3, para estimar el peso de la tapa


def texto_cm(mm) -> str:
    """Lo que ve la persona. 15 mm es 1.5 cm. 1690 mm es 169 cm."""
    decima = round(float(mm) / 10.0, 1)
    if decima == int(decima):
        return str(int(decima))
    return f"{decima:.1f}"


def cm_a_mm(texto: str) -> str:
    """Lo que escribe la persona, en cm, pasa al cálculo en mm.

    El vacío se queda vacío. Un texto que no es número se deja igual,
    para que el cálculo avise en vez de inventar un cero.
    """
    limpio = str(texto).strip().replace(",", ".")
    if limpio == "":
        return ""
    try:
        valor = float(limpio)
    except (TypeError, ValueError):
        return str(texto).strip()
    if not isfinite(valor):
        return str(texto).strip()
    return str(int(round(valor * 10)))


@dataclass
class Pieza:
    nombre: str
    cantidad: int
    alto: int
    ancho: int
    espesor: int
    material: str
    cantos: str
    canto_mm: int
    lectura: str
    notas: str = ""

    def cabe(self) -> bool:
        return min(self.alto, self.ancho) <= HOJA_ANCHO and max(self.alto, self.ancho) <= HOJA_LARGO

    def justa(self) -> bool:
        return min(self.alto, self.ancho) > HOJA_ANCHO - HOLGURA_HOJA or max(self.alto, self.ancho) > HOJA_LARGO - HOLGURA_HOJA


@dataclass
class Resultado:
    listo: bool
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    piezas: list[Pieza] = field(default_factory=list)
    ancho_exterior: int | None = None
    canto_mm: int = 0
    tableros_15: int = 0
    tableros_fondo: int = 0
    bisagras: int = 0
    pistones: int = 0
    confirmat: int = 0
    peso_tapa_kg: float = 0
    esquema: dict = field(default_factory=dict)


def aplicar_medidas(datos: dict, piezas: list, avisos: list[str]) -> None:
    """Cambia solo alto y ancho de las piezas que el usuario editó.

    El número escrito ya incluye el espesor de las tablas.
    """
    texto = str(datos.get("medidas") or "").strip()
    if not texto:
        return
    try:
        mapa = json.loads(texto)
    except json.JSONDecodeError:
        return
    if not isinstance(mapa, dict):
        return
    for pieza in piezas:
        par = mapa.get(pieza.nombre)
        if not isinstance(par, (list, tuple)) or len(par) != 2:
            continue
        try:
            alto = int(par[0])
            ancho = int(par[1])
        except (TypeError, ValueError):
            continue
        if alto < 1 or ancho < 1 or alto > 4000 or ancho > 4000:
            continue
        pieza.alto = alto
        pieza.ancho = ancho
        if pieza.cantos == "4 lados":
            pieza.canto_mm = 2 * (alto + ancho)
        elif pieza.cantos.startswith("1 largo"):
            pieza.canto_mm = 2 * alto
        elif pieza.cantos == "ninguno":
            pieza.canto_mm = 0
        if not pieza.material.startswith("Pino") and not pieza.cabe():
            avisos.append(
                f"{pieza.nombre} mide {texto_cm(alto)} × {texto_cm(ancho)} cm y pasa de la hoja de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
            )


def centros_refuerzo(largo: int, n: int, espesor: int = 20) -> list[int]:
    """Centro de cada refuerzo, en mm, desde la misma punta del marco.

    Los huecos quedan parejos entre las puntas y entre los refuerzos.
    El milímetro que sobra se reparte en los primeros huecos.
    """
    if n <= 0 or espesor <= 0 or largo <= 2 * espesor:
        return []
    claro = largo - 2 * espesor - n * espesor
    if claro < 0:
        return []
    base, sobra = divmod(claro, n + 1)
    huecos = [base + (1 if i < sobra else 0) for i in range(n + 1)]
    x = espesor
    centros = []
    for hueco in huecos[:-1]:
        x += hueco
        centros.append(x + espesor // 2)
        x += espesor
    return centros


def _marco_sierra(marco, ref, alto_zoclo: int) -> dict:
    """Cortes que sí se sierran. El despiece sigue siendo el rectángulo de afuera."""
    grueso = marco.espesor
    largo = marco.alto
    ancho = marco.ancho
    dentro = ancho - 2 * grueso
    n_ref = ref.cantidad if ref else 0
    alto_ref = ref.ancho if ref else alto_zoclo
    listado = ref.alto if ref else dentro
    # El despiece del refuerzo ya es el hueco. Solo cuenta como editado si lo cambiaron a mano.
    editado = ref is not None and listado != dentro
    corte_ref = listado if editado else dentro
    entra = dentro >= 40 and corte_ref > 0 and largo > 2 * grueso
    centros = centros_refuerzo(largo, n_ref, grueso) if entra else []
    n_sierra = n_ref if centros else 0
    mm = 2 * max(largo, 0)
    if entra:
        mm += 2 * max(dentro, 0)
        if n_sierra and corte_ref > 0:
            mm += n_sierra * corte_ref
    return {
        "largo": largo,
        "ancho": ancho,
        "espesor": grueso,
        "dentro": dentro,
        "n_ref": n_ref,
        "n_sierra": n_sierra,
        "alto_ref": alto_ref,
        "listado": listado,
        "corte_refuerzo": corte_ref,
        "refuerzo_editado": editado,
        "centros": centros,
        "entra": entra,
        "mm": mm,
        "grueso_ref": ref.espesor if ref else grueso,
    }


def cortes_carpintero(piezas, esquema: dict) -> dict | None:
    """Cortes de serrucho de los marcos de pino.

    El despiece da el rectángulo de afuera. Las puntas y los refuerzos
    se cortan para entrar entre las dos tablas largas.
    """
    zoclo = int(esquema.get("zoclo") or 0)
    pie = int(esquema.get("zoclo_pie") or 0)
    por_nombre = {p.nombre: p for p in piezas}
    pares = (
        ("cajón 2 y el esquinero", int(esquema.get("fondo_vuelta") or 0)),
        ("cajón 1", int(esquema.get("fondo_barra") or 0)),
    )
    letras = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    marcos = []
    mm = 0

    def corte(que: str, cant: int, largo_c: int, alto_c: int, grueso_c: int) -> dict:
        nonlocal mm
        mm += cant * max(largo_c, 0)
        return {
            "letra": next(letras),
            "que": que,
            "cant": cant,
            "largo": largo_c,
            "alto": alto_c,
            "grueso": grueso_c,
        }

    for clave, fondo in pares:
        marco = por_nombre.get(f"Zoclo marco {clave}")
        ref = por_nombre.get(f"Zoclo refuerzo {clave}")
        if marco is None:
            continue
        sierra = _marco_sierra(marco, ref, zoclo)
        cortes = [
            corte(
                f"Lado largo del marco del {clave}. Va completo, de punta a punta.",
                2,
                sierra["largo"],
                zoclo,
                sierra["espesor"],
            )
        ]
        if sierra["entra"]:
            cortes.append(
                corte(
                    f"Punta del marco del {clave}. Entra entre los dos lados largos.",
                    2,
                    sierra["dentro"],
                    zoclo,
                    sierra["espesor"],
                )
            )
            if sierra["n_sierra"]:
                if sierra["refuerzo_editado"] and sierra["corte_refuerzo"] != sierra["dentro"]:
                    que = (
                        f"Refuerzo del marco del {clave}. "
                        f"En el despiece dice {texto_cm(sierra['listado'])} cm. "
                        f"Entre los lados largos caben {texto_cm(sierra['dentro'])} cm."
                    )
                else:
                    que = f"Refuerzo del marco del {clave}. Entra entre los dos lados largos."
                cortes.append(
                    corte(
                        que,
                        sierra["n_sierra"],
                        sierra["corte_refuerzo"],
                        sierra["alto_ref"],
                        sierra["grueso_ref"],
                    )
                )
        marcos.append(
            {
                "clave": clave,
                "largo": sierra["largo"],
                "ancho": sierra["ancho"],
                "espesor": sierra["espesor"],
                "alto": zoclo,
                "dentro": sierra["dentro"],
                "n_ref": sierra["n_sierra"],
                "n_pedido": sierra["n_ref"],
                "alto_ref": sierra["alto_ref"],
                "corte_refuerzo": sierra["corte_refuerzo"],
                "refuerzo_editado": sierra["refuerzo_editado"],
                "centros": sierra["centros"],
                "diagonal": int(round(hypot(sierra["largo"], sierra["ancho"]))),
                "pasa": pie + sierra["ancho"] - fondo,
                "fondo": fondo,
                "entra": sierra["entra"],
                "cortes": cortes,
            }
        )
    if not marcos:
        return None
    return {
        "zoclo": zoclo,
        "pie": pie,
        "mm": mm,
        "compra": ceil(mm * 1.1 / 1000) if mm else 0,
        "pino_mm": mm,
        "marcos": marcos,
        "fondo_vuelta": int(esquema.get("fondo_vuelta") or 0),
        "fondo_barra": int(esquema.get("fondo_barra") or 0),
        "proyeccion": int(esquema.get("proyeccion") or 0),
        "ancho_tarja": int(esquema.get("ancho_tarja") or 0),
    }


def _ajustar_refuerzos(datos: dict, piezas: list) -> None:
    """Si cambia el ancho del marco, el refuerzo vuelve a restar los dos espesores.

    Una medida escrita a mano en esa fila se queda.
    """
    mapa = {}
    texto = str(datos.get("medidas") or "").strip()
    if texto:
        try:
            cargado = json.loads(texto)
        except json.JSONDecodeError:
            cargado = None
        if isinstance(cargado, dict):
            mapa = cargado
    por_nombre = {p.nombre: p for p in piezas}
    for pieza in piezas:
        if not pieza.material.startswith("Pino") or "marco" not in pieza.nombre.lower():
            continue
        nombre = pieza.nombre.replace("marco", "refuerzo", 1)
        ref = por_nombre.get(nombre)
        if ref is None or nombre in mapa:
            continue
        dentro = pieza.ancho - 2 * pieza.espesor
        if dentro > 0:
            ref.alto = dentro


def metros_pino(piezas: list) -> int:
    """Largo de serrucho del pino, el mismo que suma el PDF.

    El despiece sigue dando el rectángulo de afuera. Aquí se cuentan
    las dos tablas largas y, si el marco se arma, las dos puntas y los
    refuerzos ya recortados para entrar entre ellas.
    """
    por_nombre = {p.nombre: p for p in piezas}
    total = 0
    for pieza in piezas:
        if not pieza.material.startswith("Pino") or "marco" not in pieza.nombre.lower():
            continue
        ref = por_nombre.get(pieza.nombre.replace("marco", "refuerzo", 1))
        total += _marco_sierra(pieza, ref, 0)["mm"]
    return total


def _entero(valor, nombre: str, errores: list[str]) -> int | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto == "":
        return None
    try:
        numero = int(texto)
    except (TypeError, ValueError):
        errores.append(f"{nombre} tiene que ser un número.")
        return None
    return numero


def _pedir(valor, nombre: str, errores: list[str]) -> int | None:
    numero = _entero(valor, nombre, errores)
    if numero is None:
        if not any(nombre in e for e in errores):
            errores.append(f"Falta {nombre}.")
        return None
    if numero <= 0:
        errores.append(f"{nombre} tiene que ser mayor que cero.")
        return None
    return numero


def _repartir(total: int, partes: int) -> list[int]:
    base = total // partes
    sobra = total - base * partes
    return [base + (1 if i < sobra else 0) for i in range(partes)]


def _bisagras_de_puerta(alto: int) -> int:
    if alto > 1600:
        return 4
    if alto > 900:
        return 3
    return 2


def calcular_columna(datos: dict) -> Resultado:
    errores: list[str] = []
    avisos: list[str] = []

    alto = _pedir(datos.get("alto"), "el alto de la columna", errores)
    fondo = _pedir(datos.get("fondo"), "el fondo del cuerpo", errores)
    espesor = _pedir(datos.get("espesor"), "el espesor", errores)
    fondo_esp = _pedir(datos.get("fondo_esp"), "el espesor del fondo", errores)
    zoclo = _pedir(datos.get("zoclo"), "el alto del zoclo", errores)
    holgura = _entero(datos.get("holgura"), "la holgura", errores)
    if holgura is None and not any("holgura" in e for e in errores):
        errores.append("Falta la holgura.")
    elif holgura is not None and holgura < 0:
        errores.append("La holgura no puede ser negativa.")
    hueco_ancho = _entero(datos.get("hueco_ancho"), "el ancho del hueco", errores)
    hueco_alto = _entero(datos.get("hueco_alto"), "el alto del hueco", errores)
    hueco_desde = _entero(datos.get("hueco_desde"), "la altura donde empieza el hueco", errores)
    hueco_fondo = _entero(datos.get("hueco_fondo"), "el fondo que pide el horno", errores)
    for valor, nombre in (
        (hueco_ancho, "El ancho del hueco"),
        (hueco_alto, "El alto del hueco"),
        (hueco_desde, "La altura donde empieza el hueco"),
        (hueco_fondo, "El fondo que pide el horno"),
    ):
        if valor is not None and valor <= 0:
            errores.append(f"{nombre} tiene que ser mayor que cero.")

    color = str(datos.get("color") or "Blanco").strip() or "Blanco"
    modo = str(datos.get("fondo_modo") or "clavado").strip()
    if modo not in ("clavado", "ranura"):
        errores.append("El fondo tiene que ir clavado o en ranura.")
        modo = "clavado"

    faltan_hueco = [hueco_ancho, hueco_alto, hueco_desde].count(None)
    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos)
    if faltan_hueco:
        return Resultado(
            listo=False,
            errores=[],
            avisos=["Escribe el ancho del hueco, el alto del hueco y a qué altura del piso empieza."],
        )

    assert None not in (alto, fondo, espesor, fondo_esp, zoclo, holgura, hueco_ancho, hueco_alto, hueco_desde)

    if espesor < 9 or espesor > 30:
        errores.append("El espesor del cuerpo queda fuera de 0.9 a 3 cm.")
    if fondo_esp < 2 or fondo_esp > 12:
        errores.append("El fondo tiene que quedar entre 0.2 y 1.2 cm.")
    if zoclo >= alto:
        errores.append("El zoclo es más alto que la columna.")
    if hueco_ancho > HOJA_ANCHO:
        errores.append(f"El hueco de {texto_cm(hueco_ancho)} cm no cabe en el ancho de la hoja ({texto_cm(HOJA_ANCHO)} cm).")
    if fondo > HOJA_ANCHO:
        errores.append(f"El fondo de {texto_cm(fondo)} cm no cabe en el ancho de la hoja ({texto_cm(HOJA_ANCHO)} cm).")
    if alto > HOJA_LARGO:
        errores.append(
            f"El lateral de {texto_cm(alto)} cm no cabe en el largo de la hoja ({texto_cm(HOJA_LARGO)} cm). Hay que partir la columna."
        )

    ancho_exterior = hueco_ancho + 2 * espesor
    claro_abajo = hueco_desde - zoclo - 2 * espesor
    claro_arriba = alto - hueco_desde - hueco_alto - 2 * espesor
    if claro_abajo <= 0:
        errores.append("El hueco empieza tan abajo que el piso del horno choca con el piso del mueble.")
    if claro_arriba <= 0:
        errores.append("El hueco termina tan arriba que el techo del horno choca con el techo del mueble.")

    alto_puerta = hueco_desde - zoclo - 2 * holgura
    alto_tapa = alto - (hueco_desde + hueco_alto) - 2 * holgura
    ancho_puertas = ancho_exterior - 3 * holgura
    ancho_tapa = ancho_exterior - 2 * holgura
    if alto_puerta < 120:
        errores.append(f"Las puertas de abajo quedan de {texto_cm(alto_puerta)} cm. Sube el hueco o baja el zoclo.")
    if alto_tapa < 120:
        errores.append(f"La tapa de arriba queda de {texto_cm(alto_tapa)} cm. Baja el hueco o sube la columna.")
    if ancho_puertas < 160:
        errores.append("El módulo queda tan angosto que las dos puertas no salen.")
    if ancho_tapa < 80:
        errores.append("La tapa de arriba queda demasiado angosta.")

    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos, ancho_exterior=ancho_exterior)

    anchos_puerta = _repartir(ancho_puertas, 2)
    prof_panel = fondo if modo == "clavado" else fondo - 10
    if prof_panel < 100:
        errores.append("En ranura, el fondo del cuerpo no alcanza para el entrepaño.")
        return Resultado(listo=False, errores=errores, avisos=avisos, ancho_exterior=ancho_exterior)

    material = f"Melamina {color} {texto_cm(espesor)} cm"
    material_fondo = f"Fondo {texto_cm(fondo_esp)} cm"
    piezas: list[Pieza] = []

    def agregar(nombre, cantidad, alto_p, ancho_p, esp, mat, cantos, canto_mm, lectura, notas=""):
        piezas.append(
            Pieza(
                nombre,
                cantidad,
                int(alto_p),
                int(ancho_p),
                esp,
                mat,
                cantos,
                int(canto_mm),
                lectura,
                notas,
            )
        )

    agregar(
        "Lateral",
        2,
        alto,
        fondo,
        espesor,
        material,
        "1 largo, el frente",
        2 * alto,
        "alto de piso a techo × fondo",
        "El canto va en el frente.",
    )
    horizontales = (
        ("Piso inferior", "Cara de arriba a la altura del zoclo."),
        ("Piso del horno", "Aquí apoya el horno. Tablero completo, sin recorte."),
        ("Techo del horno", "Cierra el hueco por arriba."),
        ("Techo del módulo", "Cierra la columna."),
    )
    for nombre, nota in horizontales:
        agregar(
            nombre,
            1,
            hueco_ancho,
            prof_panel,
            espesor,
            material,
            "1 largo, el frente",
            hueco_ancho,
            "luz entre laterales × fondo",
            nota,
        )

    agregar(
        "Zoclo frontal",
        1,
        hueco_ancho,
        zoclo,
        espesor,
        material,
        "canto superior",
        hueco_ancho,
        "largo entre laterales × alto del zoclo",
        "Va entre los laterales, recargado atrás unos 7 cm para el pie.",
    )

    notas_puerta = (
        f"Cazoleta de 35 mm. {_bisagras_de_puerta(alto_puerta)} por puerta, "
        "a 10 cm de cada extremo."
    )
    if anchos_puerta[0] == anchos_puerta[1]:
        agregar(
            "Puerta inferior",
            2,
            alto_puerta,
            anchos_puerta[0],
            espesor,
            material,
            "4 lados",
            2 * 2 * (alto_puerta + anchos_puerta[0]),
            "alto × ancho",
            notas_puerta,
        )
    else:
        agregar(
            "Puerta inferior izquierda",
            1,
            alto_puerta,
            anchos_puerta[0],
            espesor,
            material,
            "4 lados",
            2 * (alto_puerta + anchos_puerta[0]),
            "alto × ancho",
            notas_puerta + " Lleva el 0.1 cm que sobra del reparto.",
        )
        agregar(
            "Puerta inferior derecha",
            1,
            alto_puerta,
            anchos_puerta[1],
            espesor,
            material,
            "4 lados",
            2 * (alto_puerta + anchos_puerta[1]),
            "alto × ancho",
            notas_puerta,
        )

    peso_tapa = (alto_tapa * ancho_tapa * espesor) / 1_000_000_000 * DENSIDAD_MELAMINA
    agregar(
        "Tapa superior",
        1,
        alto_tapa,
        ancho_tapa,
        espesor,
        material,
        "4 lados",
        2 * (alto_tapa + ancho_tapa),
        "alto × ancho",
        "Abre hacia arriba. No barrenar cazoleta. Lleva bisagra de alzada y pistón.",
    )

    def fondo_de(claro: int) -> tuple[int, int]:
        if modo == "clavado":
            return hueco_ancho - 4, claro - 4
        return hueco_ancho + 8, claro + 8

    nota_fondo = (
        "Clavado por detrás, 0.2 cm holgado por lado."
        if modo == "clavado"
        else "Entra 0.4 cm en ranura por cada lado."
    )
    fondo_inf = fondo_de(claro_abajo)
    fondo_sup = fondo_de(claro_arriba)
    agregar(
        "Fondo del cajón inferior",
        1,
        fondo_inf[1],
        fondo_inf[0],
        fondo_esp,
        material_fondo,
        "ninguno",
        0,
        "alto del claro × ancho",
        nota_fondo,
    )
    agregar(
        "Fondo del gabinete superior",
        1,
        fondo_sup[1],
        fondo_sup[0],
        fondo_esp,
        material_fondo,
        "ninguno",
        0,
        "alto del claro × ancho",
        nota_fondo,
    )

    for pieza in piezas:
        if not pieza.cabe():
            errores.append(
                f"{pieza.nombre} mide {texto_cm(pieza.alto)} × {texto_cm(pieza.ancho)} cm y no cabe en una hoja de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
            )
        elif pieza.justa():
            avisos.append(
                f"{pieza.nombre} queda muy pegada al borde de la hoja. La maderería necesita despuntar."
            )

    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos, ancho_exterior=ancho_exterior)

    if hueco_ancho >= CUERPO_HORNO_ANCHO:
        avisos.append(
            f"El hueco ({texto_cm(hueco_ancho)} cm) es igual o más ancho que el horno ({texto_cm(CUERPO_HORNO_ANCHO)} cm). "
            "El marco podría no tapar el canto. La hoja de instalación manda esta medida."
        )
    else:
        avisos.append(
            f"El hueco ({texto_cm(hueco_ancho)} cm) es más angosto que el ancho publicado del horno ({texto_cm(CUERPO_HORNO_ANCHO)} cm). "
            "Eso deja que el marco tape el canto, si la hoja de instalación lo pide así."
        )
    if hueco_alto < CUERPO_HORNO_ALTO:
        avisos.append(
            f"El hueco ({texto_cm(hueco_alto)} cm) es más bajo que el alto publicado del horno ({texto_cm(CUERPO_HORNO_ALTO)} cm)."
        )
    if hueco_fondo is not None and fondo < hueco_fondo:
        errores.append(
            f"El fondo del mueble ({texto_cm(fondo)} cm) es menor que el fondo que escribiste para el horno ({texto_cm(hueco_fondo)} cm)."
        )
    elif fondo < CUERPO_HORNO_FONDO + 30:
        avisos.append(
            f"El cuerpo del horno mide {texto_cm(CUERPO_HORNO_FONDO)} cm de fondo. "
            f"Con un mueble de {texto_cm(fondo)} cm queda poco aire atrás."
        )

    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos, ancho_exterior=ancho_exterior, piezas=piezas)

    avisos.append("Detrás del hueco no va fondo. Un horno a gas necesita ese aire.")
    avisos.append("Pide dos calados de 10 × 6 cm: uno abajo del hueco y otro arriba. El lugar exacto lo marca la hoja del horno. La rejilla de ferretería sigue siendo la de 100 × 60 mm.")
    avisos.append("La conexión de gas y la corriente no salen en este despiece. Las hace un instalador.")
    avisos.append("Estas medidas son del tablero. El canto suma aparte, cerca de 0.1 cm por lado.")
    avisos.append("La cantidad de tableros es un estimado por área. La maderería acomoda el corte en la hoja.")

    aplicar_medidas(datos, piezas, avisos)
    area_cuerpo = 0
    area_fondo = 0
    canto = 0
    for pieza in piezas:
        area = pieza.alto * pieza.ancho * pieza.cantidad
        canto += pieza.canto_mm
        if pieza.espesor == fondo_esp and pieza.material.startswith("Fondo"):
            area_fondo += area
        else:
            area_cuerpo += area

    hoja = HOJA_ANCHO * HOJA_LARGO
    tableros_15 = ceil(area_cuerpo * 1.15 / hoja)
    tableros_fondo = ceil(area_fondo * 1.15 / hoja)
    bisagras = 2 * _bisagras_de_puerta(alto_puerta)
    # 4 entrepaños × 2 extremos × 3 tornillos, más 2 del zoclo por lado.
    confirmat = 4 * 2 * 3 + 4

    esquema = {
        "alto": alto,
        "ancho": ancho_exterior,
        "zoclo": zoclo,
        "espesor": espesor,
        "hueco_desde": hueco_desde,
        "hueco_alto": hueco_alto,
        "hueco_ancho": hueco_ancho,
        "alto_puerta": alto_puerta,
        "alto_tapa": alto_tapa,
        "puertas": anchos_puerta,
        "claro_abajo": claro_abajo,
        "claro_arriba": claro_arriba,
    }

    return Resultado(
        listo=True,
        errores=[],
        avisos=avisos,
        piezas=piezas,
        ancho_exterior=ancho_exterior,
        canto_mm=canto,
        tableros_15=tableros_15,
        tableros_fondo=tableros_fondo,
        bisagras=bisagras,
        pistones=1,
        confirmat=confirmat,
        peso_tapa_kg=round(peso_tapa, 1),
        esquema=esquema,
    )


def calcular_bajos(datos: dict) -> Resultado:
    """Barra de cocina en L: zoclo, tarja, vuelta y esquina ciega.

    La barra es la medida de afuera, del piso a la cara de arriba. El zoclo va
    dentro de esa altura. Son dos marcos de pino que se tocan y forman la L:
    uno bajo el cajón 2 y el esquinero, el otro bajo el cajón 1. Van atrás,
    con el hueco del pie al frente, y miden 10 cm de alto. Encima se sientan los cajones.
    La puerta de la vuelta es el tablero. La esquina se arma aparte: un solo
    tablero del largo de la vuelta no cabe en la hoja.
    En cocina, baño y clóset no se ofrece quitar el zoclo.
    """

    errores: list[str] = []
    avisos: list[str] = []
    tipo = str(datos.get("tipo") or "cocina").strip().lower()
    if tipo == "baño":
        tipo = "bano"
    if tipo not in ("cocina", "bano", "closet"):
        return Resultado(listo=False, errores=["Elige cocina, baño o clóset."])
    distribucion = str(datos.get("distribucion") or "l").strip().lower()
    if distribucion not in ("recta", "l", "u"):
        return Resultado(listo=False, errores=["Elige una distribución recta, en L o en U."])
    if distribucion in ("recta", "u"):
        nombre = "recta" if distribucion == "recta" else "en U"
        def medida_espacio(campo: str) -> int:
            try:
                valor = int(datos.get(campo) or 0)
            except (TypeError, ValueError, OverflowError):
                return 0
            return valor
        return Resultado(
            listo=False,
            avisos=[
                f"La distribución {nombre} quedó registrada, pero este bloque todavía no genera cortes automáticos "
                "para ese plano. Usa distribución en L para obtener el despiece completo."
            ],
            esquema={
                "distribucion": distribucion,
                "largo_pared_a": medida_espacio("largo_pared_a"),
                "largo_pared_b": medida_espacio("largo_pared_b"),
                "largo_pared_c": medida_espacio("largo_pared_c"),
            },
        )
    if distribucion == "l":
        def medir_tramo(campo: str) -> int | None:
            texto = str(datos.get(campo) or "").strip()
            if not texto:
                return None
            try:
                valor = int(texto)
            except (TypeError, ValueError, OverflowError):
                return None
            return valor if valor >= 400 else valor * 10

        tramo_a = medir_tramo("largo_pared_a")
        tramo_b = medir_tramo("largo_pared_b")
        if tramo_a is not None and tramo_a > 0:
            datos["largo_barra"] = str(tramo_a)
        if tramo_b is not None and tramo_b > 0:
            datos["largo_vuelta"] = str(tramo_b)
    if tipo != "cocina":
        return Resultado(
            listo=False,
            avisos=[
                "El baño y el clóset todavía no están dibujados. "
                "En esos muebles el zoclo también va, y no se quita."
            ],
        )

    largo_barra = _pedir(datos.get("largo_barra"), "el largo de la barra", errores)
    fondo_barra = _pedir(datos.get("fondo_barra"), "el fondo de la tarja", errores)
    largo_vuelta = _pedir(datos.get("largo_vuelta"), "el largo de la vuelta", errores)
    fondo_vuelta = _pedir(datos.get("fondo_vuelta"), "el grueso de la vuelta", errores)
    ancho_tarja = _pedir(datos.get("ancho_tarja"), "el frente de la tarja", errores)
    puerta_vuelta = _pedir(datos.get("puerta_vuelta"), "la puerta de la vuelta", errores)
    alto_barra = _pedir(datos.get("alto_barra"), "el alto de la barra", errores)
    espesor = _pedir(datos.get("espesor"), "el espesor", errores)
    fondo_esp = _pedir(datos.get("fondo_esp"), "el espesor del fondo", errores)
    zoclo = _pedir(datos.get("zoclo"), "el alto del zoclo", errores)
    holgura = _entero(datos.get("holgura"), "la holgura", errores)
    if holgura is None and not any("holgura" in e for e in errores):
        errores.append("Falta la holgura.")
    elif holgura is not None and holgura < 0:
        errores.append("La holgura no puede ser negativa.")
    profundidad_esquina = _entero(datos.get("profundidad_esquina"), "la profundidad del esquinero", errores)
    if profundidad_esquina is None:
        profundidad_esquina = HUECO_PIE * 9
    elif profundidad_esquina <= 0:
        errores.append("La profundidad del esquinero tiene que ser mayor que cero.")
    entre = _entero(datos.get("entre_desde"), "la altura del entrepaño", errores)
    if entre is not None and entre <= 0:
        errores.append("La altura del entrepaño tiene que ser mayor que cero.")

    color = str(datos.get("color") or "Blanco").strip() or "Blanco"
    modo = str(datos.get("fondo_modo") or "clavado").strip()
    if modo not in ("clavado", "ranura"):
        errores.append("El fondo tiene que ir clavado o en ranura.")
        modo = "clavado"
    medidas = (
        largo_barra,
        fondo_barra,
        largo_vuelta,
        fondo_vuelta,
        ancho_tarja,
        puerta_vuelta,
        alto_barra,
        espesor,
        fondo_esp,
        zoclo,
        holgura,
    )
    if errores or None in medidas:
        return Resultado(listo=False, errores=errores)

    if espesor < 9 or espesor > 30:
        errores.append("El espesor del cuerpo queda fuera de 0.9 a 3 cm.")
    if fondo_esp < 2 or fondo_esp > 12:
        errores.append("El fondo tiene que quedar entre 0.2 y 1.2 cm.")
    if fondo_barra > HOJA_ANCHO or fondo_vuelta > HOJA_ANCHO:
        errores.append(f"Un fondo no cabe en el ancho de la hoja ({texto_cm(HOJA_ANCHO)} cm).")
    if ancho_tarja > HOJA_ANCHO or puerta_vuelta > HOJA_ANCHO:
        errores.append(f"Un frente no cabe en el ancho de la hoja ({texto_cm(HOJA_ANCHO)} cm).")
    if alto_barra > HOJA_LARGO:
        errores.append(f"El lateral de {texto_cm(alto_barra)} cm no cabe en el largo de la hoja ({texto_cm(HOJA_LARGO)} cm).")
    if zoclo >= alto_barra:
        errores.append("El zoclo es más alto que la barra.")
    elif espesor is not None and zoclo <= espesor:
        errores.append("El zoclo tiene que ser más alto que el espesor del tablero.")

    alto_puerta = alto_barra - zoclo - 2 * holgura
    if alto_puerta < 120:
        errores.append("Las puertas quedan demasiado bajas. La barra no alcanza con el zoclo y la holgura.")
    if puerta_vuelta < 120:
        errores.append("La puerta de la vuelta queda demasiado angosta.")

    ancho_puertas = ancho_tarja - 3 * holgura
    if ancho_puertas < 160:
        errores.append("El frente de la tarja no alcanza para dos puertas.")
    proyeccion = largo_vuelta - fondo_barra
    if proyeccion <= 2 * espesor:
        errores.append("La vuelta tiene que salir más allá del fondo de la tarja.")
    elif puerta_vuelta + 2 * holgura > proyeccion:
        errores.append(
            f"La puerta de {texto_cm(puerta_vuelta)} cm no cabe en el tramo de {texto_cm(proyeccion)} cm que sale la vuelta."
        )
    if ancho_tarja <= 2 * espesor or fondo_vuelta <= 2 * espesor:
        errores.append("Un módulo queda sin luz entre los laterales.")
    if errores:
        return Resultado(listo=False, errores=errores)

    anchos_tarja = _repartir(ancho_puertas, 2)
    fijo = proyeccion - puerta_vuelta - 2 * holgura
    piso_top = zoclo + espesor
    techo_bottom = alto_barra - espesor
    if techo_bottom <= piso_top:
        return Resultado(
            listo=False,
            errores=["Entre el zoclo y el techo no queda hueco para el entrepaño."],
        )
    if entre is None:
        centro = (piso_top + techo_bottom) // 2
        shelf_bottom = centro - espesor // 2
        shelf_top = shelf_bottom + espesor
        nota_entre = "A la mitad del hueco. Tablero completo, sin recorte."
    else:
        shelf_top = entre
        shelf_bottom = shelf_top - espesor
        nota_entre = f"Cara de arriba a {texto_cm(shelf_top)} cm del piso. Tablero completo, sin recorte."
        if shelf_bottom < piso_top or shelf_top > techo_bottom:
            return Resultado(
                listo=False,
                errores=["El entrepaño choca con el piso o con el techo del mueble."],
            )

    material = f"Melamina {color} {texto_cm(espesor)} cm"
    material_fondo = f"Fondo {texto_cm(fondo_esp)} cm"
    piezas: list[Pieza] = []
    bisagras = 0
    nota_techo = "Cierra el módulo. La cubierta va a la altura de la barra y no se corta aquí."
    nota_piso = "Va al fondo del cajón, sentado sobre el marco del zoclo."
    alto_cajon = alto_barra - zoclo

    def agregar(nombre, cantidad, alto_p, ancho_p, esp, mat, cantos, canto_mm, lectura, notas=""):
        piezas.append(
            Pieza(
                nombre,
                cantidad,
                int(alto_p),
                int(ancho_p),
                esp,
                mat,
                cantos,
                int(canto_mm),
                lectura,
                notas,
            )
        )

    def zoclo_marco(etiqueta: str, marco_l: int, marco_f: int, refuerzos: int, grueso: int) -> None:
        if marco_l < 40 or marco_f < 40:
            errores.append(f"El marco del {etiqueta} queda demasiado chico.")
            return
        # El marco se anota de afuera. El refuerzo ya entra entre las dos tablas largas.
        largo_ref = marco_f - 2 * grueso
        if largo_ref < 40:
            errores.append(
                f"Entre los lados del marco del {etiqueta} quedan {texto_cm(largo_ref)} cm. Necesitan al menos 4 cm."
            )
            return
        if refuerzos > 0 and not centros_refuerzo(marco_l, refuerzos, grueso):
            errores.append(f"En el marco del {etiqueta} no caben {refuerzos} refuerzos.")
            return
        pino = f"Pino {texto_cm(grueso)} cm"
        agregar(
            f"Zoclo marco {etiqueta}",
            1,
            marco_l,
            marco_f,
            grueso,
            pino,
            "ninguno",
            0,
            f"corte × ancho, espesor ya contado, alto {texto_cm(zoclo)} cm",
            f"Bajo el {etiqueta}. Va atrás, con {texto_cm(pie)} cm libres al frente para el pie.",
        )
        if refuerzos <= 0:
            return
        agregar(
            f"Zoclo refuerzo {etiqueta}",
            refuerzos,
            largo_ref,
            zoclo,
            grueso,
            pino,
            "ninguno",
            0,
            "largo entre los lados × alto del zoclo",
            f"Ya trae restados los dos espesores del marco. {texto_cm(marco_f)} - {texto_cm(grueso)} - {texto_cm(grueso)} = {texto_cm(largo_ref)}.",
        )

    def caja(clave: str, ancho_ext: int, fondo: int, puertas: list[int], nota_lateral: str):
        nonlocal bisagras
        interior = ancho_ext - 2 * espesor
        prof = fondo if modo == "clavado" else fondo - 10
        if prof < 100 or interior < 80:
            errores.append(f"El módulo {clave} no deja tablero útil.")
            return
        agregar(
            f"Lateral {clave}",
            2,
            alto_cajon,
            fondo,
            espesor,
            material,
            "1 largo, el frente" if puertas else "ninguno",
            (2 * alto_cajon) if puertas else 0,
            "alto del cajón × fondo",
            nota_lateral,
        )
        piezas_horizontales = [
            (f"Piso {clave}", nota_piso),
            (f"Entrepaño {clave}", nota_entre),
        ]
        if clave != "tarja":
            piezas_horizontales.append((f"Techo {clave}", nota_techo))
        for nombre, nota in piezas_horizontales:
            agregar(
                nombre,
                1,
                interior,
                prof,
                espesor,
                material,
                "1 largo, el frente",
                interior,
                "luz entre laterales × fondo",
                nota,
            )
        claro = techo_bottom - piso_top
        if modo == "clavado":
            fondo_ancho, fondo_alto = interior - 4, claro - 4
            nota_fondo = "Clavado por detrás, 0.2 cm holgado por lado."
        else:
            fondo_ancho, fondo_alto = interior + 8, claro + 8
            nota_fondo = "Entra 0.4 cm en ranura por cada lado."
        agregar(
            f"Fondo {clave}",
            1,
            fondo_alto,
            fondo_ancho,
            fondo_esp,
            material_fondo,
            "ninguno",
            0,
            "alto del claro × ancho",
            nota_fondo,
        )
        for indice, ancho_pta in enumerate(puertas):
            lado = ""
            if len(puertas) == 2:
                lado = " izquierda" if indice == 0 else " derecha"
            n_bis = _bisagras_de_puerta(alto_puerta)
            bisagras += n_bis
            nota = f"Cazoleta de 35 mm. {n_bis} por puerta, a 10 cm de cada extremo."
            if len(puertas) == 2 and anchos_tarja[0] != anchos_tarja[1] and indice == 0:
                nota += " Lleva el 0.1 cm que sobra del reparto."
            if clave == "vuelta":
                nota += " Va en la cara interior de la vuelta, pegada a la esquina."
            agregar(
                f"Puerta {clave}{lado}",
                1,
                alto_puerta,
                ancho_pta,
                espesor,
                material,
                "4 lados",
                2 * (alto_puerta + ancho_pta),
                "alto × ancho",
                nota,
            )

    # El largo vacío sale del plano. Cada extremo queda 10 mm adentro del mueble.
    pie_texto = str(datos.get("zoclo_pie") or "").strip()
    if pie_texto == "":
        pie = HUECO_PIE
    else:
        pie = _entero(pie_texto, "El hueco del pie", errores)
        if pie is None:
            pie = HUECO_PIE
        elif pie < 0:
            errores.append("El hueco del pie no puede ser negativo.")
            pie = 0

    def opcion(clave: str, defecto: int, nombre: str, minimo: int, maximo: int, en_cm: bool = False) -> int | None:
        if clave not in datos or datos.get(clave) is None or str(datos.get(clave)).strip() == "":
            return defecto
        numero = _entero(datos.get(clave), nombre, errores)
        if numero is None:
            return None
        if numero < minimo or numero > maximo:
            if en_cm:
                errores.append(f"{nombre} tiene que quedar entre {texto_cm(minimo)} y {texto_cm(maximo)} cm.")
            else:
                errores.append(f"{nombre} tiene que quedar entre {minimo} y {maximo}.")
            return None
        return numero

    def largo_opcion(clave: str, formula: int, nombre: str) -> tuple[int | None, bool]:
        if clave not in datos or datos.get(clave) is None or str(datos.get(clave)).strip() == "":
            return formula, True
        numero = _entero(datos.get(clave), nombre, errores)
        if numero is None:
            return None, False
        if numero < 40 or numero > 4000:
            errores.append(f"{nombre} tiene que quedar entre 4 y 400 cm. Si lo borras, sale del plano.")
            return None, False
        return numero, False

    pino = opcion("pino_esp", ESPESOR_PINO, "El espesor del pino", 8, 40, en_cm=True)

    def ancho_marco_interior(clave: str, fondo: int, nombre: str) -> int | None:
        """El marco sale del fondo interior menos el hueco libre del pie."""
        defecto = fondo - pie
        if clave not in datos or datos.get(clave) is None or str(datos.get(clave)).strip() == "":
            return defecto
        numero = _entero(datos.get(clave), nombre, errores)
        if numero is None:
            return None
        if numero < 40 or numero > 2000:
            errores.append(f"{nombre} tiene que quedar entre {texto_cm(40)} y {texto_cm(2000)} cm.")
            return None
        return numero

    ancho_2 = ancho_marco_interior("marco_a_2", fondo_vuelta, "El ancho del marco del cajón 2")
    ancho_1 = ancho_marco_interior("marco_a_1", fondo_barra, "El ancho del marco del cajón 1")
    n2 = opcion("ref_2", 4, "Los refuerzos del cajón 2", 0, 30)
    n1 = opcion("ref_1", 4, "Los refuerzos del cajón 1", 0, 30)
    if None not in (pino, ancho_2, ancho_1, n2, n1):
        largo_leg, auto_2 = largo_opcion(
            "marco_l_2",
            proyeccion + pie + ancho_2 - INSET_EXTREMO,
            "El largo del marco del cajón 2",
        )
        largo_arm, auto_1 = largo_opcion(
            "marco_l_1",
            ancho_tarja + pie - INSET_EXTREMO,
            "El largo del marco del cajón 1",
        )
    else:
        largo_leg, auto_2 = None, True
        largo_arm, auto_1 = None, True
    if None not in (pino, ancho_2, ancho_1, n2, n1, largo_leg, largo_arm):
        zoclo_marco("cajón 2 y el esquinero", largo_leg, ancho_2, n2, pino)
        zoclo_marco("cajón 1", largo_arm, ancho_1, n1, pino)
    caja(
        "tarja",
        ancho_tarja,
        fondo_barra,
        anchos_tarja,
        "Del zoclo a la cara de arriba. Se sienta sobre el zoclo del cajón 1. El canto va en el frente.",
    )
    caja(
        "vuelta",
        proyeccion,
        fondo_vuelta,
        [puerta_vuelta],
        "Módulo separado del esquinero. Del zoclo a la cara de arriba. Se une a él por un solo lateral común y comparte zoclo.",
    )
    if fijo >= 40:
        agregar(
            "Fijo vuelta",
            1,
            alto_puerta,
            fijo,
            espesor,
            material,
            "4 lados",
            2 * (alto_puerta + fijo),
            "alto × ancho",
            "Tapa lo que la puerta de la vuelta no alcanza, en la punta. No lleva bisagra.",
        )
    caja(
        "esquina",
        fondo_vuelta,
        fondo_barra,
        [],
        "Módulo separado ciego. Se sienta sobre el mismo zoclo del cajón 2 y se une al lateral de este sin repetir tableros. Sus caras dan contra la tarja y contra la vuelta.",
    )
    if errores:
        return Resultado(listo=False, errores=errores)

    for pieza in piezas:
        if pieza.material.startswith("Pino"):
            continue
        if not pieza.cabe():
            errores.append(
                f"{pieza.nombre} mide {texto_cm(pieza.alto)} × {texto_cm(pieza.ancho)} cm y no cabe en una hoja de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
            )
        elif pieza.justa():
            avisos.append(f"{pieza.nombre} queda muy pegada al borde de la hoja. La maderería necesita despuntar.")
    suma = fondo_vuelta + ancho_tarja
    if errores:
        return Resultado(listo=False, errores=errores, ancho_exterior=suma, piezas=piezas)

    if not 80 <= zoclo <= 150:
        avisos.append(
            "En cocina, baño y clóset el zoclo suele ir de 10 a 15 cm. "
            "Con 10 cm cabe el pie y pasa el trapeador."
        )
    if fondo_barra < 550 or fondo_vuelta < 550:
        avisos.append("Un fondo quedó debajo de 55 cm. En un bajo se usan más seguido 55 a 60 cm.")
    avisos.append(
        f"Cajón 1: cuerpo de 70 cm de alto sobre el zoclo de {texto_cm(zoclo)} cm. "
        "No lleva tablero superior; la cubierta va aparte. Dos puertas con melamina de 1.5 cm."
    )
    avisos.append(
        "Cajón 2 y esquinero: son dos módulos separados que se conectan entre sí. "
        "Comparten el marco de pino, el borde de unión y la altura de 70 cm. "
        "No se repite el lateral común; el esquinero queda ciego y el cajón 2 lleva una puerta."
    )
    if alto_puerta != 720:
        aviso_puerta = (
            f"Las puertas quedan de {texto_cm(alto_puerta)} cm de alto. "
            f"Salen de la barra ({texto_cm(alto_barra)} cm) menos el zoclo ({texto_cm(zoclo)} cm) y el aire de arriba y de abajo."
        )
        if alto_puerta == 694:
            aviso_puerta += " Una puerta de 72 cm no entra."
        avisos.append(aviso_puerta)
    if largo_barra != suma:
        avisos.append(
            f"El largo escrito de la barra es {texto_cm(largo_barra)} cm. "
            f"El grueso de la vuelta ({texto_cm(fondo_vuelta)} cm) más el frente de la tarja ({texto_cm(ancho_tarja)} cm) "
            f"suman {texto_cm(suma)} cm. El despiece usa esa suma."
        )
    if 0 < fijo < 40:
        avisos.append(
            f"El hueco que deja la puerta en la vuelta es de {texto_cm(fijo)} cm, menor de 4 cm, y no se corta un fijo."
        )
    avisos.append(
        f"La esquina es un cajón ciego, sin puerta. "
        f"Va aparte porque la vuelta de {texto_cm(largo_vuelta)} cm no entra en una sola pieza de la hoja de {texto_cm(HOJA_ANCHO)} cm. "
        f"La puerta de {texto_cm(puerta_vuelta)} cm queda en el tramo de {texto_cm(proyeccion)} cm, pegada a la esquina. "
        "Por esa puerta se entra a la esquina si después se abre la unión."
    )
    avisos.append("El entrepaño va completo en los tres módulos. Si el sifón lo cruza, el recorte se hace al armar.")
    avisos.append(
        f"La cubierta del dibujo queda a {texto_cm(alto_barra)} cm del piso y no se manda a cortar. La tarja dibujada tampoco."
    )
    avisos.append("Estas medidas son del tablero. El canto suma aparte, cerca de 0.1 cm por lado.")
    avisos.append("La cantidad de tableros es un estimado por área. La maderería acomoda el corte en la hoja.")

    aplicar_medidas(datos, piezas, avisos)
    _ajustar_refuerzos(datos, piezas)

    def corte(nombre: str) -> str:
        for pieza in piezas:
            if pieza.nombre == nombre:
                return f"{texto_cm(pieza.alto)} × {texto_cm(pieza.ancho)}"
        return ""

    marco_vuelta = next((p for p in piezas if p.nombre == "Zoclo marco cajón 2 y el esquinero"), None)
    marco_tarja = next((p for p in piezas if p.nombre == "Zoclo marco cajón 1"), None)
    if marco_vuelta and pie + marco_vuelta.ancho > fondo_vuelta:
        avisos.append(
            f"En el cajón 2 el hueco del pie ({texto_cm(pie)} cm) más el ancho del marco ({texto_cm(marco_vuelta.ancho)} cm) "
            f"pasan el fondo de {texto_cm(fondo_vuelta)} cm. Baja uno de los dos para que el marco cierre adentro."
        )
    if marco_tarja and pie + marco_tarja.ancho > fondo_barra:
        avisos.append(
            f"En el cajón 1 el hueco del pie ({texto_cm(pie)} cm) más el ancho del marco ({texto_cm(marco_tarja.ancho)} cm) "
            f"pasan el fondo de {texto_cm(fondo_barra)} cm. Baja uno de los dos para que el marco cierre adentro."
        )
    avisos.append(
        "La medida del marco ya cuenta el espesor de las tablas. "
        f"El del cajón 2 y el esquinero mide {corte('Zoclo marco cajón 2 y el esquinero')} cm. "
        f"El del cajón 1 mide {corte('Zoclo marco cajón 1')} cm. "
        f"Quedan {texto_cm(pie)} cm libres al frente y el marco va atrás. "
        f"El alto del zoclo es {texto_cm(zoclo)} cm. "
        "El PDF del botón trae el corte de cada tabla. "
        "Lo que entra entre los lados largos es el ancho de afuera menos dos espesores."
    )
    area_cuerpo = 0
    area_fondo = 0
    canto = 0
    for pieza in piezas:
        area = pieza.alto * pieza.ancho * pieza.cantidad
        canto += pieza.canto_mm
        if pieza.material.startswith("Pino"):
            continue
        if pieza.espesor == fondo_esp and pieza.material.startswith("Fondo"):
            area_fondo += area
        else:
            area_cuerpo += area
    hoja = HOJA_ANCHO * HOJA_LARGO
    # Cada cajón: 3 tableros × 2 extremos × 3 tornillos.
    # El marco de pino no usa confirmat.
    return Resultado(
        listo=True,
        avisos=avisos,
        piezas=piezas,
        ancho_exterior=suma,
        canto_mm=canto,
        tableros_15=ceil(area_cuerpo * 1.15 / hoja),
        tableros_fondo=ceil(area_fondo * 1.15 / hoja) if area_fondo else 0,
        bisagras=bisagras,
        pistones=0,
        confirmat=3 * (3 * 2 * 3),
        esquema={
            "distribucion": distribucion,
            "alto": alto_barra,
            "alto_cajon": alto_cajon,
            "modulos_conectados": ["cajón 2", "esquinero"],
            "ancho": suma,
            "fondo_total": largo_vuelta,
            "fondo_barra": fondo_barra,
            "fondo_vuelta": fondo_vuelta,
            "ancho_tarja": ancho_tarja,
            "proyeccion": proyeccion,
            "zoclo": zoclo,
            "espesor": espesor,
            "alto_puerta": alto_puerta,
            "puertas_tarja": anchos_tarja,
            "puerta_vuelta": puerta_vuelta,
            "fijo": fijo if fijo >= 40 else 0,
            "shelf_top": shelf_top,
            "interior_tarja": ancho_tarja - 2 * espesor,
            "interior_vuelta": proyeccion - 2 * espesor,
            "interior_esquina": fondo_vuelta - 2 * espesor,
            "largo_barra": largo_barra,
            "profundidad_esquina": profundidad_esquina,
            "zoclo_pie": pie,
            "pino_esp": pino,
            "marco_a_2": ancho_2,
            "marco_a_2_auto": "marco_a_2" not in datos or datos.get("marco_a_2") is None or str(datos.get("marco_a_2")).strip() == "",
            "marco_l_2": largo_leg,
            "marco_l_2_auto": auto_2,
            "ref_2": n2,
            "marco_a_1": ancho_1,
            "marco_a_1_auto": "marco_a_1" not in datos or datos.get("marco_a_1") is None or str(datos.get("marco_a_1")).strip() == "",
            "marco_l_1": largo_arm,
            "marco_l_1_auto": auto_1,
            "ref_1": n1,
            "pino_mm": metros_pino(piezas),
        },
    )


# LG LDP6810SS. El cuerpo es el aparato. 85.4 cm es la altura con las
# patas retraídas. El corte del gabinete es 86.4 cm. Este plano usa 87.
# Nada de esto es una tabla de melamina.
LAVA_ANCHO = 603
LAVA_ALTO = 846
LAVA_ALTO_LIBRE = 854
LAVA_CORTE_ALTO = 864
LAVA_HUECO_ALTO = 870
LAVA_FONDO = 625
LAVA_HUECO_ANCHO = 610
LAVA_HUECO_FONDO = 610
LAVA_ALTO_MUEBLE = 2440
LAVA_HOLGURA_LADO = 2
# Hileras para mover los entrepaños. 32 mm es el paso de sistema 32.
# 37 mm es el retranqueo: la hilera de enfrente sale del canto frontal
# del lateral, y la de atrás sale del canto de atrás del entrepaño.
# 2 mm es la holgura del ancho del entrepaño dentro del hueco.
PASO_ENTRE = 32
HOLGURA_ENTRE = 32
INSET_ENTRE = 37
HOLGURA_ANCHO_ENTRE = 2
# En la vista de lado del manual hay otra profundidad, de 676 a 681 mm.
# No es la apertura del gabinete. La ficha dice 625 mm y el dibujo del
# hueco pide al menos 610 mm.
LAVA_FONDO_LADO = (676, 681)
# Hoyo del manual en el lateral izquierdo, visto de frente.
# 6.3 cm es la sierra de 2 1/2". El centro queda a 6" del piso y a 4" de atrás.
LAVA_HOYO = 63
LAVA_HOYO_PISO = 152
LAVA_HOYO_ATRAS = 102
SIERRA_HOJA = 4


def acomodar_melamina(alto: int, fondo: int, tablas: list[tuple[str, int, int]]) -> list[list[dict]]:
    """Dos laterales a lo largo de la hoja. Lo demás cae en la tira de al lado.

    Cada pieza trae nombre, x, y, w, h en milímetros. y corre por los 244 cm.
    Entre corte y corte queda la sierra. El primer número de la tabla es el
    lado del frente.
    """
    if alto > HOJA_LARGO or fondo > HOJA_ANCHO or alto <= 0 or fondo <= 0:
        return []
    hojas: list[list[dict]] = []
    libres: list[dict] = []

    def colocar(nombre: str, frente: int, fondo_pieza: int, hoja: int, x: int, y: int, w: int, h: int) -> None:
        lado = "lado" if h == frente else "abajo"
        hojas[hoja].append({
            "nombre": nombre,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "frente": lado,
        })

    def poner(nombre: str, a: int, b: int) -> bool:
        for k, libre in enumerate(libres):
            wa, la = libre["w"], libre["h"]
            opciones = []
            if a <= wa and b <= la:
                opciones.append((a, b))
            if b <= wa and a <= la and (b, a) not in opciones:
                opciones.append((b, a))
            if not opciones:
                continue
            pw, pl = min(opciones, key=lambda lado: lado[1])
            libres.pop(k)
            x, y = libre["x"], libre["y"]
            colocar(nombre, a, b, libre["hoja"], x, y, pw, pl)
            if la - pl - SIERRA_HOJA > 0:
                libres.insert(0, {
                    "hoja": libre["hoja"],
                    "x": x,
                    "y": y + pl + SIERRA_HOJA,
                    "w": wa,
                    "h": la - pl - SIERRA_HOJA,
                })
            if wa - pw - SIERRA_HOJA > 0:
                libres.insert(0, {
                    "hoja": libre["hoja"],
                    "x": x + pw + SIERRA_HOJA,
                    "y": y,
                    "w": wa - pw - SIERRA_HOJA,
                    "h": pl,
                })
            return True
        return False

    if fondo * 2 + SIERRA_HOJA <= HOJA_ANCHO:
        hojas.append([])
        colocar("Lateral", alto, fondo, 0, 0, 0, fondo, alto)
        colocar("Lateral", alto, fondo, 0, fondo + SIERRA_HOJA, 0, fondo, alto)
        inicio_tira = 2 * fondo + 2 * SIERRA_HOJA
        sobra_w = HOJA_ANCHO - inicio_tira
        if sobra_w > 0:
            libres.append({
                "hoja": 0,
                "x": inicio_tira,
                "y": 0,
                "w": sobra_w,
                "h": HOJA_LARGO,
            })
        sobra_l = HOJA_LARGO - alto - SIERRA_HOJA
        if sobra_l > 0:
            libres.append({"hoja": 0, "x": 0, "y": alto + SIERRA_HOJA, "w": HOJA_ANCHO, "h": sobra_l})
    else:
        hojas.append([])
        hojas.append([])
        colocar("Lateral", alto, fondo, 0, 0, 0, fondo, alto)
        colocar("Lateral", alto, fondo, 1, 0, 0, fondo, alto)
        sobra_w = HOJA_ANCHO - fondo - SIERRA_HOJA
        sobra_l = HOJA_LARGO - alto - SIERRA_HOJA
        for indice in (0, 1):
            if sobra_w > 0:
                libres.append({
                    "hoja": indice,
                    "x": fondo + SIERRA_HOJA,
                    "y": 0,
                    "w": sobra_w,
                    "h": HOJA_LARGO,
                })
            if sobra_l > 0:
                libres.append({
                    "hoja": indice,
                    "x": 0,
                    "y": alto + SIERRA_HOJA,
                    "w": fondo,
                    "h": sobra_l,
                })
    for nombre, a, b in tablas:
        if poner(nombre, a, b):
            continue
        hojas.append([])
        indice = len(hojas) - 1
        libres.append({"hoja": indice, "x": 0, "y": 0, "w": HOJA_ANCHO, "h": HOJA_LARGO})
        poner(nombre, a, b)
    return hojas


def cortes_lavavajillas(piezas: list) -> list[list[dict]]:
    """El acomodo real de la melamina de este cajón. El respaldo no entra."""
    lateral = next((p for p in piezas if p.nombre.startswith("Lateral")), None)
    if lateral is None:
        return []
    tablas = []
    for pieza in piezas:
        if pieza.espesor != lateral.espesor or pieza.nombre.startswith("Lateral"):
            continue
        tablas.extend((pieza.nombre, pieza.alto, pieza.ancho) for _ in range(pieza.cantidad))
    return acomodar_melamina(lateral.alto, lateral.ancho, tablas)


def _hojas_lava(alto: int, fondo: int, tablas: list[tuple[int, int]]) -> int:
    """Hojas de 122 × 244 cm para dos laterales y las tablas de arriba."""
    nombradas = [("Tabla", a, b) for a, b in tablas]
    return len(acomodar_melamina(alto, fondo, nombradas))


def _hileras_entre(y_piso: int, y_techo: int, espesor: int) -> list[int]:
    primera = y_piso + HOLGURA_ENTRE
    ultima = y_techo - espesor - HOLGURA_ENTRE
    if ultima < primera:
        return []
    return list(range(primera, ultima + 1, PASO_ENTRE))


def _repartir_hileras(n: int, hileras: list[int]) -> list[int]:
    if n <= 0 or not hileras:
        return []
    ultimo = len(hileras) - 1
    usados: list[int] = []
    for i in range(n):
        indice = int(((i + 1) * ultimo) / (n + 1) + 0.5)
        while indice in usados and indice < ultimo:
            indice += 1
        while indice in usados and indice > 0:
            indice -= 1
        usados.append(indice)
    return sorted(hileras[i] for i in usados)


def _hilera_cercana(mm: int, hileras: list[int]) -> int:
    return min(hileras, key=lambda hilera: (abs(hilera - mm), hilera))


def _pedir_posiciones(texto: str, n: int, hileras: list[int], errores: list[str]) -> list[int]:
    partes = [parte.strip() for parte in texto.replace("\n", ";").split(";")]
    partes = [parte for parte in partes if parte]
    if len(partes) != n:
        errores.append(
            f"Hay {n} entrepaños y {len(partes)} alturas. "
            "Escribe una altura por entrepaño, separadas con punto y coma."
        )
        return []
    alturas: list[int] = []
    for parte in partes:
        mm = cm_a_mm(parte)
        if not mm.isdigit():
            errores.append(f"La posición {parte} tiene que ir en centímetros.")
            return []
        alturas.append(_hilera_cercana(int(mm), hileras))
    if len(set(alturas)) != n:
        errores.append("Dos entrepaños caen en la misma hilera. Sepáralos al menos 3.2 cm.")
        return []
    return sorted(alturas)


def calcular_lavavajillas(datos: dict) -> Resultado:
    """Columna del lavavajillas, con repisas arriba.

    Los laterales van del piso hasta el alto del mueble. El aparato se
    sienta en el piso: no hay zoclo ni piso. El techo del hueco es el
    piso de las repisas y no le quita alto al hueco. Detrás del aparato
    no hay fondo.
    """
    errores: list[str] = []
    avisos: list[str] = []
    alto = _pedir(datos.get("alto"), "el alto del mueble", errores)
    hueco_ancho = _pedir(datos.get("hueco_ancho"), "el ancho del hueco", errores)
    hueco_alto = _pedir(datos.get("hueco_alto"), "el alto del hueco", errores)
    fondo = _pedir(datos.get("fondo"), "el fondo del cajón", errores)
    espesor = _pedir(datos.get("espesor"), "el espesor", errores)
    fondo_esp = _pedir(datos.get("fondo_esp"), "el espesor del respaldo", errores)
    repisas = _entero(datos.get("repisas"), "las repisas", errores)
    if repisas is None and not any("repisas" in e for e in errores):
        repisas = 2
    pedido_repisa = str(datos.get("repisa_fondo") or "").strip()
    fondo_repisa = _pedir(pedido_repisa, "el fondo de la repisa", errores) if pedido_repisa else None
    if errores or None in (alto, hueco_ancho, hueco_alto, fondo, espesor, fondo_esp, repisas):
        return Resultado(listo=False, errores=errores, avisos=avisos)

    if espesor < 9 or espesor > 30:
        errores.append("El espesor del cuerpo queda fuera de 0.9 a 3 cm.")
    if fondo_esp < 2 or fondo_esp > 12:
        errores.append("El respaldo tiene que quedar entre 0.2 y 1.2 cm.")
    if repisas < 0 or repisas > 6:
        errores.append("Las repisas tienen que quedar entre 0 y 6.")
    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos)

    tira = HOJA_ANCHO - fondo - SIERRA_HOJA
    if fondo_repisa is None:
        fondo_repisa = min(fondo, tira) if tira > 0 else fondo
    if fondo_repisa <= 0:
        errores.append("El fondo de la repisa tiene que ser mayor que cero.")
    elif fondo_repisa > fondo:
        errores.append("La repisa no puede ser más honda que el cajón.")
    claro = alto - hueco_alto - 2 * espesor
    if claro <= 0:
        errores.append("El alto del mueble tiene que pasar el hueco del lavavajillas y los dos techos.")
    elif claro < repisas * espesor + (repisas + 1) * 80:
        errores.append("No caben tantos entrepaños en el alto que queda arriba del lavavajillas.")
    y_piso = (hueco_alto or 0) + (espesor or 0)
    y_techo = (alto or 0) - (espesor or 0)
    hileras = _hileras_entre(y_piso, y_techo, espesor or 0) if not errores else []
    posiciones: list[int] = []
    if repisas and not errores:
        if len(hileras) < repisas:
            errores.append("No hay hileras suficientes para mover los entrepaños.")
        else:
            pedido = str(datos.get("posiciones") or "").strip()
            posiciones = (
                _pedir_posiciones(pedido, repisas, hileras, errores)
                if pedido
                else _repartir_hileras(repisas, hileras)
            )
    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos)

    ancho_exterior = hueco_ancho + 2 * espesor
    color = str(datos.get("color") or "Blanco Frosty").strip() or "Blanco Frosty"
    material = f"Melamina {color} {texto_cm(espesor)} cm"
    material_fondo = f"Fondo {texto_cm(fondo_esp)} cm"
    piezas = [
        Pieza(
            "Lateral lavavajillas",
            2,
            alto,
            fondo,
            espesor,
            material,
            "1 largo, el frente",
            2 * alto,
            "alto del piso al techo × fondo del cajón",
            "Sigue de una pieza hasta los entrepaños. En la cara de adentro, arriba del lavavajillas, "
            f"dos hileras de barrenos de 5 mm cada {texto_cm(PASO_ENTRE)} cm. "
            f"La de enfrente queda a {texto_cm(INSET_ENTRE)} cm del canto frontal del lateral. "
            f"La de atrás queda a {texto_cm(INSET_ENTRE)} cm del canto de atrás del entrepaño, medido sobre el fondo de la tabla. "
            "Ahí entran los soportes para mover los entrepaños. El lavavajillas se sienta en el piso: este mueble no lleva zoclo.",
        ),
        Pieza(
            "Techo lavavajillas",
            1,
            hueco_ancho,
            fondo_repisa,
            espesor,
            material,
            "1 largo, el frente",
            hueco_ancho,
            "ancho del hueco × fondo del entrepaño",
            f"Entre los laterales. La cara de abajo queda a {texto_cm(hueco_alto)} cm del piso. Cierra el hueco. "
            "El canto frontal va sellado. Si el aparato no trae barrera de vapor, pon cinta de aluminio en la cara de abajo. "
            f"El aparato se fija a este techo con escuadras. Usa tornillos que no atraviesen los {texto_cm(espesor)} cm.",
        ),
        Pieza(
            "Techo entrepaños",
            1,
            hueco_ancho,
            fondo_repisa,
            espesor,
            material,
            "1 largo, el frente",
            hueco_ancho,
            "ancho del hueco × fondo del entrepaño",
            f"Entre los laterales, hasta los {texto_cm(alto)} cm. Va fijo. Ancla este techo al muro con 2 escuadras. Los entrepaños de abajo no van fijos.",
        ),
    ]
    ancho_entre = hueco_ancho - HOLGURA_ANCHO_ENTRE
    if repisas:
        if len(posiciones) == 1:
            donde = f"a {texto_cm(posiciones[0])} cm del piso"
        else:
            donde = "a " + " y a ".join(f"{texto_cm(p)} cm" for p in posiciones) + " del piso"
        piezas.append(
            Pieza(
                "Entrepaño",
                repisas,
                ancho_entre,
                fondo_repisa,
                espesor,
                material,
                "1 largo, el frente",
                repisas * ancho_entre,
                "ancho del entrepaño × fondo del entrepaño",
                "No va con confirmat. "
                f"Mide {texto_cm(ancho_entre)} cm de ancho, {texto_cm(hueco_ancho - ancho_entre)} cm menos que el hueco, para que suba y baje sin trabarse. "
                "Se apoya en cuatro soportes para poder cambiarlo de hilera. "
                f"De partida, la cara de abajo queda {donde}. Van a ras del frente.",
            )
        )
    respaldo_alto = claro - 4
    respaldo_ancho = hueco_ancho - 4
    if respaldo_alto > 40 and respaldo_ancho > 40:
        piezas.append(
            Pieza(
                "Respaldo entrepaños",
                1,
                respaldo_alto,
                respaldo_ancho,
                fondo_esp,
                material_fondo,
                "ninguno",
                0,
                "alto del claro de los entrepaños × ancho del hueco",
                "Solo detrás de los entrepaños. Detrás del lavavajillas no va fondo: por ahí pasan agua, desagüe y corriente.",
            )
        )
    for pieza in piezas:
        if not pieza.cabe():
            errores.append(
                f"{pieza.nombre} mide {texto_cm(pieza.alto)} × {texto_cm(pieza.ancho)} cm y no cabe en una hoja de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
            )
    if errores:
        return Resultado(listo=False, errores=errores, avisos=avisos, ancho_exterior=ancho_exterior, piezas=piezas)

    sobra_lados = hueco_ancho - LAVA_ANCHO
    entra = (
        hueco_ancho >= LAVA_HUECO_ANCHO
        and sobra_lados >= LAVA_HOLGURA_LADO * 2
        and hueco_alto >= LAVA_CORTE_ALTO
        and fondo >= LAVA_HUECO_FONDO
    )
    if entra:
        avisos.append(
            "El lavavajillas entra. El corte pide al menos "
            f"{texto_cm(LAVA_HUECO_ANCHO)} × {texto_cm(LAVA_CORTE_ALTO)} × {texto_cm(LAVA_HUECO_FONDO)} cm. "
            f"Este hueco mide {texto_cm(hueco_ancho)} × {texto_cm(hueco_alto)} × {texto_cm(fondo)} cm. "
            f"Con las patas retraídas el aparato mide {texto_cm(LAVA_ANCHO)} × {texto_cm(LAVA_FONDO)} × {texto_cm(LAVA_ALTO_LIBRE)} cm."
        )
    else:
        avisos.append(
            "El corte pide al menos "
            f"{texto_cm(LAVA_HUECO_ANCHO)} cm de ancho, {texto_cm(LAVA_CORTE_ALTO)} cm de alto "
            f"y {texto_cm(LAVA_HUECO_FONDO)} cm de fondo. Con estas medidas el aparato no entra como pide el dibujo."
        )
    if sobra_lados < LAVA_HOLGURA_LADO * 2:
        avisos.append(
            f"El aparato mide {texto_cm(LAVA_ANCHO)} cm de ancho. "
            f"En este hueco de {texto_cm(hueco_ancho)} cm quedan {texto_cm(sobra_lados)} cm entre los dos laterales. "
            "El manual pide al menos 0.2 cm por lado para que la puerta abra."
        )
    else:
        avisos.append(
            f"El aparato mide {texto_cm(LAVA_ANCHO)} cm de ancho y el hueco {texto_cm(hueco_ancho)} cm. "
            f"Quedan {texto_cm(sobra_lados)} cm entre los dos laterales, más de 0.2 cm por lado."
        )
    if hueco_alto < LAVA_CORTE_ALTO:
        avisos.append(
            f"El corte pide al menos {texto_cm(LAVA_CORTE_ALTO)} cm de alto, del piso al bajo del techo. "
            f"Este hueco tiene {texto_cm(hueco_alto)} cm. "
            f"{texto_cm(LAVA_ALTO_LIBRE)} cm es el aparato con las patas retraídas, sin holgura para nivelarlo."
        )
    else:
        avisos.append(
            f"El alto libre es {texto_cm(hueco_alto)} cm, del piso al bajo del techo. "
            f"El corte pide al menos {texto_cm(LAVA_CORTE_ALTO)} cm. "
            f"Con las patas retraídas el aparato mide {texto_cm(LAVA_ALTO_LIBRE)} cm y el cuerpo llega a {texto_cm(LAVA_ALTO)} cm."
        )
    if fondo < LAVA_HUECO_FONDO:
        avisos.append(
            f"El manual pide al menos {texto_cm(LAVA_HUECO_FONDO)} cm de fondo de gabinete. Este cajón tiene {texto_cm(fondo)} cm."
        )
    if fondo < LAVA_FONDO:
        avisos.append(
            f"El aparato mide {texto_cm(LAVA_FONDO)} cm de fondo. "
            f"Con este cajón de {texto_cm(fondo)} cm, la puerta sale {texto_cm(LAVA_FONDO - fondo)} cm al frente."
        )
    avisos.append(
        "En la vista de lado el dibujo marca de "
        f"{texto_cm(LAVA_FONDO_LADO[0])} a {texto_cm(LAVA_FONDO_LADO[1])} cm. "
        "Esa medida no es la apertura del gabinete. La apertura sigue siendo "
        f"{texto_cm(LAVA_HUECO_FONDO)} cm de fondo."
    )
    if alto == HOJA_LARGO:
        avisos.append(
            f"El lateral mide {texto_cm(alto)} cm, el largo completo de la hoja. No sobra largo para despuntar."
        )
    elif alto < HOJA_LARGO:
        avisos.append(
            f"El alto de {texto_cm(alto)} cm entra en la hoja de {texto_cm(HOJA_LARGO)} cm. Sobran {texto_cm(HOJA_LARGO - alto)} cm."
        )
    tablas = [
        (pieza.alto, pieza.ancho)
        for pieza in piezas
        if pieza.espesor == espesor and not pieza.nombre.startswith("Lateral")
        for _ in range(pieza.cantidad)
    ]
    hojas = _hojas_lava(alto, fondo, tablas)
    if hojas == 2 and fondo_repisa < fondo:
        avisos.append(
            f"Cada lateral de {texto_cm(alto)} × {texto_cm(fondo)} cm va en una hoja. "
            f"Al lado queda una tira de {texto_cm(tira)} cm, ya descontando la sierra. "
            f"Los entrepaños y los techos van a {texto_cm(fondo_repisa)} cm de fondo para caber en esa tira. "
            f"El corte sale en 2 hojas de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
        )
    elif hojas:
        avisos.append(
            f"Con estas medidas el acomodo pide {hojas} hojas de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm."
        )
    avisos.append(
        "No lleva zoclo ni piso ni soporte abajo. El aparato se sienta en el piso. "
        "Esos 11.5 cm de abajo son del propio lavavajillas. "
        "El manual solo habla de quitar el soporte del gabinete en una instalación al ras. Los entrepaños empiezan encima de su techo."
    )
    avisos.append(
        "El hoyo de 6.3 cm va en el lateral izquierdo, visto de frente. "
        f"El centro queda a {texto_cm(LAVA_HOYO_PISO)} cm del piso y a {texto_cm(LAVA_HOYO_ATRAS)} cm de atrás. "
        "No va en el corte. Se barrena al armar, con la plantilla y con el aparato en su lugar. Es uno solo. "
        "Por ese centro pasan la manguera, el desagüe y el cable, con las conexiones puestas."
    )
    if repisas:
        avisos.append(
            f"Los entrepaños se cortan a {texto_cm(ancho_entre)} cm de ancho. "
            f"El hueco mide {texto_cm(hueco_ancho)} cm. "
            f"Esos {texto_cm(hueco_ancho - ancho_entre)} cm dejan que la tabla suba y baje."
        )
    avisos.append(
        "Ancla el techo de arriba al muro con 2 escuadras. "
        "El mueble no tiene piso ni zoclo, y el respaldo de 0.3 cm no lo sostiene."
    )
    avisos.append(
        "Sella el canto frontal del techo del hueco. "
        "Si el aparato no trae barrera de vapor, pon cinta de aluminio en la cara de abajo de ese techo."
    )
    avisos.append(
        f"El aparato se fija con escuadras a ese techo. Usa tornillos que no atraviesen los {texto_cm(espesor)} cm."
    )
    if tira > 0:
        avisos.append(
            f"Confirma que la hoja llegue completa, de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm, sin orillas ya recortadas. "
            f"En el ancho no sobra: {texto_cm(fondo)} + {texto_cm(SIERRA_HOJA)} + {texto_cm(tira)} = {texto_cm(fondo + SIERRA_HOJA + tira)}."
        )
    avisos.append(
        "Va a no más de 3.65 m del fregadero, para que el desagüe alcance. "
        "Si queda en un rincón, deja 5 cm entre el aparato y el muro de al lado. Ese muro va libre."
    )
    if posiciones:
        alturas = " y ".join(f"{texto_cm(p)} cm" for p in posiciones)
        avisos.append(
            f"Los entrepaños van sueltos, en soportes, para moverlos. "
            f"De partida quedan a {alturas} del piso, cada uno en una hilera distinta. "
            f"Los barrenos son de 5 mm cada {texto_cm(PASO_ENTRE)} cm. "
            f"La hilera de enfrente va a {texto_cm(INSET_ENTRE)} cm del canto frontal del lateral. "
            f"La de atrás va a {texto_cm(INSET_ENTRE)} cm del canto de atrás del entrepaño, sobre el fondo de la tabla."
        )
    avisos.append("El lavavajillas no se manda a cortar.")
    avisos.append("Estas medidas son del tablero. El canto suma aparte, cerca de 0.1 cm por lado.")

    aplicar_medidas(datos, piezas, avisos)
    area = 0
    area_fondo = 0
    canto = 0
    for pieza in piezas:
        canto += pieza.canto_mm
        if pieza.nombre.startswith("Respaldo"):
            area_fondo += pieza.alto * pieza.ancho * pieza.cantidad
        else:
            area += pieza.alto * pieza.ancho * pieza.cantidad
    hoja = HOJA_ANCHO * HOJA_LARGO
    return Resultado(
        listo=True,
        avisos=avisos,
        piezas=piezas,
        ancho_exterior=ancho_exterior,
        canto_mm=canto,
        tableros_15=max(hojas, ceil(area * 1.15 / hoja)),
        tableros_fondo=ceil(area_fondo * 1.15 / hoja) if area_fondo else 0,
        bisagras=0,
        pistones=0,
        confirmat=8,
        esquema={
            "ancho": ancho_exterior,
            "alto": alto,
            "fondo": fondo,
            "espesor": espesor,
            "hueco_ancho": hueco_ancho,
            "hueco_alto": hueco_alto,
            "fondo_repisa": fondo_repisa,
            "repisas": repisas,
            "posiciones": posiciones,
            "soportes": 4 * repisas,
            "hojas": hojas,
            "fondo_esp": fondo_esp,
        },
    )
