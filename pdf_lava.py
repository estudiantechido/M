"""PDF del mueble del lavavajillas. Solo biblioteca estándar."""

from math import cos, pi, sin

from despiece import (
    HOJA_ANCHO,
    HOJA_LARGO,
    INSET_ENTRE,
    LAVA_HOYO,
    LAVA_HOYO_ATRAS,
    LAVA_HOYO_PISO,
    PASO_ENTRE,
    calcular_lavavajillas,
    texto_cm,
)
from pdf_zoclo import (
    ALTO,
    ANCHO,
    COTA,
    GUIA,
    LINEA,
    MARGEN,
    HojaPdf,
    _ancho,
    _cota_h,
    _esc,
    envolver,
)

TABLERO = (0.93, 0.94, 0.95)
HUECO = (0.86, 0.88, 0.90)

NOMBRES = (
    ("Lateral lavavajillas", "Laterales"),
    ("Techo lavavajillas", "Techo del hueco"),
    ("Techo entrepaños", "Techo de arriba"),
    ("Entrepaño", "Entrepaños"),
    ("Respaldo entrepaños", "Respaldo"),
)


def _pie(pdf: HojaPdf, numero: int, total: int):
    pdf.linea(MARGEN, 32, ANCHO - MARGEN, 32, LINEA, 0.4)
    pdf.texto(ANCHO - MARGEN - 40, 18, f"{numero} de {total}", 9, "F1", GUIA)


def _armar(paginas: list[HojaPdf], titulo: str) -> bytes:
    total = len(paginas)
    for indice, pdf in enumerate(paginas, start=1):
        _pie(pdf, indice, total)
    objetos: list[bytes] = []
    n = total
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(n))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode("ascii"))
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for pdf in paginas:
        datos = ("\n".join(pdf.ops) + "\n").encode("ascii")
        contenido = b"<< /Length " + str(len(datos)).encode("ascii") + b" >>\nstream\n" + datos + b"endstream"
        objetos.append(b"")
        objetos.append(contenido)
    for i in range(n):
        pagina_id = 5 + 2 * i
        contenido_id = pagina_id + 1
        objetos[pagina_id - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ANCHO:.2f} {ALTO:.2f}] "
            f"/Contents {contenido_id} 0 R /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>"
        ).encode("ascii")
    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n".encode("ascii")
        salida += obj
        if not obj.endswith(b"\n"):
            salida += b"\n"
        salida += b"endobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n".encode("ascii")
    salida += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        salida += f"{off:010d} 00000 n \n".encode("ascii")
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R "
        f"/Info << /Title ({_esc(titulo)}) >> >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(salida)


def _marca_v(pdf: HojaPdf, y1: float, y2: float, x: float, texto: str, derecha: bool, arriba_texto: bool):
    if abs(y2 - y1) < 6:
        return
    abajo, arriba = (y1, y2) if y1 < y2 else (y2, y1)
    pdf.linea(x, abajo, x, arriba, COTA, 0.9)
    pdf.linea(x - 3, abajo, x + 3, abajo, COTA, 0.9)
    pdf.linea(x - 3, arriba, x + 3, arriba, COTA, 0.9)
    ancho = _ancho(texto, 12, "F2")
    alto_texto = arriba - 14 if arriba_texto else (abajo + arriba) / 2 - 5
    if derecha:
        pdf.texto(x + 8, alto_texto, texto, 12, "F2", COTA)
    else:
        pdf.texto(x - 8 - ancho, alto_texto, texto, 12, "F2", COTA)


def _frente(pdf: HojaPdf, esq: dict, ox: float, base: float, alto_px: float):
    alto = esq["alto"]
    ancho = esq["ancho"]
    e = esq["espesor"]
    hueco = esq["hueco_alto"]
    escala = alto_px / max(alto, 1)

    def x(mm):
        return ox + mm * escala

    def y(mm):
        return base + mm * escala

    luz = ancho - 2 * e
    pdf.rect(x(0), y(0), e * escala, alto * escala, TABLERO, LINEA, 1)
    pdf.rect(x(ancho - e), y(0), e * escala, alto * escala, TABLERO, LINEA, 1)
    pdf.rect(x(e), y(0), luz * escala, hueco * escala, HUECO, None)
    pdf.rect(x(e), y(hueco), luz * escala, e * escala, TABLERO, LINEA, 1)
    pdf.rect(x(e), y(alto - e), luz * escala, e * escala, TABLERO, LINEA, 1)
    for puesto in esq.get("posiciones") or []:
        pdf.rect(x(e), y(puesto), luz * escala, e * escala, TABLERO, LINEA, 1)
        pdf.texto(x(ancho) + 28, y(puesto) - 4, texto_cm(puesto), 12, "F2", COTA)
    pdf.texto_centro(x(ancho / 2), y(hueco / 2) - 4, "HUECO", 10, "F2", GUIA)
    _marca_v(pdf, y(0), y(alto), x(ancho) + 14, texto_cm(alto), True, True)
    _marca_v(pdf, y(0), y(hueco), x(0) - 16, texto_cm(hueco), False, False)
    _cota_h(pdf, x(0), x(ancho), y(0) - 18, texto_cm(ancho))


def _pagina_corta(esq: dict, piezas: list, color: str, grueso: str) -> HojaPdf:
    pdf = HojaPdf()
    y = ALTO - 56
    pdf.texto(MARGEN, y, "CORTA", 22, "F2")
    y -= 22
    pdf.texto(MARGEN, y, f"{color}. Tablero de {grueso} cm.", 12, "F1")
    y -= 16
    pdf.texto(
        MARGEN,
        y,
        f"Hoja {texto_cm(HOJA_ANCHO)} x {texto_cm(HOJA_LARGO)} cm. Pide {esq['hojas']} hojas.",
        12,
        "F1",
    )
    y -= 26
    por_nombre = {pieza.nombre: pieza for pieza in piezas}
    for clave, titulo in NOMBRES:
        pieza = por_nombre.get(clave)
        if pieza is None:
            continue
        pdf.texto(MARGEN, y, f"{pieza.cantidad}   {titulo}", 14, "F2")
        y -= 16
        for linea in _medidas(clave, pieza):
            pdf.texto(MARGEN + 28, y, linea, 12, "F1")
            y -= 15
        y -= 8
    y -= 4
    pdf.texto(MARGEN, y, "Canto solo en el frente.", 13, "F2")
    y -= 16
    pdf.texto(MARGEN, y, "Sí: laterales, techos y entrepaños.", 12, "F1")
    y -= 16
    pdf.texto(MARGEN, y, "No: el respaldo.", 12, "F1")
    y -= 18
    pdf.texto(MARGEN, y, "Los entrepaños no se atornillan.", 13, "F2")
    y -= 16
    pdf.texto(MARGEN, y, "Van 0.2 cm más angostos que el hueco.", 12, "F1")
    _frente(pdf, esq, 392, 148, 420)
    pdf.texto(392, 112, "Medidas en cm.", 10, "F1", GUIA)
    _lateral(pdf, esq)
    return pdf


def _circulo(pdf: HojaPdf, cx: float, cy: float, radio: float):
    puntos = []
    for i in range(16):
        angulo = 2 * pi * i / 16
        puntos.append((cx + radio * cos(angulo), cy + radio * sin(angulo)))
    trazo = " ".join(f"{x:.2f} {y:.2f} l" for x, y in puntos[1:])
    camino = f"{puntos[0][0]:.2f} {puntos[0][1]:.2f} m {trazo} h"
    pdf._color(HUECO, False)
    pdf.ops.append(camino + " f")
    pdf._color(LINEA, True)
    pdf.ops.append("1.2 w")
    pdf.ops.append(camino + " S")


def _lateral(pdf: HojaPdf, esq: dict):
    fondo = esq["fondo"]
    visto = 480
    ox, base = 46, 78
    ancho_px = 200
    escala = ancho_px / max(fondo, 1)
    alto_px = visto * escala
    if alto_px > 210:
        alto_px = 210
        escala = alto_px / visto
        ancho_px = fondo * escala

    def x(mm):
        return ox + mm * escala

    def y(mm):
        return base + mm * escala

    pdf.texto(ox, y(visto) + 16, "LATERAL IZQUIERDO", 12, "F2")
    pdf.rect(x(0), y(0), ancho_px, alto_px, TABLERO, LINEA, 1)
    radio = (LAVA_HOYO / 2) * escala
    if radio >= 3 and LAVA_HOYO_ATRAS + LAVA_HOYO / 2 < fondo and LAVA_HOYO_PISO + LAVA_HOYO / 2 < visto:
        _circulo(pdf, x(LAVA_HOYO_ATRAS), y(LAVA_HOYO_PISO), radio)
    pdf.texto(x(LAVA_HOYO_ATRAS) + radio + 6, y(LAVA_HOYO_PISO) - 2, texto_cm(LAVA_HOYO), 11, "F2", COTA)
    pdf.texto(8, y(LAVA_HOYO_PISO) - 4, texto_cm(LAVA_HOYO_PISO), 11, "F2", COTA)
    pdf.texto(ox, y(0) - 14, "atrás", 9, "F1", GUIA)
    pdf.texto(x(fondo) - 34, y(0) - 14, "frente", 9, "F1", GUIA)
    pdf.texto(x(LAVA_HOYO_ATRAS), y(0) - 28, f"{texto_cm(LAVA_HOYO_ATRAS)} de atrás", 10, "F2", COTA)


def _medidas(clave: str, pieza) -> tuple[str, str]:
    grueso = f"Grueso {texto_cm(pieza.espesor)} cm."
    if clave == "Respaldo entrepaños":
        return (
            f"{texto_cm(pieza.alto)} cm de alto.",
            f"{texto_cm(pieza.ancho)} cm de ancho. {grueso}",
        )
    if clave == "Lateral lavavajillas":
        return (
            f"{texto_cm(pieza.alto)} cm de alto.",
            f"{texto_cm(pieza.ancho)} cm de fondo. {grueso}",
        )
    return (
        f"{texto_cm(pieza.alto)} cm de ancho.",
        f"{texto_cm(pieza.ancho)} cm de fondo. {grueso}",
    )


def _pasos(esq: dict) -> list[str]:
    pos = esq.get("posiciones") or []
    pasos = [
        "Pon los dos laterales de pie. Uno a cada lado.",
        "No pongas piso.",
        "No pongas zoclo.",
        (
            f"Mete el techo del hueco. La cara de abajo queda a {texto_cm(esq['hueco_alto'])} cm del piso. "
            "Sin barrera de vapor, cinta de aluminio en la cara de abajo. "
            f"Tornillos cortos: no atraviesan los {texto_cm(esq['espesor'])} cm."
        ),
        (
            f"Mete el techo de arriba. Llega a {texto_cm(esq['alto'])} cm. "
            "Pon 2 escuadras de este techo al muro."
        ),
        "Atornilla solo los dos techos. 4 confirmat de 7 x 50 en cada uno. Son 8.",
        (
            f"El hueco mide {texto_cm(esq['hueco_ancho'])} cm de ancho. "
            f"Mide {texto_cm(esq['hueco_alto'])} cm de alto. "
            f"Mide {texto_cm(esq['fondo'])} cm de fondo."
        ),
        "Pon el respaldo solo atrás de los entrepaños. Clavos cortos.",
    ]
    if not pos:
        pasos.append("Este mueble no lleva entrepaños.")
        return pasos
    if len(pos) == 1:
        donde = f"De partida, el entrepaño queda a {texto_cm(pos[0])} cm del piso."
    else:
        donde = "De partida quedan a " + " y a ".join(f"{texto_cm(p)} cm" for p in pos) + " del piso."
    pasos.extend(
        [
            "Haz los hoyos antes de cerrar.",
            f"Cada entrepaño lleva 4 soportes. Son {esq['soportes']}.",
            "No atornilles los entrepaños. Se suben y se bajan.",
            donde,
        ]
    )
    return pasos


def _pagina_arma(esq: dict) -> HojaPdf:
    pdf = HojaPdf()
    y = ALTO - 56
    pdf.texto(MARGEN, y, "ARMA", 22, "F2")
    y -= 28
    for indice, paso in enumerate(_pasos(esq), start=1):
        pdf.texto(MARGEN, y, f"{indice}.", 14, "F2")
        frases = [parte.strip() for parte in paso.split(". ") if parte.strip()]
        primera = True
        for frase in frases:
            if not frase.endswith("."):
                frase += "."
            for linea in envolver(frase, 13, 500):
                if not primera:
                    y -= 16
                primera = False
                pdf.texto(MARGEN + 28, y, linea, 13, "F1")
        y -= 16
    if esq.get("posiciones"):
        y -= 6
        pdf.texto(MARGEN, y, "HOYOS DE LOS ENTREPAÑOS", 14, "F2")
        y -= 20
        lineas = [
            "En la cara de adentro de cada lateral.",
            "Solo arriba del lavavajillas.",
            f"Hoyo de 5 mm. Uno cada {texto_cm(PASO_ENTRE)} cm.",
            f"La de enfrente: a {texto_cm(INSET_ENTRE)} cm del canto frontal.",
            f"La de atrás: a {texto_cm(INSET_ENTRE)} cm del canto de atrás del entrepaño.",
            "Mide ese canto sobre el fondo de la tabla.",
            "La tabla se puede subir o bajar a otro hoyo.",
        ]
        for linea in lineas:
            pdf.texto(MARGEN, y, linea, 13, "F1")
            y -= 18
    y -= 8
    pdf.texto(MARGEN, y, "NO LO HAGAS EN EL CORTE", 14, "F2", COTA)
    y -= 20
    for linea in (
        "No cortes el aparato.",
        "No hagas el hoyo del agua en el corte.",
        "Al armar, en el lateral izquierdo.",
        f"A {texto_cm(LAVA_HOYO_PISO)} cm del piso y a {texto_cm(LAVA_HOYO_ATRAS)} cm de atrás.",
        f"Mide {texto_cm(LAVA_HOYO)} cm. Es el centro. Solo uno.",
        "Ahí pasan manguera, desagüe y cable, ya con las conexiones.",
        "No pongas fondo detrás del aparato.",
    ):
        pdf.texto(MARGEN, y, linea, 13, "F1")
        y -= 18
    return pdf


def pdf_lavavajillas(datos: dict) -> bytes | None:
    resultado = calcular_lavavajillas(datos)
    if not resultado.listo:
        return None
    color = str(datos.get("color") or "Blanco Frosty").strip() or "Blanco Frosty"
    grueso = texto_cm(resultado.esquema["espesor"])
    paginas = [
        _pagina_corta(resultado.esquema, resultado.piezas, color, grueso),
        _pagina_arma(resultado.esquema),
    ]
    return _armar(paginas, "Lavavajillas")
