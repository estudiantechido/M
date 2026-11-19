import json
import unittest

from despiece import calcular_bajos, calcular_columna, cm_a_mm, cortes_carpintero, texto_cm
from pagina import datos_bajos, datos_de_consulta, render, render_bajos
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


def bajos(**extra):
    datos = {
        "tipo": "cocina",
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
        "puerta_vuelta": "600",
        "alto_barra": "800",
        "entre_desde": "",
    }
    datos.update(extra)
    return datos


class BajosTarja(unittest.TestCase):
    def test_medidas_pedidas(self):
        resultado = calcular_bajos(bajos())
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertEqual(resultado.ancho_exterior, 1690)
        self.assertEqual(resultado.esquema["alto"], 800)
        self.assertEqual(resultado.esquema["fondo_total"], 1290)
        self.assertEqual(resultado.esquema["proyeccion"], 680)
        self.assertEqual(resultado.esquema["alto_puerta"], 694)
        self.assertEqual(resultado.esquema["fijo"], 74)
        self.assertEqual(resultado.esquema["shelf_top"], 458)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual((por_nombre["Lateral tarja"].alto, por_nombre["Lateral tarja"].ancho, por_nombre["Lateral tarja"].cantidad), (700, 610, 2))
        self.assertEqual((por_nombre["Entrepaño tarja"].alto, por_nombre["Entrepaño tarja"].ancho), (1070, 610))
        self.assertEqual((por_nombre["Puerta tarja izquierda"].alto, por_nombre["Puerta tarja izquierda"].ancho), (694, 546))
        self.assertEqual(por_nombre["Puerta tarja derecha"].ancho, 545)
        self.assertEqual((por_nombre["Puerta vuelta"].alto, por_nombre["Puerta vuelta"].ancho), (694, 600))
        self.assertEqual((por_nombre["Fijo vuelta"].alto, por_nombre["Fijo vuelta"].ancho), (694, 74))
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
        self.assertEqual((por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho, por_nombre["Zoclo marco cajón 2 y el esquinero"].cantidad), (1270, 500, 1))
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].material, "Pino 2 cm")
        self.assertIn("alto 10 cm", por_nombre["Zoclo marco cajón 2 y el esquinero"].lectura)
        self.assertIn("espesor ya contado", por_nombre["Zoclo marco cajón 2 y el esquinero"].lectura)
        self.assertEqual((por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].ancho, por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].cantidad), (460, 100, 4))
        self.assertEqual((por_nombre["Zoclo marco cajón 1"].alto, por_nombre["Zoclo marco cajón 1"].ancho, por_nombre["Zoclo marco cajón 1"].cantidad), (1190, 500, 1))
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].espesor, 20)
        self.assertEqual((por_nombre["Zoclo refuerzo cajón 1"].alto, por_nombre["Zoclo refuerzo cajón 1"].ancho, por_nombre["Zoclo refuerzo cajón 1"].cantidad), (460, 100, 4))
        self.assertEqual(resultado.esquema["pino_mm"], 10440)
        self.assertEqual(resultado.esquema["zoclo_pie"], 100)
        self.assertTrue(any("127 × 50" in a and "119 × 50" in a for a in resultado.avisos))
        self.assertTrue(any("pasan el fondo" in a for a in resultado.avisos))
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
        self.assertEqual(resultado.tableros_15, 4)
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
        self.assertEqual((por_nombre["Zoclo marco cajón 1"].alto, por_nombre["Zoclo marco cajón 1"].ancho), (1190, 500))
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 1"].alto, 460)
        self.assertEqual(por_nombre["Puerta vuelta"].ancho, 600)
        self.assertEqual(por_nombre["Lateral tarja"].alto, 700)
        self.assertEqual(resultado.esquema["pino_mm"], 7740)
        self.assertTrue(any("130 × 6" in a for a in resultado.avisos))

    def test_medida_invalida_no_cambia_la_pieza(self):
        datos = bajos(medidas="no-es-json")
        resultado = calcular_bajos(datos)
        self.assertTrue(resultado.listo, resultado.errores)
        por_nombre = {p.nombre: p for p in resultado.piezas}
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1270)
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
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].ancho, 500)
        self.assertFalse(any("pasan el fondo" in a for a in resultado.avisos))

    def test_cortes_para_el_carpintero(self):
        resultado = calcular_bajos(bajos())
        hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
        self.assertEqual(hoja["mm"], 10440)
        self.assertEqual(hoja["pino_mm"], 10440)
        self.assertEqual(hoja["compra"], 12)
        self.assertEqual(resultado.esquema["pino_mm"], hoja["mm"])
        por_clave = {m["clave"]: m for m in hoja["marcos"]}
        dos = por_clave["cajón 2 y el esquinero"]
        self.assertEqual(
            [(c["letra"], c["cant"], c["largo"]) for c in dos["cortes"]],
            [("A", 2, 1270), ("B", 2, 460), ("C", 4, 460)],
        )
        self.assertEqual(dos["centros"], [260, 510, 760, 1010])
        self.assertEqual(dos["diagonal"], 1365)
        self.assertEqual(dos["pasa"], 10)
        uno = por_clave["cajón 1"]
        self.assertEqual(
            [(c["letra"], c["cant"], c["largo"]) for c in uno["cortes"]],
            [("D", 2, 1190), ("E", 2, 460), ("F", 4, 460)],
        )
        self.assertEqual(uno["centros"], [244, 478, 712, 946])
        self.assertEqual(uno["diagonal"], 1291)
        self.assertEqual(uno["pasa"], -10)
        lugar = colocar_marcos(hoja)
        self.assertEqual(lugar["sale_cajon2"], 10)
        self.assertEqual(lugar["aire_punta"], 10)
        self.assertEqual(lugar["aire_fondo_cajon1"], 10)
        self.assertEqual(lugar["aire_fin_cajon1"], 10)
        self.assertEqual(lugar["leg_x0"], -10)
        self.assertEqual(lugar["arm_x1"], 1680)
        self.assertEqual(lugar["leg_z1"], lugar["arm_z1"])
        html = render_bajos(bajos(), resultado)
        self.assertIn("Mandar a carpintero", html)
        self.assertIn("Descargas", html)
        self.assertNotIn('id="carpintero"', html)
        self.assertNotIn("Imprimir esta hoja", html)
        pdf = pdf_zoclo(bajos())
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"50 - 2 - 2 = 46", pdf)
        self.assertIn(b"se sale 1 cm", pdf)
        self.assertIn(b"136.5", pdf)
        self.assertIn(b"129.1", pdf)
        self.assertIn(b"94.6", pdf)
        self.assertIn(b"10.44 m", pdf)
        self.assertIn(b"Las medidas de", pdf)
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
        self.assertEqual(uno["dentro"], 460)
        self.assertEqual(hoja["mm"], resultado.esquema["pino_mm"])
        pdf = pdf_zoclo(datos)
        self.assertIn(b"caben 46", pdf)
        self.assertIn(b"dice 48 cm", pdf)

    def test_carpintero_marco_angosto_no_arma(self):
        datos = bajos()
        datos["medidas"] = json.dumps({"Zoclo marco cajón 2 y el esquinero": [1300, 60]})
        resultado = calcular_bajos(datos)
        hoja = cortes_carpintero(resultado.piezas, resultado.esquema)
        dos = next(m for m in hoja["marcos"] if "cajón 2" in m["clave"])
        self.assertFalse(dos["entra"])
        self.assertEqual(dos["dentro"], 20)
        self.assertEqual([c["largo"] for c in dos["cortes"]], [1300])
        self.assertEqual(resultado.esquema["pino_mm"], 7740)
        self.assertEqual(hoja["mm"], 7740)
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
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].alto, 1270)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].ancho, 500)
        self.assertEqual(por_nombre["Zoclo marco cajón 2 y el esquinero"].espesor, 18)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 464)
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].cantidad, 4)
        self.assertFalse(resultado.esquema["marco_l_1_auto"])
        self.assertTrue(resultado.esquema["marco_l_2_auto"])
        self.assertEqual(resultado.esquema["pino_esp"], 18)
        self.assertEqual(resultado.esquema["pino_mm"], 8780)
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
        self.assertEqual(por_nombre["Zoclo marco cajón 1"].ancho, 500)
        self.assertFalse(any("pasan el fondo" in a for a in resultado.avisos))

    def test_cero_refuerzos(self):
        resultado = calcular_bajos(bajos(ref_1="0", ref_2="0"))
        self.assertTrue(resultado.listo, resultado.errores)
        self.assertFalse(any("refuerzo" in p.nombre for p in resultado.piezas))
        self.assertEqual(resultado.esquema["pino_mm"], 6760)

    def test_las_medidas_van_en_su_seccion(self):
        resultado = calcular_bajos(bajos())
        html = render_bajos(bajos(), resultado)
        formulario = html.split("<form", 1)[1].split("</form>", 1)[0]
        self.assertIn("Plano de la barra", formulario)
        self.assertIn('name="largo_barra"', formulario)
        self.assertIn('name="alto_barra"', formulario)
        self.assertNotIn('name="fondo_barra"', formulario)
        self.assertNotIn('name="ancho_tarja"', formulario)
        self.assertNotIn('name="fondo_vuelta"', formulario)
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
        self.assertIn('value="127"', zoclo)
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
        self.assertIn('name="largo_barra" value="169"', html)
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
        self.assertEqual(por_nombre["Zoclo refuerzo cajón 2 y el esquinero"].alto, 460)
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


if __name__ == "__main__":
    unittest.main()
