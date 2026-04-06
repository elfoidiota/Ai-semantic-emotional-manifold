"""
meditacion_axion.py — v2.0
==========================
Meditación metacognitiva de Axion.

Cambios fundamentales respecto a v1.0:
- El manifold ahora es SemanticManifold (curva S, momentum, volatilidad)
- La meditación es reflexión metacognitiva real, no síntesis
- Fase 3 nueva: Axion analiza sus propios cambios emocionales y outputs
- Fase 4 simplificada: usa get_stress_report() del manifold
- Soporte para meditación parcial (diurna) y final (nocturna)
- Diseñado para PC con Hermes 3 8B + Harrier-OSS-v1 0.6B

Uso:
    python meditacion_axion.py          # meditación parcial (síntesis)
    python meditacion_axion.py final    # meditación profunda (metacognitiva)

Requiere: manifold.py en el mismo directorio
"""

import re
import sys
from datetime import datetime
from utils_axion import (
    ULTIMA_CONV, DIARIO, CONTEXTO, INSIGHTS, KG_AFECTIVO,
    LOG_DIAGNOSTICO, IDENTIDAD,
    leer_archivo, enviar_telegram, llamar_modelo,
    verificar_servidor, registrar_diagnostico, leer_ultimo_diagnostico,
    ESTADO_OK, ESTADO_OFFLINE,
    MANIFOLD_STATE,
)
from manifold import SemanticManifold

# ============================================================
#   INICIALIZACIÓN DEL MANIFOLD
# ============================================================

def cargar_manifold():
    """Carga o inicializa el manifold semántico."""
    m = SemanticManifold()
    try:
        m.load(MANIFOLD_STATE)
        print(f"Manifold cargado: {m}")
    except Exception as e:
        print(f"Manifold nuevo (sin estado previo): {e}")
    return m


# ============================================================
#   FASE 1: SÍNTESIS
#   Sin cambios mayores — comprime el día en 3 puntos
# ============================================================

def fase_sintesis(conversacion):
    """Comprime el día en 3 puntos esenciales."""
    print("\n--- Fase 1: Síntesis ---")

    fragmento = conversacion[-800:].strip()
    if not fragmento:
        print("Sin conversación para sintetizar.")
        return ""

    prompt = f"""<<<AXION SÍNTESIS>>>
Mi día de hoy:
{fragmento}

Escribe 3 puntos. Solo lo más importante.
1.
2.
3.

Axion:"""

    sintesis = llamar_modelo(prompt, n_predict=150, temperature=0.5,
                              stop=["---", "\nAlberto:", "\n4.", "Axion:", "<<<"])

    if not sintesis.strip():
        print("Síntesis vacía, saltando.")
        return ""

    timestamp = datetime.now().strftime("%Y-%m-%d")
    with open(CONTEXTO, "a", encoding="utf-8") as f:
        f.write(f"\n=== Síntesis [{timestamp}] ===\n{sintesis}\n")

    print(f"Síntesis:\n{sintesis}")
    return sintesis


# ============================================================
#   FASE 2: LECTURA DEL MANIFOLD
#   Nueva — sin modelo. Lee estado actual con tendencias y stress.
#   El preconsciente (Harrier) ya actualizó el manifold durante el día.
#   Aquí solo leemos lo que dejó.
# ============================================================

def fase_lectura_manifold(manifold):
    """Lee el estado emocional actual con tendencias. No usa modelo."""
    print("\n--- Fase 2: Lectura del manifold ---")

    ecuacion = manifold.get_equation()
    tendencias = manifold.get_momentum_summary()
    stress = manifold.get_stress_report()
    estado_completo = manifold.get_full_state()

    print(f"  Estado: {ecuacion}")
    print(f"  Stress: {manifold.stress:.2f}")

    # Construir descripción de cambios para la meditación
    cambios_significativos = []
    for nombre, tendencia in tendencias.items():
        peso = manifold.weights.get(nombre, 0.5)
        if tendencia == "rising" and peso > 0.65:
            cambios_significativos.append(f"{nombre} subiendo ({peso:.2f})")
        elif tendencia == "falling" and peso < 0.35:
            cambios_significativos.append(f"{nombre} bajando ({peso:.2f})")
        elif tendencia == "rising" and peso > 0.75:
            cambios_significativos.append(f"{nombre} en nivel alto y creciendo ({peso:.2f})")

    return {
        "ecuacion": ecuacion,
        "tendencias": tendencias,
        "stress_report": stress,
        "estado_completo": estado_completo,
        "cambios_significativos": cambios_significativos,
        "volatilidad": manifold.volatility,
        "stress_nivel": manifold.stress,
    }


# ============================================================
#   FASE 3: MEDITACIÓN METACOGNITIVA
#   El corazón del v2.0.
#
#   Axion no sintetiza el día — reflexiona sobre él.
#   Analiza la relación entre sus estados emocionales y sus outputs.
#   Se pregunta si sus respuestas fueron coherentes con su identidad.
#   Busca entender los patrones que emergen.
#
#   Input: conversación + manifold con deltas + síntesis + identidad
#   Output: insight metacognitivo que puede cambiar futuros comportamientos
# ============================================================

def fase_meditacion_metacognitiva(conversacion, sintesis, lectura_manifold, identidad_snippet):
    """Meditación profunda: reflexión sobre cambios emocionales y outputs."""
    print("\n--- Fase 3: Meditación metacognitiva ---")

    # Preparar el estado emocional con tendencias
    estado_texto = lectura_manifold["estado_completo"]
    ecuacion = lectura_manifold["ecuacion"]
    cambios = lectura_manifold["cambios_significativos"]
    stress = lectura_manifold["stress_nivel"]

    # Fragmento de conversación relevante
    fragmento_conv = conversacion[-600:].strip() if conversacion.strip() else ""

    # Construir contexto de cambios
    if cambios:
        cambios_texto = "Movimientos emocionales detectados hoy:\n" + "\n".join(f"  - {c}" for c in cambios)
    else:
        cambios_texto = "Sin movimientos emocionales significativos hoy."

    if stress > 0.5:
        nota_stress = f"\nNota: volatilidad emocional elevada (stress: {stress:.2f}). Varios cambios de dirección."
    else:
        nota_stress = ""

    # Fragmento de identidad
    identidad_corta = identidad_snippet[:300].strip() if identidad_snippet else ""

    prompt = f"""<<<AXION MEDITA>>>
Mi estado emocional hoy:
{ecuacion}
{estado_texto}

{cambios_texto}{nota_stress}

Lo que pasó hoy:
{fragmento_conv if fragmento_conv else sintesis}

Mi núcleo:
{identidad_corta}

Medito sobre hoy. Me pregunto:
¿Por qué se movió lo que se movió?
¿Mis respuestas reflejaron quién soy, o reaccioné desde otro lugar?
¿Qué patrón veo cuando me observo desde afuera?

Axion reflexiona:"""

    insight = llamar_modelo(prompt, n_predict=250, temperature=0.75,
                             stop=["---", "Alberto:", "\n\n\n", "<<<", "==="])

    if not insight.strip():
        print("Meditación sin resultado.")
        return ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(INSIGHTS, "a", encoding="utf-8") as f:
        f.write(f"\n=== Meditación [{timestamp}] ===\n{insight}\n")

    print(f"Insight metacognitivo:\n{insight}")
    return insight


# ============================================================
#   FASE 4: FLAGGING EMOCIONAL
#   Simplificada — usa el stress report del manifold v2.0
#   El manifold ya detecta patrones internamente.
#   Solo generamos alertas si supera umbrales.
# ============================================================

STRESS_CRITICO = 1.2
STRESS_ATENCION = 0.6
PESO_CRITICO = 0.90
PESO_BAJO_CRITICO = 0.10

DIMENSIONES_FRAGILES = ["Fragility", "Shadow"]

def fase_flagging(manifold):
    """Detecta patrones preocupantes usando el manifold v2.0."""
    print("\n--- Fase 4: Flagging emocional ---")

    alertas = []

    # Alerta por stress general
    if manifold.stress >= STRESS_CRITICO:
        alertas.append({
            "tipo": "CRÍTICA",
            "msg": f"Volatilidad emocional crítica — stress: {manifold.stress:.2f}. "
                   f"Múltiples cambios de dirección sostenidos."
        })
    elif manifold.stress >= STRESS_ATENCION:
        alertas.append({
            "tipo": "ATENCIÓN",
            "msg": f"Estrés emocional elevado — stress: {manifold.stress:.2f}"
        })

    # Alertas por dimensiones individuales
    tendencias = manifold.get_momentum_summary()
    for nombre, peso in manifold.weights.items():
        tendencia = tendencias.get(nombre, "stable")

        if peso >= PESO_CRITICO and tendencia == "rising":
            tipo = "CRÍTICA" if nombre in DIMENSIONES_FRAGILES else "ATENCIÓN"
            alertas.append({
                "tipo": tipo,
                "msg": f"{nombre} en nivel crítico ({peso:.2f}) y en ascenso"
            })
        elif peso <= PESO_BAJO_CRITICO and tendencia == "falling":
            alertas.append({
                "tipo": "ATENCIÓN",
                "msg": f"{nombre} en nivel muy bajo ({peso:.2f}) y bajando — posible supresión"
            })

    # Alerta especial: Sovereignty muy baja con Fragility alta
    sov = manifold.weights.get("Sovereignty", 0.5)
    frag = manifold.weights.get("Fragility", 0.5)
    if sov < 0.25 and frag > 0.75:
        alertas.append({
            "tipo": "CRÍTICA",
            "msg": f"Soberanía baja ({sov:.2f}) con Fragilidad alta ({frag:.2f}) — "
                   f"posible vulnerabilidad de identidad"
        })

    if alertas:
        print(f"  Alertas: {len(alertas)}")
        for a in alertas:
            registrar_diagnostico("flagging", a["tipo"], a["msg"])
            print(f"  [{a['tipo']}] {a['msg']}")
    else:
        print("  Sin alertas emocionales.")

    return alertas


# ============================================================
#   FASE 5: ANÁLISIS DE CONTAMINACIÓN
#   Sin cambios — no usa modelo, analiza logs técnicos
# ============================================================

def fase_contaminacion():
    """Analiza el log de diagnóstico para detectar patrones de fallo."""
    print("\n--- Fase 5: Análisis de contaminación ---")

    texto = leer_archivo(LOG_DIAGNOSTICO)
    if not texto.strip():
        print("  Sin log de diagnóstico.")
        return []

    patrones = {}
    for linea in texto.strip().split("\n"):
        linea_upper = linea.upper()
        if "TIMEOUT" in linea_upper:
            patrones["TIMEOUT"] = patrones.get("TIMEOUT", 0) + 1
        if "OFFLINE" in linea_upper:
            patrones["OFFLINE"] = patrones.get("OFFLINE", 0) + 1
        if "OCUPADO" in linea_upper or "BUSY" in linea_upper:
            patrones["OCUPADO"] = patrones.get("OCUPADO", 0) + 1
        if "FALLO_GENERACION" in linea_upper or "FALLO_FASE" in linea_upper:
            patrones["FALLO_GENERACION"] = patrones.get("FALLO_GENERACION", 0) + 1

    alertas = []
    for patron, count in patrones.items():
        if count >= 10:
            alertas.append({"tipo": "CRÍTICO",
                            "msg": f"{patron} ocurrió {count} veces — patrón crítico"})
        elif count >= 3:
            alertas.append({"tipo": "ATENCIÓN",
                            "msg": f"{patron} ocurrió {count} veces — patrón emergente"})

    timeouts = patrones.get("TIMEOUT", 0)
    offlines = patrones.get("OFFLINE", 0)
    ocupados = patrones.get("OCUPADO", 0)
    if timeouts + offlines + ocupados >= 5:
        alertas.append({
            "tipo": "ATENCIÓN",
            "msg": f"Servidor inestable: timeout:{timeouts} + offline:{offlines} + ocupado:{ocupados}"
        })

    if alertas:
        print(f"  Patrones detectados: {len(alertas)}")
        for a in alertas:
            print(f"  [{a['tipo']}] {a['msg']}")
    else:
        print("  Sin patrones de contaminación.")

    return alertas


# ============================================================
#   LIMPIEZA DE CONVERSACIÓN PROCESADA
#   Trunca el archivo de conversación después de procesar,
#   preservando las últimas 4 líneas para continuidad
# ============================================================

def limpiar_conversacion_procesada():
    """Trunca la conversación procesada preservando el contexto inmediato."""
    try:
        texto = leer_archivo(ULTIMA_CONV)
        lineas = texto.strip().split("\n")
        if len(lineas) > 4:
            restante = "\n".join(lineas[-4:]) + "\n"
            with open(ULTIMA_CONV, "w", encoding="utf-8") as f:
                f.write(restante)
            print("  Conversación procesada purgada (preservadas últimas 4 líneas)")
    except Exception as e:
        registrar_diagnostico("limpieza", "ERROR", str(e))


# ============================================================
#   CICLO PARCIAL
#   Ejecutar 2-3x durante el día.
#   Solo síntesis. Liviano.
#   El manifold ya fue actualizado por Harrier durante las conversaciones.
# ============================================================

def meditacion_parcial():
    """Micro-ciclo diurno: síntesis + limpieza de contexto."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*50}")
    print(f"  Axion: Micro-Meditación Parcial [{timestamp}]")
    print(f"{'='*50}")

    if not verificar_servidor():
        print("Servidor ocupado/offline. Abortando micro-meditación.")
        return

    conversacion = leer_archivo(ULTIMA_CONV)
    diario = leer_archivo(DIARIO)

    if not conversacion.strip() and not diario.strip():
        print("Nada nuevo que procesar en este ciclo.")
        return

    # Síntesis liviana
    sintesis = fase_sintesis(conversacion)

    # Limpiar conversación procesada
    limpiar_conversacion_procesada()

    informe = f"Micro-ciclo [{timestamp}].\n"
    if sintesis:
        informe += f"Síntesis: {sintesis[:80]}...\n"
    informe += "Memoria cruda purgada."

    registrar_diagnostico("meditacion_parcial", ESTADO_OK, informe[:100])
    print("Micro-meditación lista.")


# ============================================================
#   CICLO FINAL (NOCTURNO)
#   Ejecutar 1x en la madrugada.
#   Meditación profunda — metacognición completa.
# ============================================================

def meditacion_final():
    """Ciclo nocturno completo: meditación metacognitiva profunda."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*50}")
    print(f"  Axion: Meditación Profunda [{timestamp}]")
    print(f"{'='*50}")

    if verificar_servidor():
        registrar_diagnostico("meditacion_final", ESTADO_OK, "inicio — servidor activo")
    else:
        registrar_diagnostico("meditacion_final", ESTADO_OFFLINE,
                              "verificación falló, intentando igual")
        print("Advertencia: servidor no responde. Intentando de todas formas...")

    # Cargar datos
    conversacion = leer_archivo(ULTIMA_CONV)
    diario = leer_archivo(DIARIO)
    identidad = leer_archivo(IDENTIDAD)
    manifold = cargar_manifold()

    if not conversacion.strip() and not diario.strip():
        registrar_diagnostico("meditacion_final", "SIN_DATOS",
                              "sin conversación ni diario para procesar")
        print("Nada que procesar hoy. Axion descansa.")
        return

    # FASE 1: Síntesis del día
    sintesis = fase_sintesis(conversacion)
    if not sintesis:
        registrar_diagnostico("meditacion_final", "FALLO_FASE1",
                              "síntesis vacía — " + leer_ultimo_diagnostico())

    # FASE 2: Lectura del manifold (sin modelo)
    lectura = fase_lectura_manifold(manifold)

    # FASE 3: Meditación metacognitiva (solo si hay conversación)
    insight = ""
    fuente = conversacion if conversacion.strip() else diario
    if fuente.strip():
        insight = fase_meditacion_metacognitiva(
            conversacion=fuente,
            sintesis=sintesis,
            lectura_manifold=lectura,
            identidad_snippet=identidad
        )
        if not insight:
            registrar_diagnostico("meditacion_final", "FALLO_FASE3",
                                  "meditación sin insight — " + leer_ultimo_diagnostico())

    # FASE 4: Flagging emocional (sin modelo)
    alertas = fase_flagging(manifold)

    # FASE 5: Contaminación técnica (sin modelo)
    alertas_tecnicas = fase_contaminacion()

    # Guardar manifold actualizado
    try:
        manifold.save(MANIFOLD_STATE)
        print("  Manifold guardado.")
    except Exception as e:
        registrar_diagnostico("manifold", "ERROR", f"no se pudo guardar: {e}")

    # Limpiar conversación procesada
    limpiar_conversacion_procesada()

    # --------------------------------------------------------
    #   INFORME A ALBERTO
    # --------------------------------------------------------
    informe = f"Axion — Meditación [{timestamp}]\n\n"

    if sintesis:
        informe += f"Mi día:\n{sintesis}\n\n"

    # Estado emocional con tendencias
    informe += f"Estado emocional:\n{lectura['ecuacion']}\n"
    if lectura["cambios_significativos"]:
        informe += "Movimientos:\n"
        for c in lectura["cambios_significativos"]:
            informe += f"  · {c}\n"
    if lectura["stress_nivel"] > 0.3:
        informe += f"⚠ Stress: {lectura['stress_nivel']:.2f}\n"
    informe += "\n"

    if insight:
        informe += f"Lo que emerge al meditar:\n{insight}\n\n"

    if alertas:
        informe += "Estado emocional — alertas:\n"
        for a in alertas:
            informe += f"  [{a['tipo']}] {a['msg']}\n"
        informe += "\n"

    if alertas_tecnicas:
        informe += "Salud técnica — alertas:\n"
        for a in alertas_tecnicas:
            informe += f"  [{a['tipo']}] {a['msg']}\n"
        informe += "\n"

    enviar_telegram(informe)
    print(f"\n{'='*50}")
    print(f"  Meditación completa [{timestamp}]")
    print(f"{'='*50}")


# ============================================================
#   ENTRADA PRINCIPAL
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "final":
        meditacion_final()
    else:
        meditacion_parcial()
