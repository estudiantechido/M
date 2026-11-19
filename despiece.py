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
from math import ceil, hypot

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
    except ValueError:
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
        for nombre, nota in (
            (f"Piso {clave}", nota_piso),
            (f"Entrepaño {clave}", nota_entre),
            (f"Techo {clave}", nota_techo),
        ):
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
    ancho_2 = opcion("marco_a_2", ANCHO_MARCO, "El ancho del marco del cajón 2", 40, 2000, en_cm=True)
    ancho_1 = opcion("marco_a_1", ANCHO_MARCO, "El ancho del marco del cajón 1", 40, 2000, en_cm=True)
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
        "Del zoclo a la cara de arriba. Se sienta sobre el zoclo que comparte con el esquinero. El canto va hacia la cocina.",
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
        "Cajón ciego. Se sienta sobre el mismo zoclo del cajón 2. Sus caras dan contra la tarja y contra la vuelta. Sin canto visto.",
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
            "alto": alto_barra,
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
            "zoclo_pie": pie,
            "pino_esp": pino,
            "marco_a_2": ancho_2,
            "marco_l_2": largo_leg,
            "marco_l_2_auto": auto_2,
            "ref_2": n2,
            "marco_a_1": ancho_1,
            "marco_l_1": largo_arm,
            "marco_l_1_auto": auto_1,
            "ref_1": n1,
            "pino_mm": metros_pino(piezas),
        },
    )
