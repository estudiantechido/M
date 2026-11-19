/* Render de la columna. El despiece de verdad lo calcula despiece.py.
   Aquí solo se dibuja, con las mismas reglas de armado:
   laterales de piso a techo, entrepaños entre ellos, puertas de parche,
   tapa hacia arriba y hueco sin fondo. */
(function () {
  const lienzo = document.getElementById("lienzo");
  const form = document.querySelector("form");
  const leyenda = document.getElementById("leyenda");
  const apertura = document.getElementById("apertura");
  if (!lienzo || !form) return;

  const ctx = lienzo.getContext("2d");
  const HOJA_ANCHO = 1220;
  const HOJA_LARGO = 2440;
  const CARAS = [
    [0, 3, 2, 1],
    [5, 6, 7, 4],
    [1, 2, 6, 5],
    [0, 4, 7, 3],
    [3, 7, 6, 2],
    [0, 1, 5, 4],
  ];
  const LUZ = normalizar({ x: -0.45, y: 0.82, z: -0.4 });
  const LUZ2 = normalizar({ x: 0.55, y: 0.25, z: -0.2 });
  const esBajos = document.body.dataset.pieza !== "columna";
  const cam = { yaw: esBajos ? 0.9 : -0.72, pitch: esBajos ? -0.38 : -0.34, zoom: 1 };
  const ficha = document.getElementById("ficha");
  let seleccion = null;
  let tocables = [];
  const marcaUrl = new URLSearchParams(location.hash.slice(1));
  if (marcaUrl.get("tabla")) seleccion = { tipo: "tabla", id: marcaUrl.get("tabla"), nota: "" };
  else if (marcaUrl.get("modulo")) seleccion = { tipo: "modulo", id: marcaUrl.get("modulo"), nota: "" };
  let arrastre = null;
  let editando = marcaUrl.get("editar") === "1";
  let cotasVivas = [];
  let ajusteEdicion = null;
  let pedido = 0;
  let reloj = 0;
  let marco = null;
  const MODULOS_VISTA = ["zoclo", "tarja", "vuelta", "esquina"];
  const vistaModulo = new Set(MODULOS_VISTA);
  if (marcaUrl.get("ojo") && MODULOS_VISTA.includes(marcaUrl.get("ojo"))) {
    vistaModulo.clear();
    vistaModulo.add(marcaUrl.get("ojo"));
  }

  function todosVisibles() {
    return MODULOS_VISTA.every((id) => vistaModulo.has(id));
  }

  function moduloPorNombre(id) {
    const n = (id || "").toLowerCase();
    if (n.startsWith("zoclo")) return "zoclo";
    if (n.includes("tarja")) return "tarja";
    if (n.includes("vuelta")) return "vuelta";
    if (n.includes("esquina")) return "esquina";
    return "";
  }

  function caraSeVe(cara) {
    const modulo = cara.modulo || moduloPorNombre(cara.id);
    if (!modulo) return true;
    return vistaModulo.has(modulo);
  }

  function normalizar(v) {
    const l = Math.hypot(v.x, v.y, v.z) || 1;
    return { x: v.x / l, y: v.y / l, z: v.z / l };
  }

  function producto(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
  }

  function cruz(a, b) {
    return {
      x: a.y * b.z - a.z * b.y,
      y: a.z * b.x - a.x * b.z,
      z: a.x * b.y - a.y * b.x,
    };
  }

  function restar(a, b) {
    return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
  }

  function textoCm(mm) {
    const valor = Number(mm) / 10;
    if (!Number.isFinite(valor)) return "";
    const decima = Math.round(valor * 10) / 10;
    const redondo = Math.round(decima);
    if (Math.abs(decima - redondo) < 1e-6) return String(redondo);
    return decima.toFixed(1);
  }

  function leerCm(nombre) {
    const campo = form.elements[nombre];
    if (!campo) return { cm: null, mal: false };
    const texto = String(campo.value || "").trim().replace(",", ".");
    if (texto === "") return { cm: null, mal: false };
    if (!/^-?\d+(\.\d+)?$/.test(texto)) return { cm: null, mal: true };
    const cm = Number(texto);
    if (!Number.isFinite(cm)) return { cm: null, mal: true };
    return { cm: Math.round(cm * 10) / 10, mal: false };
  }

  function entero(nombre) {
    const leido = leerCm(nombre);
    if (leido.mal || leido.cm === null) return { valor: null, mal: leido.mal };
    return { valor: Math.round(leido.cm * 10), mal: false };
  }

  function colorDe(nombre) {
    const t = nombre.toLowerCase();
    const tabla = [
      ["negro", [48, 46, 44]],
      ["weng", [62, 44, 34]],
      ["nogal", [146, 104, 70]],
      ["roble", [196, 164, 120]],
      ["cendra", [168, 164, 156]],
      ["gris", [176, 174, 168]],
      ["verde", [198, 206, 190]],
      ["azul", [176, 190, 200]],
      ["blanco", [246, 243, 236]],
    ];
    for (const fila of tabla) {
      if (t.includes(fila[0])) return fila[1];
    }
    return [246, 243, 236];
  }

  function leerColumna() {
    const alto = entero("alto");
    const fondo = entero("fondo");
    const espesor = entero("espesor");
    const fondoEsp = entero("fondo_esp");
    const zoclo = entero("zoclo");
    const holgura = entero("holgura");
    const huecoAncho = entero("hueco_ancho");
    const huecoAlto = entero("hueco_alto");
    const huecoDesde = entero("hueco_desde");
    const huecoFondo = entero("hueco_fondo");
    const color = (form.elements.color.value || "Blanco").trim() || "Blanco";
    const modo = form.elements.fondo_modo.value === "ranura" ? "ranura" : "clavado";
    const mal = [alto, fondo, espesor, fondoEsp, zoclo, holgura, huecoAncho, huecoAlto, huecoDesde, huecoFondo]
      .some((n) => n.mal);
    if (mal) return { ok: false, error: "Las medidas van en centímetros. Se puede usar un decimal." };
    if ([alto, fondo, espesor, fondoEsp, zoclo, holgura].some((n) => n.valor === null)) {
      return { ok: false, error: "Faltan medidas del cuerpo." };
    }
    if (holgura.valor < 0) return { ok: false, error: "La holgura no puede ser negativa." };
    if ([huecoAncho, huecoAlto, huecoDesde].some((n) => n.valor === null)) {
      return { ok: false, error: "Escribe el ancho del hueco, el alto del hueco y a qué altura del piso empieza." };
    }
    if ([huecoAncho, huecoAlto, huecoDesde].some((n) => n.valor <= 0)) {
      return { ok: false, error: "El hueco tiene que ser mayor que cero." };
    }
    if (huecoFondo.valor !== null && huecoFondo.valor <= 0) {
      return { ok: false, error: "El fondo que pide el horno tiene que ser mayor que cero." };
    }
    const m = {
      alto: alto.valor,
      fondo: fondo.valor,
      espesor: espesor.valor,
      fondoEsp: fondoEsp.valor,
      zoclo: zoclo.valor,
      holgura: holgura.valor,
      huecoAncho: huecoAncho.valor,
      huecoAlto: huecoAlto.valor,
      huecoDesde: huecoDesde.valor,
      huecoFondo: huecoFondo.valor,
      color,
      modo,
    };
    m.ancho = m.huecoAncho + 2 * m.espesor;
    m.claroAbajo = m.huecoDesde - m.zoclo - 2 * m.espesor;
    m.claroArriba = m.alto - m.huecoDesde - m.huecoAlto - 2 * m.espesor;
    m.altoPuerta = m.huecoDesde - m.zoclo - 2 * m.holgura;
    m.altoTapa = m.alto - (m.huecoDesde + m.huecoAlto) - 2 * m.holgura;
    m.anchoPuertas = m.ancho - 3 * m.holgura;
    m.anchoTapa = m.ancho - 2 * m.holgura;
    if (m.espesor < 9 || m.espesor > 30) return { ok: false, error: "El espesor queda fuera de 0.9 a 3 cm." };
    if (m.fondoEsp < 2 || m.fondoEsp > 12) return { ok: false, error: "El fondo tiene que quedar entre 0.2 y 1.2 cm." };
    if (m.zoclo >= m.alto) return { ok: false, error: "El zoclo es más alto que la columna." };
    if (m.claroAbajo <= 0) return { ok: false, error: "El hueco empieza tan abajo que choca con el piso del mueble." };
    if (m.claroArriba <= 0) return { ok: false, error: "El hueco termina tan arriba que choca con el techo del mueble." };
    if (m.altoPuerta < 120) return { ok: false, error: "Las puertas de abajo quedan demasiado bajas." };
    if (m.altoTapa < 120) return { ok: false, error: "La tapa de arriba queda demasiado baja." };
    if (m.anchoPuertas < 160 || m.anchoTapa < 80) return { ok: false, error: "El módulo queda demasiado angosto." };
    if (m.huecoFondo !== null && m.fondo < m.huecoFondo) {
      return { ok: false, error: "El fondo del mueble es menor que el fondo que escribiste para el horno." };
    }
    const prof = m.modo === "ranura" ? m.fondo - 10 : m.fondo;
    if (prof < 100) return { ok: false, error: "En ranura, el fondo del cuerpo no alcanza para el entrepaño." };
    m.prof = prof;
    const base = Math.floor(m.anchoPuertas / 2);
    const sobra = m.anchoPuertas - base * 2;
    m.puertaIzq = base + (sobra > 0 ? 1 : 0);
    m.puertaDer = base;
    const avisos = [];
    if (m.alto > HOJA_LARGO || m.fondo > HOJA_ANCHO || m.huecoAncho > HOJA_ANCHO) {
      avisos.push("Así se ve, pero una pieza no cabe en la hoja de 122 × 244 cm.");
    }
    return { ok: true, modelo: m, avisos };
  }

  function rotarY(p, origen, ang) {
    const dx = p.x - origen.x;
    const dz = p.z - origen.z;
    const c = Math.cos(ang);
    const s = Math.sin(ang);
    return { x: origen.x + dx * c + dz * s, y: p.y, z: origen.z - dx * s + dz * c };
  }

  function rotarX(p, origen, ang) {
    const dy = p.y - origen.y;
    const dz = p.z - origen.z;
    const c = Math.cos(ang);
    const s = Math.sin(ang);
    return { x: p.x, y: origen.y + dy * c - dz * s, z: origen.z + dy * s + dz * c };
  }

  function agregarCaja(caras, x0, y0, z0, x1, y1, z1, color, map, id, nota, modulo) {
    const esquinas = [
      [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
      [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
    ].map(([x, y, z]) => (map ? map({ x, y, z }) : { x, y, z }));
    for (const cara of CARAS) {
      caras.push({
        pts: cara.map((i) => esquinas[i]),
        color,
        id: id || "",
        nota: nota || "",
        modulo: modulo || "",
      });
    }
  }

  function modelo3d(m, abrir) {
    const e = m.espesor;
    const w = m.ancho;
    const h = m.alto;
    const d = m.fondo;
    const mel = colorDe(m.color);
    const metal = [188, 188, 184];
    const horno = [36, 38, 42];
    const vidrio = [22, 26, 30];
    const zocloColor = mel.map((c) => Math.round(c * 0.86));
    const caras = [];
    const angPuerta = (abrir / 100) * 1.2;
    const angTapa = (abrir / 100) * 1.25;
    const frente = -1;

    agregarCaja(caras, 0, 0, 0, e, h, d, mel);
    agregarCaja(caras, w - e, 0, 0, w, h, d, mel);
    agregarCaja(caras, e, m.zoclo, 0, w - e, m.zoclo + e, m.prof, mel);
    agregarCaja(caras, e, m.huecoDesde - e, 0, w - e, m.huecoDesde, m.prof, mel);
    agregarCaja(caras, e, m.huecoDesde + m.huecoAlto, 0, w - e, m.huecoDesde + m.huecoAlto + e, m.prof, mel);
    agregarCaja(caras, e, h - e, 0, w - e, h, m.prof, mel);

    const retroceso = Math.min(70, Math.max(0, d - e - 20));
    agregarCaja(caras, e, 0, retroceso, w - e, m.zoclo, retroceso + e, zocloColor);

    const yFondoInf0 = m.zoclo + e + 2;
    const yFondoInf1 = m.huecoDesde - e - 2;
    const yFondoSup0 = m.huecoDesde + m.huecoAlto + e + 2;
    const yFondoSup1 = h - e - 2;
    const zFondo = d - m.fondoEsp - 1;
    if (yFondoInf1 > yFondoInf0) {
      agregarCaja(caras, e + 2, yFondoInf0, zFondo, w - e - 2, yFondoInf1, zFondo + m.fondoEsp, mel);
    }
    if (yFondoSup1 > yFondoSup0) {
      agregarCaja(caras, e + 2, yFondoSup0, zFondo, w - e - 2, yFondoSup1, zFondo + m.fondoEsp, mel);
    }

    const profHorno = Math.min(m.huecoFondo || 525, d - 24);
    if (profHorno > 40) {
      const margen = Math.min(18, m.huecoAncho / 8, m.huecoAlto / 8);
      const x0 = e + margen;
      const x1 = w - e - margen;
      const y0 = m.huecoDesde + margen;
      const y1 = m.huecoDesde + m.huecoAlto - margen;
      agregarCaja(caras, x0, y0, 22, x1, y1, 22 + profHorno, horno);
      agregarCaja(caras, x0 + 10, y0 + 10, 16, x1 - 10, y1 - 10, 24, vidrio);
    }

    const yPuerta0 = m.zoclo + m.holgura;
    const yPuerta1 = m.huecoDesde - m.holgura;
    const xIzq0 = m.holgura;
    const xIzq1 = m.holgura + m.puertaIzq;
    const xDer1 = w - m.holgura;
    const xDer0 = xDer1 - m.puertaDer;
    const mapIzq = (p) => rotarY(p, { x: xIzq0, y: 0, z: frente }, angPuerta);
    const mapDer = (p) => rotarY(p, { x: xDer1, y: 0, z: frente }, -angPuerta);
    agregarCaja(caras, xIzq0, yPuerta0, frente - e, xIzq1, yPuerta1, frente, mel, mapIzq);
    agregarCaja(caras, xDer0, yPuerta0, frente - e, xDer1, yPuerta1, frente, mel, mapDer);

    const yAsa = (yPuerta0 + yPuerta1) / 2;
    agregarCaja(caras, xIzq1 - 36, yAsa - 70, frente - e - 16, xIzq1 - 22, yAsa + 70, frente - e, metal, mapIzq);
    agregarCaja(caras, xDer0 + 22, yAsa - 70, frente - e - 16, xDer0 + 36, yAsa + 70, frente - e, metal, mapDer);

    const yTapa0 = m.huecoDesde + m.huecoAlto + m.holgura;
    const yTapa1 = h - m.holgura;
    const xTapa0 = m.holgura;
    const xTapa1 = w - m.holgura;
    const mapTapa = (p) => rotarX(p, { x: 0, y: yTapa1, z: frente }, angTapa);
    agregarCaja(caras, xTapa0, yTapa0, frente - e, xTapa1, yTapa1, frente, mel, mapTapa);
    agregarCaja(
      caras,
      (xTapa0 + xTapa1) / 2 - 70,
      yTapa0 + 18,
      frente - e - 16,
      (xTapa0 + xTapa1) / 2 + 70,
      yTapa0 + 32,
      frente - e,
      metal,
      mapTapa
    );
    return caras;
  }

  function prepararLienzo() {
    const ancho = lienzo.clientWidth || 640;
    const alto = lienzo.clientHeight || 640;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    lienzo.width = Math.round(ancho * dpr);
    lienzo.height = Math.round(alto * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ancho, alto };
  }

  function proyectar(p, m, vista) {
    const box = marco || { x0: 0, y0: 0, z0: 0, ancho: m.ancho, alto: m.alto, fondo: m.fondo };
    const cx = p.x - box.x0 - box.ancho / 2;
    const cy = p.y - box.y0 - box.alto / 2;
    const cz = p.z - box.z0 - box.fondo / 2;
    const cosY = Math.cos(cam.yaw);
    const sinY = Math.sin(cam.yaw);
    const x1 = cx * cosY + cz * sinY;
    const z1 = -cx * sinY + cz * cosY;
    const cosP = Math.cos(cam.pitch);
    const sinP = Math.sin(cam.pitch);
    const y2 = cy * cosP - z1 * sinP;
    const z2 = cy * sinP + z1 * cosP;
    const medida = ajusteEdicion || {
      alto: box.alto,
      lado: Math.max(box.ancho, box.fondo),
      dist: Math.max(box.ancho, box.alto, box.fondo),
    };
    const dist = medida.dist * 2.4;
    const f = dist / (dist + z2);
    const porAlto = (vista.alto * 0.58) / medida.alto;
    const porAncho = (vista.ancho * 0.68) / medida.lado;
    const escala = Math.min(porAlto, porAncho) * cam.zoom;
    return {
      x: vista.ancho / 2 + x1 * f * escala,
      y: vista.alto * 0.56 - y2 * f * escala,
      z: z2,
    };
  }

  function pintarFondo(vista) {
    const grad = ctx.createLinearGradient(0, 0, 0, vista.alto);
    grad.addColorStop(0, "#efe4d2");
    grad.addColorStop(1, "#d7c4a8");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, vista.ancho, vista.alto);
  }

  function piezaMarcada(id) {
    if (!seleccion || !id) return false;
    if (seleccion.tipo === "tabla" || seleccion.tipo === "nota") return id === seleccion.id;
    const nombre = id.toLowerCase();
    if (seleccion.id === "zoclo") return nombre.startsWith("zoclo");
    if (nombre.startsWith("zoclo")) return false;
    return nombre.includes(seleccion.id);
  }

  function tono(color, id) {
    if (!seleccion) return color;
    if (piezaMarcada(id)) return [222, 104, 52];
    return color.map((c) => Math.round(c * 0.62 + 70));
  }

  function dibujarCara(pts, color, vista, m, meta) {
    const proy = pts.map((p) => proyectar(p, m, vista));
    const normal = normalizar(cruz(restar(pts[1], pts[0]), restar(pts[2], pts[0])));
    const cosY = Math.cos(cam.yaw);
    const sinY = Math.sin(cam.yaw);
    const x1 = normal.x * cosY + normal.z * sinY;
    const z1 = -normal.x * sinY + normal.z * cosY;
    const y2 = normal.y * Math.cos(cam.pitch) - z1 * Math.sin(cam.pitch);
    const z2 = normal.y * Math.sin(cam.pitch) + z1 * Math.cos(cam.pitch);
    if (z2 >= -0.02) return null;
    const key = Math.max(0, producto(normal, LUZ));
    const fill = Math.max(0, producto(normal, LUZ2));
    const k = Math.min(1.05, 0.74 + 0.34 * key + 0.08 * fill);
    const profundidad = (proy[0].z + proy[1].z + proy[2].z + proy[3].z) / 4;
    const marcada = Boolean(meta && meta.marcada);
    return {
      profundidad,
      proy,
      id: (meta && meta.id) || "",
      nota: (meta && meta.nota) || "",
      pintar() {
        ctx.beginPath();
        ctx.moveTo(proy[0].x, proy[0].y);
        for (let i = 1; i < proy.length; i += 1) ctx.lineTo(proy[i].x, proy[i].y);
        ctx.closePath();
        ctx.fillStyle = `rgb(${color.map((c) => Math.min(255, Math.round(c * k))).join(",")})`;
        ctx.fill();
        ctx.strokeStyle = marcada ? "#8c3b2a" : "rgba(48, 38, 28, 0.28)";
        ctx.lineWidth = marcada ? 2.5 : 1;
        ctx.stroke();
      },
    };
  }

  function dentro(pts, x, y) {
    let adentro = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i, i += 1) {
      const yi = pts[i].y;
      const yj = pts[j].y;
      if ((yi > y) !== (yj > y)) {
        const xi = pts[i].x;
        const xj = pts[j].x;
        const cruce = ((xj - xi) * (y - yi)) / (yj - yi) + xi;
        if (x < cruce) adentro = !adentro;
      }
    }
    return adentro;
  }

  function cartel(texto, x, y, color) {
    ctx.save();
    ctx.font = "15px Palatino, serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.lineJoin = "round";
    ctx.lineWidth = 4;
    ctx.strokeStyle = "rgba(246, 241, 231, 0.92)";
    ctx.strokeText(texto, x, y);
    ctx.fillStyle = color || "#1c1915";
    ctx.fillText(texto, x, y);
    ctx.restore();
  }

  function cota(origen, extremo, fueraOrigen, fueraExtremo, texto, vista, m, minimo, clase) {
    const o = proyectar(fueraOrigen, m, vista);
    const e = proyectar(fueraExtremo, m, vista);
    const a = proyectar(origen, m, vista);
    const b = proyectar(extremo, m, vista);
    const dx = e.x - o.x;
    const dy = e.y - o.y;
    const largo = Math.hypot(dx, dy);
    if (largo < (minimo || 34)) return;
    const ux = dx / largo;
    const uy = dy / largo;
    ctx.save();
    ctx.lineWidth = editando ? 1.6 : 1;
    ctx.strokeStyle = editando ? "rgba(140, 59, 42, 0.45)" : "rgba(48, 38, 28, 0.4)";
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(o.x, o.y);
    ctx.moveTo(b.x, b.y);
    ctx.lineTo(e.x, e.y);
    ctx.stroke();
    ctx.strokeStyle = editando ? "#8c3b2a" : "#1c1915";
    ctx.beginPath();
    ctx.moveTo(o.x, o.y);
    ctx.lineTo(e.x, e.y);
    const marca = 6;
    for (const p of [o, e]) {
      ctx.moveTo(p.x - ux * marca - uy * marca, p.y - uy * marca + ux * marca);
      ctx.lineTo(p.x + ux * marca + uy * marca, p.y + uy * marca - ux * marca);
    }
    ctx.stroke();
    if (editando) {
      ctx.fillStyle = "#8c3b2a";
      for (const p of [o, e]) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    let nx = -uy;
    let ny = ux;
    if (ny > 0) {
      nx = -nx;
      ny = -ny;
    }
    const tx = (o.x + e.x) / 2 + nx * 11;
    const ty = (o.y + e.y) / 2 + ny * 11;
    ctx.font = "13px Palatino, serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(246, 241, 231, 0.92)";
    const etiqueta = textoCm(texto);
    ctx.strokeText(etiqueta, tx, ty);
    ctx.fillStyle = editando ? "#8c3b2a" : "#1c1915";
    ctx.fillText(etiqueta, tx, ty);
    ctx.restore();
    cotasVivas.push({ x1: o.x, y1: o.y, x2: e.x, y2: e.y, tx, ty, mm: Number(texto), ux, uy, px: largo, marca: clase || "" });
  }

  function cotasBajos(m, vista) {
    const xV = m.fondoVuelta;
    const zV = m.proyeccion;
    const xT = xV + 1;
    const zT = zV + 1;
    const x1 = xT + m.anchoTarja;
    const z1 = zT + m.fondoBarra;
    const y1 = m.alto;
    cota({ x: 0, y: y1, z: z1 }, { x: x1, y: y1, z: z1 }, { x: 0, y: y1, z: z1 + 80 }, { x: x1, y: y1, z: z1 + 80 }, m.ancho, vista, m);
    cota({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: z1 }, { x: -100, y: 0, z: 0 }, { x: -100, y: 0, z: z1 }, m.fondo, vista, m);
    cota({ x: 0, y: 0, z: 0 }, { x: xV, y: 0, z: 0 }, { x: 0, y: 0, z: -80 }, { x: xV, y: 0, z: -80 }, m.fondoVuelta, vista, m);
    cota({ x: xT, y: 0, z: zT }, { x: x1, y: 0, z: zT }, { x: xT, y: 0, z: zT - 250 }, { x: x1, y: 0, z: zT - 250 }, m.anchoTarja, vista, m);
    cota({ x: x1, y: 0, z: zT }, { x: x1, y: 0, z: z1 }, { x: x1 + 80, y: 0, z: zT }, { x: x1 + 80, y: 0, z: z1 }, m.fondoBarra, vista, m);
    cota({ x: x1, y: 0, z: zT }, { x: x1, y: y1, z: zT }, { x: x1 + 160, y: 0, z: zT }, { x: x1 + 160, y: y1, z: zT }, m.alto, vista, m);
  }

  function cajasDe(m) {
    const fv = m.fondoVuelta;
    const fb = m.fondoBarra;
    const proy = m.proyeccion;
    const xT = fv + 1;
    const zT = proy + 1;
    return {
      tarja: [xT, 0, zT, xT + m.anchoTarja, m.alto, zT + fb],
      vuelta: [0, 0, 0, fv, m.alto, proy],
      esquina: [0, 0, zT, fv, m.alto, zT + fb],
      zoclo: [0, 0, 0, fv + m.anchoTarja, m.zoclo, proy + fb],
    };
  }

  function marcoDe(m) {
    if (m.clase !== "bajos" || todosVisibles()) {
      return { x0: 0, y0: 0, z0: 0, ancho: m.ancho, alto: m.alto, fondo: m.fondo };
    }
    if (vistaModulo.size === 1 && vistaModulo.has("zoclo")) {
      const { leg, arm } = marcosZoclo(m);
      const x0 = Math.min(leg.x0, arm.x0);
      const z0 = Math.min(leg.z0, arm.z0);
      const x1 = Math.max(leg.x1, arm.x1);
      const z1 = Math.max(leg.z1, arm.z1);
      return {
        x0, y0: 0, z0,
        ancho: Math.max(1, x1 - x0),
        alto: Math.max(1, m.zoclo),
        fondo: Math.max(1, z1 - z0),
      };
    }
    const cajas = cajasDe(m);
    let x0 = Infinity;
    let y0 = Infinity;
    let z0 = Infinity;
    let x1 = -Infinity;
    let y1 = -Infinity;
    let z1 = -Infinity;
    for (const id of MODULOS_VISTA) {
      if (!vistaModulo.has(id)) continue;
      const caja = cajas[id];
      x0 = Math.min(x0, caja[0]);
      y0 = Math.min(y0, caja[1]);
      z0 = Math.min(z0, caja[2]);
      x1 = Math.max(x1, caja[3]);
      y1 = Math.max(y1, caja[4]);
      z1 = Math.max(z1, caja[5]);
    }
    return {
      x0, y0, z0,
      ancho: Math.max(1, x1 - x0),
      alto: Math.max(1, y1 - y0),
      fondo: Math.max(1, z1 - z0),
    };
  }

  function cotasCajon(x0, z0, x1, z1, y0, y1, vista, m) {
    cota({ x: x0, y: y1, z: z1 }, { x: x1, y: y1, z: z1 }, { x: x0, y: y1, z: z1 + 70 }, { x: x1, y: y1, z: z1 + 70 }, x1 - x0, vista, m);
    cota({ x: x1, y: y1, z: z0 }, { x: x1, y: y1, z: z1 }, { x: x1 + 70, y: y1, z: z0 }, { x: x1 + 70, y: y1, z: z1 }, z1 - z0, vista, m);
    cota({ x: x1, y: y0, z: z0 }, { x: x1, y: y1, z: z0 }, { x: x1 + 140, y: y0, z: z0 }, { x: x1 + 140, y: y1, z: z0 }, y1 - y0, vista, m);
  }

  function numeroCelda(nombre, indice, defecto) {
    const fila = document.querySelector(`tr[data-tabla="${CSS.escape(nombre)}"]`);
    if (!fila) return defecto;
    const celda = fila.querySelectorAll("td")[indice];
    if (!celda) return defecto;
    const input = celda.querySelector("input");
    const n = Number(input ? input.value : celda.textContent);
    return Number.isFinite(n) && n > 0 ? n : defecto;
  }

  function huecoPie() {
    const campo = form.elements.zoclo_pie;
    if (!campo || String(campo.value).trim() === "") return 100;
    const leido = leerCm("zoclo_pie");
    if (leido.mal || leido.cm === null || leido.cm < 0) return 100;
    return Math.round(leido.cm * 10);
  }

  function campoNumero(nombre, defecto) {
    const campo = form.elements[nombre];
    if (!campo || String(campo.value).trim() === "") return defecto;
    const leido = leerCm(nombre);
    if (leido.mal || leido.cm === null) return defecto;
    return Math.round(leido.cm * 10);
  }

  function espesorPino() {
    const n = campoNumero("pino_esp", 20);
    return n > 0 ? n : 20;
  }

  function largoMarco(nombre, formula) {
    const campo = form.elements[nombre];
    if (!campo || campo.dataset.auto === "1" || String(campo.value).trim() === "") return formula;
    const leido = leerCm(nombre);
    if (leido.mal || leido.cm === null || leido.cm <= 0) return formula;
    return Math.round(leido.cm * 10);
  }

  function cantidadRef(nombreCampo, nombrePieza) {
    const campo = form.elements[nombreCampo];
    if (campo && String(campo.value).trim() !== "") {
      const n = Number(campo.value);
      if (Number.isFinite(n) && n >= 0) return Math.round(n);
    }
    return numeroCelda(nombrePieza, 1, 4);
  }

  function medidaEscrita(nombre) {
    const campo = form.elements.medidas;
    if (campo && String(campo.value).trim()) {
      try {
        const mapa = JSON.parse(campo.value);
        const par = mapa && mapa[nombre];
        if (Array.isArray(par) && Number(par[0]) > 0 && Number(par[1]) > 0) {
          return [Math.round(Number(par[0])), Math.round(Number(par[1]))];
        }
      } catch (error) {
        /* el JSON malo se ignora y el marco sigue la fórmula */
      }
    }
    const fila = document.querySelector(`tr[data-tabla="${CSS.escape(nombre)}"]`);
    const activo = document.activeElement;
    if (!fila || !activo || !fila.contains(activo)) return null;
    const inputs = fila.querySelectorAll("input.medida");
    if (inputs.length !== 2) return null;
    const alto = Number(String(inputs[0].value).replace(",", "."));
    const ancho = Number(String(inputs[1].value).replace(",", "."));
    if (!(alto > 0) || !(ancho > 0)) return null;
    return [Math.round(alto * 10), Math.round(ancho * 10)];
  }

  function marcosZoclo(m) {
    const fv = m.fondoVuelta;
    const proy = m.proyeccion;
    const pie = huecoPie();
    const nombreLeg = "Zoclo marco cajón 2 y el esquinero";
    const nombreArm = "Zoclo marco cajón 1";
    const editLeg = medidaEscrita(nombreLeg);
    const editArm = medidaEscrita(nombreArm);
    const ancho2 = Math.round(campoNumero("marco_a_2", 500));
    const ancho1 = Math.round(campoNumero("marco_a_1", 500));
    const legW = editLeg ? editLeg[1] : (ancho2 > 0 ? ancho2 : 500);
    const armW = editArm ? editArm[1] : (ancho1 > 0 ? ancho1 : 500);
    const legL = editLeg ? editLeg[0] : largoMarco("marco_l_2", proy + pie + legW - 10);
    const armL = editArm ? editArm[0] : largoMarco("marco_l_1", m.anchoTarja + pie - 10);
    // La puerta del cajón 2 está en x = fv. Las del cajón 1, en z = proy.
    // El hueco del pie queda en ese frente y el marco se corre atrás.
    // Los dos se tocan en la esquina y cierran el fondo en la misma línea.
    const legX1 = fv - pie;
    const armZ0 = proy + pie;
    const armZ1 = armZ0 + armW;
    return {
      pie,
      leg: {
        x0: legX1 - legW,
        z0: armZ1 - legL,
        x1: legX1,
        z1: armZ1,
        n: cantidadRef("ref_2", "Zoclo refuerzo cajón 2 y el esquinero"),
      },
      arm: {
        x0: legX1,
        z0: armZ0,
        x1: legX1 + armL,
        z1: armZ1,
        n: cantidadRef("ref_1", "Zoclo refuerzo cajón 1"),
      },
    };
  }

  function cotasZoclo(m, vista) {
    const y1 = m.zoclo;
    const { leg, arm } = marcosZoclo(m);
    cota({ x: leg.x0, y: y1, z: leg.z0 }, { x: leg.x0, y: y1, z: leg.z1 }, { x: leg.x0 - 80, y: y1, z: leg.z0 }, { x: leg.x0 - 80, y: y1, z: leg.z1 }, leg.z1 - leg.z0, vista, m, 8);
    cota({ x: leg.x0, y: y1, z: leg.z0 }, { x: leg.x1, y: y1, z: leg.z0 }, { x: leg.x0, y: y1, z: leg.z0 - 70 }, { x: leg.x1, y: y1, z: leg.z0 - 70 }, leg.x1 - leg.x0, vista, m, 8);
    cota({ x: arm.x0, y: y1, z: arm.z1 }, { x: arm.x1, y: y1, z: arm.z1 }, { x: arm.x0, y: y1, z: arm.z1 + 70 }, { x: arm.x1, y: y1, z: arm.z1 + 70 }, arm.x1 - arm.x0, vista, m, 8);
    cota({ x: arm.x1, y: y1, z: arm.z0 }, { x: arm.x1, y: y1, z: arm.z1 }, { x: arm.x1 + 70, y: y1, z: arm.z0 }, { x: arm.x1 + 70, y: y1, z: arm.z1 }, arm.z1 - arm.z0, vista, m, 8);
    cota({ x: arm.x1, y: 0, z: arm.z0 }, { x: arm.x1, y: y1, z: arm.z0 }, { x: arm.x1 + 150, y: 0, z: arm.z0 }, { x: arm.x1 + 150, y: y1, z: arm.z0 }, y1, vista, m, 8);
    const fv = m.fondoVuelta;
    const proy = m.proyeccion;
    const huecoVuelta = Math.round(fv - leg.x1);
    const huecoTarja = Math.round(arm.z0 - proy);
    if (huecoVuelta > 0) {
      cota({ x: fv, y: y1, z: leg.z0 }, { x: leg.x1, y: y1, z: leg.z0 }, { x: fv, y: y1, z: leg.z0 - 50 }, { x: leg.x1, y: y1, z: leg.z0 - 50 }, huecoVuelta, vista, m, 8, "pie");
    }
    if (huecoTarja > 0) {
      cota({ x: arm.x1, y: y1, z: proy }, { x: arm.x1, y: y1, z: arm.z0 }, { x: arm.x1 + 50, y: y1, z: proy }, { x: arm.x1 + 50, y: y1, z: arm.z0 }, huecoTarja, vista, m, 8, "pie");
    }
  }

  function cotasVisibles(m, vista) {
    if (todosVisibles()) {
      cotasBajos(m, vista);
      return;
    }
    const fv = m.fondoVuelta;
    const fb = m.fondoBarra;
    const proy = m.proyeccion;
    const y0 = m.zoclo;
    const y1 = m.alto;
    if (vistaModulo.has("zoclo")) cotasZoclo(m, vista);
    if (vistaModulo.has("tarja")) cotasCajon(fv, proy, fv + m.anchoTarja, proy + fb, y0, y1, vista, m);
    if (vistaModulo.has("vuelta")) cotasCajon(0, 0, fv, proy, y0, y1, vista, m);
    if (vistaModulo.has("esquina")) cotasCajon(0, proy, fv, proy + fb, y0, y1, vista, m);
  }

  function cotasColumna(m, vista) {
    const w = m.ancho;
    const h = m.alto;
    const d = m.fondo;
    cota({ x: 0, y: 0, z: 0 }, { x: w, y: 0, z: 0 }, { x: 0, y: 0, z: -80 }, { x: w, y: 0, z: -80 }, w, vista, m);
    cota({ x: w, y: 0, z: 0 }, { x: w, y: h, z: 0 }, { x: w + 90, y: 0, z: 0 }, { x: w + 90, y: h, z: 0 }, h, vista, m);
    cota({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: d }, { x: -80, y: 0, z: 0 }, { x: -80, y: 0, z: d }, d, vista, m);
    const yHueco = m.huecoDesde + m.huecoAlto;
    cota(
      { x: m.espesor, y: yHueco, z: 0 },
      { x: w - m.espesor, y: yHueco, z: 0 },
      { x: m.espesor, y: yHueco, z: -46 },
      { x: w - m.espesor, y: yHueco, z: -46 },
      m.huecoAncho,
      vista,
      m
    );
  }

  function leerBajos() {
    const tipo = form.elements.tipo ? form.elements.tipo.value : "cocina";
    if (tipo === "bano" || tipo === "closet") {
      return {
        ok: false,
        error: "El baño y el clóset todavía no están dibujados. En esos muebles el zoclo también va, y no se quita.",
      };
    }
    const largoBarra = entero("largo_barra");
    const fondoBarra = entero("fondo_barra");
    const largoVuelta = entero("largo_vuelta");
    const fondoVuelta = entero("fondo_vuelta");
    const anchoTarja = entero("ancho_tarja");
    const puertaVuelta = entero("puerta_vuelta");
    const altoBarra = entero("alto_barra");
    const espesor = entero("espesor");
    const fondoEsp = entero("fondo_esp");
    const zoclo = entero("zoclo");
    const holgura = entero("holgura");
    const entre = entero("entre_desde");
    const numeros = [
      largoBarra, fondoBarra, largoVuelta, fondoVuelta, anchoTarja, puertaVuelta,
      altoBarra, espesor, fondoEsp, zoclo, holgura, entre,
    ];
    if (numeros.some((n) => n.mal)) return { ok: false, error: "Las medidas van en centímetros. Se puede usar un decimal." };
    if (
      [largoBarra, fondoBarra, largoVuelta, fondoVuelta, anchoTarja, puertaVuelta, altoBarra, espesor, fondoEsp, zoclo, holgura]
        .some((n) => n.valor === null)
    ) {
      return { ok: false, error: "Falta una medida de la barra." };
    }
    if (holgura.valor < 0) return { ok: false, error: "La holgura no puede ser negativa." };
    if (entre.valor !== null && entre.valor <= 0) {
      return { ok: false, error: "La altura del entrepaño tiene que ser mayor que cero." };
    }
    const e = espesor.valor;
    const z = zoclo.valor;
    const hol = holgura.valor;
    const alto = altoBarra.valor;
    const fb = fondoBarra.valor;
    const fv = fondoVuelta.valor;
    const tarja = anchoTarja.valor;
    const puerta = puertaVuelta.valor;
    const modo = form.elements.fondo_modo.value === "ranura" ? "ranura" : "clavado";
    if (e < 9 || e > 30) return { ok: false, error: "El espesor queda fuera de 0.9 a 3 cm." };
    if (fondoEsp.valor < 2 || fondoEsp.valor > 12) return { ok: false, error: "El fondo tiene que quedar entre 0.2 y 1.2 cm." };
    if (z >= alto) return { ok: false, error: "El zoclo es más alto que la barra." };
    const altoPuerta = alto - z - 2 * hol;
    const proy = largoVuelta.valor - fb;
    if (altoPuerta < 120 || puerta < 120 || tarja - 3 * hol < 160) {
      return { ok: false, error: "Con estas medidas las puertas no salen." };
    }
    if (proy <= 2 * e) return { ok: false, error: "La vuelta tiene que salir más allá del fondo de la tarja." };
    if (puerta + 2 * hol > proy) {
      return { ok: false, error: `La puerta de ${textoCm(puerta)} cm no cabe en el tramo de ${textoCm(proy)} cm que sale la vuelta.` };
    }
    if (tarja <= 2 * e || fv <= 2 * e) return { ok: false, error: "Un módulo queda sin luz entre los laterales." };
    const pisoTop = z + e;
    const techoBottom = alto - e;
    if (techoBottom <= pisoTop) return { ok: false, error: "Entre el zoclo y el techo no queda hueco para el entrepaño." };
    let shelfTop;
    if (entre.valor === null) {
      const centro = Math.floor((pisoTop + techoBottom) / 2);
      shelfTop = centro - Math.floor(e / 2) + e;
    } else {
      shelfTop = entre.valor;
      if (shelfTop - e < pisoTop || shelfTop > techoBottom) {
        return { ok: false, error: "El entrepaño choca con el piso o con el techo del mueble." };
      }
    }
    const profBarra = modo === "ranura" ? fb - 10 : fb;
    const profVuelta = modo === "ranura" ? fv - 10 : fv;
    if (profBarra < 100 || profVuelta < 100) {
      return { ok: false, error: "En ranura, el fondo del cuerpo no alcanza para el entrepaño." };
    }
    const puertas = tarja - 3 * hol;
    const base = Math.floor(puertas / 2);
    const sobra = puertas - base * 2;
    const fijo = proy - puerta - 2 * hol;
    const avisos = [];
    if (fb > 1220 || fv > 1220 || tarja > 1220 || puerta > 1220 || alto > 2440) {
      avisos.push("Una pieza no cabe en la hoja de 122 × 244 cm.");
    }
    if (fb < 550 || fv < 550) avisos.push("Un fondo quedó debajo de 55 cm.");
    if (largoBarra.valor !== fv + tarja) {
      avisos.push(`El largo escrito (${textoCm(largoBarra.valor)} cm) no cierra con ${textoCm(fv + tarja)} cm. El dibujo usa la suma.`);
    }
    return {
      ok: true,
      avisos,
      modelo: {
        clase: "bajos",
        ancho: fv + tarja,
        alto,
        fondo: largoVuelta.valor,
        espesor: e,
        fondoEsp: fondoEsp.valor,
        zoclo: z,
        holgura: hol,
        color: (form.elements.color.value || "Blanco").trim() || "Blanco",
        modo,
        fondoBarra: fb,
        fondoVuelta: fv,
        anchoTarja: tarja,
        proyeccion: proy,
        profBarra,
        profVuelta,
        puertaVuelta: puerta,
        fijo: fijo >= 40 ? fijo : 0,
        puertaTarjaIzq: base + (sobra > 0 ? 1 : 0),
        puertaTarjaDer: base,
        altoPuerta,
        shelfTop,
        texto: `Barra en L ${textoCm(fv + tarja)} × ${textoCm(largoVuelta.valor)} cm · Alto ${textoCm(alto)} cm · Zoclo ${textoCm(z)} cm · Puertas ${textoCm(altoPuerta)} cm · Vuelta ${textoCm(puerta)} cm. La cubierta y la tarja no se cortan.`,
      },
    };
  }

  function modeloBajos(m, abrir) {
    const caras = [];
    const mel = colorDe(m.color);
    const e = m.espesor;
    const h = m.alto;
    const hol = m.holgura;
    const ang = (abrir / 100) * 1.15;
    const metal = [188, 188, 184];
    const piedra = [206, 202, 196];
    const fijoColor = mel.map((c) => Math.round(c * 0.94));
    const sep = 1;
    const fv = m.fondoVuelta;
    const fb = m.fondoBarra;
    const proy = m.proyeccion;
    const tarja = m.anchoTarja;
    const zTarja = proy + sep;
    const xTarja = fv + sep;

    function pisoTecho(x0, x1, z0, z1, clave) {
      agregarCaja(caras, x0, m.zoclo, z0, x1, m.zoclo + e, z1, mel, null, `Piso ${clave}`);
      agregarCaja(caras, x0, m.shelfTop - e, z0, x1, m.shelfTop, z1, mel, null, `Entrepaño ${clave}`);
      agregarCaja(caras, x0, h - e, z0, x1, h, z1, mel, null, `Techo ${clave}`);
    }

    function respaldo(x0, y0, z0, x1, y1, z1, id) {
      if (y1 > y0 && x1 > x0 && z1 > z0) agregarCaja(caras, x0, y0, z0, x1, y1, z1, mel, null, id);
    }

    function centrosMarco(largo, n, t) {
      if (n <= 0 || largo <= 2 * t) return [];
      const claro = largo - 2 * t - n * t;
      if (claro < 0) return [];
      const base = Math.floor(claro / (n + 1));
      const sobra = claro % (n + 1);
      let x = t;
      const centros = [];
      for (let i = 0; i < n; i += 1) {
        x += base + (i < sobra ? 1 : 0);
        centros.push(x + Math.floor(t / 2));
        x += t;
      }
      return centros;
    }

    function zocloMarco(fx0, fz0, fx1, fz1, nombre, refuerzos, largoEnX) {
      const zh = m.zoclo;
      const t = espesorPino();
      const pino = [176, 138, 92];
      if (zh < 8 || t < 8 || fx1 - fx0 < 30 || fz1 - fz0 < 30) return;
      const idMarco = `Zoclo marco ${nombre}`;
      const idRef = `Zoclo refuerzo ${nombre}`;
      const largo = Math.round(largoEnX ? fx1 - fx0 : fz1 - fz0);
      const corto = Math.round(largoEnX ? fz1 - fz0 : fx1 - fx0);
      const centros = corto - 2 * t >= 40 ? centrosMarco(largo, refuerzos, t) : [];
      if (largoEnX) {
        agregarCaja(caras, fx0, 0, fz0, fx1, zh, fz0 + t, pino, null, idMarco, "lado largo", "zoclo");
        agregarCaja(caras, fx0, 0, fz1 - t, fx1, zh, fz1, pino, null, idMarco, "lado largo", "zoclo");
        agregarCaja(caras, fx0, 0, fz0 + t, fx0 + t, zh, fz1 - t, pino, null, idMarco, "extremo", "zoclo");
        agregarCaja(caras, fx1 - t, 0, fz0 + t, fx1, zh, fz1 - t, pino, null, idMarco, "extremo", "zoclo");
        centros.forEach((c) => {
          const cx = fx0 + c;
          agregarCaja(caras, cx - t / 2, 0, fz0 + t, cx + t / 2, zh, fz1 - t, pino, null, idRef, "refuerzo", "zoclo");
        });
      } else {
        agregarCaja(caras, fx0, 0, fz0, fx0 + t, zh, fz1, pino, null, idMarco, "lado largo", "zoclo");
        agregarCaja(caras, fx1 - t, 0, fz0, fx1, zh, fz1, pino, null, idMarco, "lado largo", "zoclo");
        agregarCaja(caras, fx0 + t, 0, fz0, fx1 - t, zh, fz0 + t, pino, null, idMarco, "extremo", "zoclo");
        agregarCaja(caras, fx0 + t, 0, fz1 - t, fx1 - t, zh, fz1, pino, null, idMarco, "extremo", "zoclo");
        centros.forEach((c) => {
          const cz = fz0 + c;
          agregarCaja(caras, fx0 + t, 0, cz - t / 2, fx1 - t, zh, cz + t / 2, pino, null, idRef, "refuerzo", "zoclo");
        });
      }
    }
    const marcos = marcosZoclo(m);
    zocloMarco(marcos.leg.x0, marcos.leg.z0, marcos.leg.x1, marcos.leg.z1, "cajón 2 y el esquinero", marcos.leg.n, false);
    zocloMarco(marcos.arm.x0, marcos.arm.z0, marcos.arm.x1, marcos.arm.z1, "cajón 1", marcos.arm.n, true);

    // Vuelta: la punta queda hacia quien mira. La puerta da a la cocina, en +x.
    agregarCaja(caras, 0, m.zoclo, 0, fv, h, e, mel, null, "Lateral vuelta", "el de la punta");
    agregarCaja(caras, 0, m.zoclo, proy - e, fv, h, proy, mel, null, "Lateral vuelta", "el que pega con el esquinero");
    const profVx0 = m.modo === "ranura" ? fv - m.profVuelta : 0;
    pisoTecho(profVx0, fv, e, proy - e, "vuelta");
    const yF0 = m.zoclo + e + 2;
    const yF1 = h - e - 2;
    respaldo(1, yF0, e + 2, 1 + m.fondoEsp, yF1, proy - e - 2, "Fondo vuelta");

    const y0 = m.zoclo + hol;
    const y1 = y0 + m.altoPuerta;
    const zPuerta1 = proy;
    const zPuerta0 = zPuerta1 - m.puertaVuelta;
    const mapVuelta = (p) => rotarY(p, { x: fv, y: 0, z: zPuerta1 }, -ang);
    agregarCaja(caras, fv + sep, y0, zPuerta0, fv + sep + e, y1, zPuerta1, mel, mapVuelta, "Puerta vuelta", "en la cara de adentro, pegada al esquinero");
    const yAsa = (y0 + y1) / 2;
    agregarCaja(caras, fv + sep + e, yAsa - 50, zPuerta0 + 18, fv + sep + e + 14, yAsa + 50, zPuerta0 + 32, metal, mapVuelta, "jaladera", "", "vuelta");
    if (m.fijo > 0) {
      agregarCaja(caras, fv + sep, y0, hol, fv + sep + e, y1, hol + m.fijo, fijoColor, null, "Fijo vuelta", "en la punta, sin bisagra");
    }

    // Esquina ciega, contra la tarja y contra la vuelta.
    agregarCaja(caras, 0, m.zoclo, zTarja, e, h, zTarja + fb, mel, null, "Lateral esquina", "el de afuera");
    agregarCaja(caras, fv - e, m.zoclo, zTarja, fv, h, zTarja + fb, mel, null, "Lateral esquina", "el que pega con la tarja");
    const profEz = m.modo === "ranura" ? fb - 10 : fb;
    pisoTecho(e, fv - e, zTarja, zTarja + profEz, "esquina");
    respaldo(e + 2, yF0, zTarja + fb - m.fondoEsp - 1, fv - e - 2, yF1, zTarja + fb - 1, "Fondo esquina");

    // Tarja. Las puertas dan hacia quien mira, en el frente de este tramo.
    agregarCaja(caras, xTarja, m.zoclo, zTarja, xTarja + e, h, zTarja + fb, mel, null, "Lateral tarja", "el que pega con el esquinero");
    agregarCaja(caras, xTarja + tarja - e, m.zoclo, zTarja, xTarja + tarja, h, zTarja + fb, mel, null, "Lateral tarja", "el del extremo");
    const profTz = m.modo === "ranura" ? fb - 10 : fb;
    pisoTecho(xTarja + e, xTarja + tarja - e, zTarja, zTarja + profTz, "tarja");
    respaldo(xTarja + e + 2, yF0, zTarja + fb - m.fondoEsp - 1, xTarja + tarja - e - 2, yF1, zTarja + fb - 1, "Fondo tarja");

    const zFrente = zTarja - sep;
    function puertaTarja(x0, x1, lado, id) {
      const hingeX = lado === "izq" ? x0 : x1;
      const map = (p) => rotarY(p, { x: hingeX, y: 0, z: zTarja }, lado === "izq" ? ang : -ang);
      agregarCaja(caras, x0, y0, zFrente - e, x1, y1, zFrente, mel, map, id);
      const asaX = lado === "izq" ? x1 - 28 : x0 + 14;
      agregarCaja(caras, asaX, yAsa - 50, zFrente - e - 14, asaX + 14, yAsa + 50, zFrente - e, metal, map, "jaladera", "", "tarja");
    }
    puertaTarja(xTarja + hol, xTarja + hol + m.puertaTarjaIzq, "izq", "Puerta tarja izquierda");
    puertaTarja(xTarja + tarja - hol - m.puertaTarjaDer, xTarja + tarja - hol, "der", "Puerta tarja derecha");

    const verCubierta = todosVisibles() && !(seleccion && seleccion.tipo === "tabla" && seleccion.id.startsWith("Techo"));
    if (verCubierta) {
      agregarCaja(caras, -18, h - 16, -18, fv + 18, h, proy, piedra, null, "cubierta");
      agregarCaja(caras, -18, h - 16, zTarja, xTarja + tarja + 18, h, zTarja + fb + 18, piedra, null, "cubierta");
    }
    if (verCubierta) {
      const bw = Math.min(420, tarja * 0.4);
      const bd = Math.min(280, fb * 0.42);
      const cx = xTarja + tarja / 2;
      const cz = zTarja + fb * 0.46;
      agregarCaja(caras, cx - bw / 2, h - 10, cz - bd / 2, cx + bw / 2, h - 1, cz + bd / 2, [176, 184, 188], null, "tina");
      agregarCaja(caras, cx - bw / 2 + 16, h - 78, cz - bd / 2 + 16, cx + bw / 2 - 16, h - 8, cz + bd / 2 - 16, [62, 74, 82], null, "tina");
    }
    return caras;
  }

  function dibujar() {
    tocables = [];
    cotasVivas = [];
    marco = null;
    const vista = prepararLienzo();
    pintarFondo(vista);
    const leido = document.body.dataset.pieza === "columna" ? leerColumna() : leerBajos();
    if (!leido.ok) {
      ctx.fillStyle = "#5c5348";
      ctx.font = "18px Palatino, serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const palabras = leido.error.split(" ");
      const lineas = [];
      let actual = "";
      const maximo = vista.ancho * 0.72;
      for (const palabra of palabras) {
        const prueba = actual ? `${actual} ${palabra}` : palabra;
        if (ctx.measureText(prueba).width > maximo && actual) {
          lineas.push(actual);
          actual = palabra;
        } else {
          actual = prueba;
        }
      }
      if (actual) lineas.push(actual);
      const y0 = vista.alto / 2 - ((lineas.length - 1) * 26) / 2;
      lineas.forEach((linea, i) => ctx.fillText(linea, vista.ancho / 2, y0 + i * 26));
      leyenda.textContent = leido.error;
      leyenda.classList.add("falla");
      return;
    }
    const m = leido.modelo;
    marco = marcoDe(m);
    if (editando && !ajusteEdicion) {
      ajusteEdicion = {
        alto: marco.alto,
        lado: Math.max(marco.ancho, marco.fondo),
        dist: Math.max(marco.ancho, marco.alto, marco.fondo),
      };
    }
    if (!editando) ajusteEdicion = null;
    const abrir = Number(apertura.value);
    const piezas = m.clase === "bajos" ? modeloBajos(m, abrir) : modelo3d(m, abrir);
    const box = marco;
    const suelo = [
      { x: -m.ancho, y: -6, z: -m.fondo },
      { x: m.ancho * 2, y: -6, z: -m.fondo },
      { x: m.ancho * 2, y: -6, z: m.fondo * 2.2 },
      { x: -m.ancho, y: -6, z: m.fondo * 2.2 },
    ];
    const caraSuelo = dibujarCara(suelo, [186, 154, 112], vista, m);
    if (caraSuelo) caraSuelo.pintar();
    const centro = proyectar({ x: box.x0 + box.ancho / 2, y: 0, z: box.z0 + box.fondo / 2 }, m, vista);
    const rx = todosVisibles()
      ? Math.max(36, (m.ancho / m.alto) * vista.alto * 0.22 * cam.zoom)
      : Math.min(vista.ancho * 0.38, Math.max(28, (box.ancho / box.alto) * vista.alto * 0.1 * cam.zoom));
    const ry = rx * 0.28;
    ctx.save();
    ctx.translate(centro.x, centro.y);
    ctx.scale(1, ry / rx);
    ctx.beginPath();
    ctx.arc(0, 0, rx, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(60, 44, 30, 0.16)";
    ctx.fill();
    ctx.restore();

    const visibles = [];
    for (const cara of piezas) {
      if (m.clase === "bajos" && !caraSeVe(cara)) continue;
      const marcada = piezaMarcada(cara.id);
      const lista = dibujarCara(cara.pts, tono(cara.color, cara.id), vista, m, {
        id: cara.id,
        nota: cara.nota,
        marcada,
      });
      if (lista) visibles.push(lista);
    }
    visibles.sort((a, b) => b.profundidad - a.profundidad);
    tocables = visibles;
    for (const cara of visibles) cara.pintar();

    if (m.clase === "bajos") {
      const zTarja = m.proyeccion + 1;
      const xTarja = m.fondoVuelta + 1;
      const nombreSel = (seleccion && seleccion.id ? seleccion.id : "").toLowerCase();
      const activo = !seleccion
        ? ""
        : seleccion.tipo === "modulo"
          ? seleccion.id
          : nombreSel.startsWith("zoclo")
            ? "zoclo"
            : nombreSel.includes("tarja")
              ? "tarja"
              : nombreSel.includes("vuelta")
                ? "vuelta"
                : nombreSel.includes("esquina")
                  ? "esquina"
                  : "";
      const cajas = cajasDe(m);
      if (cajas[activo] && vistaModulo.has(activo)) {
        const [x0, y0, z0, x1, y1, z1] = cajas[activo];
        const esquinas = [
          [x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1],
          [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1],
        ].map(([x, y, z]) => proyectar({ x, y, z }, m, vista));
        const aristas = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]];
        ctx.save();
        ctx.strokeStyle = "#8c3b2a";
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (const [a, b] of aristas) {
          ctx.moveTo(esquinas[a].x, esquinas[a].y);
          ctx.lineTo(esquinas[b].x, esquinas[b].y);
        }
        ctx.stroke();
        ctx.restore();
      }
      if (vistaModulo.has("tarja")) {
        const pTarja = proyectar({ x: xTarja + m.anchoTarja / 2, y: m.alto + 48, z: zTarja + m.fondoBarra * 0.42 }, m, vista);
        cartel("Cajón 1", pTarja.x, pTarja.y);
      }
      if (vistaModulo.has("vuelta")) {
        const pVuelta = proyectar({ x: m.fondoVuelta * 0.42, y: m.alto + 48, z: m.proyeccion * 0.4 }, m, vista);
        cartel("Cajón 2", pVuelta.x, pVuelta.y);
      }
      if (vistaModulo.has("esquina")) {
        const pEsquina = proyectar({ x: m.fondoVuelta * 0.35, y: m.alto + 90, z: zTarja + m.fondoBarra * 0.55 }, m, vista);
        cartel("Esquinero", pEsquina.x, pEsquina.y);
      }
      if (vistaModulo.has("zoclo") && !todosVisibles() && vistaModulo.size > 1) {
        const zc = cajasDe(m).zoclo;
        const pZ = proyectar({ x: (zc[0] + zc[3]) / 2, y: m.zoclo + 36, z: (zc[2] + zc[5]) / 2 }, m, vista);
        cartel(`Zoclo ${textoCm(m.zoclo)} cm`, pZ.x, pZ.y);
      }
      if (seleccion && seleccion.tipo === "tabla") {
        const cara = tocables.filter((c) => c.id === seleccion.id).sort((a, b) => a.profundidad - b.profundidad)[0];
        if (cara) {
          const cx = cara.proy.reduce((s, p) => s + p.x, 0) / cara.proy.length;
          const cy = cara.proy.reduce((s, p) => s + p.y, 0) / cara.proy.length;
          cartel(seleccion.id, cx, cy - 8, "#8c3b2a");
        }
      }
      cotasVisibles(m, vista);
    } else {
      cotasColumna(m, vista);
    }

    const extra = leido.avisos.length ? ` ${leido.avisos[0]}` : "";
    const base = m.texto || `Ancho exterior ${textoCm(m.ancho)} cm · Alto ${textoCm(m.alto)} cm · Fondo ${textoCm(m.fondo)} cm.`;
    const nombresVista = { zoclo: "el zoclo", tarja: "el cajón 1", vuelta: "el cajón 2", esquina: "el esquinero" };
    const filtro = todosVisibles()
      ? ""
      : `Viendo ${MODULOS_VISTA.filter((id) => vistaModulo.has(id)).map((id) => nombresVista[id]).join(" y ")}. `;
    const edicion = editando ? "Editar: arrastra una cota, o cambia los centímetros de una pieza. Esa medida ya incluye el espesor. " : "";
    leyenda.textContent = `${edicion}${filtro}${base}${extra}`;
    leyenda.classList.toggle("falla", leido.avisos.length > 0);
  }

  function escribiendoMedida() {
    const activo = document.activeElement;
    return Boolean(
      activo &&
      activo.classList &&
      (activo.classList.contains("medida") || activo.classList.contains("de-parte"))
    );
  }

  function paramsDelPlano() {
    const autos = Array.from(document.querySelectorAll('input[data-auto="1"]'));
    const previos = autos.map((el) => el.value);
    autos.forEach((el) => { el.value = ""; });
    const params = new URLSearchParams(new FormData(form));
    autos.forEach((el, i) => { el.value = previos[i]; });
    return params;
  }

  function limpiarMedidasZoclo() {
    const campo = form.elements.medidas;
    if (!campo || !String(campo.value).trim()) return;
    try {
      const mapa = JSON.parse(campo.value);
      if (!mapa || typeof mapa !== "object" || Array.isArray(mapa)) return;
      let cambio = false;
      Object.keys(mapa).forEach((nombre) => {
        if (String(nombre).toLowerCase().startsWith("zoclo")) {
          delete mapa[nombre];
          cambio = true;
        }
      });
      if (cambio) campo.value = JSON.stringify(mapa);
    } catch (error) {
      campo.value = "";
    }
  }

  async function traerLista() {
    if (escribiendoMedida()) {
      programarLista();
      return;
    }
    const id = ++pedido;
    const consulta = paramsDelPlano();
    let respuesta;
    try {
      respuesta = await fetch(`/?${consulta.toString()}`, { headers: { Accept: "text/html" } });
    } catch (error) {
      if (id === pedido) leyenda.textContent += " No pude actualizar la lista.";
      return;
    }
    if (!respuesta.ok || id !== pedido) return;
    const html = await respuesta.text();
    if (id !== pedido) return;
    if (escribiendoMedida()) {
      programarLista();
      return;
    }
    const doc = new DOMParser().parseFromString(html, "text/html");
    const nuevo = doc.getElementById("resultado");
    const actual = document.getElementById("resultado");
    if (nuevo && actual) actual.replaceWith(nuevo);
    const nuevoBanner = doc.getElementById("banner");
    const banner = document.getElementById("banner");
    if (nuevoBanner && banner) banner.innerHTML = nuevoBanner.innerHTML;
    pintarOjos();
    pintarMedidas();
    marcarFila(false);
  }

  function guardarMedidas(fila) {
    const campo = form.elements.medidas;
    if (!campo || !fila) return;
    const inputs = fila.querySelectorAll("input.medida");
    if (inputs.length !== 2) return;
    const alto = Number(String(inputs[0].value).replace(",", "."));
    const ancho = Number(String(inputs[1].value).replace(",", "."));
    if (!(alto > 0) || !(ancho > 0)) return;
    let mapa = {};
    try {
      const previo = JSON.parse(campo.value || "{}");
      if (previo && typeof previo === "object" && !Array.isArray(previo)) mapa = previo;
    } catch (error) {
      mapa = {};
    }
    mapa[fila.dataset.tabla] = [Math.round(alto * 10), Math.round(ancho * 10)];
    campo.value = JSON.stringify(mapa);
  }

  function pintarMedidas() {
    document.querySelectorAll("#resultado tr[data-tabla]").forEach((fila) => {
      const celdas = fila.querySelectorAll("td");
      [2, 3].forEach((indice) => {
        const celda = celdas[indice];
        if (!celda) return;
        const input = celda.querySelector("input.medida");
        if (!editando) {
          if (input) celda.textContent = input.value;
          return;
        }
        if (input) return;
        const valor = celda.textContent.trim();
        celda.textContent = "";
        const caja = document.createElement("input");
        caja.type = "number";
        caja.min = "1";
        caja.max = "400";
        caja.step = "0.1";
        caja.inputMode = "decimal";
        caja.value = valor;
        caja.className = "medida";
        caja.setAttribute("aria-label", `${fila.dataset.tabla}, medida ${indice === 2 ? "1" : "2"}`);
        caja.addEventListener("keydown", (ev) => {
          if (ev.key === "Enter") {
            ev.preventDefault();
            caja.blur();
          }
        });
        caja.addEventListener("input", () => {
          dibujar();
        });
        caja.addEventListener("change", () => {
          guardarMedidas(fila);
          dibujar();
          programarLista();
        });
        celda.appendChild(caja);
      });
    });
  }

  function alternarOjo(id) {
    if (!MODULOS_VISTA.includes(id)) return;
    ajusteEdicion = null;
    if (todosVisibles()) {
      vistaModulo.clear();
      vistaModulo.add(id);
    } else if (vistaModulo.has(id) && vistaModulo.size === 1) {
      MODULOS_VISTA.forEach((modulo) => vistaModulo.add(modulo));
    } else if (vistaModulo.has(id)) {
      vistaModulo.delete(id);
    } else {
      vistaModulo.add(id);
    }
    pintarOjos();
    dibujar();
  }

  function pintarOjos() {
    document.querySelectorAll("[data-ojo]").forEach((boton) => {
      boton.setAttribute("aria-pressed", vistaModulo.has(boton.dataset.ojo) ? "true" : "false");
    });
    document.querySelectorAll("section.parte[data-modulo], #modulos [data-modulo], svg .zona[data-modulo]").forEach((nodo) => {
      nodo.classList.toggle("oculto", !vistaModulo.has(nodo.dataset.modulo));
    });
  }

  function textoDeSeleccion() {
    const sueltas = {
      cubierta: "La cubierta gris no es una tabla. No entra en el despiece.",
      tina: "La tarja dibujada no es una tabla. No entra en el despiece.",
      jaladera: "La jaladera no es una tabla. No entra en el despiece.",
    };
    if (!seleccion) return "Toca un mueble, una tabla del dibujo o una fila del despiece.";
    if (seleccion.tipo === "nota" || sueltas[seleccion.id]) return sueltas[seleccion.id] || seleccion.id;
    if (seleccion.tipo === "modulo") {
      return {
        zoclo: (() => {
          const leido = leerBajos();
          if (!leido.ok) return "Zócalo de pino. Revisa las medidas de la barra.";
          const { leg, arm, pie } = marcosZoclo(leido.modelo);
          return `Zócalo de pino de ${textoCm(espesorPino())} cm, atrás, con ${textoCm(pie)} cm libres al frente. El del cajón 2 y el esquinero mide ${textoCm(Math.round(leg.z1 - leg.z0))} × ${textoCm(Math.round(leg.x1 - leg.x0))} cm, con ${leg.n} refuerzos. El del cajón 1 mide ${textoCm(Math.round(arm.x1 - arm.x0))} × ${textoCm(Math.round(arm.z1 - arm.z0))} cm, con ${arm.n} refuerzos. Si borras un largo, vuelve a salir del plano.`;
        })(),
        tarja: "Cajón 1: el de la tarja, al frente, con dos puertas. Se sienta sobre su marco de pino.",
        vuelta: "Cajón 2: el de la vuelta, con una puerta y el fijo de la punta. Comparte el marco de pino con el esquinero.",
        esquina: "Esquinero: el cuadro de la esquina. No tiene puerta. Va sobre el mismo marco de pino del cajón 2.",
      }[seleccion.id] || "";
    }
    const fila = document.querySelector(`tr[data-tabla="${CSS.escape(seleccion.id)}"]`);
    if (!fila) return seleccion.id;
    const td = fila.querySelectorAll("td");
    const donde = fila.dataset.modulo === "zoclo"
      ? (seleccion.id.includes("cajón 2")
        ? "zócalo de pino del cajón 2 y el esquinero"
        : "zócalo de pino del cajón 1")
      : {
          tarja: "cajón 1, el de la tarja",
          vuelta: "cajón 2, el de la vuelta",
          esquina: "esquinero, el de la esquina sin puerta",
        }[fila.dataset.modulo] || "mueble";
    const textoCelda = (celda) => {
      if (!celda) return "";
      const input = celda.querySelector("input");
      return (input ? input.value : celda.textContent).trim();
    };
    const cant = Number(textoCelda(td[1]));
    const cuantas = cant > 1 ? ` En el despiece son ${cant} tablas iguales.` : "";
    const cual = seleccion.nota ? `, ${seleccion.nota}` : "";
    return `${td[0].textContent}${cual}: ${textoCelda(td[2])} × ${textoCelda(td[3])} cm, espesor ${textoCelda(td[4])} cm. Va en el ${donde}.${cuantas}`;
  }

  function marcarFila(conScroll) {
    document.querySelectorAll("tr.activa, #modulos button.activa, svg .zona.activa").forEach((nodo) => {
      nodo.classList.remove("activa");
    });
    if (ficha) {
      ficha.textContent = textoDeSeleccion();
      ficha.classList.toggle("activa", Boolean(seleccion));
    }
    if (!seleccion) return;
    if (seleccion.tipo === "tabla") {
      const fila = document.querySelector(`tr[data-tabla="${CSS.escape(seleccion.id)}"]`);
      if (fila) {
        fila.classList.add("activa");
        const boton = document.querySelector(`#modulos [data-modulo="${fila.dataset.modulo}"]`);
        if (boton) boton.classList.add("activa");
        if (conScroll) fila.scrollIntoView({ block: "nearest" });
      }
      return;
    }
    if (seleccion.tipo === "modulo") {
      document.querySelectorAll(`[data-modulo="${seleccion.id}"]`).forEach((nodo) => {
        if (nodo.matches("tr, button, g, section")) nodo.classList.add("activa");
      });
      const fila = document.querySelector(`section.parte[data-modulo="${seleccion.id}"]`);
      if (conScroll && fila) fila.scrollIntoView({ block: "nearest" });
    }
  }

  function elegir(sel) {
    if (seleccion && sel && seleccion.tipo === sel.tipo && seleccion.id === sel.id && seleccion.nota === (sel.nota || "")) {
      seleccion = null;
    } else {
      seleccion = sel;
    }
    marcarFila(true);
    dibujar();
  }

  function elegirCara(ev) {
    const rect = lienzo.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    let mejor = null;
    for (const cara of tocables) {
      if (!cara.id || !dentro(cara.proy, x, y)) continue;
      if (!mejor || cara.profundidad < mejor.profundidad) mejor = cara;
    }
    if (!mejor) {
      elegir(null);
      return;
    }
    if (mejor.id === "cubierta" || mejor.id === "tina" || mejor.id === "jaladera") {
      elegir({ tipo: "nota", id: mejor.id, nota: "" });
      return;
    }
    elegir({ tipo: "tabla", id: mejor.id, nota: mejor.nota || "" });
  }

  function programarLista() {
    clearTimeout(reloj);
    reloj = setTimeout(traerLista, 280);
  }

  function camposDeEspacio() {
    if (!esBajos) {
      const campos = ["alto", "fondo", "zoclo", "hueco_ancho", "hueco_alto", "hueco_desde"];
      const fondoHorno = form.elements.hueco_fondo;
      if (fondoHorno && fondoHorno.value.trim() !== "") campos.push("hueco_fondo");
      return campos;
    }
    const campos = [
      "largo_barra", "fondo_barra", "largo_vuelta", "fondo_vuelta",
      "ancho_tarja", "puerta_vuelta", "alto_barra", "zoclo",
    ];
    const entre = form.elements.entre_desde;
    if (entre && entre.value.trim() !== "") campos.push("entre_desde");
    return campos;
  }

  function fotoEspacio() {
    const foto = {};
    for (const nombre of camposDeEspacio()) {
      const leido = leerCm(nombre);
      if (leido.mal || leido.cm === null) return null;
      foto[nombre] = leido.cm;
    }
    return foto;
  }

  function aplicarFoto(foto) {
    for (const [nombre, valor] of Object.entries(foto)) {
      form.elements[nombre].value = textoCm(Math.round(Number(valor) * 10));
    }
  }

  function proporcionar(base, factor) {
    const foto = {};
    for (const [nombre, valor] of Object.entries(base)) {
      foto[nombre] = Math.max(0.1, Math.round(valor * factor * 10) / 10);
    }
    if (esBajos) {
      foto.largo_barra = Math.round((foto.fondo_vuelta + foto.ancho_tarja) * 10) / 10;
      const hol = (entero("holgura").valor || 0) / 10;
      const libre = Math.round((foto.largo_vuelta - foto.fondo_barra - 2 * hol) * 10) / 10;
      if (foto.puerta_vuelta > libre) foto.puerta_vuelta = Math.max(0.1, libre);
    }
    return foto;
  }

  function puntoLienzo(ev) {
    const rect = lienzo.getBoundingClientRect();
    return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
  }

  function distanciaSegmento(x, y, x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const largo = dx * dx + dy * dy || 1;
    let t = ((x - x1) * dx + (y - y1) * dy) / largo;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(x - (x1 + t * dx), y - (y1 + t * dy));
  }

  function cotaCercana(x, y) {
    let mejor = null;
    let dist = 22;
    for (const cotaLinea of cotasVivas) {
      if (!cotaLinea.mm) continue;
      const d = Math.min(
        distanciaSegmento(x, y, cotaLinea.x1, cotaLinea.y1, cotaLinea.x2, cotaLinea.y2),
        Math.hypot(x - cotaLinea.tx, y - cotaLinea.ty)
      );
      if (d < dist) {
        dist = d;
        mejor = cotaLinea;
      }
    }
    return mejor;
  }

  function moverProporcion(factor) {
    if (!arrastre || !arrastre.base) return;
    factor = Math.max(0.4, Math.min(1.65, factor));
    const previa = fotoEspacio();
    const foto = proporcionar(arrastre.base, factor);
    aplicarFoto(foto);
    if (form.elements.medidas) form.elements.medidas.value = "";
    const leido = esBajos ? leerBajos() : leerColumna();
    if (!leido.ok || !previa) {
      if (previa) aplicarFoto(previa);
      return;
    }
    dibujar();
    programarLista();
  }

  const CAMPOS_ZOCLO = ["marco_a_1", "marco_a_2", "marco_l_1", "marco_l_2", "pino_esp", "zoclo"];
  document.addEventListener("input", (ev) => {
    const el = ev.target;
    if (!el || el.form !== form) return;
    if (el.classList && el.classList.contains("de-parte") && String(el.name || "").startsWith("marco_l_")) {
      if (String(el.value).trim() === "") el.dataset.auto = "1";
      else delete el.dataset.auto;
    }
    if (CAMPOS_ZOCLO.includes(el.name)) limpiarMedidasZoclo();
    dibujar();
    programarLista();
  });
  form.addEventListener("submit", () => {
    document.querySelectorAll('input[data-auto="1"]').forEach((el) => { el.value = ""; });
  });
  apertura.addEventListener("input", dibujar);
  window.addEventListener("resize", dibujar);

  lienzo.addEventListener("pointerdown", (ev) => {
    const p = puntoLienzo(ev);
    if (editando) {
      const cotaLinea = cotaCercana(p.x, p.y);
      if (cotaLinea) {
        arrastre = {
          modo: cotaLinea.marca === "pie" ? "pie" : "cota",
          x: ev.clientX,
          y: ev.clientY,
          ux: cotaLinea.ux,
          uy: cotaLinea.uy,
          px: cotaLinea.px,
          mm: cotaLinea.mm,
          base: fotoEspacio(),
          movio: false,
        };
        lienzo.setPointerCapture(ev.pointerId);
        return;
      }
    }
    arrastre = { modo: "giro", x: ev.clientX, y: ev.clientY, yaw: cam.yaw, pitch: cam.pitch, movio: false };
    lienzo.setPointerCapture(ev.pointerId);
  });
  lienzo.addEventListener("pointermove", (ev) => {
    if (!arrastre) {
      if (!editando) return;
      const p = puntoLienzo(ev);
      lienzo.classList.toggle("en-cota", Boolean(cotaCercana(p.x, p.y)));
      return;
    }
    const dx = ev.clientX - arrastre.x;
    const dy = ev.clientY - arrastre.y;
    if (!arrastre.movio && dx * dx + dy * dy < 16) return;
    arrastre.movio = true;
    if (arrastre.modo === "cota" || arrastre.modo === "pie") {
      lienzo.classList.add("escalando");
      const delta = dx * arrastre.ux + dy * arrastre.uy;
      if (arrastre.modo === "pie") {
        const campo = form.elements.zoclo_pie;
        if (campo && arrastre.px > 0) {
          const nuevo = Math.round(arrastre.mm * (arrastre.px + delta) / arrastre.px);
          campo.value = textoCm(Math.max(0, Math.min(400, nuevo)));
          dibujar();
          programarLista();
        }
        return;
      }
      moverProporcion((arrastre.px + delta) / arrastre.px);
      return;
    }
    lienzo.classList.add("girando");
    cam.yaw = arrastre.yaw + dx * 0.008;
    cam.pitch = Math.max(-1.05, Math.min(0.2, arrastre.pitch + dy * 0.006));
    dibujar();
  });
  function soltar(ev) {
    const fueClic = arrastre && arrastre.modo !== "cota" && arrastre.modo !== "pie" && !arrastre.movio && ev.type === "pointerup";
    arrastre = null;
    lienzo.classList.remove("girando", "escalando");
    if (fueClic) elegirCara(ev);
  }
  lienzo.addEventListener("pointerup", soltar);
  lienzo.addEventListener("pointercancel", soltar);
  document.addEventListener("click", (ev) => {
    if (ev.target.closest("#lienzo")) return;
    if (ev.target.closest(".medidas-parte")) return;
    const ojo = ev.target.closest("[data-ojo]");
    if (ojo) {
      alternarOjo(ojo.dataset.ojo);
      return;
    }
    if (ev.target.closest("[data-carpintero]")) {
      const params = paramsDelPlano();
      params.set("carpintero", "pdf");
      const ficha = document.getElementById("ficha");
      fetch("/?" + params.toString()).then((res) => {
        const tipo = res.headers.get("Content-Type") || "";
        if (!res.ok || !tipo.includes("pdf")) throw new Error("sin pdf");
        return res.blob();
      }).then((blob) => {
        const enlace = document.createElement("a");
        const url = URL.createObjectURL(blob);
        enlace.href = url;
        enlace.download = "zoclo.pdf";
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
      }).catch(() => {
        if (ficha) ficha.textContent = "El zoclo todavía no se arma. Revisa las medidas y vuelve a pedir el PDF.";
      });
      return;
    }
    const fila = ev.target.closest("tr[data-tabla]");
    if (fila) {
      elegir({ tipo: "tabla", id: fila.dataset.tabla, nota: "" });
      return;
    }
    const zona = ev.target.closest("[data-modulo]");
    if (!zona || zona.closest("#vistas")) return;
    elegir({ tipo: "modulo", id: zona.dataset.modulo, nota: "" });
  });
  lienzo.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    cam.zoom = Math.max(0.65, Math.min(2.4, cam.zoom * (ev.deltaY > 0 ? 0.94 : 1.06)));
    dibujar();
  }, { passive: false });
  function ponerVista(nombre) {
    const bajos = document.body.dataset.pieza !== "columna";
    if (nombre === "frente") {
      cam.yaw = bajos ? 0.05 : 0;
      cam.pitch = bajos ? -0.22 : -0.08;
    } else if (nombre === "lado") {
      cam.yaw = bajos ? 1.35 : -1.38;
      cam.pitch = -0.28;
    } else {
      cam.yaw = bajos ? 0.9 : -0.72;
      cam.pitch = bajos ? -0.38 : -0.34;
    }
    cam.zoom = 1;
  }

  lienzo.addEventListener("dblclick", () => {
    ponerVista("tres");
    dibujar();
  });

  document.getElementById("vistas").addEventListener("click", (ev) => {
    const boton = ev.target.closest("button");
    if (!boton || !boton.dataset.vista) return;
    ponerVista(boton.dataset.vista);
    dibujar();
  });

  const botonEditar = document.getElementById("editar");
  function pintarEditar() {
    if (!botonEditar) return;
    botonEditar.setAttribute("aria-pressed", editando ? "true" : "false");
    lienzo.classList.toggle("editando", editando);
    if (!editando) lienzo.classList.remove("en-cota");
    pintarMedidas();
  }
  if (botonEditar) {
    botonEditar.addEventListener("click", () => {
      editando = !editando;
      ajusteEdicion = null;
      pintarEditar();
      dibujar();
    });
  }
  pintarEditar();

  pintarOjos();
  marcarFila(false);
  dibujar();
})();
