"""Servidor local del despiece. Solo escucha en esta máquina."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pagina import datos_bajos, datos_lavavajillas, responder
from pdf_corte import pdf_corte
from pdf_lava import pdf_lavavajillas
from pdf_zoclo import pdf_zoclo

HOST = "127.0.0.1"
PUERTO = 8765
RAIZ = Path(__file__).resolve().parent


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, cuerpo: bytes, tipo: str):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/vista.js":
            self._enviar((RAIZ / "vista.js").read_bytes(), "text/javascript; charset=utf-8")
            return
        if url.path == "/estilo.css":
            self._enviar((RAIZ / "estilo.css").read_bytes(), "text/css; charset=utf-8")
            return
        if url.path not in ("/", "/ejemplo", "/columna"):
            self.send_error(404)
            return
        query = parse_qs(url.query, keep_blank_values=True)
        pedido = query.get("pieza", [""])[0]
        if url.path in ("/ejemplo", "/columna") or pedido == "columna":
            pieza = "columna"
        elif pedido == "lavavajillas":
            pieza = "lavavajillas"
        else:
            pieza = "bajos"
        pedido_pdf = None
        if url.path == "/" and pieza == "lavavajillas" and query.get("corte", [""])[0] == "pdf":
            pedido_pdf = (pdf_corte(datos_lavavajillas(query)), "corte.pdf", "Revisa las medidas.".encode("utf-8"))
        elif url.path == "/" and query.get("carpintero", [""])[0] == "pdf" and pieza in ("bajos", "lavavajillas"):
            if pieza == "lavavajillas":
                pedido_pdf = (pdf_lavavajillas(datos_lavavajillas(query)), "lavavajillas.pdf", "Revisa las medidas.".encode("utf-8"))
            else:
                pedido_pdf = (pdf_zoclo(datos_bajos(query)), "zoclo.pdf", "Este zoclo todavía no se arma. Revisa las medidas.".encode("utf-8"))
        if pedido_pdf:
            pdf, nombre, aviso = pedido_pdf
            if pdf is None:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(aviso)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(aviso)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
            self.send_header("Content-Length", str(len(pdf)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pdf)
            return
        ejemplo = url.path == "/ejemplo" or (pieza == "columna" and query.get("ejemplo", [""])[0] == "1")
        cuerpo = responder(query, ejemplo=ejemplo, pieza=pieza).encode("utf-8")
        self._enviar(cuerpo, "text/html; charset=utf-8")

    def log_message(self, formato, *args):
        return


def main():
    servidor = ThreadingHTTPServer((HOST, PUERTO), Manejador)
    print(f"http://{HOST}:{PUERTO}/", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
