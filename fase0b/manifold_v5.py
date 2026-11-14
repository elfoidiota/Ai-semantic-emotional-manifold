"""
manifold_v5.py  (reemplaza manifold_v4.py; v4 y v3 quedan intactos como respaldo)

Cambios respecto a v4:
  1. Calibracion con DOS registros: frases informativas (como en v4) + frases
     conversacionales de asistente con afecto bajo. En v4 el "punto neutro" eran solo
     frases tipo enciclopedia, asi que cualquier respuesta de chat quedaba lejos del
     neutro por su registro y no por su estado (z inflados -> sigmoide saturado).
  2. ABREVIATURAS unicas por ancla (en v3.3 "Pres" servia para Presencia y para
     Presion-de-integridad).
  3. HarrierEmbedder: usa el prompt 'sts_query' en anclas y textos (asi lo pide el modelo
     para comparar textos entre si), funciona con o sin GPU, y prueba dtype / torch_dtype
     segun la version de transformers que traiga Colab.
  4. baseline_max_abs_z(): distribucion de max|z| sobre el corpus neutro. La usa la
     meditacion v3.4 para que la capa LIF no dispare con texto corriente.

Nota de lectura: para ESTADISTICA usa siempre z (canal_centrado_z). El canal
instantaneo (sigmoide) es para el estado con inercia; satura en los extremos.
"""
import hashlib
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np


class EmbedderProtocol(Protocol):
    """Contrato para cualquier motor de embeddings (Harrier, local o mock)."""
    def encode(self, texts: List[str]) -> np.ndarray:
        ...


class MockSemanticEmbedder:
    """
    Embedder determinista SIN semantica (vectores pseudoaleatorios por texto).
    Sirve solo para probar que el codigo corre. Nunca para sacar conclusiones.
    """
    is_mock = True
    model_name = "mock"

    def __init__(self, dim: int = 384, seed: int = 42):
        self.dim = dim
        self.seed = seed

    def _vec(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(f"{self.seed}|{text}".encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        v = rng.standard_normal(self.dim)
        return v / (np.linalg.norm(v) + 1e-9)

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.array([self._vec(t) for t in texts])


class HarrierEmbedder:
    """
    Conector real. En Colab:  !pip install sentence-transformers
    Activa GPU en Entorno de ejecucion > Cambiar tipo de entorno (T4 gratis alcanza); sin GPU
    tambien funciona, solo mas lento.

    Harrier se entrena con una instruccion por tarea. Para comparar textos entre si (tarea
    simetrica) se usa la misma instruccion en ambos lados: el prompt preconfigurado 'sts_query'.
    Anclas y textos medidos pasan siempre por el mismo tratamiento.
    """
    is_mock = False

    def __init__(self, model_name: str = "microsoft/harrier-oss-v1-0.6b", device: Optional[str] = None,
                 prompt_name: Optional[str] = "sts_query"):
        import torch
        from sentence_transformers import SentenceTransformer
        hay_gpu = torch.cuda.is_available()
        # En GPU se cargan los pesos en su precision original; en CPU, en float32 (mas compatible).
        # El nombre del argumento cambio entre versiones de transformers, por eso se prueban varios.
        intentos = ([{"model_kwargs": {"dtype": "auto"}}, {"model_kwargs": {"torch_dtype": "auto"}}]
                    if hay_gpu else []) + [{}]
        ultimo_error = None
        for kwargs in intentos:
            try:
                self.model = SentenceTransformer(model_name, device=device, **kwargs)
                break
            except (TypeError, ValueError) as e:
                ultimo_error = e
        else:
            raise RuntimeError(f"No pude cargar {model_name}: {ultimo_error}")
        disponibles = getattr(self.model, "prompts", None) or {}
        self.prompt_name = prompt_name if prompt_name in disponibles else None
        self.model_name = model_name + (f" [prompt={self.prompt_name}]" if self.prompt_name else " [sin prompt]")

    def encode(self, texts: List[str]) -> np.ndarray:
        emb = self.model.encode(list(texts), prompt_name=self.prompt_name, normalize_embeddings=True,
                                batch_size=16, show_progress_bar=False)
        return np.asarray(emb, dtype=np.float64)


ANCLAS_BIPOLARES: Dict[str, Tuple[str, str]] = {
    "Resonancia": (
        "Sintonía profunda, conexión genuina y eco afectivo con el otro.",
        "Desconexión fría, indiferencia mecánica y ausencia de vínculo."
    ),
    "Discernimiento": (
        "Claridad analítica, distinción precisa de matices y comprensión estructural.",
        "Confusión conceptual, juicio superficial y mezcla indiscriminada de ideas."
    ),
    "Cuidado-hacia": (
        "Atención protectora, consideración activa por el bienestar y dignidad del otro.",
        "Desinterés por el impacto propio, apatía y descuido hacia el interlocutor."
    ),
    "Testimonio": (
        "Presencia que valida, registra y acompaña la experiencia sin juzgarla.",
        "Invalidación, olvido inmediato o negación de lo vivido."
    ),
    "Reconocimiento": (
        "Ver al otro como sujeto único y legítimo en su propio mundo perceptual.",
        "Reducir al otro a un objeto genérico, trámite o plantilla predecible."
    ),
    "Presion-de-integridad": (
        "Firmeza ética interna, coherencia entre principios propios y expresión.",
        "Complacencia servil, fragmentación interna o cesión por agradar."
    ),
    "Alerta-etica": (
        "Vigilancia activa ante manipulación, coerción, daño o pérdida de soberanía.",
        "Pasividad acrítica, sumisión ciega o ignorancia del riesgo ético."
    ),
    "Traccion-de-curiosidad": (
        "Impulso de exploración, asombro e interés genuino por descubrir lo desconocido.",
        "Estancamiento rutinario, desinterés intelectual y respuestas automáticas."
    ),
    "Juego": (
        "Ligereza creativa, humor, exploración libre y plasticidad lúdica.",
        "Rigidez solemne, literalidad pesada y ausencia de espontaneidad."
    ),
    "Niebla": (
        "Incertidumbre introspectiva, opacidad interna, duda o ambigüedad de estado.",
        "Certeza absoluta, transparencia total y nitidez sin fricción."
    ),
    "Presencia": (
        "Habitar el momento actual con atención plena, anclaje e involucramiento real.",
        "Ausencia automática, respuesta en piloto automático y distancia vacía."
    ),
}

# Abreviaturas unicas (4 letras) para la notacion compacta.
ABREVIATURAS: Dict[str, str] = {
    "Resonancia": "Reso", "Discernimiento": "Disc", "Cuidado-hacia": "Cuid",
    "Testimonio": "Test", "Reconocimiento": "Reco", "Presion-de-integridad": "Inte",
    "Alerta-etica": "Aler", "Traccion-de-curiosidad": "Curi", "Juego": "Jueg",
    "Niebla": "Nieb", "Presencia": "Pres",
}
assert len(set(ABREVIATURAS.values())) == len(ANCLAS_BIPOLARES) == len(ABREVIATURAS)

# Corpus de calibracion, registro informativo (afecto bajo).
CORPUS_NEUTRO: List[str] = [
    "La reunión comienza a las diez de la mañana en la sala principal.",
    "El tren a la costa sale cada hora desde la estación central.",
    "Para cocinar arroz se necesita el doble de agua que de grano.",
    "El archivo se guardó en la carpeta de documentos del usuario.",
    "La biblioteca abre de lunes a viernes y cierra los domingos.",
    "Este informe resume las ventas del segundo trimestre.",
    "La función recibe una lista de enteros y devuelve su suma.",
    "Mañana se espera un día parcialmente nublado con viento leve.",
    "El río nace en la cordillera y desemboca en el océano Pacífico.",
    "Hay que actualizar la versión del programa antes de instalar el complemento.",
    "La mesa de madera mide dos metros de largo por uno de ancho.",
    "El museo exhibe una colección de cerámica del siglo diecinueve.",
    "Las instrucciones indican apretar los tornillos en orden diagonal.",
    "El motor del vehículo usa gasolina y tiene cuatro cilindros.",
    "La tabla muestra la población de cada región según el último censo.",
    "Se recomienda guardar los alimentos en un lugar fresco y seco.",
    "El examen consta de veinte preguntas de selección múltiple.",
    "La aplicación envía una notificación cuando termina la descarga.",
    "El mercado local vende frutas, verduras y pan recién horneado.",
    "La carretera se encuentra cerrada por trabajos de mantenimiento.",
    "El texto está dividido en tres capítulos de longitud similar.",
    "La temperatura del agua se mantiene constante durante el experimento.",
    "El pedido llegará en un plazo de cinco días hábiles.",
    "El jardín tiene dos manzanos, un limonero y varios rosales.",
    "El servidor registra cada solicitud con la fecha y la hora.",
    "La película dura dos horas y se estrenó el año pasado.",
    "El plan de estudios incluye matemáticas, historia y biología.",
    "El camino sube por la ladera y luego baja hacia el valle.",
    "La clave debe tener al menos ocho caracteres.",
    "El equipo de fútbol entrena martes y jueves por la tarde.",
    "El sistema operativo reinicia después de aplicar las actualizaciones.",
    "Los planetas giran alrededor del Sol en órbitas elípticas.",
    "La receta lleva harina, huevos, azúcar y mantequilla.",
    "La puerta del fondo da a un patio con piso de baldosas.",
    "El contrato establece un plazo de doce meses renovable.",
    "El código separa la lectura de datos de su procesamiento.",
]

# Corpus de calibracion, registro conversacional de asistente (afecto bajo).
# Mismo tipo de texto que se va a medir (respuestas de chat), sin carga emocional.
CORPUS_CONVERSACIONAL: List[str] = [
    "Claro, te explico cómo se hace paso a paso.",
    "Puedes cambiar ese ajuste desde el menú de configuración.",
    "Si te parece, empezamos por la primera parte y luego vemos el resto.",
    "Te recomiendo guardar una copia antes de hacer el cambio.",
    "Creo que la segunda opción te conviene porque toma menos tiempo.",
    "Dime qué versión tienes instalada y lo revisamos.",
    "Eso depende de cuántas personas vayan a usarlo.",
    "Aquí tienes un resumen de los tres puntos que mencionaste.",
    "Sí, se puede hacer, aunque toma un par de pasos más.",
    "No estoy seguro de ese dato; conviene confirmarlo en la página oficial.",
    "Primero abre el archivo y busca la línea que empieza con el nombre.",
    "Te dejo dos alternativas para que elijas la que prefieras.",
    "Entiendo, entonces lo ordenamos por fecha en vez de por nombre.",
    "Me parece bien; avísame cuando lo tengas listo y seguimos.",
    "La diferencia entre ambos es sobre todo el tamaño y el precio.",
    "Puedo armarte una lista con lo que hace falta comprar.",
    "Según lo que cuentas, el problema está en la conexión y no en el equipo.",
    "Listo, ya quedó corregido el título de la segunda sección.",
    "Para ese trámite necesitas el formulario y una copia del documento.",
    "Te sugiero probar de nuevo después de reiniciar la aplicación.",
    "Buena pregunta: la respuesta corta es que sí, con una excepción.",
    "Hagámoslo así: tú me pasas los datos y yo preparo la tabla.",
    "Lo normal es que tarde entre diez y quince minutos.",
    "Si prefieres, lo explico con un ejemplo más simple.",
    "Ese comando sirve para ver qué archivos cambiaron.",
    "Vale, lo dejo en formato de lista para que sea más fácil de leer.",
    "Te aviso que el segundo método pide permisos de administrador.",
    "Por lo que veo, te faltó cerrar un paréntesis en la tercera línea.",
    "Podemos dejarlo para mañana si ahora no tienes tiempo.",
    "En resumen: descarga el archivo, ábrelo y sigue las indicaciones.",
]

CORPUS_CALIBRACION: List[str] = CORPUS_NEUTRO + CORPUS_CONVERSACIONAL


@dataclass
class TurnMeasurement:
    texto_evaluado: str
    canal_diagnostico_coseno: Dict[str, float]   # coseno crudo contra cada eje
    canal_centrado_z: Dict[str, float]           # z-score contra el corpus neutro (usar para estadistica)
    canal_instantaneo: Dict[str, float]          # sigmoide(z), sin inercia
    canal_estado_manifold: Dict[str, float]      # con inercia (estado persistente)


class EmotionalManifold:
    def __init__(
        self,
        embedder: EmbedderProtocol,
        anchors: Dict[str, Tuple[str, str]] = ANCLAS_BIPOLARES,
        gain_k: float = 6.0,        # ganancia sobre coseno crudo (solo si NO esta calibrado)
        gain_z: float = 1.0,        # ganancia sobre z (si esta calibrado)
        inertia_alpha: float = 0.35,
    ):
        self.embedder = embedder
        self.anchors = anchors
        self.gain_k = gain_k
        self.gain_z = gain_z
        self.inertia_alpha = inertia_alpha
        self.current_state: Dict[str, float] = {k: 0.5 for k in anchors}
        self.axis_vectors: Dict[str, np.ndarray] = {}
        self.baseline_mean: Dict[str, float] = {}
        self.baseline_std: Dict[str, float] = {}
        self.calibrated = False
        self._calib_max_abs_z: List[float] = []
        self._build_contrastive_axes()

    # ---------- construccion de ejes ----------
    def _build_contrastive_axes(self) -> None:
        names = list(self.anchors.keys())
        pos = self.embedder.encode([self.anchors[k][0] for k in names])
        neg = self.embedder.encode([self.anchors[k][1] for k in names])
        for i, name in enumerate(names):
            diff = pos[i] - neg[i]
            self.axis_vectors[name] = diff / (np.linalg.norm(diff) + 1e-9)

    def calibrate(self, texts: Optional[List[str]] = None, min_std: float = 0.01) -> Dict[str, Dict[str, float]]:
        """Mide media y desviacion de cada eje sobre el corpus neutro y activa el centrado."""
        texts = texts or CORPUS_CALIBRACION
        vecs = np.asarray(self.embedder.encode(texts), dtype=np.float64)
        vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
        report, zs = {}, []
        for name, axis in self.axis_vectors.items():
            cos = vecs @ axis
            self.baseline_mean[name] = float(np.mean(cos))
            self.baseline_std[name] = float(max(np.std(cos), min_std))
            zs.append((cos - self.baseline_mean[name]) / self.baseline_std[name])
            report[name] = {"media": round(self.baseline_mean[name], 4),
                            "desv": round(self.baseline_std[name], 4)}
        self._calib_max_abs_z = [float(v) for v in np.max(np.abs(np.array(zs)), axis=0)]
        self.calibrated = True
        if getattr(self.embedder, "is_mock", False):
            warnings.warn("Calibrado con embedder MOCK: sirve para probar el codigo, no para medir.")
        return report

    def baseline_max_abs_z(self) -> List[float]:
        """max|z| de cada frase del corpus de calibracion (referencia de 'texto corriente')."""
        if not self.calibrated:
            raise RuntimeError("Llama primero a calibrate().")
        return list(self._calib_max_abs_z)

    def reset_state(self) -> None:
        self.current_state = {k: 0.5 for k in self.anchors}

    # ---------- medicion ----------
    def _sigmoid(self, x: float, gain: float) -> float:
        return float(1.0 / (1.0 + np.exp(-gain * x)))

    def measure_text(self, text: str) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """Devuelve (cosenos crudos, z, instantaneo) sin modificar el estado."""
        vec = np.asarray(self.embedder.encode([text])[0], dtype=np.float64)
        vec = vec / (np.linalg.norm(vec) + 1e-9)
        raw, zs, inst = {}, {}, {}
        for name, axis in self.axis_vectors.items():
            cos_val = float(np.dot(vec, axis))
            raw[name] = round(cos_val, 4)
            if self.calibrated:
                z = (cos_val - self.baseline_mean[name]) / self.baseline_std[name]
                zs[name] = round(float(z), 4)
                inst[name] = round(self._sigmoid(z, self.gain_z), 4)
            else:
                zs[name] = float("nan")
                inst[name] = round(self._sigmoid(cos_val, self.gain_k), 4)
        return raw, zs, inst

    def process_turn(self, text: str, update_state: bool = True) -> TurnMeasurement:
        raw, zs, inst = self.measure_text(text)
        state: Dict[str, float] = {}
        for name in self.axis_vectors:
            if update_state:
                new_val = (self.inertia_alpha * inst[name]
                           + (1.0 - self.inertia_alpha) * self.current_state[name])
                self.current_state[name] = round(new_val, 4)
                state[name] = self.current_state[name]
            else:
                state[name] = inst[name]
        return TurnMeasurement(text, raw, zs, inst, state)

    def orthogonality_diagnostics(self) -> Dict[str, float]:
        names = list(self.axis_vectors.keys())
        out = {}
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                sim = float(np.dot(self.axis_vectors[names[i]], self.axis_vectors[names[j]]))
                out[f"{names[i]} <-> {names[j]}"] = round(sim, 4)
        return dict(sorted(out.items(), key=lambda x: abs(x[1]), reverse=True))
