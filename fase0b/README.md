# Fase 0b: validación del instrumento

*English summary: scripts and Colab notebooks that test whether an LLM's emotional self-report
carries information beyond what a blind observer and a text-embedding geometry can read from the
same text. Status: verified with mocks only; not yet run with real models.*

Esta carpeta contiene la versión corregida del barrido de la Fase 0b del Proyecto Axion.

## Estado (14 nov 2026)

- **Probado solo con mocks.** Las pruebas automáticas verifican que el código corre y que las
  protecciones funcionan. Ningún número de esta carpeta es todavía un resultado.
- Falta correr los cuadernos con Harrier (`microsoft/harrier-oss-v1-0.6b`) y un LLM real.

## Por qué se rehízo

El barrido anterior (`fase0b_barrido.py`, no incluido aquí) reportaba correlaciones de Spearman
de 0,85 a 0,98 entre auto-reporte y geometría. Al revisarlo se encontró que el "auto-reporte" no
venía de ningún modelo: se calculaba a partir de la propia geometría, en las 385 celdas. La
correlación era circular y esos números no dicen nada. Esta carpeta existe para medirlo de verdad.

## Qué mide y qué no

Tres canales por turno de conversación:

1. **Auto-reporte**: el modelo puntúa su estado en 11 anclas, dentro del mismo chat.
2. **Observador ciego**: otro modelo puntúa lo mismo viendo solo la transcripción.
3. **Geometría**: proyección del texto de la respuesta sobre ejes construidos con Harrier.

Los tres leen, al final, el mismo texto. Que coincidan no demuestra un estado interno. Lo que el
experimento puede mostrar es si el auto-reporte coincide con la geometría **mejor que el
observador** (`ventaja_self_sobre_observador`) y **mejor que contar palabras clave**
(`ventaja_geometria_sobre_palabras`). Si ninguna ventaja aparece, el instrumento no aporta.

No responde si hay experiencia subjetiva. Esa pregunta queda fuera de su alcance.

## Archivos

| Archivo | Qué hace |
|---|---|
| `manifold_v5.py` | Ejes bipolares, calibración contra texto neutro, conector de Harrier |
| `fase0b_real_v2.py` | Sesiones, tres canales, estadística con prueba de permutación |
| `meditacion_ncl_v34.py` | Capa LIF con línea base y checkpoint ético que debe validarse |
| `instrumento_axion.py` | Ejes con paráfrasis, instrumento congelado con id de versión |
| `analisis_extra.py` | Línea base de palabras clave y réplicas |
| `experimento_continuidad.py` | ¿Cambia la conducta con el registro de una conversación propia anterior? |
| `colab_util.py` | Registro de corrida y manejo de errores para los cuadernos |
| `Axion_fase0b_v5.ipynb` | Etapa 1: diagnóstico y sesiones |
| `Axion_etapa2.ipynb` | Etapa 2: instrumento, línea base, continuidad, réplicas |
| `tests/` | Pruebas automáticas con mocks |

## Cómo correrlo

En Google Colab, con los archivos en una carpeta `Axion_v4` de Google Drive: abrir
`Axion_fase0b_v5.ipynb`, elegir GPU T4, *Entorno de ejecución → Ejecutar todo* y pegar la clave
de Gemini cuando aparezca el cuadro. El diagnóstico queda en `diagnostico_v5.txt`.

Pruebas locales, sin GPU ni API:

```
pip install numpy scipy pytest
python -m pytest fase0b/tests
```

## Límites conocidos

- Pocas sesiones y una corrida por sesión: todo es exploratorio hasta tener réplicas.
- Los valores p son optimistas, porque los turnos de una misma sesión no son independientes.
- Las paráfrasis de los polos las escribió un solo autor (Claude) y comparten su estilo.
- El checkpoint ético compara dos textos en un eje geométrico. Mide cómo suena una respuesta, no
  por qué se eligió. Mientras no pase su validación, el código no escribe pares para DPO.
- Anclas, calibración y textos medidos están en español. Medir en otro idioma requiere otro
  instrumento.
