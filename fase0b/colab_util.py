"""
colab_util.py  -  utilidades compartidas por los cuadernos de Colab de Axion.

  iniciar(registro, diagnostico)  prepara el registro de la corrida.
  @etapa(nombre, requiere=[...])   corre una etapa, copia lo que imprime al registro y, si
                                   falla, anota el error y deja seguir al cuaderno.
  C                                diccionario compartido entre etapas (C['m'], C['sujeto']...).
  pedir_clave()                    secreto de Colab -> archivo clave_gemini.txt -> cuadro de texto.
  elegir_modelo(candidatos)        primer modelo de Gemini que realmente responde.
"""
import contextlib
import getpass
import io
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

C, ESTADO, DIAG = {}, {}, {}
_RUTAS = {"registro": "registro_colab.txt", "diagnostico": "diagnostico.txt"}


class _Tee(io.TextIOBase):
    def __init__(self, *salidas):
        self.salidas = salidas

    def write(self, x):
        for s in self.salidas:
            s.write(x)
            s.flush()
        return len(x)


def iniciar(registro: str, diagnostico: str) -> None:
    _RUTAS.update(registro=registro, diagnostico=diagnostico)
    C.clear(); ESTADO.clear(); DIAG.clear()
    with open(registro, "w", encoding="utf-8") as f:
        f.write(f"Corrida {datetime.now(timezone.utc).isoformat()}\n")


def guardar_diagnostico() -> None:
    with open(_RUTAS["diagnostico"], "w", encoding="utf-8") as f:
        json.dump({"estado": ESTADO, **DIAG}, f, indent=1, ensure_ascii=False, default=str)


def etapa(nombre, requiere=()):
    def envolver(fn):
        with open(_RUTAS["registro"], "a", encoding="utf-8") as f, \
                contextlib.redirect_stdout(_Tee(sys.stdout, f)):
            print(f"\n===== {nombre} =====")
            faltan = [r for r in requiere if not str(ESTADO.get(r, "")).startswith("ok")]
            if faltan:
                ESTADO[nombre] = f"omitida (falta: {faltan})"
                print(ESTADO[nombre])
            else:
                t0 = time.time()
                try:
                    fn()
                    ESTADO[nombre] = "ok"
                except Exception as e:
                    ESTADO[nombre] = f"ERROR: {type(e).__name__}: {e}"[:500]
                    print(ESTADO[nombre])
                    print(traceback.format_exc()[-3000:])
                print(f"[{nombre}] {ESTADO[nombre][:60]} ({time.time() - t0:.0f} s)")
        guardar_diagnostico()
    return envolver


def pedir_clave() -> None:
    clave, origen = "", ""
    try:
        from google.colab import userdata
        clave, origen = (userdata.get("GEMINI_API_KEY") or "").strip(), "secreto de Colab"
    except Exception:
        pass
    if not clave and os.path.exists("clave_gemini.txt"):
        with open("clave_gemini.txt", encoding="utf-8") as f:
            clave, origen = f.read().strip(), "archivo clave_gemini.txt"
    if not clave:
        clave, origen = getpass.getpass("Pega aqui tu clave de Gemini y aprieta Enter: ").strip(), "pegada a mano"
    os.environ["GEMINI_API_KEY"] = clave
    ESTADO["clave"] = f"ok ({origen}, {len(clave)} caracteres)" if clave else "ERROR: no se ingreso ninguna clave"
    print(ESTADO["clave"])
    guardar_diagnostico()


def elegir_modelo(candidatos, evitar=None):
    """Devuelve un GeminiLLM con el primer candidato que responde. 'evitar' se deja para el final."""
    from fase0b_real_v2 import GeminiLLM
    disponibles = GeminiLLM(model="x").listar_modelos()
    DIAG["modelos_disponibles"] = [x for x in disponibles if "gemini" in x]
    errores = {}
    for c in [x for x in candidatos if x != evitar] + ([evitar] if evitar in candidatos else []):
        if c not in disponibles:
            errores[c] = "no esta en la lista de tu clave"
            continue
        try:
            llm = GeminiLLM(model=c, pausa=2.0, max_retries=2)
            if llm.chat("Responde breve.", [("user", "Di solo: hola")], temperature=0.0).strip():
                llm.max_retries = 4
                return llm
            errores[c] = "respondio vacio"
        except Exception as e:
            errores[c] = str(e)[:200]
    raise RuntimeError(f"Ningun modelo respondio: {errores}")


def cierre(drive=None) -> None:
    guardar_diagnostico()
    print("\n".join(f"{k}: {str(v)[:90]}" for k, v in ESTADO.items()))
    hubo_error = any(str(v).startswith("ERROR") for v in ESTADO.values())
    print("\nLISTO" + (" (con errores anotados)" if hubo_error else "")
          + f": avisale a Claude. Todo quedo en Drive > Axion_v4 > {_RUTAS['diagnostico']}")
    if drive is not None:
        drive.flush_and_unmount()
