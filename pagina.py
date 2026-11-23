"""Página del despiece. El cálculo vive en despiece.py."""

from html import escape
from math import ceil

from despiece import (
    HOJA_ANCHO,
    HOJA_LARGO,
    Resultado,
    calcular_bajos,
    calcular_columna,
    LAVA_ALTO_MUEBLE,
    LAVA_CORTE_ALTO,
    LAVA_HUECO_ALTO,
    LAVA_HOYO,
    LAVA_HOYO_ATRAS,
    LAVA_HOYO_PISO,
    calcular_lavavajillas,
    cortes_lavavajillas,
    cm_a_mm,
    texto_cm,
)

CAMPOS_CM = (
    "alto",
    "fondo",
    "espesor",
    "fondo_esp",
    "zoclo",
    "holgura",
    "hueco_ancho",
    "hueco_alto",
    "hueco_desde",
    "hueco_fondo",
)

CAMPOS_CM_BAJOS = (
    "profundidad_esquina",
    "largo_pared_a",
    "largo_pared_b",
    "largo_pared_c",
    "altura_cubierta",
    "espesor_cubierta",
    "profundidad_cubierta",
    "vuelo_cubierta",
    "pasillo_libre",
    "altura_techo",
    "desnivel_piso",
    "largo_barra",
    "fondo_barra",
    "largo_vuelta",
    "fondo_vuelta",
    "ancho_tarja",
    "puerta_vuelta",
    "alto_barra",
    "espesor",
    "fondo_esp",
    "zoclo",
    "zoclo_pie",
    "pino_esp",
    "marco_a_2",
    "marco_l_2",
    "marco_a_1",
    "marco_l_1",
    "holgura",
    "entre_desde",
)

CAMPOS = (
    "proyecto",
    "color",
    "alto",
    "fondo",
    "espesor",
    "fondo_esp",
    "zoclo",
    "holgura",
    "fondo_modo",
    "hueco_ancho",
    "hueco_alto",
    "hueco_desde",
    "hueco_fondo",
    "ejemplo",
    "medidas",
)

VACIO = {
    "proyecto": "Columna horno Teka HLF 824 G",
    "color": "Blanco",
    "alto": "2100",
    "fondo": "580",
    "espesor": "15",
    "fondo_esp": "3",
    "zoclo": "100",
    "holgura": "3",
    "fondo_modo": "clavado",
    "hueco_ancho": "",
    "hueco_alto": "",
    "hueco_desde": "",
    "hueco_fondo": "",
    "ejemplo": "",
}

EJEMPLO = {
    **VACIO,
    "hueco_ancho": "800",
    "hueco_alto": "600",
    "hueco_desde": "900",
    "ejemplo": "1",
}


def _texto_consulta(query: dict, campo: str) -> str:
    valores = query[campo]
    return valores[0] if isinstance(valores, list) else str(valores)


def datos_de_consulta(query: dict, ejemplo: bool = False) -> dict:
    datos = dict(EJEMPLO if ejemplo else VACIO)
    for campo in CAMPOS:
        if campo in query:
            crudo = _texto_consulta(query, campo)
            datos[campo] = cm_a_mm(crudo) if campo in CAMPOS_CM else crudo
    return datos


def _cm_visible(valor) -> str:
    texto = str(valor if valor is not None else "").strip()
    if texto == "":
        return ""
    try:
        return texto_cm(float(texto))
    except (TypeError, ValueError):
        return texto


def _campo(datos, nombre, etiqueta, ayuda, ancho=True):
    valor = escape(_cm_visible(datos.get(nombre, "")))
    return f"""
    <label>
      <span>{etiqueta}</span>
      <input name="{nombre}" value="{valor}" inputmode="decimal" step="0.1" autocomplete="off">
      <small>{ayuda}</small>
    </label>
    """


def _svg(esq: dict) -> str:
    alto = esq["alto"]
    ancho = esq["ancho"]
    escala = 640 / alto
    margen_x = 150
    margen_y = 36
    ancho_px = ancho * escala
    alto_px = alto * escala

    def y(mm):
        return margen_y + (alto - mm) * escala

    def x(mm):
        return margen_x + mm * escala

    zoclo = esq["zoclo"]
    desde = esq["hueco_desde"]
    hueco_alto = esq["hueco_alto"]
    techo_hueco = desde + hueco_alto
    partes = [
        f'<rect x="{x(0):.1f}" y="{y(alto):.1f}" width="{ancho_px:.1f}" height="{alto_px:.1f}" class="caja"/>',
        f'<rect x="{x(0):.1f}" y="{y(zoclo):.1f}" width="{ancho_px:.1f}" height="{zoclo * escala:.1f}" class="zoclo"/>',
        f'<rect x="{x(8):.1f}" y="{y(desde):.1f}" width="{ancho_px - 16 * escala:.1f}" height="{(desde - zoclo) * escala:.1f}" class="puerta"/>',
        f'<line x1="{x(ancho / 2):.1f}" y1="{y(desde):.1f}" x2="{x(ancho / 2):.1f}" y2="{y(zoclo):.1f}" class="corte"/>',
        f'<rect x="{x(0):.1f}" y="{y(techo_hueco):.1f}" width="{ancho_px:.1f}" height="{hueco_alto * escala:.1f}" class="hueco"/>',
        f'<rect x="{x(8):.1f}" y="{y(alto):.1f}" width="{ancho_px - 16 * escala:.1f}" height="{(alto - techo_hueco) * escala:.1f}" class="tapa"/>',
        f'<text x="{x(ancho / 2):.1f}" y="{y(desde + hueco_alto / 2) + 4:.1f}" text-anchor="middle">hueco del horno</text>',
        f'<text x="{x(ancho / 4):.1f}" y="{y((desde + zoclo) / 2) + 4:.1f}" text-anchor="middle">puerta</text>',
        f'<text x="{x(3 * ancho / 4):.1f}" y="{y((desde + zoclo) / 2) + 4:.1f}" text-anchor="middle">puerta</text>',
        f'<text x="{x(ancho / 2):.1f}" y="{y((alto + techo_hueco) / 2) + 4:.1f}" text-anchor="middle">tapa hacia arriba</text>',
        f'<text x="{margen_x - 8}" y="{y(alto / 2):.1f}" text-anchor="end" transform="rotate(-90 {margen_x - 8} {y(alto / 2):.1f})">{texto_cm(alto)} cm</text>',
        f'<text x="{x(ancho / 2):.1f}" y="{y(0) + 22:.1f}" text-anchor="middle">{texto_cm(ancho)} cm de ancho exterior</text>',
    ]
    vista_w = margen_x + ancho_px + 24
    vista_h = margen_y + alto_px + 36
    return (
        f'<svg viewBox="0 0 {vista_w:.0f} {vista_h:.0f}" role="img" aria-label="Frente de la columna">'
        + "".join(partes)
        + "</svg>"
    )


OJO = (
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
    '<path fill="none" stroke="currentColor" stroke-width="1.8" '
    'd="M2 12s4-6.5 10-6.5S22 12 22 12s-4 6.5-10 6.5S2 12 2 12z"/>'
    '<circle cx="12" cy="12" r="2.5" fill="currentColor"/>'
    '<path class="raya" fill="none" stroke="currentColor" stroke-width="1.8" d="M4 20L20 4"/>'
    "</svg>"
)


def _ojo(modulo: str, nombre: str) -> str:
    return (
        f'<button type="button" class="ojo" data-ojo="{modulo}" aria-pressed="true" '
        f'aria-label="Ver solo {escape(nombre)}">{OJO}</button>'
    )


def _nav(activa: str) -> str:
    entradas = (
        ("bajos", "/", "Bajo de tarja"),
        ("columna", "/?pieza=columna", "Columna de horno"),
        ("lavavajillas", "/?pieza=lavavajillas", "Lavavajillas"),
    )
    partes = []
    for pieza, href, texto in entradas:
        clase = "boton" if pieza == activa else "boton claro"
        partes.append(f'<a class="{clase}" href="{href}">{texto}</a>')
    return '<nav class="piezas">' + "".join(partes) + "</nav>"


CABEZA_TABLA = (
    "<th>Pieza</th><th>Cant.</th><th>cm</th><th>cm</th><th>Espesor cm</th>"
    "<th>Material</th><th>Cantos</th><th>Cómo se lee</th><th>Notas para el corte</th>"
)


def _rango_pieza(nombre: str) -> tuple[int, int]:
    n = nombre.lower()
    if n.startswith("zoclo"):
        if "cajón 2" in n or "cajon 2" in n:
            modulo = 0
        else:
            modulo = 1
        return modulo, 0 if "marco" in n else 1
    if n.startswith("lateral"):
        orden = 0
    elif n.startswith("piso"):
        orden = 1
    elif n.startswith("entrepa"):
        orden = 2
    elif n.startswith("techo"):
        orden = 3
    elif n.startswith("fondo"):
        orden = 4
    elif n.startswith("puerta"):
        orden = 5
    elif n.startswith("tapa"):
        orden = 6
    elif n.startswith("fijo"):
        orden = 7
    else:
        orden = 9
    if "tarja" in n:
        cual = 0
    elif "vuelta" in n or "inferior" in n:
        cual = 1
    elif "esquina" in n or "superior" in n or "horno" in n:
        cual = 2
    else:
        cual = 3
    return orden, cual


def _parte(titulo: str, ayuda: str, piezas: list, modulo: str = "", accion: str = "", medidas: str = "", ficha: str = "", con_ojo: bool = True) -> str:
    if not piezas:
        return ""
    marca = f' data-modulo="{modulo}"' if modulo else ""
    filas = []
    for pieza in sorted(piezas, key=lambda p: _rango_pieza(p.nombre)):
        tabla = f' data-tabla="{escape(pieza.nombre)}"' if modulo else ""
        filas.append(
            f"<tr{tabla}{marca}>"
            f"<td>{escape(pieza.nombre)}</td>"
            f"<td class='num'>{pieza.cantidad}</td>"
            f"<td class='num'>{texto_cm(pieza.alto)}</td>"
            f"<td class='num'>{texto_cm(pieza.ancho)}</td>"
            f"<td class='num'>{texto_cm(pieza.espesor)}</td>"
            f"<td>{escape(pieza.material)}</td>"
            f"<td>{escape(pieza.cantos)}</td>"
            f"<td>{escape(pieza.lectura)}</td>"
            f"<td>{escape(pieza.notas)}</td>"
            "</tr>"
        )
    ojo = _ojo(modulo, titulo.removeprefix("1. ").removeprefix("2. ").removeprefix("3. ").removeprefix("4. ")) if modulo and con_ojo else ""
    return (
        f'<section class="parte"{marca}>'
        f"<h3>{ojo}<span>{escape(titulo)}</span>{accion}</h3>"
        f"<p>{escape(ayuda)}</p>"
        f"{medidas}"
        f"{ficha}"
        f"<table><thead><tr>{CABEZA_TABLA}</tr></thead>"
        f"<tbody>{''.join(filas)}</tbody></table>"
        "</section>"
    )


def _partes_columna(piezas: list) -> str:
    grupos = {
        "zoclo": [],
        "laterales": [],
        "abajo": [],
        "hueco": [],
        "arriba": [],
        "otras": [],
    }
    for pieza in piezas:
        n = pieza.nombre.lower()
        if n.startswith("zoclo"):
            grupos["zoclo"].append(pieza)
        elif n.startswith("lateral"):
            grupos["laterales"].append(pieza)
        elif n.startswith("puerta") or n.startswith("piso inferior") or "inferior" in n:
            grupos["abajo"].append(pieza)
        elif "horno" in n:
            grupos["hueco"].append(pieza)
        elif n.startswith("tapa") or n.startswith("techo") or n.startswith("fondo"):
            grupos["arriba"].append(pieza)
        else:
            grupos["otras"].append(pieza)
    return "".join(
        (
            _parte("1. Zoclo", "La tabla del pie, suelta del resto.", grupos["zoclo"]),
            _parte("2. Laterales", "Los dos costados, de piso a techo.", grupos["laterales"]),
            _parte("3. Cajón de abajo", "Piso, fondo y las dos puertas.", grupos["abajo"]),
            _parte("4. Hueco del horno", "El piso donde apoya y el techo que lo cierra.", grupos["hueco"]),
            _parte("5. Cajón de arriba", "Techo, fondo y la tapa que abre hacia arriba.", grupos["arriba"]),
            _parte("6. Otras piezas", "", grupos["otras"]),
        )
    )


def render(datos: dict, resultado: Resultado) -> str:
    proyecto = escape(datos.get("proyecto") or "Columna de horno")
    color = escape(datos.get("color") or "Blanco")
    ejemplo = (
        datos.get("ejemplo") == "1"
        and datos.get("hueco_ancho") == EJEMPLO["hueco_ancho"]
        and datos.get("hueco_alto") == EJEMPLO["hueco_alto"]
        and datos.get("hueco_desde") == EJEMPLO["hueco_desde"]
    )
    modo = datos.get("fondo_modo") or "clavado"
    clavado = "checked" if modo != "ranura" else ""
    ranura = "checked" if modo == "ranura" else ""

    if resultado.listo:
        partes = _partes_columna(resultado.piezas)
        canto_m = resultado.canto_mm / 1000
        canto_compra = ceil(resultado.canto_mm * 1.1 / 1000)
        hoja = f"""
        <section class="hoja" id="resultado">
          <header class="hoja-cabeza">
            <div>
              <p class="kicker">Despiece para la maderería</p>
              <h2>{proyecto}</h2>
              <p>Teka HLF 824 G. El cuerpo publicado mide 79.8 × 59.5 × 52.5 cm. El hueco de esta hoja es el que escribiste.</p>
              {("<p class='ejemplo'>Ejemplo para ver el formato. 80 × 60 cm a 90 cm del piso no es el hueco de tu horno. No lo mandes a cortar.</p>" if ejemplo else "")}
            </div>
            <p class="exterior">Ancho exterior<br><strong>{texto_cm(resultado.ancho_exterior)} cm</strong></p>
          </header>
          {_svg(resultado.esquema)}
          <div class="partes">{partes}</div>
          <div class="compra">
            <section>
              <h3>Se lo pides a la maderería</h3>
              <ul>
                <li>{resultado.tableros_15} tableros de melamina {color} de {_cm_visible(datos.get('espesor'))} cm, hoja {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm. Es un estimado por área, con 15% de más. Ellos acomodan el corte.</li>
                <li>{resultado.tableros_fondo} tablero de {_cm_visible(datos.get('fondo_esp'))} cm para los fondos. Misma reserva.</li>
                <li>{canto_m:.2f} m de canto {color}. Pide {canto_compra} m para que alcance el desperdicio. Lo enchapán ahí.</li>
                <li>{resultado.bisagras} barrenos de cazoleta de 35 mm, solo en las dos puertas de abajo.</li>
                <li>La tapa de arriba no se barrena. Abre hacia arriba.</li>
                <li>Dos calados de 10 × 6 cm para ventilación, uno abajo del hueco y otro arriba, donde diga la hoja del horno.</li>
              </ul>
            </section>
            <section>
              <h3>Herraje, aparte del tablero</h3>
              <ul>
                <li>{resultado.bisagras} bisagras de cazoleta de 35 mm, cierre suave, para las puertas de abajo.</li>
                <li>2 bisagras de alzada y 1 par de pistones para la tapa. La tapa pesa cerca de {resultado.peso_tapa_kg} kg.</li>
                <li>2 jaladeras para las puertas y 1 perfil o jaladera para la tapa.</li>
                <li>Unos {resultado.confirmat} tornillos confirmat de 7 × 50 mm, más tarugos. Es una cuenta de armado, no una norma.</li>
                <li>Tapas de tornillo {color}.</li>
                <li>2 rejillas de 100 × 60 mm.</li>
              </ul>
              <p class="nota">En Home Depot Coapa del Hueso y Coapa Miramontes el pasillo de melamina trae cubrecanto y tapas de tornillo. Las bisagras de cazoleta y los pistones se consiguen en la maderería o en una ferretería de herraje. El cubrecanto Canplast de Home Depot es de 16 mm: en un tablero de 1.5 cm queda un poco ancho. Si la maderería enchapá, el canto lo pone ella.</p>
            </section>
          </div>
          <ul class="avisos">
            {''.join(f'<li>{escape(a)}</li>' for a in resultado.avisos)}
          </ul>
        </section>
        """
    else:
        mensajes = resultado.errores or resultado.avisos
        titulo = "Así no se arma el despiece" if resultado.errores else "El despiece espera el hueco"
        hoja = (
            f"<section class='espera' id='resultado'><h2>{titulo}</h2><ul>"
            + "".join(f"<li>{escape(m)}</li>" for m in mensajes)
            + "</ul></section>"
        )

    banner = ""
    if ejemplo:
        banner = """
        <p class="ejemplo">Ejemplo para ver el formato. 80 × 60 cm a 90 cm del piso no es el hueco de tu horno. No lo mandes a cortar.</p>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Despiece de melamina</title>
  <link rel="stylesheet" href="/estilo.css">
</head>
<body data-pieza="columna">
  <main>
    <header class="sitio">
      <h1>Muebles de melamina</h1>
      <p class="intro">Columna del horno Teka HLF 824 G. Abajo, un cajón con dos puertas. En medio, el hueco. Arriba, una tapa que abre hacia arriba. El dibujo cambia al escribir. Arrástralo para girarlo.</p>
      {_nav("columna")}
    </header>
    <div class="estudio">
    <div class="trabajo">
    <div id="banner">{banner}</div>
    <form method="get" action="/">
      <input type="hidden" name="pieza" value="columna">
      <input type="hidden" name="medidas" value="{escape(datos.get('medidas', ''))}">
      <input type="hidden" name="ejemplo" value="{escape(datos.get('ejemplo') or '')}">
      <div class="rejilla">
        <label class="ancho">
          <span>Nombre</span>
          <input name="proyecto" value="{escape(datos.get('proyecto') or '')}">
          <small>Sale en la hoja que llevas a cortar.</small>
        </label>
        <label>
          <span>Color</span>
          <input name="color" value="{color}">
          <small>Blanco en este primer mueble.</small>
        </label>
        {_campo(datos, 'alto', 'Alto de la columna', 'Del piso al techo del mueble, en cm. 210 cabe en la hoja.')}
        {_campo(datos, 'fondo', 'Fondo del cuerpo', 'Profundidad del mueble, en cm, sin la puerta.')}
        {_campo(datos, 'espesor', 'Espesor', '1.5 cm en este mueble. Se puede cambiar.')}
        {_campo(datos, 'fondo_esp', 'Espesor del fondo', '0.3 cm, detrás de los gabinetes cerrados.')}
        {_campo(datos, 'zoclo', 'Alto del zoclo', 'El hueco de las puertas empieza encima de esto.')}
        {_campo(datos, 'holgura', 'Holgura', 'Aire entre puertas y en el contorno, en cm.')}
        {_campo(datos, 'hueco_ancho', 'Ancho del hueco', 'Luz interior, en cm, entre los dos laterales.')}
        {_campo(datos, 'hueco_alto', 'Alto del hueco', 'Luz, en cm, entre el piso y el techo del horno.')}
        {_campo(datos, 'hueco_desde', 'El hueco empieza a', 'Centímetros del piso a la cara donde apoya el horno.')}
        {_campo(datos, 'hueco_fondo', 'Fondo que pide el horno', 'Opcional, en cm. Si lo dejas vacío, no se compara.')}
      </div>
      <div class="radios">
        <strong>Fondo</strong>
        <label><input type="radio" name="fondo_modo" value="clavado" {clavado}> Clavado por detrás</label>
        <label><input type="radio" name="fondo_modo" value="ranura" {ranura}> Metido en ranura</label>
      </div>
      <div class="acciones">
        <button type="submit">Armar despiece</button>
        <a class="boton claro" href="/?pieza=columna&ejemplo=1">Ver un ejemplo</a>
        <a class="boton claro" href="/?pieza=columna">Dejar el hueco en blanco</a>
        <button type="button" onclick="window.print()">Imprimir la hoja</button>
      </div>
    </form>
    {hoja}
    </div>
    <aside class="vista">
      <div class="vista-barra" id="vistas">
        <button type="button" data-vista="frente">Frente</button>
        <button type="button" data-vista="tres">Tres cuartos</button>
        <button type="button" data-vista="lado">Lado</button>
        <button type="button" id="editar" aria-pressed="false" title="Arrastra una cota para la proporción, o cambia los centímetros de cada pieza">Editar</button>
      </div>
      <canvas id="lienzo" aria-label="Vista del mueble"></canvas>
      <label class="abrir">
        <span>Abrir</span>
        <input id="apertura" type="range" min="0" max="100" value="0">
      </label>
      <p id="leyenda"></p>
      <p class="pista">Editar: arrastra una cota para cambiar el mueble con la misma proporción, o cambia solo los centímetros de cada pieza en el despiece. Arrastra para girar. La rueda acerca. Doble clic vuelve a la vista inicial.</p>
    </aside>
    </div>
  </main>
  <script src="/vista.js"></script>
</body>
</html>
"""


CAMPOS_BAJOS = (
    "proyecto",
    "tipo",
    "distribucion",
    "profundidad_esquina",
    "largo_pared_a",
    "largo_pared_b",
    "largo_pared_c",
    "altura_cubierta",
    "espesor_cubierta",
    "profundidad_cubierta",
    "vuelo_cubierta",
    "pasillo_libre",
    "altura_techo",
    "desnivel_piso",
    "observaciones_espacio",
    "color",
    "largo_barra",
    "fondo_barra",
    "largo_vuelta",
    "fondo_vuelta",
    "ancho_tarja",
    "puerta_vuelta",
    "alto_barra",
    "espesor",
    "fondo_esp",
    "zoclo",
    "zoclo_pie",
    "pino_esp",
    "marco_a_2",
    "marco_l_2",
    "ref_2",
    "marco_a_1",
    "marco_l_1",
    "ref_1",
    "holgura",
    "fondo_modo",
    "entre_desde",
    "medidas",
)

BAJOS = {
    "proyecto": "Barra en L",
    "tipo": "cocina",
    "distribucion": "l",
    "profundidad_esquina": "900",
    "largo_pared_a": "1690",
    "largo_pared_b": "1290",
    "largo_pared_c": "",
    "altura_cubierta": "900",
    "espesor_cubierta": "30",
    "profundidad_cubierta": "610",
    "vuelo_cubierta": "20",
    "pasillo_libre": "",
    "altura_techo": "",
    "desnivel_piso": "0",
    "observaciones_espacio": "",
    "color": "Blanco",
    "largo_barra": "1690",
    "fondo_barra": "610",
    "largo_vuelta": "1290",
    "fondo_vuelta": "590",
    "ancho_tarja": "1100",
    "puerta_vuelta": "590",
    "alto_barra": "800",
    "espesor": "15",
    "fondo_esp": "3",
    "zoclo": "100",
    "zoclo_pie": "100",
    "pino_esp": "20",
    "marco_a_2": "",
    "marco_l_2": "",
    "ref_2": "4",
    "marco_a_1": "",
    "marco_l_1": "",
    "ref_1": "4",
    "holgura": "3",
    "fondo_modo": "clavado",
    "entre_desde": "",
    "medidas": "",
}


def datos_bajos(query: dict) -> dict:
    datos = dict(BAJOS)
    for campo in CAMPOS_BAJOS:
        if campo in query:
            crudo = _texto_consulta(query, campo)
            datos[campo] = cm_a_mm(crudo) if campo in CAMPOS_CM_BAJOS else crudo
    return datos


def _svg_bajos(esq: dict) -> str:
    largo = esq["ancho"]
    vuelta = esq["fondo_total"]
    fondo_b = esq["fondo_barra"]
    grueso = esq["fondo_vuelta"]
    proy = esq["proyeccion"]
    escala = 460 / max(largo, vuelta, 1)
    mx, my = 56, 26

    def x(mm):
        return mx + mm * escala

    def y(mm):
        return my + mm * escala

    medio = grueso + esq["ancho_tarja"] / 2
    y_puerta = min(vuelta, fondo_b + esq["puerta_vuelta"])
    esquinero = (
        f'<rect x="{x(0):.1f}" y="{y(0):.1f}" width="{grueso * escala:.1f}" '
        f'height="{fondo_b * escala:.1f}" class="zoclo"/>'
        f'<text x="{x(grueso / 2):.1f}" y="{y(fondo_b / 2):.1f}" '
        f'text-anchor="middle">Esquinero</text>'
    )
    partes = [
        f'<g class="zona" data-modulo="tarja"><rect x="{x(grueso):.1f}" y="{y(0):.1f}" width="{esq["ancho_tarja"] * escala:.1f}" height="{fondo_b * escala:.1f}" class="caja"/>'
        f'<text x="{x(grueso + esq["ancho_tarja"] / 2):.1f}" y="{y(fondo_b / 2):.1f}" text-anchor="middle">Cajón 1</text></g>',
        f'<g class="zona" data-modulo="esquina">{esquinero}</g>',
        f'<g class="zona" data-modulo="vuelta"><rect x="{x(0):.1f}" y="{y(fondo_b):.1f}" width="{grueso * escala:.1f}" height="{proy * escala:.1f}" class="caja"/>'
        f'<text x="{x(grueso / 2):.1f}" y="{y(fondo_b + proy / 2):.1f}" text-anchor="middle">Cajón 2</text></g>',
        f'<line x1="{x(medio):.1f}" y1="{y(fondo_b):.1f}" x2="{x(medio):.1f}" y2="{y(fondo_b - min(fondo_b, 70)):.1f}" class="corte"/>',
        f'<line x1="{x(grueso):.1f}" y1="{y(fondo_b):.1f}" x2="{x(grueso):.1f}" y2="{y(y_puerta):.1f}" class="corte"/>',
        f'<text x="{x(largo / 2):.1f}" y="{y(0) - 8:.1f}" text-anchor="middle">{texto_cm(largo)} cm</text>',
        f'<text x="{x(0) - 8:.1f}" y="{y(vuelta / 2):.1f}" text-anchor="middle" transform="rotate(-90 {x(0) - 8:.1f} {y(vuelta / 2):.1f})">{texto_cm(vuelta)} cm</text>',
        f'<text x="{x(largo) + 8:.1f}" y="{y(fondo_b / 2):.1f}" text-anchor="start">{texto_cm(fondo_b)} cm ancho barra</text>',
        f'<line x1="{x(0) - 42:.1f}" y1="{y(fondo_b):.1f}" x2="{x(0) - 42:.1f}" y2="{y(fondo_b + proy):.1f}" class="corte"/>'
        f'<line x1="{x(0) - 47:.1f}" y1="{y(fondo_b):.1f}" x2="{x(0) - 37:.1f}" y2="{y(fondo_b):.1f}" class="corte"/>'
        f'<line x1="{x(0) - 47:.1f}" y1="{y(fondo_b + proy):.1f}" x2="{x(0) - 37:.1f}" y2="{y(fondo_b + proy):.1f}" class="corte"/>'
        f'<text x="{x(0) - 58:.1f}" y="{y(fondo_b + proy / 2):.1f}" text-anchor="middle" transform="rotate(-90 {x(0) - 58:.1f} {y(fondo_b + proy / 2):.1f})">{texto_cm(esq["puerta_vuelta"])} cm puerta cajón 2</text>',
        f'<text x="{x(grueso + 8):.1f}" y="{y(fondo_b) + 14:.1f}">90°</text>',
    ]
    vista_w = mx + largo * escala + 36
    vista_h = my + vuelta * escala + 28
    return (
        f'<svg viewBox="0 0 {vista_w:.0f} {vista_h:.0f}" role="img" aria-label="Planta de la barra en L">'
        + "".join(partes)
        + "</svg>"
    )


def _valor_parte(datos: dict, nombre: str, defecto: str = "") -> str:
    if nombre in datos and datos[nombre] is not None:
        return str(datos[nombre])
    return defecto


def _input_parte(datos: dict, esq: dict, nombre: str, etiqueta: str, ayuda: str, defecto: str = "", auto: str = "", centimetros: bool = True) -> str:
    sigue = bool(auto and esq and esq.get(auto))
    if sigue:
        valor = str(esq.get(nombre, ""))
        marca = ' data-auto="1"'
    else:
        valor = _valor_parte(datos, nombre, defecto)
        marca = ""
    if centimetros:
        valor = _cm_visible(valor)
    modo = "decimal" if centimetros else "numeric"
    paso = ' step="0.1"' if centimetros else ""
    return (
        "<label>"
        f"<span>{escape(etiqueta)}</span>"
        f'<input class="de-parte" form="plano" name="{escape(nombre)}" value="{escape(valor)}"{marca} '
        f'inputmode="{modo}"{paso} autocomplete="off">'
        f"<small>{escape(ayuda)}</small>"
        "</label>"
    )


def _solo_lectura(etiqueta: str, valor: str, ayuda: str) -> str:
    return (
        "<label>"
        f"<span>{escape(etiqueta)}</span>"
        f'<input value="{escape(valor)}" readonly tabindex="-1">'
        f"<small>{escape(ayuda)}</small>"
        "</label>"
    )


def _medidas_zoclo(datos: dict, esq: dict) -> str:
    return (
        '<div class="medidas-parte">'
        "<h4>Medidas del zoclo</h4>"
        + _input_parte(datos, esq, "zoclo", "Alto", "10 cm. Va dentro de los 80 cm de la barra.", "100")
        + _input_parte(datos, esq, "zoclo_pie", "Hueco del pie", "Centímetros libres al frente. 10 deja el marco atrás.", "100")
        + _input_parte(datos, esq, "pino_esp", "Espesor del pino", "De 0.8 a 4 cm. 2 es el de ahora. El refuerzo lo resta dos veces.", "20")
        + "<h4>Marco del cajón 2 y el esquinero</h4>"
        + _input_parte(
            datos, esq, "marco_l_2", "Largo",
            "Si lo cambias, se queda. Si lo borras, vuelve a salir del plano.",
            "", "marco_l_2_auto",
        )
        + _input_parte(datos, esq, "marco_a_2", "Ancho", "Sale del fondo interior menos 10 cm de espacio para los zapatos.", "", "marco_a_2_auto")
        + _input_parte(datos, esq, "ref_2", "Refuerzos", "Cuántos quieres. 4 es el de ahora. 0 es marco solo.", "4", centimetros=False)
        + "<h4>Marco del cajón 1</h4>"
        + _input_parte(
            datos, esq, "marco_l_1", "Largo",
            "Si lo cambias, se queda. Si lo borras, vuelve a salir del plano.",
            "", "marco_l_1_auto",
        )
        + _input_parte(datos, esq, "marco_a_1", "Ancho", "Sale del fondo interior menos 10 cm de espacio para los zapatos.", "", "marco_a_1_auto")
        + _input_parte(datos, esq, "ref_1", "Refuerzos", "Cuántos quieres. 4 es el de ahora. 0 es marco solo.", "4", centimetros=False)
        + "</div>"
    )


def _ficha_cajon1(esq: dict) -> str:
    alto = int(esq.get("alto", 800)) - int(esq.get("zoclo", 100))
    ancho = int(esq.get("ancho_tarja", 1100))
    fondo = int(esq.get("fondo_barra", 610))
    espesor = int(esq.get("espesor", 15))
    interior = ancho - 2 * espesor
    puerta_izq = (ancho - 3 * 30) // 2
    puerta_der = ancho - 3 * 30 - puerta_izq
    if esq:
        puertas = esq.get("puertas_tarja")
        if isinstance(puertas, (list, tuple)) and len(puertas) == 2:
            puerta_izq, puerta_der = int(puertas[0]), int(puertas[1])
    return (
        '<div class="ficha-carpintero ficha-cajon1">'
        '<div class="ficha-cabeza"><strong>CAJÓN 1 - 2 PUERTAS</strong><span>SIN TABLA SUPERIOR</span></div>'
        '<svg viewBox="0 0 640 260" role="img" aria-label="Plano de armado del cajón 1">'
        '<rect x="55" y="45" width="530" height="135" fill="#fffdf8" stroke="#1c1915" stroke-width="3"/>'
        '<rect x="55" y="45" width="28" height="135" fill="#ece4d6" stroke="#1c1915" stroke-width="2"/>'
        '<rect x="557" y="45" width="28" height="135" fill="#ece4d6" stroke="#1c1915" stroke-width="2"/>'
        '<line x1="320" y1="45" x2="320" y2="180" stroke="#8c3b2a" stroke-width="2"/>'
        '<text x="320" y="24" text-anchor="middle" fill="#8c3b2a" font-size="18" font-family="sans-serif">'
        f"{texto_cm(alto)} cm alto · {texto_cm(ancho)} cm frente</text>"
        '<text x="320" y="210" text-anchor="middle" fill="#8c3b2a" font-size="18" font-family="sans-serif">'
        f"{texto_cm(fondo)} cm fondo · melamina {texto_cm(espesor)} cm</text>"
        f'<text x="187" y="118" text-anchor="middle" font-size="16" font-family="sans-serif">{texto_cm(puerta_izq)} cm</text>'
        f'<text x="438" y="118" text-anchor="middle" font-size="16" font-family="sans-serif">{texto_cm(puerta_der)} cm</text>'
        '</svg>'
        '<div class="ficha-corte"><strong>ARMAR:</strong>'
        '<span>2 laterales <b>' + f"{texto_cm(alto)} x {texto_cm(fondo)} cm" + '</b></span>'
        '<span>Piso + entrepaño <b>-' + f"{texto_cm(interior)} x {texto_cm(fondo)} cm" + '</b></span>'
        '<span>2 puertas <b>' + f"{texto_cm(puerta_izq)} + {texto_cm(puerta_der)} cm" + '</b></span>'
        '<span><b>SIN TECHO / SIN TAPA</b></span>'
        '</div></div>'
    )


def _medidas_tarja(datos: dict, esq: dict) -> str:
    return (
        '<div class="medidas-parte">'
        "<h4>Medidas del cajón 1</h4>"
        + _input_parte(datos, esq, "fondo_barra", "Fondo", "61 cm. Es la profundidad del tramo largo.", "610")
        + _input_parte(datos, esq, "ancho_tarja", "Frente", "110 cm. Se parte en dos puertas.", "1100")
        + "</div>"
    )


def _medidas_vuelta(datos: dict, esq: dict) -> str:
    return (
        '<div class="medidas-parte">'
        "<h4>Medidas del cajón 2</h4>"
        + _input_parte(datos, esq, "fondo_vuelta", "Grueso", "59 cm. Es el ancho de ese lado.", "590")
        + _input_parte(datos, esq, "puerta_vuelta", "Puerta", "59 cm. Es el tablero, en la cara de adentro.", "590")
        + "</div>"
    )


def _medidas_esquina(datos: dict, esq: dict) -> str:
    if esq:
        frente = _cm_visible(esq.get("fondo_vuelta", ""))
        fondo = _cm_visible(esq.get("fondo_barra", ""))
    else:
        frente = _cm_visible(_valor_parte(datos, "fondo_vuelta", "590"))
        fondo = _cm_visible(_valor_parte(datos, "fondo_barra", "610"))
    return (
        '<div class="medidas-parte">'
        "<h4>Medidas del esquinero</h4>"
        + _solo_lectura("Frente", frente, "Es el grueso de la vuelta. Se cambia en el cajón 2.")
        + _solo_lectura("Fondo", fondo, "Es el fondo de la tarja. Se cambia en el cajón 1.")
        + _input_parte(datos, esq, "profundidad_esquina", "Profundidad", "90 cm en esta barra.", "900")
        + "</div>"
    )


def _ficha_union_esquina(esq: dict) -> str:
    alto = int(esq.get("alto_cajon") or max(int(esq.get("alto", 800)) - int(esq.get("zoclo", 100)), 0))
    vuelta = int(esq.get("puerta_vuelta", 590))
    fondo = int(esq.get("fondo_vuelta", 590))
    profundidad = int(esq.get("profundidad_esquina", 900))
    return (
        '<div class="ficha-carpintero ficha-union-esquina">'
        '<div class="ficha-cabeza"><strong>CAJÓN 2 + ESQUINERO</strong><span>2 MÓDULOS CONECTADOS</span></div>'
        '<svg viewBox="0 0 640 260" role="img" aria-label="Unión del cajón 2 y el esquinero">'
        '<rect x="70" y="45" width="220" height="150" fill="#fffdf8" stroke="#1c1915" stroke-width="3"/>'
        '<rect x="290" y="45" width="280" height="150" fill="#ece4d6" stroke="#1c1915" stroke-width="3"/>'
        '<line x1="290" y1="45" x2="290" y2="195" stroke="#8c3b2a" stroke-width="5"/>'
        '<text x="180" y="118" text-anchor="middle" font-size="18" font-family="sans-serif">CAJÓN 2</text>'
        '<text x="430" y="118" text-anchor="middle" font-size="18" font-family="sans-serif">ESQUINERO</text>'
        '<text x="180" y="145" text-anchor="middle" font-size="15" font-family="sans-serif">'
        f"{texto_cm(vuelta)} cm puerta · {texto_cm(alto)} cm alto</text>"
        '<text x="430" y="145" text-anchor="middle" font-size="15" font-family="sans-serif">'
        f"{texto_cm(profundidad)} cm profundo · SIN PUERTA</text>"
        '</svg>'
        '<div class="ficha-corte"><strong>UNIÓN:</strong>'
        '<span>Compartir <b>zoclo de pino</b></span>'
        '<span>Compartir <b>borde vertical</b></span>'
        '<span>CaJón 2 <b>1 puerta</b></span>'
        '<span>Esquinero <b>ciego, sin puerta</b></span>'
        '</div></div>'
    )


def _medidas_sueltas(datos: dict) -> str:
    return "".join(
        f'<section class="parte" data-modulo="{modulo}"><h3>{titulo}</h3>{html}</section>'
        for modulo, titulo, html in (
            ("zoclo", "1. Zoclo", _medidas_zoclo(datos, {})),
            ("tarja", "2. Cajón 1", _medidas_tarja(datos, {})),
            ("vuelta", "3. Cajón 2", _medidas_vuelta(datos, {})),
            ("esquina", "4. Esquinero", _medidas_esquina(datos, {})),
        )
    )


def render_bajos(datos: dict, resultado: Resultado) -> str:
    proyecto = escape(datos.get("proyecto") or "Bajos de tarja")
    color = escape(datos.get("color") or "Blanco")
    tipo = datos.get("tipo") or "cocina"
    modo = datos.get("fondo_modo") or "clavado"
    clavado = "checked" if modo != "ranura" else ""
    ranura = "checked" if modo == "ranura" else ""
    distribucion = datos.get("distribucion") or "l"

    def marca(valor):
        return "checked" if tipo == valor else ""

    def forma_marca(valor):
        return "checked" if distribucion == valor else ""

    if resultado.listo:
        por_modulo: dict[str, list] = {"zoclo": [], "tarja": [], "vuelta": [], "esquina": [], "otras": []}

        def modulo_de(nombre: str) -> str:
            n = nombre.lower()
            if n.startswith("zoclo"):
                return "zoclo"
            if "tarja" in n:
                return "tarja"
            if "vuelta" in n:
                return "vuelta"
            if "esquina" in n:
                return "esquina"
            return "otras"

        for pieza in resultado.piezas:
            por_modulo[modulo_de(pieza.nombre)].append(pieza)
        esq_med = resultado.esquema
        partes = "".join(
            (
                _parte(
                    "1. Zoclo",
                    "Dos marcos de pino, atrás. Al frente queda el hueco del pie. La medida ya cuenta el espesor. Aquí cambias el marco y cuántos refuerzos. El botón baja el PDF a Descargas.",
                    por_modulo["zoclo"],
                    "zoclo",
                    '<button type="button" class="mandar" data-carpintero="zoclo" title="Baja un PDF a la carpeta de Descargas">Mandar a carpintero</button>',
                    _medidas_zoclo(datos, esq_med),
                ),
                _parte(
                    "2. Cajón 1",
                    "El de la tarja, al frente, con dos puertas. Se sienta sobre su zoclo.",
                    por_modulo["tarja"],
                    "tarja",
                    "",
                    _medidas_tarja(datos, esq_med),
                    _ficha_cajon1(esq_med),
                ),
                _parte(
                    "3. Cajón 2",
                    "Módulo separado de la vuelta, con una puerta y el fijo de la punta. Se une al esquinero sin repetir el lateral común.",
                    por_modulo["vuelta"],
                    "vuelta",
                    "",
                    _medidas_vuelta(datos, esq_med),
                ),
                _parte(
                    "4. Esquinero",
                    "Módulo separado ciego, sin puerta. Se une al cajón 2 y aprovecha el espacio de la esquina sobre el mismo zoclo.",
                    por_modulo["esquina"],
                    "esquina",
                    "",
                    _medidas_esquina(datos, esq_med),
                    _ficha_union_esquina(esq_med),
                ),
                _parte("5. Otras piezas", "", por_modulo["otras"], "otras"),
            )
        )
        canto_m = resultado.canto_mm / 1000
        canto_compra = ceil(resultado.canto_mm * 1.1 / 1000)
        pino_mm = int(resultado.esquema.get("pino_mm", 0))
        pino_compra = ceil(pino_mm * 1.1 / 1000)
        puertas = sum(p.cantidad for p in resultado.piezas if p.nombre.startswith("Puerta"))
        esq = resultado.esquema
        hoja = f"""
        <section class="hoja" id="resultado">
          <header class="hoja-cabeza">
            <div>
              <p class="kicker">Despiece para la maderería</p>
              <h2>{proyecto}</h2>
              <p>La hoja va por partes. Primero el zoclo: dos marcos de pino que forman la L, con sus refuerzos. Después el cajón 1, el de la tarja. Después el cajón 2, el de la vuelta. Al final el esquinero, sin puerta. Toca una fila o el dibujo para ver qué tabla es.</p>
            </div>
            <p class="exterior">Planta<br><strong>{texto_cm(esq["ancho"])} × {texto_cm(esq["fondo_total"])} cm</strong></p>
          </header>
          {_svg_bajos(resultado.esquema)}
          <p class="pista-tabla">El ojo deja a la vista solo ese bloque. Otro ojo lo suma. El mismo ojo, otra vez, muestra todo. Toca una fila o el dibujo para ver qué tabla es.</p>
          <div class="partes">{partes}</div>
          <div class="compra">
            <section>
              <h3>Se lo pides a la maderería</h3>
              <ul>
                <li>{resultado.tableros_15} tableros de melamina {color} de {_cm_visible(datos.get('espesor'))} cm, hoja {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm. Es un estimado por área, con 15% de más.</li>
                <li>{pino_mm / 1000:.2f} m de pino de {texto_cm(esq.get("pino_esp", 20))} × {texto_cm(esq["zoclo"])} cm. Es el largo de los cortes del serrucho. Pide {pino_compra} m. El despiece da el rectángulo de afuera y el PDF trae cada corte. El pino no se cuenta en la melamina.</li>
                <li>{resultado.tableros_fondo} tablero de {_cm_visible(datos.get('fondo_esp'))} cm para los fondos. Misma reserva.</li>
                <li>{canto_m:.2f} m de canto {color}. Pide {canto_compra} m para el desperdicio. Lo enchapán ahí.</li>
                <li>{resultado.bisagras} barrenos de cazoleta de 35 mm, en las puertas. El fijo no se barrena.</li>
              </ul>
            </section>
            <section>
              <h3>Herraje, aparte del tablero</h3>
              <ul>
                <li>{resultado.bisagras} bisagras de cazoleta de 35 mm, cierre suave.</li>
                <li>{puertas} jaladeras, una por puerta.</li>
                <li>Unos {resultado.confirmat} tornillos confirmat de 7 × 50 mm, más tarugos, para los cajones. Es una cuenta de armado, no una norma.</li>
                <li>Tornillos para madera, para armar los marcos de pino.</li>
                <li>Tapas de tornillo {color}.</li>
              </ul>
              <p class="nota">La cubierta no entra en este corte. En Home Depot Coapa del Hueso y Coapa Miramontes hay cubrecanto y tapas de tornillo. Las bisagras se consiguen en la maderería o en una ferretería de herraje.</p>
            </section>
          </div>
          <ul class="avisos">
            {''.join(f'<li>{escape(a)}</li>' for a in resultado.avisos)}
          </ul>
        </section>
        """
    else:
        mensajes = resultado.errores or resultado.avisos
        titulo = "Así no se arma el despiece" if resultado.errores else "Este mueble sigue después"
        hoja = (
            f"<section class='espera' id='resultado'><h2>{titulo}</h2><ul>"
            + "".join(f"<li>{escape(m)}</li>" for m in mensajes)
            + "</ul><p>Las medidas de cada parte siguen aquí. Corrígelas y arma otra vez.</p>"
            + _medidas_sueltas(datos)
            + "</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Despiece de melamina</title>
  <link rel="stylesheet" href="/estilo.css">
</head>
<body data-pieza="bajos">
  <main>
    <header class="sitio">
      <h1>Muebles de melamina</h1>
      <p class="intro">Esta barra en L mide 169 cm al frente y 129 cm hacia el lado izquierdo por dentro. Tiene 61 cm de profundidad al frente, 59 cm de puerta en el cajón 2 y 80 cm de alto. El frente útil tiene 110 cm para las puertas. El esquinero mide 90 cm de profundidad.</p>
      {_nav("bajos")}
    </header>
    <div class="estudio">
    <div class="trabajo">
    <div id="banner"></div>
    <form id="plano" method="get" action="/">
      <input type="hidden" name="pieza" value="bajos">
      <input type="hidden" name="medidas" value="{escape(datos.get('medidas', ''))}">
      <h2 class="plano-titulo">Plano de la barra</h2>
      <p class="pista">Completa primero las medidas generales del espacio. Las medidas de los tableros van después, en cada módulo.</p>

      <fieldset class="grupo-medicion">
        <legend>1. Forma y uso del espacio</legend>
        <div class="forma-opciones">
          <label><input type="radio" name="distribucion" value="recta" {forma_marca("recta")}> <strong>Recta</strong><small>Un tramo lineal.</small></label>
          <label><input type="radio" name="distribucion" value="l" {forma_marca("l")}> <strong>En L</strong><small>Dos paredes perpendiculares.</small></label>
          <label><input type="radio" name="distribucion" value="u" {forma_marca("u")}> <strong>En U</strong><small>Tres frentes continuos.</small></label>
        </div>
        <div class="radios">
          <strong>Espacio</strong>
          <label><input type="radio" name="tipo" value="cocina" {marca("cocina")}> Cocina</label>
          <label><input type="radio" name="tipo" value="bano" {marca("bano")}> Baño</label>
          <label><input type="radio" name="tipo" value="closet" {marca("closet")}> Clóset</label>
        </div>
      </fieldset>

      <fieldset class="grupo-medicion">
        <legend>2. Medidas principales de esta barra en L</legend>
        <div class="rejilla">
          <div class="solo-distribucion solo-recta">
            {_campo(datos, 'largo_pared_a', 'Largo libre', 'Medir de pared a pared, por el piso.')}
          </div>
          <div class="solo-distribucion solo-l">
            {_campo(datos, 'largo_pared_a', 'Frente visto', '169 cm en esta barra. Medir de extremo a extremo en el frente.')}
            {_campo(datos, 'largo_pared_b', 'Lado izquierdo por dentro', '129 cm en esta barra. Medir desde la esquina hacia dentro.')}
          </div>
          <div class="solo-distribucion solo-u">
            {_campo(datos, 'largo_pared_a', 'Brazo izquierdo', 'Medir el tramo útil de izquierda a derecha.')}
            {_campo(datos, 'largo_pared_b', 'Tramo central', 'Medir entre las esquinas internas.')}
            {_campo(datos, 'largo_pared_c', 'Brazo derecho', 'Medir el tramo útil hasta la última pared.')}
          </div>
          {_campo(datos, 'alto_barra', 'Alto de la barra', '80 cm del piso terminado a la cara superior antes de la cubierta.')}
          {_campo(datos, 'fondo_barra', 'Profundidad frente', '61 cm para el lado frontal.')}
          {_campo(datos, 'fondo_vuelta', 'Profundidad lado izquierdo', '59 cm para el lado izquierdo visto desde el frente.')}
          {_campo(datos, 'ancho_tarja', 'Frente útil para puertas', '110 cm en el frente. En esta barra se reparten en dos puertas.')}
          {_campo(datos, 'profundidad_esquina', 'Profundidad del esquinero', '90 cm en esta barra.')}
        </div>
      </fieldset>

      <fieldset class="grupo-medicion">
        <legend>3. Medición complementaria del espacio</legend>
        <div class="rejilla">
          {_campo(datos, 'altura_techo', 'Altura al techo', 'Opcional. Medir del piso terminado al techo.')}
          {_campo(datos, 'desnivel_piso', 'Desnivel del piso', 'Diferencia entre los puntos más alto y bajo. 0 si está nivelado.')}
          {_campo(datos, 'pasillo_libre', 'Pasillo libre', 'Espacio útil frente a la barra. Mínimo recomendado: 107 cm para una persona.')}
          <label>
            <span>Detalles que deben respetarse</span>
            <input name="observaciones_espacio" value="{escape(datos.get('observaciones_espacio') or '')}" autocomplete="off">
            <small>Puertas, ventanas, enchufes, tuberías, gas, horno, refrigerador o columnas.</small>
          </label>
        </div>
      </fieldset>

      <fieldset class="grupo-medicion">
        <legend>4. Alturas y profundidades generales</legend>
        <div class="rejilla">
          <label>
            <span>Nombre del proyecto</span>
            <input name="proyecto" value="{proyecto}">
            <small>Sale en la hoja que llevas a cortar.</small>
          </label>
          <label>
            <span>Color</span>
            <input name="color" value="{color}">
            <small>Color visible de la melamina.</small>
          </label>
          {_campo(datos, 'altura_cubierta', 'Alto terminado de la cocina', 'Meta recomendada: 88–92 cm con piso y cubierta terminados.')}
          {_campo(datos, 'espesor_cubierta', 'Espesor de la cubierta', 'Medir o escoger la losa, tableta o granito.')}
          {_campo(datos, 'profundidad_cubierta', 'Profundidad de la cubierta', '55–62 cm según el frente de los módulos y el vuelo.')}
          {_campo(datos, 'vuelo_cubierta', 'Vuelo frontal', 'Cuánto sobresale la cubierta frente al tablero. 1–2 cm es habitual.')}
          {_campo(datos, 'espesor', 'Espesor de la melamina', '15 mm recomendado en el tablero de 1.5 cm.')}
          {_campo(datos, 'fondo_esp', 'Espesor del fondo', '3 mm recomendado para fondo clavado o ranurado.')}
          {_campo(datos, 'holgura', 'Holgura entre puertas', 'Aire lateral y superior. 3 mm es el punto de partida.')}
          {_campo(datos, 'entre_desde', 'Entrepaño desde el piso', 'Vacío: queda a la mitad. Si escribes, es la cara superior en cm.')}
        </div>
      </fieldset>

      <fieldset class="grupo-medicion">
        <legend>5. Construcción del cuerpo</legend>
        <div class="radios">
          <strong>Fondo</strong>
          <label><input type="radio" name="fondo_modo" value="clavado" {clavado}> Clavado por detrás</label>
          <label><input type="radio" name="fondo_modo" value="ranura" {ranura}> Metido en ranura</label>
        </div>
        <p class="pista">El largo de los módulos, el fondo de cada tramo, las puertas y el zoclo se ajustan en las secciones 5 a 8.</p>
      </fieldset>
      <div class="acciones">
        <button type="submit">Armar despiece</button>
        <button type="button" onclick="window.print()">Imprimir la hoja</button>
      </div>
    </form>
    {hoja}
    </div>
    <aside class="vista">
      <div class="vista-barra" id="vistas">
        <button type="button" data-vista="frente">Frente</button>
        <button type="button" data-vista="tres">Tres cuartos</button>
        <button type="button" data-vista="lado">Lado</button>
        <button type="button" id="editar" aria-pressed="false" title="Arrastra una cota para la proporción, o cambia los centímetros de cada pieza">Editar</button>
      </div>
      <button type="button" id="croquis-ojo" class="croquis-ojo" aria-pressed="true" aria-controls="croquis-plano" title="Ocultar o mostrar el plano con cotas">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path fill="none" stroke="currentColor" stroke-width="1.8" d="M2 12s4-6.5 10-6.5S22 12 22 12s-4 6.5-10 6.5S2 12 2 12z"/>
          <circle cx="12" cy="12" r="2.5" fill="currentColor"/>
        </svg>
        Plano con cotas
      </button>
      <div id="croquis-plano" class="croquis-plano">
        <div class="croquis-cabeza">
          <strong>Plano con cotas</strong>
          <small>Se actualiza al cambiar las medidas.</small>
        </div>
        <svg id="croquis-svg" viewBox="0 0 700 590" role="img" aria-label="Plano en planta de la barra con cotas"></svg>
      </div>
      <div class="modulos" id="modulos">
        <span class="con-ojo">{_ojo("zoclo", "el zoclo")}<button type="button" data-modulo="zoclo">Zoclo</button></span>
        <span class="con-ojo">{_ojo("tarja", "el cajón 1")}<button type="button" data-modulo="tarja">Cajón 1</button></span>
        <span class="con-ojo">{_ojo("vuelta", "el cajón 2")}<button type="button" data-modulo="vuelta">Cajón 2</button></span>
        <span class="con-ojo">{_ojo("esquina", "el esquinero")}<button type="button" data-modulo="esquina">Esquinero</button></span>
      </div>
      <canvas id="lienzo" aria-label="Vista del mueble"></canvas>
      <label class="abrir">
        <span>Abrir</span>
        <input id="apertura" type="range" min="0" max="100" value="28">
      </label>
      <p id="ficha">Toca un mueble, una tabla del dibujo o una fila del despiece.</p>
      <p id="leyenda"></p>
      <p class="pista">Editar: arrastra una cota para cambiar todo el mueble con la misma proporción, o cambia solo los centímetros de cada pieza en el despiece. Esa medida ya incluye el espesor. El ojo deja solo ese bloque. El botón del zoclo baja el PDF a Descargas. Arrastra para girar. Un clic marca la tabla.</p>
    </aside>
    </div>
  </main>
  <script src="/vista.js"></script>
</body>
</html>
"""


CAMPOS_CM_LAVA = (
    "alto",
    "hueco_ancho",
    "hueco_alto",
    "fondo",
    "espesor",
    "fondo_esp",
    "repisa_fondo",
)

CAMPOS_LAVA = (
    "proyecto",
    "color",
    "alto",
    "hueco_ancho",
    "hueco_alto",
    "fondo",
    "espesor",
    "fondo_esp",
    "repisa_fondo",
    "repisas",
    "posiciones",
    "medidas",
)

LAVA = {
    "proyecto": "Lavavajillas con entrepaños",
    "color": "Blanco Frosty",
    "alto": str(LAVA_ALTO_MUEBLE),
    "hueco_ancho": "610",
    "hueco_alto": str(LAVA_HUECO_ALTO),
    "fondo": "610",
    "espesor": "16",
    "fondo_esp": "3",
    "repisa_fondo": "",
    "repisas": "2",
    "posiciones": "",
    "medidas": "",
}


def datos_lavavajillas(query: dict) -> dict:
    datos = dict(LAVA)
    for campo in CAMPOS_LAVA:
        if campo in query:
            crudo = _texto_consulta(query, campo)
            datos[campo] = cm_a_mm(crudo) if campo in CAMPOS_CM_LAVA else crudo
    return datos


def _svg_lava(esq: dict) -> str:
    alto = esq["alto"]
    ancho = esq["ancho"]
    e = esq["espesor"]
    claro = esq["hueco_ancho"]
    hueco = esq["hueco_alto"]
    posiciones = [int(p) for p in esq.get("posiciones") or []]
    escala = 520 / max(alto, 1)
    mx, my = 86, 28

    def y(mm):
        return my + (alto - mm) * escala

    def x(mm):
        return mx + mm * escala

    partes = [
        f'<rect x="{x(0):.1f}" y="{y(alto):.1f}" width="{e * escala:.1f}" height="{alto * escala:.1f}" class="caja"/>',
        f'<rect x="{x(ancho - e):.1f}" y="{y(alto):.1f}" width="{e * escala:.1f}" height="{alto * escala:.1f}" class="caja"/>',
        f'<rect x="{x(e):.1f}" y="{y(hueco):.1f}" width="{claro * escala:.1f}" height="{hueco * escala:.1f}" class="hueco"/>',
        f'<rect x="{x(e):.1f}" y="{y(hueco + e):.1f}" width="{claro * escala:.1f}" height="{e * escala:.1f}" class="tapa"/>',
        f'<rect x="{x(e):.1f}" y="{y(alto):.1f}" width="{claro * escala:.1f}" height="{e * escala:.1f}" class="tapa"/>',
    ]
    y_piso = hueco + e
    y_techo = alto - e
    for cursor in posiciones:
        partes.append(
            f'<rect x="{x(e):.1f}" y="{y(cursor + e):.1f}" width="{claro * escala:.1f}" height="{e * escala:.1f}" class="entre"/>'
        )
    partes.append(
        f'<text x="{x(ancho / 2):.1f}" y="{y(hueco / 2) + 4:.1f}" text-anchor="middle">lavavajillas</text>'
    )
    partes.append(
        f'<text x="{x(ancho / 2):.1f}" y="{y((y_piso + y_techo) / 2) + 4:.1f}" text-anchor="middle">entrepaños</text>'
    )
    partes.append(
        f'<text x="{x(ancho / 2):.1f}" y="{y(0) + 16:.1f}" text-anchor="middle">{texto_cm(ancho)} cm por fuera</text>'
    )
    partes.append(
        f'<text x="{x(0) - 10:.1f}" y="{y(alto / 2):.1f}" text-anchor="end" transform="rotate(-90 {x(0) - 10:.1f} {y(alto / 2):.1f})">{texto_cm(alto)} cm</text>'
    )
    vista_w = mx + ancho * escala + 36
    vista_h = my + alto * escala + 28
    return (
        f'<svg viewBox="0 0 {vista_w:.0f} {vista_h:.0f}" role="img" aria-label="Frente del lavavajillas con entrepaños">'
        + "".join(partes)
        + "</svg>"
        + _svg_hoyo(esq)
    )


def _svg_hoyo(esq: dict) -> str:
    fondo = int(esq["fondo"])
    visto = 480
    escala = 280 / max(fondo, 1)
    mx, my = 78, 36

    def x(mm):
        return mx + mm * escala

    def y(mm):
        return my + (visto - mm) * escala

    radio = LAVA_HOYO / 2 * escala
    partes = [
        '<text x="8" y="18" font-size="15" font-weight="700">Lateral izquierdo</text>',
        f'<rect x="{mx:.1f}" y="{y(visto):.1f}" width="{fondo * escala:.1f}" height="{visto * escala:.1f}" class="caja"/>',
        f'<circle cx="{x(LAVA_HOYO_ATRAS):.1f}" cy="{y(LAVA_HOYO_PISO):.1f}" r="{radio:.1f}" class="hueco"/>',
        f'<text x="{x(LAVA_HOYO_ATRAS) + radio + 8:.1f}" y="{y(LAVA_HOYO_PISO) + 4:.1f}" font-size="13">{texto_cm(LAVA_HOYO)} cm</text>',
        f'<text x="8" y="{y(LAVA_HOYO_PISO) + 4:.1f}" font-size="13">{texto_cm(LAVA_HOYO_PISO)} cm</text>',
        f'<text x="{mx:.0f}" y="{y(0) + 16:.1f}" font-size="12">atrás</text>',
        f'<text x="{x(fondo) - 42:.1f}" y="{y(0) + 16:.1f}" font-size="12">frente</text>',
        f'<text x="{x(LAVA_HOYO_ATRAS):.1f}" y="{y(0) + 34:.1f}" font-size="13">{texto_cm(LAVA_HOYO_ATRAS)} cm de atrás</text>',
    ]
    vista_w = mx + fondo * escala + 70
    vista_h = my + visto * escala + 46
    return (
        f'<svg viewBox="0 0 {vista_w:.0f} {vista_h:.0f}" role="img" aria-label="Lateral izquierdo con el hoyo">'
        + "".join(partes)
        + "</svg>"
    )


def _svg_corte(piezas: list) -> str:
    hojas = cortes_lavavajillas(piezas)
    if not hojas:
        return ""
    nombres = {
        "Lateral lavavajillas": "Lateral",
        "Lateral": "Lateral",
        "Techo lavavajillas": "Techo hueco",
        "Techo entrepaños": "Techo arriba",
        "Entrepaño": "Entrepaño",
    }
    bloques = ['<p class="pista">Así caen en la hoja de 122 × 244 cm. La raya es el frente.</p>']
    for indice, hoja in enumerate(hojas, start=1):
        figs = [
            f'<text x="12" y="52" font-size="48" font-weight="700">Hoja {indice}</text>',
            '<rect x="70" y="80" width="1220" height="2440" fill="#e4e6e8" stroke="#1c1915" stroke-width="4"/>',
        ]
        for pieza in hoja:
            x = 70 + pieza["x"]
            y = 80 + (2440 - pieza["y"] - pieza["h"])
            w, h = pieza["w"], pieza["h"]
            nombre = nombres.get(pieza["nombre"], pieza["nombre"])
            medida = f"{texto_cm(max(w, h))} x {texto_cm(min(w, h))}"
            figs.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="#1c1915" stroke-width="4"/>'
            )
            figs.append(f'<text x="{x + 18}" y="{y + 64}" font-size="40" font-weight="700">{nombre}</text>')
            figs.append(f'<text x="{x + 18}" y="{y + 112}" font-size="32">{medida}</text>')
            if pieza["frente"] == "lado":
                figs.append(
                    f'<line x1="{x + w}" y1="{y + 12}" x2="{x + w}" y2="{y + h - 12}" stroke="#8c3b2a" stroke-width="8"/>'
                )
            else:
                figs.append(
                    f'<line x1="{x + 12}" y1="{y + h}" x2="{x + w - 12}" y2="{y + h}" stroke="#8c3b2a" stroke-width="8"/>'
                )
        derechos = [pieza for pieza in hoja if pieza["x"] > 0]
        if derechos:
            tope = max(pieza["y"] + pieza["h"] for pieza in derechos)
            if 2440 - tope > 200:
                sx = 70 + derechos[0]["x"] + 24
                sy = 80 + (2440 - tope) / 2
                figs.append(f'<text x="{sx:.0f}" y="{sy:.0f}" font-size="40" fill="#5c5348">sobra</text>')
        bloques.append(
            f'<svg viewBox="0 0 1400 2580" role="img" aria-label="Hoja {indice} del corte">'
            + "".join(figs)
            + "</svg>"
        )
    return "".join(bloques)


def render_lavavajillas(datos: dict, resultado: Resultado) -> str:
    proyecto = escape(datos.get("proyecto") or "Cajón lavavajillas")
    color = escape(datos.get("color") or "Blanco")
    repisa_src = datos.get("repisa_fondo") or ""
    repisa_auto = False
    if resultado.listo and str(repisa_src).strip() == "":
        repisa_src = str(resultado.esquema["fondo_repisa"])
        repisa_auto = True
    repisa_marca = ' data-auto="1"' if repisa_auto else ""
    repisa_visible = escape(_cm_visible(repisa_src))
    repisas_visible = escape(str(datos.get("repisas") or "2"))
    pos_src = str(datos.get("posiciones") or "")
    pos_auto = False
    if resultado.listo and pos_src.strip() == "":
        pos_src = "; ".join(texto_cm(p) for p in resultado.esquema.get("posiciones") or [])
        pos_auto = True
    pos_marca = ' data-auto="1"' if pos_auto else ""
    pos_visible = escape(pos_src)
    if resultado.listo:
        cajon = [p for p in resultado.piezas if p.nombre in ("Lateral lavavajillas", "Techo lavavajillas")]
        arriba = [p for p in resultado.piezas if p not in cajon]
        partes = _parte(
            "Cajón del lavavajillas",
            "Dos laterales de piso a techo y el techo del hueco. El aparato se sienta en el piso.",
            cajon,
            modulo="cajon",
            con_ojo=False,
        ) + _parte(
            "Entrepaños",
            "El mueble de arriba: techo, entrepaños y el respaldo. Los entrepaños van sueltos, para moverlos.",
            arriba,
            modulo="repisa",
            con_ojo=False,
        )
        canto_m = resultado.canto_mm / 1000
        canto_compra = ceil(resultado.canto_mm * 1.1 / 1000)
        esq = resultado.esquema
        hoja = f"""
        <section class="hoja" id="resultado">
          <header class="hoja-cabeza">
            <div>
              <p class="kicker">Despiece para el carpintero</p>
              <h2>{proyecto}</h2>
              <p><button type="button" class="mandar" data-carpintero="lavavajillas">Mandar a carpintero</button>
              <button type="button" class="mandar" data-carpintero="corte">Corte de maderería</button></p>
              <p>Mueble de {texto_cm(esq["alto"])} cm. Hueco del lavavajillas {texto_cm(esq["hueco_ancho"])} × {texto_cm(esq["hueco_alto"])} × {texto_cm(esq["fondo"])} cm. Arriba, {esq["repisas"]} entrepaños a {texto_cm(esq["fondo_repisa"])} cm de fondo, en alturas distintas. El aparato no se corta.</p>
            </div>
            <p class="exterior">Ancho exterior<br><strong>{texto_cm(resultado.ancho_exterior)} cm</strong></p>
          </header>
          {_svg_lava(esq)}
          {_svg_corte(resultado.piezas)}
          <p class="pista">Los laterales son de una pieza, del piso a los {texto_cm(esq["alto"])} cm. Los entrepaños no van atornillados: se mueven en las hileras. De partida quedan a {"; ".join(texto_cm(p) for p in esq.get("posiciones") or [])} cm del piso.</p>
          <div class="partes">{partes}</div>
          <div class="compra">
            <section>
              <h3>Se lo pides a la maderería</h3>
              <ul>
                <li>{resultado.tableros_15} tableros de melamina {color} de {_cm_visible(datos.get("espesor"))} cm, hoja {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm. Modelo 717863: aglomerado recubierto, acabado mate liso. Pide la hoja completa, sin orillas recortadas.</li>
                <li>{resultado.tableros_fondo} tablero de {_cm_visible(datos.get("fondo_esp"))} cm para el respaldo de los entrepaños. Detrás del lavavajillas no lleva.</li>
                <li>{canto_m:.2f} m de canto {color}. Pide {canto_compra} m para que alcance el desperdicio. Lo enchapán ahí. El canto va en el frente de los laterales, de los techos y de los entrepaños.</li>
                <li>El hoyo de {texto_cm(LAVA_HOYO)} cm no se hace en la maderería. Va en el lateral izquierdo, a {texto_cm(LAVA_HOYO_PISO)} cm del piso y a {texto_cm(LAVA_HOYO_ATRAS)} cm de atrás. Se barrena al armar.</li>
              </ul>
            </section>
            <section>
              <h3>Herraje, aparte del tablero</h3>
              <ul>
                <li>Unos {resultado.confirmat} tornillos confirmat de 7 × 50 mm, solo en los dos techos. Los entrepaños no van atornillados.</li>
                <li>2 escuadras para anclar el techo de arriba al muro.</li>
                <li>Cinta de aluminio para la cara de abajo del techo del hueco, si el aparato no trae barrera de vapor.</li>
                <li>Tornillos cortos para fijar el aparato a ese techo. No deben atravesar los {texto_cm(esq["espesor"])} cm.</li>
                <li>{esq.get("soportes", 0)} soportes de entrepaño, cuatro por tabla, para poder moverlos de hilera.</li>
                <li>Clavos o tornillos cortos para el respaldo.</li>
                <li>Tapas de tornillo {color}.</li>
                <li>Este mueble no lleva puertas, así que no se barrenan cazoletas.</li>
              </ul>
              <p class="nota">La tabla de este mueble es el tablero de melamina de {texto_cm(HOJA_ANCHO)} × {texto_cm(HOJA_LARGO)} cm y 16 mm, Blanco Frosty, modelo 717863. El cubrecanto de 16 mm queda al espesor del tablero. En Home Depot Coapa del Hueso y Coapa Miramontes hay cubrecanto y tapas de tornillo. Aquí no hay precio ni existencia.</p>
            </section>
          </div>
          <ul class="avisos">
            {''.join(f'<li>{escape(a)}</li>' for a in resultado.avisos)}
          </ul>
        </section>
        """
    else:
        mensajes = resultado.errores or resultado.avisos
        hoja = (
            "<section class='espera' id='resultado'><h2>Así no se arma el despiece</h2><ul>"
            + "".join(f"<li>{escape(m)}</li>" for m in mensajes)
            + "</ul></section>"
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Despiece de melamina</title>
  <link rel="stylesheet" href="/estilo.css">
</head>
<body data-pieza="lavavajillas">
  <main>
    <header class="sitio">
      <h1>Muebles de melamina</h1>
      <p class="intro">Cajón del lavavajillas LDP6810SS, con entrepaños arriba. El hueco de partida queda a {texto_cm(LAVA_HUECO_ALTO)} cm: el corte pide al menos {texto_cm(LAVA_CORTE_ALTO)}. El aparato se sienta en el piso, sin zócalo. Los entrepaños van sueltos y 0.2 cm más angostos que el hueco, para moverlos. La tabla es melamina Blanco Frosty de 16 mm, hoja de 122 × 244 cm, modelo 717863. Los laterales miden 244 cm, el largo completo de la hoja. Va aparte de la barra de 80 cm.</p>
      {_nav("lavavajillas")}
    </header>
    <div class="estudio">
    <div class="trabajo">
    <div id="banner"></div>
    <form method="get" action="/">
      <input type="hidden" name="pieza" value="lavavajillas">
      <input type="hidden" name="medidas" value="{escape(datos.get('medidas', ''))}">
      <div class="rejilla">
        <label class="ancho">
          <span>Nombre</span>
          <input name="proyecto" value="{proyecto}">
          <small>Sale en la hoja que llevas a cortar.</small>
        </label>
        <label>
          <span>Color</span>
          <input name="color" value="{color}">
          <small>Blanco Frosty, modelo 717863. Acabado mate liso.</small>
        </label>
        {_campo(datos, 'alto', 'Alto del mueble', 'Del piso al techo, en cm. 244 es el largo completo de la hoja.')}
        {_campo(datos, 'hueco_ancho', 'Ancho del hueco', 'Luz entre los laterales, en cm. El manual pide al menos 61.')}
        {_campo(datos, 'hueco_alto', 'Alto del hueco', f'Del piso al bajo del techo del lavavajillas, en cm. El corte pide al menos {texto_cm(LAVA_CORTE_ALTO)}. Este plano usa {texto_cm(LAVA_HUECO_ALTO)}.')}
        {_campo(datos, 'fondo', 'Fondo del cajón', 'Profundidad de los laterales, en cm. El manual pide al menos 61.')}
        {_campo(datos, 'espesor', 'Espesor', '1.6 cm. Es el tablero de 16 mm del modelo 717863.')}
        {_campo(datos, 'fondo_esp', 'Espesor del respaldo', '0.3 cm. Solo va detrás de los entrepaños.')}
        <label>
          <span>Fondo de los entrepaños</span>
          <input name="repisa_fondo" value="{repisa_visible}" inputmode="decimal" step="0.1" autocomplete="off"{repisa_marca}>
          <small>Vacío: sale de la tira que sobra al lado del lateral. Con el fondo de 61 cm esa tira es de 60.6 cm.</small>
        </label>
        <label>
          <span>Entrepaños</span>
          <input name="repisas" value="{repisas_visible}" inputmode="numeric" step="1" autocomplete="off">
          <small>Cuántas tablas sueltas van arriba del lavavajillas, de 0 a 6.</small>
        </label>
        <label class="ancho">
          <span>Posiciones</span>
          <input name="posiciones" value="{pos_visible}" autocomplete="off"{pos_marca}>
          <small>Del piso a la cara de abajo de cada entrepaño, en cm, separadas con punto y coma. Vacío: quedan en alturas distintas y se pueden mover de hilera.</small>
        </label>
      </div>
      <div class="acciones">
        <button type="submit">Armar despiece</button>
        <button type="button" onclick="window.print()">Imprimir la hoja</button>
      </div>
    </form>
    {hoja}
    </div>
    <aside class="vista">
      <div class="vista-barra" id="vistas">
        <button type="button" data-vista="frente">Frente</button>
        <button type="button" data-vista="tres">Tres cuartos</button>
        <button type="button" data-vista="lado">Lado</button>
        <button type="button" id="editar" aria-pressed="false" title="Arrastra una cota para la proporción, o cambia los centímetros de cada pieza">Editar</button>
      </div>
      <canvas id="lienzo" aria-label="Vista del lavavajillas con repisas"></canvas>
      <label class="abrir">
        <span>Abrir</span>
        <input id="apertura" type="range" min="0" max="100" value="0">
      </label>
      <p id="ficha">Toca una tabla del dibujo o una fila del despiece.</p>
      <p id="leyenda"></p>
      <p class="pista">Editar: arrastra una cota para cambiar el mueble con la misma proporción, o cambia solo los centímetros de cada pieza. El aparato gris no se corta. Arrastra para girar. La rueda acerca.</p>
    </aside>
    </div>
  </main>
  <script src="/vista.js"></script>
</body>
</html>
"""


def responder(query: dict, ejemplo: bool = False, pieza: str = "bajos") -> str:
    if pieza == "lavavajillas":
        datos = datos_lavavajillas(query)
        return render_lavavajillas(datos, calcular_lavavajillas(datos))
    if pieza == "columna" or ejemplo:
        datos = datos_de_consulta(query, ejemplo=ejemplo)
        return render(datos, calcular_columna(datos))
    datos = datos_bajos(query)
    return render_bajos(datos, calcular_bajos(datos))
