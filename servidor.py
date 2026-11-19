"""Servidor local del despiece. Solo escucha en esta máquina."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pagina import datos_bajos, responder
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
        query = parse_qs(url.query)
        pieza = "columna" if url.path in ("/ejemplo", "/columna") or query.get("pieza", [""])[0] == "columna" else "bajos"
        if pieza == "bajos" and url.path == "/" and query.get("carpintero", [""])[0] == "pdf":
            pdf = pdf_zoclo(datos_bajos(query))
            if pdf is None:
                aviso = "Este zoclo todavía no se arma. Revisa las medidas.".encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(aviso)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(aviso)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="zoclo.pdf"')
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
