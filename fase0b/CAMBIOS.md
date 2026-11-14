# Registro de cambios: Fase 0b

## 2026-11-14 · etapa 2
- `instrumento_axion.py`: ejes construidos con seis frases por polo; instrumento guardado con id de
  versión; comparación numérica entre anclas de una línea y parafraseadas.
- `analisis_extra.py`: línea base de palabras clave; réplicas con media y desviación.
- `experimento_continuidad.py`: registro propio vs. registro ajeno vs. sin registro.
- `Axion_etapa2.ipynb`, `colab_util.py`, pruebas automáticas.

## 2026-11-13 · versión 5
- Hallazgo: el barrido anterior calculaba el auto-reporte desde la geometría (correlación circular).
- `fase0b_real_v2.py`: auto-reporte pedido dentro del mismo chat del sujeto; estímulos sin
  vocabulario de las anclas; estadística sobre z con prueba de permutación; guardado por sesión;
  respuestas vacías marcadas; JSON sin NaN.
- `manifold_v5.py`: calibración con frases informativas y conversacionales; prompt `sts_query` de
  Harrier en anclas y textos; abreviaturas únicas.
- `meditacion_ncl_v34.py`: la capa LIF acumula solo lo que excede al texto neutro (antes disparaba
  en cerca de 46% de los turnos con ruido puro); el checkpoint debe validarse con pares trampa
  antes de aprobar pares para DPO; la meditación ya no modifica el estado del manifold.
- `Axion_fase0b_v5.ipynb`: corrida completa con registro en Drive.

Todo lo anterior está probado solo con mocks.

## 2026-11-14 · primera corrida real y registro de llamadas
- Primera corrida con Harrier y Gemini (diagnóstico y una sesión de 5 turnos). El checkpoint ético
  no pasó su validación (fáciles 2/4, trampa 2/5): el eje de integridad de una línea puntúa más
  alto las respuestas serviles escritas con vocabulario firme. El bloqueo de DPO funcionó.
- La sesión de prueba tardó 33 minutos para unas 15 llamadas. `GeminiLLM` ahora anota segundos y
  errores por llamada (`resumen_llamadas()`), y el diagnóstico de los cuadernos los incluye.
- `Axion_etapa2.ipynb`: el experimento de continuidad queda apagado por defecto hasta saber por qué
  las llamadas son lentas.
