"""PDF del zoclo de pino. Solo biblioteca estándar. Helvetica, WinAnsi."""

from despiece import calcular_bajos, cortes_carpintero, texto_cm

ANCHO = 595.28
ALTO = 841.89
MARGEN = 40
PINO = (0.91, 0.83, 0.69)
TINTA = (0.18, 0.14, 0.11)
COTA = (0.55, 0.23, 0.16)
AVISO_RELLENO = (0.98, 0.93, 0.90)
GUIA = (0.54, 0.49, 0.45)
LINEA = (0.25, 0.20, 0.16)


def colocar_marcos(hoja: dict) -> dict | None:
    """Misma colocación que el dibujo 3D. Las cotas salen de aquí."""
    por_clave = {m["clave"]: m for m in hoja["marcos"]}
    leg = por_clave.get("cajón 2 y el esquinero")
    arm = por_clave.get("cajón 1")
    if leg is None or arm is None:
        return None
    fv = hoja["fondo_vuelta"]
    fb = hoja["fondo_barra"]
    proy = hoja["proyeccion"]
    tarja = hoja["ancho_tarja"]
    pie = hoja["pie"]
    leg_x1 = fv - pie
    arm_z0 = proy + pie
    arm_z1 = arm_z0 + arm["ancho"]
    leg_x0 = leg_x1 - leg["ancho"]
    leg_z1 = arm_z1
    leg_z0 = arm_z1 - leg["largo"]
    arm_x0 = leg_x1
    arm_x1 = arm_x0 + arm["largo"]
    return {
        "fv": fv,
        "fb": fb,
        "proy": proy,
        "tarja": tarja,
        "pie": pie,
        "leg": leg,
        "arm": arm,
        "leg_x0": leg_x0,
        "leg_x1": leg_x1,
        "leg_z0": leg_z0,
        "leg_z1": leg_z1,
        "arm_x0": arm_x0,
        "arm_x1": arm_x1,
        "arm_z0": arm_z0,
        "arm_z1": arm_z1,
        "sale_cajon2": -leg_x0,
        "aire_punta": leg_z0,
        "aire_fondo_cajon1": (proy + fb) - arm_z1,
        "aire_fin_cajon1": (fv + tarja) - arm_x1,
    }


def _esc(texto: str) -> str:
    partes = []
    for ch in str(texto):
        if ch in "\\()":
            partes.append("\\" + ch)
            continue
        o = ord(ch)
        if 32 <= o <= 126:
            partes.append(ch)
            continue
        try:
            partes.append("\\" + format(ch.encode("latin-1")[0], "03o"))
        except UnicodeEncodeError:
            partes.append("?")
    return "".join(partes)


def _ancho(texto: str, size: float, font: str) -> float:
    factor = 0.56 if font == "F2" else 0.52
    return len(str(texto)) * size * factor


def envolver(texto: str, size: float, ancho: float, font: str = "F1") -> list[str]:
    palabras = str(texto).split()
    if not palabras:
        return []
    lineas = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        prueba = actual + " " + palabra
        if _ancho(prueba, size, font) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


class HojaPdf:
    def __init__(self):
        self.ops: list[str] = []

    def _color(self, color, trazo: bool):
        r, g, b = color
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} {'RG' if trazo else 'rg'}")

    def rect(self, x, y, w, h, relleno=None, trazo=None, grosor=0.8):
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        if w == 0 or h == 0:
            return
        if relleno:
            self._color(relleno, False)
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        if trazo:
            self._color(trazo, True)
            self.ops.append(f"{grosor:.2f} w")
            self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def linea(self, x1, y1, x2, y2, color=COTA, grosor=0.9):
        self._color(color, True)
        self.ops.append(f"{grosor:.2f} w")
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def guia(self, x, y, w, h):
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        self._color(GUIA, True)
        self.ops.append("[3 2] 0 d")
        self.ops.append("0.8 w")
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")
        self.ops.append("[] 0 d")

    def texto(self, x, y, s, size=11, font="F1", color=TINTA):
        self._color(color, False)
        self.ops.append("BT")
        self.ops.append(f"/{font} {size:.1f} Tf")
        self.ops.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm")
        self.ops.append(f"({_esc(s)}) Tj")
        self.ops.append("ET")

    def texto_centro(self, x, y, s, size=11, font="F1", color=TINTA):
        self.texto(x - _ancho(s, size, font) / 2, y, s, size, font, color)

    def texto_vertical(self, x, y, s, size=9, font="F2", color=COTA):
        self._color(color, False)
        self.ops.append("BT")
        self.ops.append(f"/{font} {size:.1f} Tf")
        self.ops.append(f"0 1 -1 0 {x:.2f} {y:.2f} Tm")
        self.ops.append(f"({_esc(s)}) Tj")
        self.ops.append("ET")


def _parrafo(hoja, x, y, texto, ancho, size=11, leading=14, font="F1", color=TINTA, gap=4):
    for linea in envolver(texto, size, ancho, font):
        hoja.texto(x, y, linea, size, font, color)
        y -= leading
    return y - gap


def _lista(hoja, x, y, pasos, ancho, size=11, leading=14):
    for indice, paso in enumerate(pasos, start=1):
        etiqueta = f"{indice}. "
        hueco = _ancho(etiqueta, size, "F2")
        lineas = envolver(paso, size, ancho - hueco, "F1")
        for i, linea in enumerate(lineas):
            if i == 0:
                hoja.texto(x, y, etiqueta, size, "F2", TINTA)
            hoja.texto(x + hueco, y, linea, size, "F1", TINTA)
            y -= leading
        y -= 3
    return y


def _cota_h(hoja, x1, x2, y, texto):
    if abs(x2 - x1) < 6:
        return
    hoja.linea(x1, y, x2, y)
    hoja.linea(x1, y - 3, x1, y + 3)
    hoja.linea(x2, y - 3, x2, y + 3)
    hoja.texto_centro((x1 + x2) / 2, y + 5, str(texto), 9, "F2", COTA)


def _cota_v(hoja, y1, y2, x, texto):
    if abs(y2 - y1) < 6:
        return
    abajo, arriba = (y1, y2) if y1 < y2 else (y2, y1)
    hoja.linea(x, abajo, x, arriba)
    hoja.linea(x - 3, abajo, x + 3, abajo)
    hoja.linea(x - 3, arriba, x + 3, arriba)
    alto = _ancho(str(texto), 9, "F2")
    hoja.texto_vertical(x - 11, (abajo + arriba) / 2 - alto / 2, str(texto), 9, "F2", COTA)


def _letra(marco: dict, empieza: str) -> str:
    for pieza in marco["cortes"]:
        if pieza["que"].startswith(empieza):
            return pieza["letra"]
    return ""


def _pasos_marco(marco: dict) -> list[str]:
    lado = _letra(marco, "Lado") or "largas"
    if not marco["entra"]:
        return [
            f"Este marco todavía no se arma. De afuera mediría {texto_cm(marco['largo'])} x {texto_cm(marco['ancho'])} cm "
            f"y el ancho no alcanza para dos tablas de {texto_cm(marco['espesor'])} cm más las del medio. "
            "Sube el ancho en el despiece y vuelve a bajar esta hoja."
        ]
    punta = _letra(marco, "Punta") or "de las puntas"
    refuerzo = _letra(marco, "Refuerzo")
    centros = ", ".join(texto_cm(n) for n in marco["centros"])
    pasos = [
        f"Acuesta las dos tablas {lado} en el piso, paralelas. De afuera a afuera, a lo ancho, quedan {texto_cm(marco['ancho'])} cm.",
        f"Mete una tabla {punta} en cada punta, entre las dos {lado}. El marco de afuera queda en {texto_cm(marco['largo'])} x {texto_cm(marco['ancho'])} cm.",
        f"Mide las dos diagonales, de esquina a esquina. Las dos tienen que dar {texto_cm(marco['diagonal'])} cm. Si una da más, empuja esa esquina hasta que queden iguales.",
    ]
    if refuerzo and marco["centros"]:
        aviso = ""
        if marco["refuerzo_editado"] and marco["corte_refuerzo"] != marco["dentro"]:
            aviso = (
                f" Esta tabla está en {texto_cm(marco['corte_refuerzo'])} cm y entre los lados caben {texto_cm(marco['dentro'])} cm. "
                f"Si no entra, recórtala a {texto_cm(marco['dentro'])} cm."
            )
        pasos.append(
            f"Mete las tablas {refuerzo} entre las dos {lado}. "
            f"El centro de cada una, desde la punta marcada, va a {centros} cm.{aviso}"
        )
        pasos.append(
            f"En cada punta de las {punta} y de las {refuerzo}, dos tornillos para madera, atravesando la tabla {lado}. Taladra antes, para que el pino no se raje."
        )
    elif marco.get("n_pedido"):
        pasos.append(
            "Los refuerzos del despiece no caben a lo largo de este marco. No los cortes hasta alargar el marco y volver a bajar esta hoja."
        )
    else:
        pasos.append(
            f"En cada punta de las {punta}, dos tornillos para madera, atravesando la tabla {lado}. Taladra antes, para que el pino no se raje."
        )
    return pasos


def _dibujar_marco(hoja: HojaPdf, marco: dict, izquierda: float, arriba: float) -> float:
    largo = max(marco["largo"], 1)
    ancho = max(marco["ancho"], 1)
    grueso = marco["espesor"]
    escala = min(430 / largo, 168 / ancho)
    ox = izquierda + 52
    oy = arriba - 28 - ancho * escala

    def x(mm):
        return ox + mm * escala

    def y(mm):
        return oy + mm * escala

    if marco["entra"]:
        hoja.rect(x(0), y(0), largo * escala, grueso * escala, PINO, LINEA, 0.8)
        hoja.rect(x(0), y(ancho - grueso), largo * escala, grueso * escala, PINO, LINEA, 0.8)
        hoja.rect(x(0), y(grueso), grueso * escala, marco["dentro"] * escala, PINO, LINEA, 0.8)
        hoja.rect(x(largo - grueso), y(grueso), grueso * escala, marco["dentro"] * escala, PINO, LINEA, 0.8)
        for centro in marco["centros"]:
            hoja.rect(
                x(centro - grueso / 2),
                y(grueso),
                grueso * escala,
                marco["dentro"] * escala,
                PINO,
                LINEA,
                0.8,
            )
        puestos = []
        for centro in marco["centros"]:
            px = x(centro)
            if any(abs(px - otro) < 28 for otro in puestos):
                continue
            puestos.append(px)
            hoja.linea(px, y(ancho) + 2, px, y(ancho) + 9, COTA, 0.7)
            hoja.texto_centro(px, y(ancho) + 12, texto_cm(centro), 8, "F2", COTA)
        hoja.texto(x(0), y(ancho) + 24, "Centros desde esta punta, en cm", 8, "F1", TINTA)
    else:
        hoja.guia(x(0), y(0), largo * escala, ancho * escala)
        hoja.texto_centro(x(largo / 2), y(ancho / 2) - 4, "todavía no se arma", 11, "F2", COTA)
    _cota_h(hoja, x(0), x(largo), y(0) - 16, texto_cm(largo))
    _cota_v(hoja, y(0), y(ancho), x(0) - 28, texto_cm(ancho))
    if marco["entra"]:
        hoja.texto(x(largo) - 210, y(0) - 32, f"Entre las tablas largas: {texto_cm(marco['dentro'])} cm", 10, "F2", COTA)
    return y(0) - 48


def _pagina_cortes(proyecto: str, hoja: dict) -> HojaPdf:
    pdf = HojaPdf()
    ancho = ANCHO - 2 * MARGEN
    y = ALTO - 48
    pdf.texto(MARGEN, y, "CORTES - VISTA GRANDE", 18, "F2")
    y -= 18
    pdf.texto(MARGEN, y, proyecto, 12, "F1", COTA)
    y -= 20
    grueso = hoja["marcos"][0]["espesor"]
    pdf.rect(MARGEN, y - 58, ancho, 58, AVISO_RELLENO, COTA, 1)
    pdf.texto(MARGEN + 10, y - 18, f"PINO: {texto_cm(grueso)} cm x {texto_cm(hoja['zoclo'])} cm", 15, "F2", TINTA)
    pdf.texto(MARGEN + 10, y - 38, f"{hoja['mm'] / 1000:.2f} m cortados  -  {hoja['compra']} m para comprar", 13, "F2", COTA)
    y -= 72
    for marco in hoja["marcos"]:
        if marco["pasa"] > 0:
            nuevo_pie = max(marco["fondo"] - marco["ancho"], 0)
            nuevo_ancho = max(marco["fondo"] - hoja["pie"], 0)
            texto = (
                f"OJO: se sale {texto_cm(marco['pasa'])} cm de la pared de atrás, en el marco del {marco['clave']}. "
                f"El hueco del pie ({texto_cm(hoja['pie'])} cm) más el ancho ({texto_cm(marco['ancho'])} cm) "
                f"pasan el fondo de {texto_cm(marco['fondo'])} cm. "
                f"Baja el hueco a {texto_cm(nuevo_pie)} cm o el ancho a {texto_cm(nuevo_ancho)} cm y vuelve a bajar esta hoja."
            )
            lineas = envolver(texto, 11, ancho - 16, "F2")
            alto_caja = 14 + len(lineas) * 14
            pdf.rect(MARGEN, y - alto_caja + 10, ancho, alto_caja, AVISO_RELLENO, COTA, 1.6)
            yy = y
            for linea in lineas:
                pdf.texto(MARGEN + 8, yy, linea, 11, "F2", COTA)
                yy -= 14
            y = yy - 8
    y -= 6
    pdf.texto(MARGEN, y, "MEDIDAS EN cm  -  MARCAR A, B, C, D, E, F", 13, "F2")
    y -= 8
    columnas = [36, 52, 52, 46, 52]
    encabezados = ["Letra", "Cuántas", "Largo", "Alto", "Grueso", "Para qué"]
    pdf.linea(MARGEN, y, MARGEN + ancho, y, LINEA, 0.8)
    y -= 12
    x = MARGEN
    for i, titulo in enumerate(encabezados):
        pdf.texto(x, y, titulo, 9, "F2")
        if i < len(columnas):
            x += columnas[i]
    y -= 5
    pdf.linea(MARGEN, y, MARGEN + ancho, y, LINEA, 0.4)
    y -= 12
    resto = ancho - sum(columnas)
    for marco in hoja["marcos"]:
        for pieza in marco["cortes"]:
            valores = [
                pieza["letra"],
                str(pieza["cant"]),
                texto_cm(pieza["largo"]),
                texto_cm(pieza["alto"]),
                texto_cm(pieza["grueso"]),
            ]
            if "Lado largo" in pieza["que"]:
                detalle = ["TABLA LARGA"]
            elif "Punta" in pieza["que"]:
                detalle = ["PUNTA"]
            elif "Refuerzo" in pieza["que"]:
                detalle = ["REFUERZO"]
            else:
                detalle = ["PINO"]
            alto_fila = max(14, 11 * len(detalle))
            x = MARGEN
            for i, valor in enumerate(valores):
                pdf.texto(x, y, valor, 9, "F2" if i == 0 else "F1")
                x += columnas[i]
            yy = y
            for linea in detalle:
                pdf.texto(x, yy, linea, 8, "F1")
                yy -= 10
            y -= alto_fila
            pdf.linea(MARGEN, y + 4, MARGEN + ancho, y + 4, (0.8, 0.76, 0.7), 0.4)
            y -= 2
    y -= 8
    vistos = set()
    for marco in hoja["marcos"]:
        if not marco["entra"]:
            y = _parrafo(
                pdf, MARGEN, y,
                f"El marco del {marco['clave']} no se arma con el ancho de {texto_cm(marco['ancho'])} cm.",
                ancho, color=COTA, font="F2",
            )
            continue
        firma = (marco["ancho"], marco["espesor"], marco["dentro"])
        if firma in vistos:
            continue
        vistos.add(firma)
        y = _parrafo(
            pdf, MARGEN, y,
            f"Donde el despiece dice {texto_cm(marco['ancho'])} cm de ancho, es de afuera a afuera. "
            f"Cada lado gasta {texto_cm(marco['espesor'])} cm.",
            ancho, gap=2,
        )
        pdf.texto(
            MARGEN, y,
            f"{texto_cm(marco['ancho'])} - {texto_cm(marco['espesor'])} - {texto_cm(marco['espesor'])} = {texto_cm(marco['dentro'])}",
            12, "F2", COTA,
        )
        y -= 16
        y = _parrafo(
            pdf, MARGEN, y,
            f"Esa es la tabla que entra en medio. No la cortes a {texto_cm(marco['ancho'])} cm: no entra.",
            ancho,
        )
    return pdf


def _pagina_marco(marco: dict, punta: str) -> HojaPdf:
    pdf = HojaPdf()
    ancho = ANCHO - 2 * MARGEN
    y = ALTO - 48
    pdf.texto(MARGEN, y, f"MARCO - {marco['clave']}", 16, "F2")
    y -= 16
    pdf.rect(MARGEN, y - 34, ancho, 34, AVISO_RELLENO, COTA, 1)
    pdf.texto(MARGEN + 8, y - 18, f"FUERA: {texto_cm(marco['largo'])} x {texto_cm(marco['ancho'])} cm", 14, "F2", TINTA)
    pdf.texto(MARGEN + 330, y - 18, f"PINO {texto_cm(marco['espesor'])} x {texto_cm(marco['alto'])} cm", 11, "F2", COTA)
    y -= 48
    y = _dibujar_marco(pdf, marco, MARGEN, y)
    y -= 8
    lados = _letra(marco, "Lado") or "A/D"
    puntas = _letra(marco, "Punta") or "B/E"
    ref = _letra(marco, "Refuerzo")
    pasos = [
        f"1  ACOSTAR  -  2 tablas {lados}",
        f"2  PONER  -  2 puntas {puntas}",
    ]
    if marco["centros"] and ref:
        centros = "  -  ".join(texto_cm(n) for n in marco["centros"])
        pasos.append(f"3  REFUERZOS {ref}  -  centros: {centros} cm")
        pasos.append("4  TORNILLOS  -  2 por punta")
    else:
        pasos.append("3  SIN REFUERZOS")
        pasos.append("4  TORNILLOS  -  2 por punta")
    pasos.append(f"✓  DIAGONAL  -  {texto_cm(marco['diagonal'])} cm")
    y = _lista(pdf, MARGEN, y, pasos, ancho, size=11, leading=16)
    return pdf


def _dibujar_l(pdf: HojaPdf, hoja: dict, lugar: dict, arriba: float) -> float:
    cajas = (
        (0, 0, lugar["fv"], lugar["proy"]),
        (0, lugar["proy"], lugar["fv"], lugar["proy"] + lugar["fb"]),
        (lugar["fv"], lugar["proy"], lugar["fv"] + lugar["tarja"], lugar["proy"] + lugar["fb"]),
    )
    xs = [lugar["leg_x0"], lugar["arm_x1"], 0, lugar["fv"] + lugar["tarja"]]
    zs = [lugar["leg_z0"], lugar["leg_z1"], 0, lugar["proy"] + lugar["fb"]]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    span_x = max(max_x - min_x, 1)
    span_z = max(max_z - min_z, 1)
    escala = min(400 / span_x, 230 / span_z)
    ox = MARGEN + 70
    oy = arriba - 44 - span_z * escala

    def x(mm):
        return ox + (mm - min_x) * escala

    def y(mm):
        return oy + (mm - min_z) * escala

    for x0, z0, x1, z1 in cajas:
        pdf.guia(x(x0), y(z0), (x1 - x0) * escala, (z1 - z0) * escala)
    leg = lugar["leg"]
    arm = lugar["arm"]
    if leg["entra"]:
        pdf.rect(x(lugar["leg_x0"]), y(lugar["leg_z0"]), leg["ancho"] * escala, leg["largo"] * escala, PINO, LINEA, 1)
    else:
        pdf.guia(x(lugar["leg_x0"]), y(lugar["leg_z0"]), leg["ancho"] * escala, leg["largo"] * escala)
    if arm["entra"]:
        pdf.rect(x(lugar["arm_x0"]), y(lugar["arm_z0"]), arm["largo"] * escala, arm["ancho"] * escala, PINO, LINEA, 1)
    else:
        pdf.guia(x(lugar["arm_x0"]), y(lugar["arm_z0"]), arm["largo"] * escala, arm["ancho"] * escala)
    pdf.texto_centro(x((lugar["leg_x0"] + lugar["leg_x1"]) / 2), y((lugar["leg_z0"] + lugar["leg_z1"]) / 2) - 4, "Cajón 2", 10, "F2")
    pdf.texto_centro(x((lugar["arm_x0"] + lugar["arm_x1"]) / 2), y((lugar["arm_z0"] + lugar["arm_z1"]) / 2) - 4, "Cajón 1", 10, "F2")
    _cota_v(pdf, y(lugar["leg_z0"]), y(lugar["leg_z1"]), x(lugar["leg_x0"]) - 30, texto_cm(leg["largo"]))
    _cota_h(pdf, x(lugar["leg_x0"]), x(lugar["leg_x1"]), y(min_z) - 16, texto_cm(leg["ancho"]))
    if lugar["pie"] > 0:
        _cota_h(pdf, x(lugar["leg_x1"]), x(lugar["fv"]), y(min_z) - 16, texto_cm(lugar["pie"]))
    _cota_h(pdf, x(lugar["arm_x0"]), x(lugar["arm_x1"]), y(lugar["arm_z1"]) + 8, texto_cm(arm["largo"]))
    _cota_v(pdf, y(lugar["arm_z0"]), y(lugar["arm_z1"]), x(max_x) + 22, texto_cm(arm["ancho"]))
    if lugar["pie"] > 0:
        _cota_v(pdf, y(lugar["proy"]), y(lugar["arm_z0"]), x(max_x) + 22, texto_cm(lugar["pie"]))
    pdf.texto(x(lugar["fv"]) + 12, y(lugar["proy"]) - 26, "90 grados", 8, "F2", COTA)
    pdf.texto(x(lugar["arm_x0"]), y(max_z) + 26, "atrás, misma línea", 8, "F1", TINTA)
    pdf.texto(x(lugar["leg_x0"]), y(min_z) - 40, "frente cajón 2", 8, "F1", TINTA)
    if lugar["sale_cajon2"] > 0:
        pdf.texto(MARGEN, y(lugar["leg_z1"]) + 22, f"se sale {texto_cm(lugar['sale_cajon2'])} cm", 9, "F2", COTA)
    return y(min_z) - 56


def _pagina_l(hoja: dict, lugar: dict) -> HojaPdf:
    pdf = HojaPdf()
    ancho = ANCHO - 2 * MARGEN
    y = ALTO - 48
    pdf.texto(MARGEN, y, "JUNTAR LA L", 18, "F2")
    y -= 18
    pdf.rect(MARGEN, y - 48, ancho, 48, AVISO_RELLENO, COTA, 1)
    pdf.texto(MARGEN + 10, y - 18, f"ATRAS  -  MISMA LINEA", 13, "F2", TINTA)
    pdf.texto(MARGEN + 10, y - 36, f"FRENTE  -  {texto_cm(hoja['pie'])} cm libres para zapatos", 13, "F2", COTA)
    y -= 60
    y = _dibujar_l(pdf, hoja, lugar, y)
    pasos = [
        "1  UNIR  -  lado contra lado",
        "2  ATRAS  -  bordes alineados",
        f"3  FRENTE  -  dejar {texto_cm(hoja['pie'])} cm",
        "4  CUADRAR  -  medir las diagonales",
        "5  FIJAR  -  4 tornillos",
    ]
    y = _lista(pdf, MARGEN, y, pasos, ancho, size=12, leading=18)
    y -= 8
    pdf.texto(MARGEN, y, "ANTES DE SENTAR LOS CAJONES", 12, "F2")
    y -= 16
    revisiones = []
    for marco in hoja["marcos"]:
        if marco["entra"]:
            revisiones.append(f"Diagonal del {marco['clave']}: {texto_cm(marco['diagonal'])} cm, las dos iguales.")
    revisiones.append(f"Hueco del pie, en los dos frentes: {texto_cm(hoja['pie'])} cm.")
    revisiones.append("Una sola línea atrás, y el alto parejo en los dos marcos.")
    revisiones.append("Si un marco se pasa de la pared, no uses esta hoja.")
    for linea in revisiones:
        pdf.texto(MARGEN, y, "- " + linea, 10, "F1")
        y -= 13
    alto = hoja["zoclo"]
    if y > 90 and alto > 0:
        y -= 8
        pdf.texto(MARGEN, y, f"Alto, {texto_cm(alto)} cm del piso a la cara de arriba", 10, "F2")
        y -= 8
        alto_px = min(70, alto * 0.7)
        pdf.linea(MARGEN, y - alto_px, MARGEN + 150, y - alto_px, LINEA, 0.8)
        pdf.rect(MARGEN + 36, y - alto_px, 54, alto_px, PINO, LINEA, 0.8)
        _cota_v(pdf, y - alto_px, y, MARGEN + 110, texto_cm(alto))
        pdf.texto(MARGEN, y - alto_px - 12, "piso", 8, "F1")
    return pdf


def _pie(pdf: HojaPdf, numero: int, total: int):
    pdf.linea(MARGEN, 32, ANCHO - MARGEN, 32, LINEA, 0.4)
    pdf.texto(MARGEN, 20, "Zoclo de pino. No es el corte de la melamina.", 8, "F1", GUIA)
    pdf.texto(ANCHO - MARGEN - 70, 20, f"Hoja {numero} de {total}", 8, "F1", GUIA)


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
        objetos.append(b"")  # page, filled after we know the content id
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
    titulo_pdf = _esc(titulo)
    salida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R "
        f"/Info << /Title ({titulo_pdf}) /Producer (Muebles de melamina) >> >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    return bytes(salida)


def pdf_zoclo(datos: dict) -> bytes | None:
    resultado = calcular_bajos(datos)
    if not resultado.listo:
        return None
    hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
    if not hoja:
        return None
    lugar = colocar_marcos(hoja)
    if lugar is None:
        return None
    proyecto = str(datos.get("proyecto") or "Bajos de tarja")
    paginas = [_pagina_cortes(proyecto, hoja)]
    paginas.append(
        _pagina_marco(
            lugar["leg"],
            "La punta marcada es la de afuera, la que no toca al cajón 1.",
        )
    )
    paginas.append(
        _pagina_marco(
            lugar["arm"],
            "La punta marcada es la que se recarga en el costado del cajón 2.",
        )
    )
    paginas.append(_pagina_l(hoja, lugar))
    return _armar(paginas, "Zoclo " + proyecto)
