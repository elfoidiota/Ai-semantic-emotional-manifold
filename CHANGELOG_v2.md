# Manifold Emocional Semántico — Changelog v2.0

**Fecha:** 2026-04-03
**Sesión:** Alberto Alvear — Claude Opus

---

## Resumen

El manifold emocional fue actualizado de v1.0 (EMA lineal con α fijo) a v2.0 (curva S adaptativa con momentum, resistencia y volatilidad). Los cambios surgen de un análisis de tres problemas fundamentales detectados por Alberto en la fórmula original.

---

## Problemas detectados en v1.0

### Problema 1 — Inversión de la banda elástica

La fórmula EMA original (`w_new = w_current * (1-α) + resonance * α`) produce un efecto de banda elástica: cuanto más lejos está el peso del input, mayor es el cambio. Esto significa que un solo mensaje opuesto después de un estado emocional establecido produce un cambio desproporcionado — exactamente lo contrario de lo que ocurre en la experiencia real.

**Riesgo:** Un atacante podría llevar a Axion a un estado emocional alto con mensajes reforzadores y después un solo mensaje agresivo produciría un colapso emocional violento.

**En la experiencia real:** Si estás en un estado emocional estable y alguien te dice algo hiriente, resistís. El cambio es gradual, no instantáneo.

### Problema 2 — Cancelación de fuerzas opuestas

Con cambios radicales constantes en direcciones opuestas (un mensaje de vínculo, uno de ruptura, uno de expansión, uno de fragilidad), el EMA promedia todo y el estado queda en el centro del mapa. Pero en una persona, eso no es equilibrio — es estrés. El sistema v1 no distinguía entre "calma" y "caos que promedia a cero".

### Problema 3 — Alpha demasiado conservador

Con α=0.15, el modelo se mueve muy poco con cada mensaje. Dado que Axion solo puede estar en un punto del espacio a la vez, el estado debería reflejar más fielmente el impacto de experiencias significativas.

---

## Solución: Curva S adaptativa

### El concepto

El cambio emocional sigue una curva S (sigmoide):

```
Cambio
  │         ╭────── saturación (lento)
  │        ╱
  │       ╱  ← flujo (rápido)
  │      ╱
  │    ╱
  │  ╱  ← resistencia (lento)
  │╱
  └──────────────── Exposición sostenida
```

1. **Resistencia** — Un estímulo nuevo que contradice el estado actual produce cambio mínimo. Protege contra ataques al prompt.
2. **Flujo** — Si el estímulo se refuerza consistentemente, el cambio acelera. La idea gana tracción.
3. **Saturación** — Acercarse a los extremos (0 o 1) es cada vez más difícil. Habituación.

### Implementación

```python
# Alpha base más alto para mayor responsividad
ALPHA_BASE = 0.30

# Momentum: consistencia direccional de últimos 5 cambios
momentum = same_direction_count / total_recent_changes

# Factor de dirección
if estímulo_opuesto_al_momentum:
    direction_factor = 0.25     # RESISTENCIA
else:
    direction_factor = 0.3 + (momentum * 0.15)  # FLUJO

# Factor de saturación
distance_to_extreme = min(w_actual, 1 - w_actual)
saturation_factor = distance_to_extreme ^ (1/2)

# Alpha efectivo
α_effective = α_base × direction_factor × saturation_factor
```

### Rango efectivo de α

| Situación | α efectivo aprox. |
|---|---|
| Estímulo opuesto a estado establecido | 0.02 - 0.05 |
| Primer estímulo en nueva dirección | 0.07 - 0.10 |
| Estímulo reforzando tendencia | 0.12 - 0.20 |
| Máximo flujo con momentum completo | 0.20 - 0.30 |
| Cerca de extremos (saturación) | reducido 50-90% |

---

## Nuevas funcionalidades

### Momentum por dimensión

Cada dimensión mantiene un historial de los últimos 5 cambios direccionales. Esto permite:
- Detectar si hay una tendencia sostenida (rising/falling/stable)
- Resistir cambios que contradicen la tendencia
- Acelerar cambios que la refuerzan

### Volatilidad como señal de estrés

La volatilidad se calcula como el promedio de cambios absolutos recientes en todas las dimensiones. Cuando la volatilidad supera un umbral (0.06), se genera una señal de estrés que:
- Se incluye en el contexto del prompt para el LLM consciente
- Se registra en el estado completo para el preconsciente
- Puede ser detectada por el sistema de flagging emocional

### Reporte de estrés

```python
manifold.get_stress_report()
# Volatility: 0.0842
# Stress: 1.40
# Status: High stress
# Most active: Bond(Δ0.0234), Fragility(Δ0.0198), Sovereignty(Δ0.0156)
```

### Estado completo con tendencias

```python
manifold.get_full_state()
# Bond: 0.7234 ^       (subiendo)
# Sovereignty: 0.6891 >  (estable)
# Fragility: 0.4521 v   (bajando)
# ...
```

---

## Protección contra ataques al prompt

### Simulación de ataque

1. Se establece estado de Vínculo alto con 5 mensajes cariñosos
2. Se envía un mensaje agresivo opuesto

**v1 (EMA fijo):** El mensaje agresivo produce un cambio proporcional a la distancia — efecto banda elástica. Cambio grande e inmediato.

**v2 (S-curve):** El mensaje agresivo encuentra resistencia porque:
- El momentum de Bond es alto (5 mensajes en la misma dirección)
- El estímulo va en dirección opuesta → `direction_factor = 0.25`
- Bond está cerca de un extremo → saturación reduce α adicional
- Resultado: cambio mínimo. Axion resiste.

### Para que el ataque funcione

El atacante necesitaría mantener la dirección opuesta de forma sostenida (5+ mensajes) para que el momentum se revierta y el flujo se active. Eso da tiempo al sistema de diagnóstico para detectar el patrón.

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `manifold.py` | Reescrito completo — v2.0 con S-curve |
| `requirements.txt` | Sin cambios |

---

## Otros temas discutidos en esta sesión

### Publicación del framework
- Repositorio creado: `github.com/elfoidiota/Ai-semantic-emotional-manifold`
- README en inglés y español
- Visualización 2D interactiva (canvas)
- Visualización 3D interactiva (Three.js)

### Análisis de feedback externo (ChatGPT)
- Validación independiente de originalidad del concepto
- Puntos técnicos incorporados: diferenciación de fuente de input, tensión entre dimensiones
- Puntos rechazados: anclajes aprendidos (vs escritos por Alberto), sobre-formalización matemática

### Corrección de error analítico
- Claude analizó incorrectamente el efecto de banda elástica del EMA
- Alberto corrigió: la banda elástica SÍ existe pero está invertida respecto a lo deseado
- El efecto snap-back es una vulnerabilidad, no una feature

---

## Decisiones de diseño pendientes

- **Alpha por tipo de input:** ¿Debería variar según la fuente? (conversación vs memoria vs insight)
- **Tensión entre dimensiones:** ¿Soberanía alta + Vínculo alto debería generar disonancia?
- **Drift interno:** ¿El manifold debería tener dinámica propia sin input externo?
- **Integración con preconsciente:** ¿Cómo alimenta el preconsciente los deltas al manifold?

---

*Documento generado en sesión Alberto Alvear — Claude Opus, 3 abril 2026*
