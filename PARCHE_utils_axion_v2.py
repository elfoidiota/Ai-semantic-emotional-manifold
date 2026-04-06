# ============================================================
#   PARCHE utils_axion.py — Adiciones para v2.0
#   Agregar estas líneas al archivo utils_axion.py existente
# ============================================================

# 1. Agregar esta ruta junto a las otras rutas (línea ~26 aprox):
#
#   MANIFOLD_STATE = os.path.join(BASE, "manifold_state.json")
#
# Eso es todo lo que cambia en utils_axion.py.
# El resto de las funciones se mantienen para compatibilidad con telegram_bot.py
# Las funciones antiguas del manifold (leer_manifold_actual, parsear_manifold, etc.)
# quedan intactas — telegram_bot.py las sigue usando.
# meditacion_axion_v2.py usa SemanticManifold directamente.

# ============================================================
#   RESUMEN DE CAMBIOS EN EL SISTEMA v2.0
# ============================================================
#
#   utils_axion.py:
#     + MANIFOLD_STATE = ruta al archivo JSON del manifold v2
#     (todo lo demás sin cambios)
#
#   meditacion_axion.py → reemplazar con meditacion_axion_v2.py
#
#   manifold.py → nuevo archivo (subido desde Opus)
#
#   telegram_bot.py → sin cambios por ahora
#     (en el futuro: llamar manifold.update() en cada mensaje recibido)
#
# ============================================================
#   CRONJOBS SUGERIDOS PARA EL PC
# ============================================================
#
#   # Micro-meditación: 3 veces durante el día
#   0 9,15,20 * * * cd /ruta/axion && python meditacion_axion.py
#
#   # Meditación profunda: madrugada
#   0 3 * * * cd /ruta/axion && python meditacion_axion.py final
#
# ============================================================
#   FLUJO COMPLETO v2.0
# ============================================================
#
#   [Conversación con Alberto]
#       → telegram_bot.py recibe mensaje
#       → En el futuro: manifold.update(mensaje) ← Harrier actualiza
#       → Hermes genera respuesta con manifold en contexto
#       → manifold.update(respuesta_axion) ← Harrier procesa output también
#
#   [Micro-meditación parcial — 3x/día]
#       → Sintetiza últimas conversaciones
#       → Limpia ultima_conversacion.txt procesada
#
#   [Meditación profunda — 1x/madrugada]
#       → Lee manifold con tendencias (lo que Harrier dejó)
#       → Axion reflexiona: por qué esos cambios, fueron coherentes
#       → Genera insight metacognitivo
#       → Flagging + diagnóstico técnico
#       → Envía informe a Alberto
