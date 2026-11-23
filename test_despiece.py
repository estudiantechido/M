import json
import unittest
from urllib.parse import parse_qs

from despiece import (
    LAVA_HUECO_ALTO,
    calcular_bajos,
    calcular_columna,
    calcular_lavavajillas,
    cm_a_mm,
    cortes_carpintero,
    texto_cm,
)
from pagina import datos_bajos, datos_de_consulta, datos_lavavajillas, render, render_bajos, render_lavavajillas, responder
from despiece import acomodar_melamina, cortes_lavavajillas
from pdf_corte import pdf_corte
from pdf_lava import pdf_lavavajillas
from pdf_zoclo import colocar_marcos, pdf_zoclo


def base(**extra):
    datos = {
        "alto": "2100",
        "fondo": "580",
        "espesor": "15",
        "fondo_esp": "3",
        "zoclo": "100",
        "holgura": "3",
        "color": "Blanco",
        "fondo_modo": "clavado",
        "hueco_ancho": "800",
        "hueco_alto": "600",
        "hueco_desde": "900",
    }
    datos.update(extra)
    return datos


class ColumnaHorno(unittest.TestCase):
    def test_medidas_no_finitas_se_tratan_como_entrada_invalida(self):
        for valor in ("nan", "inf", "-inf"):
            resultado = calcular_columna(base(alto=valor))
            self.assertFalse(resultado.listo)
            self.assertTrue(any("alto de la columna" in error for error in resultado.errores))

    def test_sin_hueco_no_inventa_piezas(self):
        datos = base()
        datos["hueco_ancho"] = ""
        datos["hueco_alto"] = ""
        datos["hueco_desde"] = ""
        resultado = calcular_columna(datos)
        self.assertFalse(resultado.listo)
        self.assertEqual(resultado.errores, [])
        self.assertEqual(resultado.piezas, [])

    def test_medidas_del_ejemplo(self):
        resultado = calcular_columna(base())
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 830)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual((por_nombre["Lateral"].alto, por_nombre["Lateral"].ancho, por_nombre["Lateral"].cantidad), (2100, 580, 2))
        self.assertEqual((por_nombre["Piso del horno"].alto, por_nombre["Piso del horno"].ancho), (800, 580))
        self.assertEqual((por_nombre["Puerta inferior izquierda"].alto, por_nombre["Puerta inferior izquierda"].ancho), (794, 411))
        self.assertEqual(por_nombre["Puerta inferior derecha"].ancho, 410)
        self.assertEqual((por_nombre["Tapa superior"].alto, por_nombre["Tapa superior"].ancho), (594, 824))
        self.assertEqual((por_nombre["Zoclo frontal"].alto, por_nombre["Zoclo frontal"].ancho), (800, 100))
        self.assertEqual((por_nombre["Fondo del cajón inferior"].alto, por_nombre["Fondo del cajón inferior"].ancho), (766, 796))
        self.assertEqual(resultado.canto_mm, 15854)
        self.assertEqual(resultado.tableros_15, 3)
        self.assertEqual(resultado.tableros_fondo, 1)
        self.assertEqual(resultado.bisagras, 4)
        self.assertEqual(resultado.peso_tapa_kg, 4.8)
        self.assertTrue(all(p.cabe() for p in resultado.piezas))
        self.assertIn("No barrenar cazoleta", por_nombre["Tapa superior"].notas)

    def test_lateral_mas_largo_que_la_hoja(self):
        resultado = calcular_columna(base(alto="2500", hueco_desde="1000"))
        self.assertFalse(resultado.listo)
        self.assertTrue(any("244 cm" in e for e in resultado.errores))

    def test_hueco_mas_ancho_que_la_hoja(self):
        resultado = calcular_columna(base(hueco_ancho="1300"))
        self.assertFalse(resultado.listo)
        self.assertTrue(any("122 cm" in e for e in resultado.errores))

    def test_ranura_achica_el_entrepanio_y_agranda_el_fondo(self):
        resultado = calcular_columna(base(fondo_modo="ranura"))
        self.assertTrue(resultado.listo, resultado.errores)
        piso = next(p for p in resultado.piezas if p.nombre == "Piso del horno")
        fondo = next(p for p in resultado.piezas if p.nombre == "Fondo del cajón inferior")
        self.assertEqual(piso.ancho, 570)
        self.assertEqual((fondo.alto, fondo.ancho), (778, 808))

    def test_hueco_menor_que_el_cuerpo_se_calcula_y_avisa(self):
        resultado = calcular_columna(base(hueco_ancho="760"))
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 790)
        self.assertTrue(any("más angosto" in a for a in resultado.avisos))

    def test_parametro_vacio_no_restaura_el_valor_predeterminado(self):
        datos = datos_de_consulta(parse_qs("alto=", keep_blank_values=True))
        self.assertEqual(datos["alto"], "")


def bajos(**extra):
    datos = {
        "tipo": "cocina",
        "distribucion": "l",
        "profundidad_esquina": "900",
        "color": "Blanco",
        "espesor": "15",
        "fondo_esp": "3",
        "zoclo": "100",
        "holgura": "3",
        "fondo_modo": "clavado",
        "largo_barra": "1690",
        "fondo_barra": "610",
        "largo_vuelta": "1290",
        "fondo_vuelta": "590",
        "ancho_tarja": "1100",
        "puerta_vuelta": "590",
        "alto_barra": "800",
        "entre_desde": "",
    }
    datos.update(extra)
    return datos


class BajosTarja(unittest.TestCase):
    def test_medidas_principales_de_la_barra_en_l(self):
        resultado = calcular_bajos(bajos())
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.esquema["distribucion"], "l")
        self.assertEqual(resultado.esquema["largo_barra"], 1690)
        self.assertEqual(resultado.esquema["fondo_total"], 1290)
        self.assertEqual(resultado.esquema["fondo_barra"], 610)
        self.assertEqual(resultado.esquema["fondo_vuelta"], 590)
        self.assertEqual(resultado.esquema["ancho_tarja"], 1100)
        self.assertEqual(resultado.esquema["alto"], 800)
        self.assertEqual(resultado.esquema["profundidad_esquina"], 900)
        html = render_bajos(bajos(), resultado)
        self.assertIn("Frente visto", html)
        self.assertIn("Lado izquierdo por dentro", html)

    def test_el_plano_en_vivo_tiene_un_ojo_y_cotas(self):
        resultado = calcular_bajos(bajos())
        html = render_bajos(bajos(), resultado)
        self.assertIn('id="croquis-ojo"', html)
        self.assertIn('aria-controls="croquis-plano"', html)
        self.assertIn('id="croquis-plano"', html)
        self.assertIn('id="croquis-svg"', html)
        self.assertIn('id="croquis-ojo" class="croquis-ojo" aria-pressed="true"', html)
        self.assertIn('<div id="croquis-plano" class="croquis-plano">', html)
        self.assertNotIn("Esquinero 45°", html)
        self.assertNotIn("<polygon", html)
        with open("vista.js", "r", encoding="utf-8") as archivo:
            javascript = archivo.read()
        self.assertIn('const paredA = entero("largo_pared_a")', javascript)
        self.assertIn('const paredB = entero("largo_pared_b")', javascript)
        self.assertIn("getClientRects()", javascript)
        with open("vista.js", "r", encoding="utf-8") as archivo:
            javascript = archivo.read()
        self.assertIn("puerta cajón 2", javascript)
        self.assertIn("mx - 72", javascript)
        self.assertIn("mx - 42", javascript)
        with open("vista.js", "r", encoding="utf-8") as archivo:
            javascript = archivo.read()
        self.assertIn("cm lado izquierdo", javascript)

    def test_estructura_del_espacio_recta_l_y_u(self):
        html = render_bajos(bajos(), calcular_bajos(bajos()))
        formulario = html.split("<form", 1)[1].split("</form>", 1)[0]
        self.assertIn("1. Forma y uso del espacio", formulario)
        self.assertIn('name="distribucion" value="recta"', formulario)
        self.assertIn('name="distribucion" value="l"', formulario)
        self.assertIn('name="distribucion" value="u"', formulario)
        self.assertIn('name="altura_cubierta"', formulario)
        self.assertIn('name="pasillo_libre"', formulario)
        self.assertIn('name="observaciones_espacio"', formulario)

    def test_distribuciones_recta_y_u_se_registran_sin_cortes_ficticios(self):
        for distribucion in ("recta", "u"):
            resultado = calcular_bajos(bajos(distribucion=distribucion))
            self.assertFalse(resultado.listo)
            self.assertIn(distribucion, resultado.esquema["distribucion"])
            self.assertTrue(resultado.avisos)
            self.assertEqual(resultado.piezas, [])

    def test_los_tramos_de_pared_en_l_alimentan_los_largos(self):
        resultado = calcular_bajos(
            bajos(distribucion="l", largo_pared_a="180", largo_pared_b="135")
        )
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.esquema["largo_barra"], 1800)
        self.assertEqual(resultado.esquema["fondo_total"], 1350)

    def test_medidas_pedidas(self):
        resultado = calcular_bajos(bajos())
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 1690)
        self.assertEqual(resultado.esquema["alto"], 800)
        self.assertEqual(resultado.esquema["fondo_total"], 1290)
        self.assertEqual(resultado.esquema["proyeccion"], 680)
        self.assertEqual(resultado.esquema["alto_puerta"], 694)
        self.assertEqual(resultado.esquema["fijo"], 84)
        self.assertEqual(resultado.esquema["shelf_top"], 458)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(resultado.esquema["alto_cajon"], 700)
        self.assertEqual(resultado.esquema["modulos_conectados"], ["cajón 2", "esquinero"])
        html = render_bajos(bajos(), resultado)
        self.assertIn("2 MÓDULOS CONECTADOS", html)
        self.assertIn("SIN PUERTA", html)
        self.assertNotIn("Techo tarja", por_nombre)
        self.assertIn("Cajón 1", render_bajos(bajos(), resultado))
        self.assertIn("SIN TABLA SUPERIOR", render_bajos(bajos(), resultado))
        self.assertEqual((por_nombre["Lateral tarja"].alto, por_nombre["Lateral tarja"].ancho, por_nombre["Lateral tarja"].cantidad), (700, 610, 2))
        self.assertEqual((por_nombre["Entrepaño tarja"].alto, por_nombre["Entrepaño tarja"].ancho), (1070, 610))
        self.assertEqual((por_nombre["Puerta tarja izquierda"].alto, por_nombre["Puerta tarja izquierda"].ancho), (694, 546))
        self.assertEqual(por_nombre["Puerta tarja derecha"].ancho, 545)
        self.assertEqual((por_nombre["Puerta vuelta"].alto, por_nombre["Puerta vuelta"].ancho), (694, 590))
        self.assertEqual((por_nombre["Fijo vuelta"].alto, por_nombre["Fijo vuelta"].ancho), (694, 84))
        zoclos = [p.nombre for p in resultado.piezas if p.nombre.lower().startswith("zoclo")]
        self.assertEqual(
            zoclos,
            [
                "Zoclo marco cajón 2 y el esquinero",
                "Zoclo refuerzo cajón 2 y el esquinero",
                "Zoclo marco cajón 1",
                "Zoclo refuerzo cajón 1",
            ],
        )
        self.assertEqual((por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho, por_nombre["Zoclo marco cajón 2 y el esquinero"].cantidad), (1260, 490, 1))
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].material, "Pino 2 cm")
        self.assertIn("alto 10 cm", por_nombre["Zoclo marco cajón 2 y el esquinero"].lectura)
        self.assertIn("espesor ya contado", por_nombre["Zoclo marco cajón 2 y el esquinero"].lectura)
        self.assertEqual((por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].ancho, por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].cantidad), (450, 100, 4))
        self.assertEqual((por_nombre["Zoclo marco cajón 1"].alto, por_nombre["Zoclo marco cajón 1"].ancho, por_nombre["Zoclo marco cajón 1"].cantidad), (1190, 510, 1))
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].espesor, 20)
        self.assertEqual((por_nombre["Zoclo refuerzo cajón 1"].alto, por_nombre["Zoclo refuerzo cajón 1"].ancho, por_nombre["Zoclo refuerzo cajón 1"].cantidad), (470, 100, 4))
        self.assertEqual(resultado.esquema["pino_mm"], 10420)
        self.assertEqual(resultado.esquema["zoclo_pie"], 100)
        self.assertTrue(any("126 × 49" in a and "119 × 51" in a for a in resultado.avisos))
        self.assertFalse(any("pasan el fondo" in a for a in resultado.avisos))
        self.assertFalse(any("tapadera" in p.nombre.lower() for p in resultado.piezas))
        self.assertNotIn("Zoclo tarja", por_nombre)
        self.assertNotIn("Zoclo vuelta", por_nombre)
        self.assertEqual((por_nombre["Fondo tarja"].alto, por_nombre["Fondo tarja"].ancho), (666, 1066))
        self.assertEqual((por_nombre["Lateral vuelta"].alto, por_nombre["Lateral vuelta"].ancho), (700, 590))
        self.assertEqual((por_nombre["Entrepaño esquina"].alto, por_nombre["Entrepaño esquina"].ancho), (560, 610))
        self.assertEqual((por_nombre["Fondo esquina"].alto, por_nombre["Fondo esquina"].ancho), (666, 556))
        self.assertNotIn("Zoclo esquina", por_nombre)
        self.assertNotIn("Puerta esquina", por_nombre)
        self.assertTrue(all(p.cabe() for p in resultado.piezas))
        self.assertEqual(resultado.bisagras, 6)
        self.assertEqual(resultado.confirmat, 54)
        self.assertEqual(resultado.tableros_15, 3)
        self.assertEqual(resultado.tableros_fondo, 1)
        self.assertTrue(any("69.4" in a for a in resultado.avisos))
        self.assertTrue(any("ciego" in a for a in resultado.avisos))

    def test_largo_distinto_avisa_y_arma(self):
        resultado = calcular_bajos(bajos(largo_barra="1800"))
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 1690)
        self.assertTrue(any("180 cm" in a and "169 cm" in a for a in resultado.avisos))

    def test_puerta_de_vuelta_no_cabe(self):
        resultado = calcular_bajos(bajos(largo_vuelta="700"))
        self.assertFalse(resultado.listo)
        self.assertEqual(resultado.piezas, [])

    def test_bano_no_inventa_el_mueble(self):
        resultado = calcular_bajos(bajos(tipo="bano"))
        self.assertFalse(resultado.listo)
        self.assertEqual(resultado.piezas, [])
        self.assertTrue(any("zoclo" in a for a in resultado.avisos))

    def test_sin_zoclo_no_arma(self):
        resultado = calcular_bajos(bajos(zoclo=""))
        self.assertFalse(resultado.listo)
        self.assertEqual(resultado.piezas, [])

    def test_editar_una_medida(self):
        datos = bajos()
        datos["medidas"] = json.dumps({"Zoclo marco cajón 2 y el esquinero": [1300, 60]})
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual((por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho), (1300, 60))
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 20)
        self.assertEqual((por_nombre["Zoclo marco cajón 1"].alto, por_nombre["Zoclo marco cajón 1"].ancho), (1190, 510))
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 1"].alto, 470)
        self.assertEqual(por_nombre["Puerta vuelta"].ancho, 590)
        self.assertEqual(por_nombre["Lateral tarja"].alto, 700)
        self.assertEqual(resultado.esquema["pino_mm"], 7800)
        self.assertTrue(any("130 × 6" in a for a in resultado.avisos))

    def test_medida_invalida_no_cambia_la_pieza(self):
        datos = bajos(medidas="no-es-json")
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1260)
        datos = bajos()
        datos["medidas"] = json.dumps({"Puerta vuelta": [3000, 600]})
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Puerta vuelta"].alto, 3000)
        self.assertEqual(por_nombre["Puerta vuelta"].canto_mm, 2 * (3000 + 600))
        self.assertTrue(any("Puerta vuelta" in a and "pasa de la hoja" in a for a in resultado.avisos))

    def test_largo_del_marco_sigue_el_hueco(self):
        resultado = calcular_bajos(bajos(zoclo_pie="90"))
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1260)
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].alto, 1180)
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].ancho, 520)
        self.assertFalse(any("pasan el fondo" in a for a in resultado.avisos))

    def test_cortes_para_el_carpintero(self):
        resultado = calcular_bajos(bajos())
        hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
        self.assertEqual(hoja["mm"], 10420)
        self.assertEqual(hoja["pino_mm"], 10420)
        self.assertEqual(hoja["compra"], 12)
        self.assertEqual(resultado.esquema["pino_mm"], hoja["mm"])
        por_clave = {m["clave"]: m for m in hoja["marcos"]}
        dos = por_clave["cajón 2 y el esquinero"]
        self.assertEqual(
            [(c["letra"], c["cant"], c["largo"]) for c in dos["cortes"]],
            [("A", 2, 1260), ("B", 2, 450), ("C", 4, 450)],
        )
        self.assertEqual(dos["centros"], [258, 506, 754, 1002])
        self.assertEqual(dos["diagonal"], 1352)
        self.assertEqual(dos["pasa"], 0)
        uno = por_clave["cajón 1"]
        self.assertEqual(
            [(c["letra"], c["cant"], c["largo"]) for c in uno["cortes"]],
            [("D", 2, 1190), ("E", 2, 470), ("F", 4, 470)],
        )
        self.assertEqual(uno["centros"], [244, 478, 712, 946])
        self.assertEqual(uno["diagonal"], 1295)
        self.assertEqual(uno["pasa"], 0)
        lugar = colocar_marcos(hoja)
        self.assertEqual(lugar["sale_cajon2"], 0)
        self.assertEqual(lugar["aire_punta"], 30)
        self.assertEqual(lugar["aire_fondo_cajon1"], 0)
        self.assertEqual(lugar["aire_fin_cajon1"], 10)
        self.assertEqual(lugar["leg_x0"], 0)
        self.assertEqual(lugar["arm_x1"], 1680)
        self.assertEqual(lugar["leg_z1"], lugar["arm_z1"])
        html = render_bajos(bajos(), resultado)
        self.assertIn("Mandar a carpintero", html)
        self.assertIn("Descargas", html)
        self.assertNotIn('id="carpintero"', html)
        self.assertNotIn("Imprimir esta hoja", html)
        pdf = pdf_zoclo(bajos())
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"49 - 2 - 2 = 45", pdf)
        self.assertIn(b"135.2", pdf)
        self.assertIn(b"129.5", pdf)
        self.assertIn(b"94.6", pdf)
        self.assertIn(b"10.42 m", pdf)
        self.assertIn(b"MEDIDAS", pdf)
        self.assertNotIn(b"Junta los dos marcos", pdf)
        self.assertNotIn(b"1270", pdf)
        self.assertNotIn(b"1190", pdf)
        self.assertNotIn(b" mm", pdf)

    def test_carpintero_avisa_refuerzo_editado(self):
        datos = bajos()
        datos["medidas"] = json.dumps({"Zoclo refuerzo cajón 1": [480, 100]})
        resultado = calcular_bajos(datos)
        hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
        uno = next(m for m in hoja["marcos"] if m["clave"] == "cajón 1")
        self.assertTrue(uno["refuerzo_editado"])
        self.assertEqual(uno["corte_refuerzo"], 480)
        self.assertEqual(uno["dentro"], 470)
        self.assertEqual(hoja["mm"], resultado.esquema["pino_mm"])
        pdf = pdf_zoclo(datos)
        self.assertIn(b"Entre las tablas largas: 47 cm", pdf)
        self.assertIn(b"(48)", pdf)

    def test_carpintero_marco_angosto_no_arma(self):
        datos = bajos()
        datos["medidas"] = json.dumps({"Zoclo marco cajón 2 y el esquinero": [1300, 60]})
        resultado = calcular_bajos(datos)
        hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
        dos = next(m for m in hoja["marcos"] if "cajón 2" in m["clave"])
        self.assertFalse(dos["entra"])
        self.assertEqual(dos["dentro"], 20)
        self.assertEqual([c["largo"] for c in dos["cortes"]], [1300])
        self.assertEqual(resultado.esquema["pino_mm"], 7800)
        self.assertEqual(hoja["mm"], 7800)
        pdf = pdf_zoclo(datos)
        self.assertIn(b"no se arma", pdf)

    def test_columna_no_trae_hoja_de_carpintero(self):
        html = render(base(), calcular_columna(base()))
        self.assertNotIn("Mandar a carpintero", html)
        self.assertNotIn("data-carpintero", html)
        self.assertNotIn("Plano de la barra", html)
        self.assertNotIn('name="marco_a_1"', html)
        self.assertIn('name="alto" value="210"', html)
        self.assertIn('name="espesor" value="1.5"', html)
        self.assertIn('name="fondo_esp" value="0.3"', html)
        self.assertIn("79.8", html)
        self.assertNotIn('value="2100"', html)

    def test_cada_marco_tiene_sus_medidas(self):
        datos = bajos(ref_1="2", marco_a_1="400", pino_esp="18", marco_l_1="1000")
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(
            (por_nombre["Zoclo marco cajón 1"].alto, por_nombre["Zoclo marco cajón 1"].ancho, por_nombre["Zoclo marco cajón 1"].espesor),
            (1000, 400, 18),
        )
        self.assertEqual(
            (por_nombre["Zoclo refuerzo cajón 1"].alto, por_nombre["Zoclo refuerzo cajón 1"].ancho, por_nombre["Zoclo refuerzo cajón 1"].cantidad),
            (364, 100, 2),
        )
        self.assertIn("40 - 1.8 - 1.8 = 36.4", por_nombre["Zoclo refuerzo cajón 1"].notas)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1260)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho, 490)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].espesor, 18)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 454)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].cantidad, 4)
        self.assertFalse(resultado.esquema["marco_l_1_auto"])
        self.assertTrue(resultado.esquema["marco_l_2_auto"])
        self.assertEqual(resultado.esquema["pino_esp"], 18)
        self.assertEqual(resultado.esquema["pino_mm"], 8700)
        pdf = pdf_zoclo(datos)
        self.assertIn(b"40 - 1.8 - 1.8 = 36.4", pdf)
        self.assertIn(b"36.4", pdf)
        self.assertNotIn(b"1000", pdf)

    def test_el_largo_del_marco_usa_su_ancho(self):
        resultado = calcular_bajos(bajos(marco_a_2="490"))
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1260)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho, 490)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 450)
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].alto, 1190)
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].ancho, 510)
        self.assertFalse(any("pasan el fondo" in a for a in resultado.avisos))

    def test_cero_refuerzos(self):
        resultado = calcular_bajos(bajos(ref_1="0", ref_2="0"))
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertFalse(any("refuerzo" in p.nombre for p in resultado.piezas))
        self.assertEqual(resultado.esquema["pino_mm"], 6740)

    def test_las_medidas_van_en_su_seccion(self):
        resultado = calcular_bajos(bajos())
        html = render_bajos(bajos(), resultado)
        formulario = html.split("<form", 1)[1].split("</form>", 1)[0]
        self.assertIn("Plano de la barra", formulario)
        self.assertIn('name="largo_pared_a"', formulario)
        self.assertIn('name="largo_pared_b"', formulario)
        self.assertIn('name="alto_barra"', formulario)
        self.assertNotIn('name="largo_barra"', formulario)
        self.assertIn('name="fondo_barra"', formulario)
        self.assertIn('name="ancho_tarja"', formulario)
        self.assertIn('name="fondo_vuelta"', formulario)
        self.assertNotIn('name="puerta_vuelta"', formulario)
        self.assertNotIn('name="zoclo"', formulario)
        self.assertNotIn('name="zoclo_pie"', formulario)
        self.assertNotIn('name="marco_a_1"', formulario)
        zoclo = html.split('section class="parte" data-modulo="tarja"', 1)[0]
        self.assertIn('name="pino_esp"', zoclo)
        self.assertIn('name="zoclo_pie"', zoclo)
        self.assertIn('name="marco_l_2"', zoclo)
        self.assertIn('name="marco_a_2"', zoclo)
        self.assertIn('name="ref_2"', zoclo)
        self.assertIn('name="marco_l_1"', zoclo)
        self.assertIn('name="marco_a_1"', zoclo)
        self.assertIn('name="ref_1"', zoclo)
        self.assertIn('data-auto="1"', zoclo)
        self.assertIn('value="126"', zoclo)
        self.assertIn('value="119"', zoclo)
        self.assertNotIn('value="1270"', zoclo)
        self.assertNotIn('value="1190"', zoclo)
        tarja = html.split('section class="parte" data-modulo="tarja"', 1)[1].split('section class="parte" data-modulo="vuelta"', 1)[0]
        self.assertIn('name="fondo_barra"', tarja)
        self.assertIn('name="ancho_tarja"', tarja)
        self.assertNotIn('name="puerta_vuelta"', tarja)
        vuelta = html.split('section class="parte" data-modulo="vuelta"', 1)[1].split('section class="parte" data-modulo="esquina"', 1)[0]
        self.assertIn('name="fondo_vuelta"', vuelta)
        self.assertIn('name="puerta_vuelta"', vuelta)
        esquina = html.split('section class="parte" data-modulo="esquina"', 1)[1].split("<table", 1)[0]
        self.assertIn("Se cambia en el cajón 2", esquina)
        self.assertIn('value="59"', esquina)
        self.assertIn('value="61"', esquina)
        self.assertNotIn('name="fondo_vuelta"', esquina)
        self.assertIn("pino de 2 × 10", html)
        self.assertIn('name="largo_pared_a"', html)
        self.assertIn('name="espesor" value="1.5"', html)
        self.assertNotIn('value="1690"', html)
        self.assertIn('form="plano"', html)

    def test_el_error_conserva_las_medidas(self):
        datos = bajos(puerta_vuelta="900", fondo_barra="580", ref_1="3", marco_a_1="420")
        resultado = calcular_bajos(datos)
        self.assertFalse(resultado.listo)
        html = render_bajos(datos, resultado)
        self.assertIn('name="fondo_barra" value="58"', html)
        self.assertIn('name="ref_1" value="3"', html)
        self.assertIn('name="marco_a_1" value="42"', html)
        self.assertIn('name="puerta_vuelta" value="90"', html)

    def test_la_consulta_entra_en_centimetros(self):
        self.assertEqual(texto_cm(15), "1.5")
        self.assertEqual(texto_cm(1690), "169")
        self.assertEqual(texto_cm(694), "69.4")
        self.assertEqual(texto_cm(3), "0.3")
        self.assertEqual(cm_a_mm("1,5"), "15")
        self.assertEqual(cm_a_mm("69.4"), "694")
        self.assertEqual(cm_a_mm(""), "")
        self.assertEqual(cm_a_mm("no"), "no")
        datos = datos_bajos({
            "largo_barra": ["169"],
            "espesor": ["1,5"],
            "ref_1": ["2"],
            "marco_a_1": ["40"],
            "zoclo_pie": ["10"],
        })
        self.assertEqual(datos["largo_barra"], "1690")
        self.assertEqual(datos["espesor"], "15")
        self.assertEqual(datos["ref_1"], "2")
        self.assertEqual(datos["marco_a_1"], "400")
        self.assertEqual(datos["zoclo_pie"], "100")
        self.assertEqual(datos["marco_l_1"], "")
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 1"].alto, 360)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 1"].cantidad, 2)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].cantidad, 4)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 450)
        html = render_bajos(datos, resultado)
        self.assertIn('name="marco_a_1" value="40"', html)
        self.assertIn('name="ref_1" value="2"', html)
        self.assertIn("40 - 2 - 2 = 36", html)
        self.assertNotIn('value="400"', html)
        columna = datos_de_consulta({
            "hueco_ancho": ["80"],
            "hueco_alto": ["60"],
            "hueco_desde": ["90"],
            "ejemplo": ["1"],
            "espesor": ["1.5"],
        }, ejemplo=False)
        self.assertEqual(columna["hueco_ancho"], "800")
        self.assertEqual(columna["hueco_alto"], "600")
        self.assertEqual(columna["hueco_desde"], "900")
        self.assertEqual(columna["alto"], "2100")
        self.assertEqual(columna["espesor"], "15")
        self.assertEqual(columna["ejemplo"], "1")
        hoja = render(columna, calcular_columna(columna))
        self.assertIn("80 × 60 cm a 90 cm", hoja)
        self.assertNotIn("Mandar a carpintero", hoja)


def lava(**extra):
    datos = {
        "alto": "2440",
        "hueco_ancho": "610",
        "hueco_alto": str(LAVA_HUECO_ALTO),
        "fondo": "610",
        "espesor": "16",
        "fondo_esp": "3",
        "repisa_fondo": "",
        "repisas": "2",
        "color": "Blanco Frosty",
    }
    datos.update(extra)
    return datos


class Lavavajillas(unittest.TestCase):
    def test_el_cajon_de_fabrica(self):
        self.assertEqual(round(85.4 * 10), 854)
        self.assertEqual(round(86.4 * 10), 864)
        self.assertEqual(round(87 * 10), 870)
        resultado = calcular_lavavajillas(lava())
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 642)
        self.assertEqual(resultado.bisagras, 0)
        self.assertEqual(resultado.tableros_15, 2)
        self.assertEqual(resultado.tableros_fondo, 1)
        self.assertEqual(resultado.confirmat, 8)
        self.assertEqual(resultado.esquema["soportes"], 8)
        self.assertEqual(resultado.esquema["hueco_alto"], 870)
        self.assertEqual(resultado.esquema["posiciones"], [1398, 1878])
        self.assertEqual(resultado.esquema["posiciones"][0] % 32, (870 + 16 + 32) % 32)
        self.assertEqual(resultado.esquema["alto"], 2440)
        self.assertEqual(resultado.esquema["fondo_repisa"], 606)
        self.assertEqual(resultado.esquema["hojas"], 2)
        self.assertEqual(resultado.esquema["repisas"], 2)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(
            set(por_nombre),
            {"Lateral lavavajillas", "Techo lavavajillas", "Techo entrepaños", "Entrepaño", "Respaldo entrepaños"},
        )
        lateral = por_nombre["Lateral lavavajillas"]
        self.assertEqual((lateral.cantidad, lateral.alto, lateral.ancho, lateral.espesor), (2, 2440, 610, 16))
        for nombre in ("Techo lavavajillas", "Techo entrepaños"):
            tabla = por_nombre[nombre]
            self.assertEqual((tabla.cantidad, tabla.alto, tabla.ancho, tabla.espesor), (1, 610, 606, 16))
        entre = por_nombre["Entrepaño"]
        self.assertEqual((entre.cantidad, entre.alto, entre.ancho, entre.espesor), (2, 608, 606, 16))
        self.assertIn("soportes", entre.notas)
        self.assertIn("No va con confirmat", entre.notas)
        self.assertIn("60.8", entre.notas)
        respaldo = por_nombre["Respaldo entrepaños"]
        self.assertEqual((respaldo.alto, respaldo.ancho), (1534, 606))
        for pieza in resultado.piezas:
            self.assertTrue(pieza.cabe())
            self.assertNotIn("Zoclo", pieza.nombre)
            self.assertNotIn("Puerta", pieza.nombre)
            self.assertNotIn("Fondo", pieza.nombre)
            self.assertNotIn("Riel", pieza.nombre)
        texto = " ".join(resultado.avisos)
        self.assertIn("60.3", texto)
        self.assertIn("62.5", texto)
        self.assertIn("plantilla", texto)
        self.assertIn("izquierdo", texto)
        self.assertIn("15.2", texto)
        self.assertIn("10.2", texto)
        self.assertIn("1.5 cm", texto)
        self.assertIn("244", texto)
        self.assertIn("largo completo", texto)
        self.assertIn("60.6", texto)
        self.assertIn("2 hojas", texto)
        self.assertIn("El lavavajillas entra.", texto)
        self.assertIn("86.4", texto)
        self.assertIn("60.8", texto)
        self.assertIn("escuadras", texto)
        self.assertIn("aluminio", texto)
        self.assertIn("sin orillas", texto)
        self.assertIn("canto de atrás del entrepaño", texto)
        self.assertIn("conexiones puestas", texto)
        self.assertIn("67.6", texto)
        self.assertIn("entrepaños", texto)
        self.assertIn("5 mm", texto)

    def test_un_hueco_bajo_avisa_y_arma(self):
        resultado = calcular_lavavajillas(lava(hueco_alto="800"))
        self.assertTrue(resultado.listo, resultado.errores)
        texto = " ".join(resultado.avisos)
        self.assertIn("86.4", texto)
        self.assertIn("85.4", texto)
        self.assertNotIn("El lavavajillas entra.", texto)

    def test_85_4_es_la_pata_retraida_y_no_entra(self):
        resultado = calcular_lavavajillas(lava(hueco_alto="854"))
        texto = " ".join(resultado.avisos)
        self.assertIn("86.4", texto)
        self.assertNotIn("El lavavajillas entra.", texto)

    def test_el_corte_minimo_de_86_4_entra(self):
        resultado = calcular_lavavajillas(lava(hueco_alto="864"))
        self.assertIn("El lavavajillas entra.", " ".join(resultado.avisos))

    def test_un_alto_de_250_no_cabe_en_la_hoja(self):
        resultado = calcular_lavavajillas(lava(alto="2500"))
        self.assertFalse(resultado.listo)

    def test_posiciones_distintas_se_pueden_pedir(self):
        resultado = calcular_lavavajillas(lava(posiciones="140; 200"))
        self.assertTrue(resultado.listo, resultado.errores)
        bajas, altas = resultado.esquema["posiciones"]
        self.assertLess(bajas, altas)
        notas = " ".join(p.notas for p in resultado.piezas if p.nombre == "Entrepaño")
        self.assertIn(texto_cm(bajas), notas)
        self.assertIn(texto_cm(altas), notas)

    def test_la_misma_hilera_no_arma(self):
        resultado = calcular_lavavajillas(lava(posiciones="150; 150"))
        self.assertFalse(resultado.listo)
        self.assertTrue(any("misma hilera" in e for e in resultado.errores))

    def test_repisa_de_61_pide_mas_de_dos_hojas(self):
        resultado = calcular_lavavajillas(lava(repisa_fondo="610"))
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertGreater(resultado.tableros_15, 2)
        self.assertEqual(resultado.esquema["fondo_repisa"], 610)

    def test_la_hoja_va_en_centimetros(self):
        datos = lava()
        html = render_lavavajillas(datos, calcular_lavavajillas(datos))
        self.assertIn('data-pieza="lavavajillas"', html)
        self.assertIn('href="/?pieza=lavavajillas"', html)
        self.assertIn('name="alto" value="244"', html)
        self.assertIn('name="hueco_ancho" value="61"', html)
        self.assertIn('name="hueco_alto" value="87"', html)
        self.assertIn('name="fondo" value="61"', html)
        self.assertIn('name="espesor" value="1.6"', html)
        self.assertIn('name="fondo_esp" value="0.3"', html)
        self.assertIn('name="repisas" value="2"', html)
        self.assertIn('name="posiciones"', html)
        self.assertIn("Entrepaño", html)
        self.assertIn("soportes de entrepaño", html)
        self.assertNotIn('data-tabla="Repisa"', html)
        self.assertIn('name="repisa_fondo" value="60.6"', html)
        self.assertIn('data-auto="1"', html)
        self.assertIn('value="Blanco Frosty"', html)
        self.assertIn("717863", html)
        self.assertIn("El lavavajillas entra.", html)
        self.assertIn("86.4", html)
        self.assertIn("60.8", html)
        self.assertIn("153.4", html)
        self.assertIn("LDP6810SS", html)
        self.assertIn("escuadras", html)
        self.assertIn("85.4 cm", html)
        self.assertIn("<strong>64.2 cm</strong>", html)
        self.assertIn(">244<", html)
        self.assertIn(">60.6<", html)
        self.assertNotIn('name="riel"', html)
        self.assertIn("Mandar a carpintero", html)
        self.assertIn('data-carpintero="lavavajillas"', html)
        self.assertIn('data-carpintero="corte"', html)
        self.assertIn("Corte de maderería", html)
        self.assertIn("Hoja 1", html)
        self.assertIn("Lateral izquierdo", html)
        self.assertIn("15.2 cm del piso", html)
        self.assertNotIn('data-carpintero="zoclo"', html)
        self.assertNotIn("Plano de la barra", html)
        self.assertNotIn('name="zoclo"', html)
        self.assertNotIn('name="marco_a_1"', html)
        self.assertNotIn('name="hueco_desde"', html)
        barra = render_bajos(bajos(), calcular_bajos(bajos()))
        self.assertIn("Lavavajillas", barra)
        self.assertIn("Mandar a carpintero", barra)
        self.assertNotIn('name="riel"', barra)
        columna = render(base(), calcular_columna(base()))
        self.assertIn("Lavavajillas", columna)
        self.assertNotIn("Mandar a carpintero", columna)
        self.assertNotIn('name="riel"', columna)
        self.assertNotIn('name="marco_a_1"', columna)
        pagina = responder({}, pieza="lavavajillas")
        self.assertIn('name="alto" value="244"', pagina)
        self.assertIn('name="espesor" value="1.6"', pagina)
        self.assertIn("Blanco Frosty", pagina)
        self.assertIn("717863", pagina)
        self.assertNotIn("Gris Oxford", pagina)
        self.assertIn('data-carpintero="lavavajillas"', pagina)

    def test_el_pdf_son_instrucciones(self):
        pdf = pdf_lavavajillas(lava())
        self.assertIsNotNone(pdf)
        self.assertTrue(pdf.startswith(b"%PDF"))
        texto = pdf.decode("latin-1", errors="ignore")
        self.assertIn("CORTA", texto)
        self.assertIn("ARMA", texto)
        self.assertIn("Entrepa", texto)
        self.assertIn("244", texto)
        self.assertIn("139.8", texto)
        self.assertIn("187.8", texto)
        self.assertIn("87 cm", texto)
        self.assertIn("60.8", texto)
        self.assertIn("escuadras", texto)
        self.assertIn("aluminio", texto)
        self.assertNotIn("138.2", texto)
        self.assertIn("6.3", texto)
        self.assertIn("izquierdo", texto)
        self.assertIn("15.2", texto)
        self.assertIn("10.2", texto)
        self.assertNotIn("programa", texto.lower())
        self.assertNotIn("Muebles", texto)
        self.assertNotIn("comprensi", texto.lower())
        self.assertIsNone(pdf_lavavajillas(lava(alto="2500")))

    def test_el_corte_de_la_hoja(self):
        resultado = calcular_lavavajillas(lava())
        hojas = cortes_lavavajillas(resultado.piezas)
        self.assertEqual(len(hojas), 2)
        self.assertEqual(len(hojas[0]), 4)
        self.assertEqual(len(hojas[1]), 2)
        self.assertEqual(hojas[0][0]["nombre"], "Lateral")
        self.assertEqual((hojas[0][0]["w"], hojas[0][0]["h"]), (610, 2440))
        self.assertEqual(hojas[1][0]["nombre"], "Lateral")
        entre = next(pieza for pieza in hojas[0] if pieza["nombre"] == "Entrepaño")
        self.assertEqual(sorted((entre["w"], entre["h"])), [606, 608])
        techo = next(pieza for pieza in hojas[0] if pieza["nombre"] == "Techo lavavajillas")
        self.assertEqual(sorted((techo["w"], techo["h"])), [606, 610])

        def se_toca(a, b):
            return not (
                a["x"] + a["w"] <= b["x"]
                or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"]
                or b["y"] + b["h"] <= a["y"]
            )

        for hoja in hojas:
            for pieza in hoja:
                self.assertGreaterEqual(pieza["x"], 0)
                self.assertGreaterEqual(pieza["y"], 0)
                self.assertLessEqual(pieza["x"] + pieza["w"], 1220)
                self.assertLessEqual(pieza["y"] + pieza["h"], 2440)
            for i, una in enumerate(hoja):
                for otra in hoja[i + 1:]:
                    self.assertFalse(se_toca(una, otra))
        pdf = pdf_corte(lava())
        self.assertTrue(pdf.startswith(b"%PDF"))
        texto = pdf.decode("latin-1")
        self.assertIn("HOJA", texto)
        self.assertIn("244", texto)
        self.assertIn("60.6", texto)
        self.assertIn("60.8", texto)
        self.assertIn("153.4", texto)
        self.assertIn("orillas", texto)
        self.assertIn("sierra", texto)
        self.assertNotIn("programa", texto.lower())
        self.assertNotIn("Muebles", texto)
        self.assertIsNone(pdf_corte(lava(alto="2500")))

    def test_la_consulta_entra_en_centimetros(self):
        datos = datos_lavavajillas({
            "alto": ["244"],
            "hueco_ancho": ["61"],
            "hueco_alto": ["85,4"],
            "fondo": ["61"],
            "espesor": ["1.6"],
            "fondo_esp": ["0.3"],
            "repisa_fondo": [""],
            "repisas": ["2"],
        })
        self.assertEqual(datos["alto"], "2440")
        self.assertEqual(datos["hueco_ancho"], "610")
        self.assertEqual(datos["hueco_alto"], "854")
        self.assertEqual(datos["fondo"], "610")
        self.assertEqual(datos["espesor"], "16")
        self.assertEqual(datos["fondo_esp"], "3")
        self.assertEqual(datos["repisa_fondo"], "")
        self.assertEqual(datos["repisas"], "2")
        resultado = calcular_lavavajillas(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.esquema["alto"], 2440)
        self.assertEqual(resultado.esquema["fondo_repisa"], 606)


if __name__ == "__main__":
    unittest.main()
