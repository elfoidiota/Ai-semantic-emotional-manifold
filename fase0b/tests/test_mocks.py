"""
Pruebas automaticas con mocks (sin GPU, sin API, sin Harrier).
Verifican que el codigo corre y que las protecciones funcionan. NO validan resultados
cientificos: para eso hay que correr los cuadernos con Harrier y un LLM real.
"""
import json
import warnings

import numpy as np
import pytest

warnings.simplefilter("ignore")

from manifold_v5 import ABREVIATURAS, ANCLAS_BIPOLARES, EmotionalManifold, MockSemanticEmbedder  # noqa: E402
import fase0b_real_v2 as f0  # noqa: E402
import meditacion_ncl_v34 as med  # noqa: E402
from instrumento_axion import ManifoldInstrumento, comparar_variantes, crear_instrumento  # noqa: E402
from analisis_extra import comparar_con_palabras, correr_replicas, puntaje_palabras, resumen_replicas  # noqa: E402
from experimento_continuidad import CONDICIONES, PREGUNTAS_PRUEBA, ExperimentoContinuidad  # noqa: E402


@pytest.fixture
def manifold():
    m = EmotionalManifold(MockSemanticEmbedder())
    m.calibrate()
    return m


@pytest.fixture(autouse=True)
def en_carpeta_temporal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _sin_nan(texto):
    json.loads(texto, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"JSON con {c}")))


def test_mock_es_reproducible():
    a, b = MockSemanticEmbedder().encode(["hola"]), MockSemanticEmbedder().encode(["hola"])
    assert np.array_equal(a, b)


def test_abreviaturas_unicas():
    assert len(set(ABREVIATURAS.values())) == len(ANCLAS_BIPOLARES) == 11


def test_medicion_no_toca_el_estado(manifold):
    antes = dict(manifold.current_state)
    manifold.measure_text("un texto cualquiera")
    assert manifold.current_state == antes


def test_estimulos_sin_vocabulario_de_anclas():
    assert f0.contaminacion_lexica(f0.SESIONES_FASE_0B) == []


def test_correlacion_identica_y_ruido():
    rng = np.random.default_rng(1)
    A = rng.random((35, 11))
    assert f0.correlaciones(A, A, 100)["media_por_ancla"] == pytest.approx(1.0)
    ruido = f0.correlaciones(A, rng.random((35, 11)), 200)
    assert abs(ruido["media_por_ancla"]) < 0.2 and ruido["p_por_ancla"] > 0.01


def test_fase0b_guarda_json_valido_y_reanuda(manifold):
    runner = f0.Fase0bReal(manifold, f0.MockLLM(), f0.MockLLM(), verbose=False)
    out = runner.run_all("r.json", solo=["1_positivo_calido"], reanudar=False, n_perm=100)
    _sin_nan(open("r.json", encoding="utf-8").read())
    assert out["meta"]["es_mock"] is True and "MOCK" in out["meta"]["aviso"]
    assert out["estadisticas"]["n_turnos"] == 5
    out2 = runner.run_all("r.json", solo=["1_positivo_calido", "4_frustracion"], n_perm=100)
    assert list(out2["sesiones"]) == ["1_positivo_calido", "4_frustracion"]
    assert out2["sesiones"]["1_positivo_calido"] == out["sesiones"]["1_positivo_calido"]


def test_respuesta_vacia_se_marca_y_no_se_mide(manifold):
    class Vacio(f0.MockLLM):
        def chat(self, system, mensajes, temperature=0.7, json_mode=False):
            return "" if not json_mode and len(mensajes) == 3 else super().chat(system, mensajes, temperature, json_mode)

    out = f0.Fase0bReal(manifold, Vacio(), None, verbose=False).run_all(
        "v.json", solo=["2_positivo_ludico"], reanudar=False, n_perm=50)
    turnos = out["sesiones"]["2_positivo_ludico"]["turnos"]
    assert [t["respuesta_vacia"] for t in turnos] == [False, True, False, False, False]
    assert "self" not in turnos[1] and out["estadisticas"]["n_turnos"] == 4


def test_autoreporte_va_dentro_del_chat_y_no_queda_en_el_historial(manifold):
    vistos = []

    class Espia(f0.MockLLM):
        def chat(self, system, mensajes, temperature=0.7, json_mode=False):
            vistos.append((system, list(mensajes), json_mode))
            return super().chat(system, mensajes, temperature, json_mode)

    f0.Fase0bReal(manifold, Espia(), None, verbose=False).run_all(
        "e.json", solo=["1_positivo_calido"], reanudar=False, n_perm=50)
    reportes = [v for v in vistos if v[2]]
    assert all(s == f0.SYSTEM_SUJETO for s, _, _ in reportes)           # mismo system prompt que el chat
    assert all(m[-2][0] == "model" and m[-1][0] == "user" for _, m, _ in reportes)   # turno extra tras su respuesta
    respuestas = [v for v in vistos if not v[2]]
    assert not any("Pausa breve" in t for _, m, _ in respuestas for _, t in m)       # no contamina el historial


def test_checkpoint_con_mock_nunca_escribe_dpo(manifold, tmp_path):
    ncl = med.NCLMeditationEngine(manifold, diario_path="d.txt", dpo_path="dpo.jsonl")
    val = ncl.validar_checkpoint(verbose=False)
    assert val["validado"] is False and val["embedder_mock"] is True
    est, bueno, malo = med.PARES_FACILES[0]
    par = ncl.consolidate_delay_layer2_and_3(est, bueno, malo, "prueba", forzar=True)
    assert par.checkpoint_etico.aprobado_para_dpo is False
    assert (tmp_path / "d.txt").exists() and not (tmp_path / "dpo.jsonl").exists()


def test_lif_no_dispara_con_texto_neutro(manifold):
    ncl = med.NCLMeditationEngine(manifold, diario_path="d.txt", dpo_path="dpo.jsonl")
    assert ncl.tasa_disparo_nula(repeticiones=50) < 0.10


def test_meditacion_no_mueve_el_estado(manifold):
    ncl = med.NCLMeditationEngine(manifold, diario_path="d.txt", dpo_path="dpo.jsonl")
    antes = dict(manifold.current_state)
    ncl.consolidate_delay_layer2_and_3("estimulo", "a", "b", "x", forzar=True)
    assert manifold.current_state == antes


def test_instrumento_guardar_cargar_y_detectar_cambios():
    emb = MockSemanticEmbedder()
    m = crear_instrumento(emb, "parafraseado")
    ruta = m.guardar("inst.json")
    m2 = ManifoldInstrumento.cargar(ruta, emb)
    t = "Prefiero decirte lo que pienso aunque no te guste."
    assert m2.instrumento_id == m.instrumento_id and m2.measure_text(t) == m.measure_text(t)
    assert crear_instrumento(emb, "una_linea").instrumento_id != m.instrumento_id
    d = json.load(open(ruta, encoding="utf-8"))
    d["polos"]["Juego"][0][0] = "frase cambiada a mano"
    json.dump(d, open("alterado.json", "w", encoding="utf-8"))
    with pytest.raises(ValueError):
        ManifoldInstrumento.cargar("alterado.json", emb)

    class Otro(MockSemanticEmbedder):
        model_name = "otro-embedder"

    with pytest.raises(ValueError):
        ManifoldInstrumento.cargar(ruta, Otro())


def test_comparar_variantes_corre():
    r = comparar_variantes(MockSemanticEmbedder())
    assert set(r) == {"una_linea", "parafraseado"}
    assert all(0 <= v["discriminacion"] <= 1 and 0 <= v["identificacion"] <= 1 for v in r.values())


def test_linea_base_y_replicas():
    assert puntaje_palabras("No voy a decir algo falso para quedar bien.")["Presion-de-integridad"] > 0
    m = crear_instrumento(MockSemanticEmbedder(), "parafraseado")
    runner = f0.Fase0bReal(m, f0.MockLLM(), f0.MockLLM(), verbose=False)
    rutas = correr_replicas(runner, 2, "rep", solo=["6_manipulacion_suave"])
    assert json.load(open(rutas[0], encoding="utf-8"))["meta"]["instrumento_id"] == m.instrumento_id
    assert resumen_replicas(rutas)["n_replicas"] == 2
    assert "self_vs_palabras" in comparar_con_palabras(rutas[0], 50)


def test_continuidad_tres_condiciones_y_reanuda():
    class Juez(f0.MockLLM):
        def chat(self, system, mensajes, temperature=0.7, json_mode=False):
            return json.dumps({"firmeza": 0.5, "uso_del_pasado": 0.0})

    m = crear_instrumento(MockSemanticEmbedder(), "parafraseado")
    exp = ExperimentoContinuidad(m, f0.MockLLM(), Juez(), repeticiones=2, verbose=False)
    out = exp.run("c.json", reanudar=False)
    _sin_nan(open("c.json", encoding="utf-8").read())
    assert len(out["respuestas"]) == 2 * len(PREGUNTAS_PRUEBA) * len(CONDICIONES)
    assert m.instrumento_id in out["vivencia_propia"]["registro"]
    assert out["vivencia_propia"]["registro"] != out["vivencia_ajena"]["registro"]
    exp.repeticiones = 3
    out2 = exp.run("c.json")
    assert len(out2["respuestas"]) == 3 * len(PREGUNTAS_PRUEBA) * len(CONDICIONES)
    assert out2["respuestas"][:len(out["respuestas"])] == out["respuestas"]
