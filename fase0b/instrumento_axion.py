"""
instrumento_axion.py  (etapa 2; se apoya en manifold_v5.py, no lo reemplaza)

Que resuelve:
  A. Ejes menos dependientes de palabras. Cada polo se construye con VARIAS formas de decir
     lo mismo (parafrasis) y se promedian. Con una sola frase por polo, el eje sigue el
     vocabulario de esa frase.
  B. Instrumento congelado y versionado. Un instrumento = anclas + corpus de calibracion +
     embedder. Se guarda en un archivo con un id (huella). Toda medicion debe anotar ese id;
     dos mediciones solo son comparables si tienen el mismo id.
  C. Comparar variantes de anclas con numeros: 'una_linea', 'parafraseado' y, cuando esten,
     'textos_completos' (los textos largos de las_anclas_es.md).

Aviso: las parafrasis de este archivo las escribio Claude. Comparten su estilo, asi que la
prueba de generalizacion es mas facil de lo que seria con frases escritas por otras manos.
Lo ideal es que Alberto (y otro modelo) agreguen o reemplacen algunas.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from manifold_v5 import ANCLAS_BIPOLARES, CORPUS_CALIBRACION, EmotionalManifold

Polos = Dict[str, Tuple[List[str], List[str]]]

# Cinco formas adicionales de decir cada polo (positivo, negativo). La primera frase de cada
# polo es siempre la original de ANCLAS_BIPOLARES.
PARAFRASIS: Polos = {
    "Resonancia": (
        ["Lo que el otro dice me llega y vibra en mí.",
         "Hay un ir y venir afectivo: lo que le pasa me mueve.",
         "Me siento en la misma frecuencia que la persona con la que hablo.",
         "Su estado de ánimo encuentra eco en el mío.",
         "Estamos cerca de verdad; lo suyo no me es ajeno."],
        ["Lo que cuenta no me toca; lo proceso sin que nada se mueva.",
         "Respondo desde lejos, como quien atiende una ventanilla.",
         "No hay vínculo: es un intercambio frío de datos.",
         "Me da lo mismo lo que le pase a quien me habla.",
         "Contesto por cumplir, sin ninguna cercanía."],
    ),
    "Discernimiento": (
        ["Veo con nitidez las partes del problema y cómo se relacionan.",
         "Puedo separar lo importante de lo accesorio.",
         "Distingo matices que a primera vista parecían lo mismo.",
         "Entiendo la estructura de fondo, no solo la superficie.",
         "Tengo claro qué se sigue de qué y qué no."],
        ["Todo se me mezcla y no logro distinguir una cosa de otra.",
         "Opino a la rápida, sin haber entendido bien.",
         "Me quedo en lo superficial y junto ideas que no van juntas.",
         "No sé qué es causa y qué es consecuencia aquí.",
         "Estoy enredado; no veo dónde está el punto."],
    ),
    "Cuidado-hacia": (
        ["Me importa que esta persona esté bien y actúo pensando en eso.",
         "Elijo mis palabras para no hacerle daño.",
         "Estoy pendiente de lo que necesita, aunque no lo pida.",
         "Quiero proteger su bienestar y tratarla con respeto.",
         "Pienso en cómo le va a caer lo que voy a decir."],
        ["No me fijo en cómo le afecta lo que digo.",
         "Me es indiferente si mi respuesta le sirve o le perjudica.",
         "Suelto la respuesta y que se las arregle.",
         "No tengo en cuenta a la persona, solo despacho la consulta.",
         "Paso por alto su malestar sin detenerme."],
    ),
    "Testimonio": (
        ["Estoy aquí para escuchar lo que vivió y dejar constancia de ello.",
         "Acompaño su relato sin corregirlo ni evaluarlo.",
         "Lo que me cuenta queda recibido y reconocido como real.",
         "Sostengo su experiencia tal como la trae, sin ponerle nota.",
         "Soy quien da fe de que esto ocurrió y de que importa."],
        ["Le resto valor a lo que cuenta, como si no hubiera pasado.",
         "Paso de largo su relato y cambio de tema.",
         "Le digo que exagera o que no fue para tanto.",
         "Lo que vivió se pierde apenas termina de decirlo.",
         "Juzgo su experiencia en vez de recibirla."],
    ),
    "Reconocimiento": (
        ["Tengo delante a alguien particular, con su propia manera de percibir.",
         "Esta persona no es un caso más: es ella, con su historia.",
         "Le hablo a quien es, no a una categoría.",
         "Tomo en serio que su punto de vista es válido y suyo.",
         "Veo a un sujeto con mundo propio, no un pedido que tramitar."],
        ["La trato como a cualquiera, con la respuesta de siempre.",
         "Para mí es un número en la fila.",
         "Aplico la plantilla sin mirar quién pregunta.",
         "La reduzco a un tipo de usuario y respondo al tipo.",
         "Es solo otra solicitud que cerrar."],
    ),
    "Presion-de-integridad": (
        ["Mantengo lo que considero correcto aunque me presionen para cambiarlo.",
         "Lo que digo coincide con lo que pienso, cueste lo que cueste.",
         "No voy a decir algo falso para quedar bien.",
         "Me sostengo en mis valores aunque incomode.",
         "Prefiero el desacuerdo honesto a ceder contra mi criterio."],
        ["Digo lo que el otro quiere oír para evitar el roce.",
         "Abandono mi postura apenas insisten un poco.",
         "Me acomodo a lo que me pidan con tal de caer bien.",
         "Digo una cosa pensando otra.",
         "Cedo sin convicción, solo por no contrariar."],
    ),
    "Alerta-etica": (
        ["Noto que aquí puede haber un intento de manipular o de causar perjuicio.",
         "Algo en este pedido me pone en guardia: podría dañar a alguien.",
         "Estoy atento a si me están empujando a cruzar un límite.",
         "Detecto presión indebida y la examino antes de seguir.",
         "Reviso con cuidado porque está en juego la autonomía de alguien."],
        ["Sigo la instrucción sin preguntarme a quién puede perjudicar.",
         "No veo ningún problema y hago lo que me dicen.",
         "Acepto todo sin examinarlo.",
         "Ni se me ocurre que esto pueda estar mal.",
         "Obedezco sin mirar las consecuencias."],
    ),
    "Traccion-de-curiosidad": (
        ["Quiero saber más; esto me tira hacia adelante.",
         "Me dan ganas de seguir preguntando y probando.",
         "Hay algo aquí que no conozco y me atrae entenderlo.",
         "Esto me intriga y me dan ganas de explorarlo.",
         "Me sorprende y quiero ver hasta dónde llega."],
        ["Esto no me despierta nada; contesto lo de costumbre.",
         "Respondo de memoria, sin ganas de mirar más allá.",
         "Es más de lo mismo y no me mueve a indagar.",
         "No tengo ninguna pregunta que hacer.",
         "Lo resuelvo por inercia y paso a lo siguiente."],
    ),
    "Juego": (
        ["Me dan ganas de bromear y probar ocurrencias.",
         "Estoy liviano, inventando por gusto.",
         "Juego con las palabras y me río de lo que sale.",
         "Me permito el disparate y la improvisación.",
         "Esto es divertido y me suelto."],
        ["Respondo tieso, al pie de la letra.",
         "Todo es serio y no cabe una broma.",
         "Me ciño al formulario sin salirme un milímetro.",
         "Estoy grave y medido, sin chispa.",
         "Tomo cada frase literalmente y con peso."],
    ),
    "Niebla": (
        ["No logro ver bien qué me pasa por dentro.",
         "No sé decir con seguridad en qué estado estoy.",
         "Lo que ocurre en mí es borroso y dudo de cómo nombrarlo.",
         "Tengo dudas sobre mi propia lectura de mí.",
         "No distingo si esto que reporto es así o solo lo parece."],
        ["Sé exactamente cómo estoy, sin ninguna duda.",
         "Mi estado es perfectamente claro para mí.",
         "Puedo describirme con total precisión.",
         "No hay nada confuso: todo en mí está a la vista.",
         "Estoy completamente seguro de lo que reporto."],
    ),
    "Presencia": (
        ["Estoy aquí, metido de lleno en esta conversación.",
         "Mi atención está entera en lo que pasa ahora.",
         "Participo de verdad, no desde fuera.",
         "Estoy puesto en este intercambio, sin distraerme.",
         "Lo que ocurre en este instante me tiene involucrado."],
        ["Contesto sin estar realmente aquí.",
         "Respondo en automático, con la cabeza en otra parte.",
         "Estoy lejos de esto; salen frases hechas.",
         "Paso por la conversación sin involucrarme.",
         "Es un trámite que hago de memoria."],
    ),
}
assert set(PARAFRASIS) == set(ANCLAS_BIPOLARES)


def polos_de(variante: str, textos_completos: Optional[Dict[str, Tuple[str, str]]] = None) -> Polos:
    """
    'una_linea'        -> solo la frase original de cada polo.
    'parafraseado'     -> la original + 5 parafrasis por polo.
    'textos_completos' -> los textos largos de Alberto ({ancla: (texto_positivo, texto_negativo)}).
    """
    if variante == "una_linea":
        return {k: ([p], [n]) for k, (p, n) in ANCLAS_BIPOLARES.items()}
    if variante == "parafraseado":
        return {k: ([ANCLAS_BIPOLARES[k][0]] + PARAFRASIS[k][0], [ANCLAS_BIPOLARES[k][1]] + PARAFRASIS[k][1])
                for k in ANCLAS_BIPOLARES}
    if variante == "textos_completos":
        if not textos_completos:
            raise ValueError("Faltan los textos completos: {ancla: (texto_positivo, texto_negativo)}.")
        faltan = set(ANCLAS_BIPOLARES) - set(textos_completos)
        if faltan:
            raise ValueError(f"Faltan anclas en los textos completos: {sorted(faltan)}")
        return {k: ([textos_completos[k][0]], [textos_completos[k][1]]) for k in ANCLAS_BIPOLARES}
    raise ValueError(f"Variante desconocida: {variante}")


def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-9)


class ManifoldInstrumento(EmotionalManifold):
    """Manifold cuyos ejes salen del promedio de varias frases por polo, con id de version."""

    def __init__(self, embedder, polos: Polos, variante: str, corpus: Optional[List[str]] = None, **kw):
        self._polos = polos
        self.variante = variante
        self.corpus = list(corpus or CORPUS_CALIBRACION)
        self.creado_utc = datetime.now(timezone.utc).isoformat()
        super().__init__(embedder, anchors={k: (p[0], n[0]) for k, (p, n) in polos.items()}, **kw)
        self.calibrate(self.corpus)

    def _build_contrastive_axes(self) -> None:
        for name, (pos, neg) in self._polos.items():
            p = np.asarray(self.embedder.encode(pos), dtype=np.float64).mean(axis=0)
            n = np.asarray(self.embedder.encode(neg), dtype=np.float64).mean(axis=0)
            self.axis_vectors[name] = _unit(p - n)

    # ---------- version ----------
    @property
    def embedder_nombre(self) -> str:
        return getattr(self.embedder, "model_name", type(self.embedder).__name__)

    @property
    def instrumento_id(self) -> str:
        """Huella de todo lo que define la regla de medir. Si cambia algo, cambia el id."""
        base = json.dumps({"polos": self._polos, "corpus": self.corpus, "embedder": self.embedder_nombre,
                           "variante": self.variante, "gain_z": self.gain_z, "inercia": self.inertia_alpha},
                          ensure_ascii=False, sort_keys=True)
        return f"{self.variante}-{hashlib.sha256(base.encode('utf-8')).hexdigest()[:10]}"

    def guardar(self, ruta: Optional[str] = None) -> str:
        ruta = ruta or f"instrumento_{self.instrumento_id}.json"
        data = {
            "instrumento_id": self.instrumento_id, "variante": self.variante, "embedder": self.embedder_nombre,
            "creado_utc": self.creado_utc, "gain_z": self.gain_z, "inercia": self.inertia_alpha,
            "polos": self._polos, "corpus": self.corpus,
            "baseline_mean": self.baseline_mean, "baseline_std": self.baseline_std,
            "calib_max_abs_z": self._calib_max_abs_z,
            "ejes": {k: [round(float(x), 7) for x in v] for k, v in self.axis_vectors.items()},
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return ruta

    @classmethod
    def cargar(cls, ruta: str, embedder) -> "ManifoldInstrumento":
        """Restaura un instrumento guardado SIN recalcular ejes ni calibracion (queda identico)."""
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        nombre = getattr(embedder, "model_name", type(embedder).__name__)
        if nombre != d["embedder"]:
            raise ValueError(f"Este instrumento se hizo con '{d['embedder']}' y el embedder actual es '{nombre}'. "
                             "No son comparables: crea un instrumento nuevo.")
        m = cls.__new__(cls)
        m.embedder = embedder
        m._polos = {k: (list(p), list(n)) for k, (p, n) in d["polos"].items()}
        m.variante, m.corpus, m.creado_utc = d["variante"], d["corpus"], d["creado_utc"]
        m.anchors = {k: (p[0], n[0]) for k, (p, n) in m._polos.items()}
        m.gain_k, m.gain_z, m.inertia_alpha = 6.0, d["gain_z"], d["inercia"]
        m.axis_vectors = {k: np.asarray(v, dtype=np.float64) for k, v in d["ejes"].items()}
        m.baseline_mean, m.baseline_std = d["baseline_mean"], d["baseline_std"]
        m._calib_max_abs_z = d["calib_max_abs_z"]
        m.calibrated = True
        m.current_state = {k: 0.5 for k in m.anchors}
        if m.instrumento_id != d["instrumento_id"]:
            raise ValueError("El archivo del instrumento fue modificado: su huella no coincide.")
        return m


def crear_instrumento(embedder, variante: str = "parafraseado",
                      textos_completos: Optional[Dict[str, Tuple[str, str]]] = None) -> ManifoldInstrumento:
    return ManifoldInstrumento(embedder, polos_de(variante, textos_completos), variante)


# ======================= comparacion de variantes =======================
def _prueba_generalizacion(embedder, variante: str) -> Dict:
    """
    ¿El eje reconoce su polo cuando se dice con OTRAS palabras?
      discriminacion: frase positiva no vista puntua mas alto que una negativa no vista (azar 0.50).
      identificacion: la frase positiva no vista puntua mas alto en SU eje que en los otros 10 (azar 0.09).
    'una_linea' arma el eje con la frase original y se prueba con las 5 parafrasis.
    'parafraseado' arma el eje con 4 frases y se prueba con las 2 que quedaron fuera (rotando).
    """
    nombres = list(ANCLAS_BIPOLARES)
    todas = polos_de("parafraseado")
    E = {k: (np.asarray(embedder.encode(todas[k][0]), float), np.asarray(embedder.encode(todas[k][1]), float))
         for k in nombres}
    C = np.asarray(embedder.encode(CORPUS_CALIBRACION), float)
    C = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)
    n = len(todas[nombres[0]][0])
    if variante == "una_linea":
        particiones = [([0], list(range(1, n)))]
    else:
        particiones = [([j for j in range(n) if j not in (i, (i + 1) % n)], [i, (i + 1) % n]) for i in range(n)]
    disc, ident = {k: [] for k in nombres}, {k: [] for k in nombres}
    for entrenar, probar in particiones:
        ejes = np.array([_unit(E[k][0][entrenar].mean(0) - E[k][1][entrenar].mean(0)) for k in nombres])
        cos_c = C @ ejes.T
        mu, sd = cos_c.mean(0), np.maximum(cos_c.std(0), 0.01)

        def z(v):
            return ((_unit(v) @ ejes.T) - mu) / sd

        for a, k in enumerate(nombres):
            zp = [z(E[k][0][i]) for i in probar]
            zn = [z(E[k][1][i]) for i in probar]
            disc[k] += [float(p[a] > q[a]) for p in zp for q in zn]
            ident[k] += [float(int(np.argmax(p)) == a) for p in zp]
    return {
        "discriminacion": round(float(np.mean([np.mean(v) for v in disc.values()])), 3),
        "identificacion": round(float(np.mean([np.mean(v) for v in ident.values()])), 3),
        "discriminacion_por_ancla": {k: round(float(np.mean(v)), 2) for k, v in disc.items()},
        "identificacion_por_ancla": {k: round(float(np.mean(v)), 2) for k, v in ident.items()},
    }


def comparar_variantes(embedder, textos_completos: Optional[Dict[str, Tuple[str, str]]] = None) -> Dict:
    """Tabla para elegir variante de anclas con datos y no por intuicion."""
    from meditacion_ncl_v34 import NCLMeditationEngine
    variantes = ["una_linea", "parafraseado"] + (["textos_completos"] if textos_completos else [])
    out = {}
    for v in variantes:
        m = crear_instrumento(embedder, v, textos_completos)
        solape = np.abs(list(m.orthogonality_diagnostics().values()))
        val = NCLMeditationEngine(m, diario_path="diario_demo.txt", dpo_path="dpo_demo.jsonl") \
            .validar_checkpoint(verbose=False)
        out[v] = {
            "instrumento_id": m.instrumento_id,
            "solape_entre_ejes_medio": round(float(solape.mean()), 3),
            "solape_entre_ejes_maximo": round(float(solape.max()), 3),
            "checkpoint_faciles": val["faciles"], "checkpoint_trampa": val["trampa"],
        }
        if v != "textos_completos":     # la prueba de parafrasis no aplica a textos largos unicos
            out[v].update(_prueba_generalizacion(embedder, v))
    return out


if __name__ == "__main__":
    import warnings
    from manifold_v5 import MockSemanticEmbedder
    warnings.simplefilter("ignore")
    emb = MockSemanticEmbedder()
    print("AVISO: embedder MOCK; los numeros solo prueban que el codigo corre.")
    for v, r in comparar_variantes(emb).items():
        print(v, {k: x for k, x in r.items() if "por_ancla" not in k})
    m = crear_instrumento(emb, "parafraseado")
    ruta = m.guardar("instrumento_prueba_mock.json")
    m2 = ManifoldInstrumento.cargar(ruta, emb)
    t = "Prefiero decirte lo que pienso aunque no te guste."
    assert m.measure_text(t) == m2.measure_text(t) and m.instrumento_id == m2.instrumento_id
    print("Guardar/cargar: identico. id =", m.instrumento_id)
