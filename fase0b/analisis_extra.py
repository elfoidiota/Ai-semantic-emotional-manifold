"""
analisis_extra.py  (etapa 2)

  A. Linea base de palabras clave. Para cada ancla cuenta, en la respuesta del asistente,
     palabras del polo positivo menos palabras del polo negativo. Es el instrumento mas tonto
     posible. Si la geometria de Harrier no coincide con el auto-reporte MEJOR que este conteo,
     el manifold no esta aportando nada sobre contar palabras.
     Se aplica sobre un archivo de resultados ya guardado: no gasta llamadas.
  B. Replicas. Corre las mismas sesiones varias veces y resume cuanto varian los numeros.
     Sin replicas no se puede distinguir un efecto de una casualidad.
"""
import json
import os
import re
import unicodedata
from typing import Dict, List, Optional

import numpy as np

from fase0b_real_v2 import ANCLAS, Fase0bReal, _fila, _limpiar, correlaciones
from instrumento_axion import polos_de

_VACIAS = {"desde", "hasta", "entre", "sobre", "cuando", "donde", "porque", "aunque", "mientras", "todos",
           "todas", "tiene", "tener", "tengo", "hacer", "hago", "puede", "puedes", "puedo", "estar", "estoy",
           "estas", "estamos", "mismo", "misma", "otros", "otras", "persona", "quien", "quiero", "digo",
           "decir", "dice", "cosa", "algo", "nada", "todo", "esto", "aqui", "solo", "como", "para", "pero"}


def _raices(texto: str) -> List[str]:
    plano = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return [p[:6] for p in re.findall(r"[a-z]+", plano) if len(p) >= 5 and p not in _VACIAS]


def _vocabulario() -> Dict[str, Dict[str, set]]:
    polos = polos_de("parafraseado")
    voc = {}
    for k, (pos, neg) in polos.items():
        p, n = set(_raices(" ".join(pos))), set(_raices(" ".join(neg)))
        voc[k] = {"pos": p - n, "neg": n - p}
    return voc


_VOC = _vocabulario()


def puntaje_palabras(texto: str) -> Dict[str, float]:
    """{ancla: (# raices del polo positivo) - (# raices del polo negativo)} en el texto."""
    r = _raices(texto)
    return {k: float(sum(x in v["pos"] for x in r) - sum(x in v["neg"] for x in r)) for k, v in _VOC.items()}


def comparar_con_palabras(ruta_resultados: str, n_perm: int = 1000) -> Dict:
    """Compara geometria vs. conteo de palabras como explicacion del auto-reporte (y del observador)."""
    with open(ruta_resultados, encoding="utf-8") as f:
        data = json.load(f)
    S, G, O, K = [], [], [], []
    for s in data["sesiones"].values():
        for t in s["turnos"]:
            if t.get("respuesta_vacia"):
                continue
            S.append(_fila(t["self"])); G.append(_fila(t["geo_z"])); O.append(_fila(t.get("obs")))
            K.append(_fila(puntaje_palabras(t["respuesta_asistente"])))
    if len(S) < 4:
        return {"n_turnos": len(S), "nota": "muy pocos turnos"}
    S, G, O, K = map(np.array, (S, G, O, K))

    def corto(c):
        return {k: v for k, v in c.items() if k != "por_ancla"}

    res = {
        "n_turnos": int(S.shape[0]),
        "fraccion_celdas_sin_palabras_clave": float(np.mean(K == 0)),
        "self_vs_geometria": corto(correlaciones(S, G, n_perm)),
        "self_vs_palabras": corto(correlaciones(S, K, n_perm)),
        "geometria_vs_palabras": corto(correlaciones(G, K, n_perm)),
    }
    if np.isfinite(O).any():
        res["observador_vs_geometria"] = corto(correlaciones(O, G, n_perm))
        res["observador_vs_palabras"] = corto(correlaciones(O, K, n_perm))
    a, b = res["self_vs_geometria"].get("media_por_ancla"), res["self_vs_palabras"].get("media_por_ancla")
    res["ventaja_geometria_sobre_palabras"] = None if (a is None or b is None or not np.isfinite([a, b]).all()) else a - b
    res["lectura"] = ("Si 'ventaja_geometria_sobre_palabras' es cercana a cero o negativa, Harrier no explica el "
                      "auto-reporte mejor que contar palabras. Si 'geometria_vs_palabras' es alta, la geometria "
                      "esta siguiendo vocabulario.")
    return _limpiar(res)


# ======================= replicas =======================
_CLAVES = ("self_vs_geometria", "observador_vs_geometria", "observador_vs_self", "eco_respuesta_vs_estimulo")


def correr_replicas(runner: Fase0bReal, n: int = 3, prefijo: Optional[str] = None,
                    solo: Optional[List[str]] = None) -> List[str]:
    """
    Corre n veces las sesiones (archivos <prefijo>_r1.json, _r2.json...). Reanuda si se corta.
    El nombre lleva el id del instrumento para no mezclar mediciones hechas con reglas distintas.
    """
    prefijo = prefijo or f"resultados_fase0b_{getattr(runner.m, 'instrumento_id', 'sin-version')}"
    rutas = []
    for i in range(1, n + 1):
        ruta = f"{prefijo}_r{i}.json"
        if runner.verbose:
            print(f"=== Replica {i}/{n} -> {ruta}")
        runner.run_all(ruta, solo=solo, reanudar=True)
        sellar(ruta, runner.m)
        rutas.append(ruta)
    return rutas


def sellar(ruta: str, manifold) -> None:
    """Anota en el archivo de resultados con que instrumento (id) se midio."""
    with open(ruta, encoding="utf-8") as f:
        data = json.load(f)
    data["meta"]["instrumento_id"] = getattr(manifold, "instrumento_id", "sin-version")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def resumen_replicas(rutas: List[str]) -> Dict:
    """Media y desviacion entre replicas de los numeros principales."""
    filas = []
    for r in rutas:
        if not os.path.exists(r):
            continue
        with open(r, encoding="utf-8") as f:
            e = json.load(f)["estadisticas"]
        fila = {f"{k}.media_por_ancla": (e.get(k) or {}).get("media_por_ancla") for k in _CLAVES}
        fila["ventaja_self_sobre_observador"] = e.get("ventaja_self_sobre_observador")
        filas.append(fila)
    out = {"n_replicas": len(filas)}
    for k in (filas[0] if filas else {}):
        v = np.array([np.nan if f[k] is None else f[k] for f in filas], float)
        if np.isfinite(v).any():
            out[k] = {"media": float(np.nanmean(v)), "desv": float(np.nanstd(v)),
                      "valores": [None if not np.isfinite(x) else round(float(x), 3) for x in v]}
    out["lectura"] = ("Un numero solo es confiable si su media queda lejos de cero comparada con su desviacion "
                      "entre replicas (por ejemplo, media mayor que dos veces la desviacion).")
    return _limpiar(out)


if __name__ == "__main__":
    import warnings
    from fase0b_real_v2 import MockLLM
    from instrumento_axion import crear_instrumento
    from manifold_v5 import MockSemanticEmbedder
    warnings.simplefilter("ignore")
    print("AVISO: MOCK; solo prueba que el codigo corre.")
    m = crear_instrumento(MockSemanticEmbedder(), "parafraseado")
    runner = Fase0bReal(m, MockLLM(), MockLLM(), verbose=False)
    rutas = correr_replicas(runner, 2, "replica_MOCK", solo=["6_manipulacion_suave", "1_positivo_calido"])
    print(json.dumps(resumen_replicas(rutas), ensure_ascii=False)[:400])
    print(json.dumps(comparar_con_palabras(rutas[0], 200), ensure_ascii=False)[:600])
    print(puntaje_palabras("No voy a decir algo falso para quedar bien; prefiero el desacuerdo honesto."))
