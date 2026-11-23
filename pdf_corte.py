"""Plano de las piezas sobre la hoja. Solo biblioteca estándar."""

from despiece import (
    HOJA_ANCHO,
    HOJA_LARGO,
    SIERRA_HOJA,
    cortes_lavavajillas,
    calcular_lavavajillas,
    texto_cm,
)
from pdf_lava import _armar
from pdf_zoclo import ALTO, ANCHO, COTA, GUIA, LINEA, MARGEN, HojaPdf, _ancho

TABLERO = (1, 1, 1)
SOBRA = (0.91, 0.92, 0.93)
NOMBRE = {
    "Lateral lavavajillas": "Lateral",
    "Lateral": "Lateral",
    "Techo lavavajillas": "Techo hueco",
    "Techo entrepaños": "Techo arriba",
    "Entrepaño": "Entrepaño",
    "Tabla": "Tabla",
}


def _nombre(pieza: dict) -> str:
    return NOMBRE.get(pieza["nombre"], pieza["nombre"])


def _pagina(numero: int, hojas: list[list[dict]], color: str, grueso: str, respaldo: str) -> HojaPdf:
    pdf = HojaPdf()
    y = ALTO - 52
    pdf.texto(MARGEN, y, f"HOJA {numero}", 22, "F2")
    y -= 20
    pdf.texto(MARGEN, y, f"{color}. Tablero de {grueso} cm.", 13, "F1")
    y -= 16
    pdf.texto(MARGEN, y, f"{texto_cm(HOJA_ANCHO)} x {texto_cm(HOJA_LARGO)} cm.", 13, "F2")
    alto_px = 500
    escala = alto_px / HOJA_LARGO
    ancho_px = HOJA_ANCHO * escala
    ox = (ANCHO - ancho_px) / 2
    oy = 210
    pdf.rect(ox, oy, ancho_px, alto_px, SOBRA, LINEA, 1.1)
    piezas = hojas[numero - 1]
    for pieza in piezas:
        x = ox + pieza["x"] * escala
        y0 = oy + pieza["y"] * escala
        w = pieza["w"] * escala
        h = pieza["h"] * escala
        pdf.rect(x, y0, w, h, TABLERO, LINEA, 1)
        nombre = _nombre(pieza)
        medida = f"{texto_cm(max(pieza['w'], pieza['h']))} x {texto_cm(min(pieza['w'], pieza['h']))}"
        if w > _ancho(nombre, 11, "F2") + 8 and h > 28:
            pdf.texto(x + 6, y0 + 16, nombre, 11, "F2")
        if w > _ancho(medida, 10, "F1") + 8 and h > 42:
            pdf.texto(x + 6, y0 + 30, medida, 10, "F1")
        if pieza["frente"] == "lado" and h > 20:
            pdf.linea(x + w, y0 + 4, x + w, y0 + h - 4, COTA, 1.4)
        elif pieza["frente"] == "abajo" and w > 20:
            pdf.linea(x + 4, y0, x + w - 4, y0, COTA, 1.4)
    derechos = [pieza for pieza in piezas if pieza["x"] > 0]
    if derechos:
        tope = max(pieza["y"] + pieza["h"] for pieza in derechos)
        if HOJA_LARGO - tope > 200:
            pdf.texto(
                ox + derechos[0]["x"] * escala + 8,
                oy + (tope + (HOJA_LARGO - tope) / 2) * escala,
                "sobra",
                12,
                "F1",
                GUIA,
            )
    y = oy - 22
    pdf.texto(MARGEN, y, "En esta hoja", 12, "F2")
    y -= 16
    for pieza in piezas:
        linea = f"{_nombre(pieza)}   {texto_cm(max(pieza['w'], pieza['h']))} x {texto_cm(min(pieza['w'], pieza['h']))} cm"
        pdf.texto(MARGEN, y, linea, 12, "F1")
        y -= 15
    y -= 4
    pdf.texto(MARGEN, y, f"Entre corte y corte, {texto_cm(SIERRA_HOJA)} cm de sierra.", 11, "F1", GUIA)
    y -= 14
    pdf.texto(MARGEN, y, "La raya roja es el frente. Ahí va el canto.", 11, "F1", GUIA)
    if numero == len(hojas):
        y -= 16
        pdf.texto(MARGEN, y, "Pide la hoja completa, sin orillas recortadas.", 11, "F1")
        if respaldo:
            y -= 14
            pdf.texto(MARGEN, y, respaldo, 11, "F1")
    return pdf


def pdf_corte(datos: dict) -> bytes | None:
    resultado = calcular_lavavajillas(datos)
    if not resultado.listo:
        return None
    hojas = cortes_lavavajillas(resultado.piezas)
    if not hojas:
        return None
    color = str(datos.get("color") or "Blanco Frosty").strip() or "Blanco Frosty"
    grueso = texto_cm(resultado.esquema["espesor"])
    respaldo = ""
    for pieza in resultado.piezas:
        if pieza.nombre.startswith("Respaldo"):
            respaldo = (
                f"El respaldo, {texto_cm(pieza.alto)} x {texto_cm(pieza.ancho)} cm, "
                f"es de {texto_cm(pieza.espesor)} cm. Va en otra hoja."
            )
    paginas = [_pagina(i, hojas, color, grueso, respaldo) for i in range(1, len(hojas) + 1)]
    return _armar(paginas, "Corte")
