# Diverge

[English](README.md) | **Español**

> **Traducción.** Esta es una traducción al español del [README en inglés](README.md), que es la versión de referencia. Si hay alguna diferencia, prevalece el texto en inglés.

> **Distribución pública.** Este repositorio es una distribución pública independiente de Diverge v0.1.0-beta.1, preparada a partir del estado actual de un repositorio de investigación aparte. Los identificadores de commits, las etiquetas, las ubicaciones de copias de seguridad y los conjuntos de datos que mencionan los documentos de investigación se refieren a ese repositorio privado y no forman parte de esta distribución. No se incluyen los conjuntos de datos internos de investigación ni los recursos de validación. `CLAUDE.md`, citado en algunos documentos históricos, es un archivo privado de contexto del proyecto y no forma parte de esta distribución.

Diverge es una aplicación local, **en desarrollo**, para analizar la similitud y la divergencia semántica entre palabras del español con un modelo de embeddings multilingüe que se ejecuta en tu propio equipo. También pretende estudiar en qué medida las distancias del modelo se corresponden con las valoraciones de similitud de hablantes de español ecuatoriano.

> **Estado: existe una primera versión local.** `backend/` contiene el motor semántico, una capa de servicio y una API HTTP v1; `frontend/` contiene una interfaz React para ella. Junto a ellos, el repositorio contiene documentos de investigación, decisiones y experimentos reproducibles. El estudio de similitud con personas no ha comenzado. Véanse [Estado actual](#estado-actual) y [Ejecución local](#ejecución-local).

## Versión

**Versión actual: `v0.1.0-beta.1`.** Es una beta experimental y local: se ejecuta en tu propio equipo, no es un servicio alojado, y su interfaz, el contrato de su API y sus resultados pueden cambiar antes de una versión estable. No es un instrumento validado.

Varios elementos llevan versión, y son independientes entre sí:

| Qué | Identificador | Dónde se declara |
|---|---|---|
| Producto | `v0.1.0-beta.1` | Etiqueta de Git, cuando el propietario la cree (todavía no creada) |
| Frontend | `0.1.0-beta.1` (SemVer) | `frontend/package.json`, `frontend/package-lock.json` |
| Backend | `0.1.0b1` (PEP 440) | `backend/app/__init__.py` (`__version__`), también la versión de la aplicación FastAPI |
| API HTTP | `v1` | Prefijo de rutas `/api/v1` |
| Modelo | Revisión fijada, `a9cb5338491faf32b73dd17b714a31821c021bbf` | `backend/app/engine`; la informa `/api/v1/model` |
| Línea base experimental | Su propio identificador, por ejemplo `semantic_baseline_dat7_v0.1` | `experiments/results/` (no versionado en Git) |

`0.1.0-beta.1` y `0.1.0b1` son la misma versión escrita con la notación de cada ecosistema. La etiqueta histórica `dat-line-v0.1` marca la línea de investigación DAT conservada (`docs/decisions.md`, D21) en el repositorio privado de investigación; no es una versión de este producto y no forma parte de esta distribución.

## El problema

Los modelos de embeddings representan las palabras como vectores, y el ángulo entre dos vectores se usa con frecuencia como medida de lo cercanos que son sus significados. Que esas distancias coincidan con lo que los hablantes de español, y en particular los de español ecuatoriano, perciben como similar no es algo que un modelo garantice.

Diverge pretende hacer esas distancias calculables en local, inspeccionables y reproducibles, y contrastarlas con juicios humanos.

## Cómo funciona

1. **Embeddings.** Cada palabra se normaliza (`strip`, NFC, `casefold`, NFC) y la codifica el modelo de referencia, `ibm-granite/granite-embedding-278m-multilingual`, en una revisión fijada. La inferencia se ejecuta en local, en CPU y en fp32, y produce vectores de 768 dimensiones, normalizados en L2 por el propio módulo `Normalize` del modelo.
2. **Similitud y distancia.** Para dos palabras con vectores *a* y *b*:
   - la similitud del coseno `cos(a, b)` está en [−1, 1], y un valor mayor significa más similar;
   - la distancia del coseno `d = 1 − cos(a, b)` está en [0, 2], y un valor mayor significa menos similar.

   Contienen la misma información en sentidos opuestos. Una distancia es una afirmación sobre dos vectores de este modelo, no sobre las palabras en cualquier contexto.
3. **Parejas y conjuntos.**
   - **La pareja es la unidad principal de análisis:** dos palabras dan una distancia.
   - **Un conjunto** de *n* palabras produce las *n*(*n* − 1)/2 parejas, con una matriz de distancias y sus parejas más cercanas y más distantes.
   - **La media de las distancias de un conjunto** es un **indicador experimental** de lo dispersas que están sus palabras en este modelo. No es una medida validada de ninguna otra cosa.
4. **DAT7.** La línea de investigación original implementaba un protocolo inspirado en la Divergent Association Task: las primeras siete palabras elegibles, 21 parejas, media × 100. Se conserva como referencia histórica y como función opcional, no como el centro del producto.

## Límites

- **Un solo modelo.** Los resultados dependen del modelo, de su revisión y de su configuración, que todo resultado debe identificar. Superar las comprobaciones de reproducibilidad no hace que el modelo sea el mejor para el español ni que esté validado semánticamente.
- **Rango comprimido.** En la línea base exploratoria de DAT7, las distancias entre parejas de palabras «diversas» elegidas a mano estuvieron entre 0,17 y 0,39. Los valores absolutos no deben leerse como porcentajes ni como notas.
- **Palabras sin contexto.** La polisemia, los sentidos regionales, los plurales y las erratas modifican las distancias. Los antónimos pueden resultar cercanos.
- **Solo comprobaciones de formato.** Las comprobaciones de entrada solo cubren el formato: una sola palabra, solo letras, sin repetición. No verifican que la palabra exista en español.
- **Estudio pequeño.** Cualquier estudio con personas planificado aquí es pequeño y local. Evalúa el modelo frente a juicios humanos y no es una validación psicométrica.

## Lo que Diverge no mide

Diverge no mide creatividad, inteligencia, originalidad ni ninguna capacidad cognitiva, y no es un instrumento psicométrico validado. No reproduce la validez científica del DAT ni traslada sus normas, percentiles o clasificaciones. No se presenta como el primer sistema multilingüe de análisis de divergencia semántica.

## Arquitectura

```
frontend/              React + TypeScript + Vite: análisis de parejas (principal), de conjuntos, panel del modelo
    │  HTTP, solo local (127.0.0.1)
backend/
    app/api, app/main  FastAPI: /pairs (principal), /sets, /model, /health
    app/services       AnalysisService: límite de entradas, un análisis a la vez, estado del servicio, errores sin texto del usuario
    app/engine         Python puro, sin importaciones de FastAPI: normalización, validación, embedder, distancias
    │
caché local del modelo     caché de Hugging Face, revisión fijada, sin conexión; los pesos nunca están en el repositorio
```

El motor se puede usar por sí solo, desde las pruebas y, más adelante, desde los scripts de análisis del estudio, que todavía no existen. La API no guarda estado: no hay base de datos, cuentas ni seguimiento. Las valoraciones humanas, cuando se recojan, permanecerán anónimas y fuera del repositorio, y nunca pasarán por el motor ni por la API.

## Tecnologías

| Componente | Tecnología | Estado |
|---|---|---|
| Lenguaje y entorno | Python 3.12, entorno virtual del proyecto `.venv` | En uso |
| Inferencia | PyTorch (compilación para CPU), Transformers, Sentence Transformers, NumPy | En uso por el motor y por los experimentos; versiones en `backend/requirements.txt` |
| Pruebas | pytest (backend); Vitest y Testing Library (frontend) | En uso; versiones en `backend/requirements-dev.txt` y `frontend/package.json` |
| API | FastAPI, Starlette, Pydantic, Uvicorn | En uso; versiones en `backend/requirements.txt` |
| Interfaz | React, TypeScript, Vite | En uso; versiones exactas en `frontend/package.json` y `frontend/package-lock.json` |
| Empaquetado | Docker, al final, con los pesos del modelo en un volumen o caché | Previsto |

## Estado actual

| Componente | Estado | Dónde |
|---|---|---|
| Decisiones y alcance del proyecto | **Existe** | `docs/decisions.md` (D21 es el alcance vigente) |
| Comprobaciones técnicas del modelo: carga, pooling, normalización, reproducibilidad | **Existe**, Fase 2a superada (PASS) | `experiments/embedding_poc/`, `experiments/check_2a_correctness.py` |
| Adjudicación léxica (D19) e inventario regional (D20), con validadores y pruebas | **Existe** en el repositorio de investigación; no se incluye en esta distribución | `experiments/semantic_2b/evidence/`, `experiments/wordsets/regional/` (repositorio privado de investigación, no forma parte de esta distribución) |
| Línea base DAT7 y diagnósticos B3/B4 | **Experimental**, exploratorio, sobre conjuntos de palabras provisionales; verificado con datos privados, no incluidos en esta distribución; resultados no versionados, con copias de seguridad privadas | `experiments/results/` |
| Línea de investigación DAT, conservada | **Histórica**; conservada en el repositorio privado de investigación (etiqueta `dat-line-v0.1`), no incluida en esta distribución | `docs/phase-2b-design.md`, `docs/acceptance-criteria-2c.md`, `docs/scoring.md`, `docs/roadmap.md` |
| Motor semántico y sus pruebas, incluida la regresión de la línea base DAT7 (necesita archivos de referencia privados, no incluidos, y solo se ejecuta con `--baseline`) | **Existe** | `backend/app/engine/`, `backend/tests/` |
| Capa de servicio (`AnalysisService`) | **Existe** | `backend/app/services/` |
| API HTTP v1: `/health`, `/model`, `/pairs`, `/sets` | **Existe**; solo local, sin autenticación ni persistencia | `backend/app/api/`, `backend/app/main.py` |
| Interfaz: análisis de parejas y de conjuntos, matriz de distancias, estado del backend | **Existe**; sus pruebas automáticas usan un embedder sintético. El 2026-11-06 también se ejecutó una vez, en local y de extremo a extremo, con el modelo Granite real: los análisis de parejas y de conjuntos, los casos de error de entrada y el panel del modelo funcionaron a través de la API. Esa ejecución no tenía umbrales de aceptación predefinidos | `frontend/` |
| Estudio de similitud con personas | **Previsto**; no se han recogido datos; requiere antes diseño y requisitos institucionales | `docs/decisions.md` D21, `docs/future/human-evaluation.md` |

Las instrucciones de instalación y ejecución están en [Ejecución local](#ejecución-local). Los experimentos documentan sus propios comandos: véase `experiments/embedding_poc/README.md`. La interfaz muestra el aviso de que Diverge solo comprueba el formato de la entrada (`docs/scoring.md` §8); ninguno de sus resultados es una medida validada de creatividad ni de ningún otro constructo.

## Obtención del modelo

Los pesos del modelo no están en el repositorio. Descarga una vez la revisión fijada (unos 544 MiB, nueve archivos). Granite Embedding 278M Multilingual tiene licencia Apache-2.0 según la ficha del modelo de esa revisión; la licencia del tokenizer no se ha verificado por separado. Tras la descarga, la aplicación funciona sin conexión (`HF_HUB_OFFLINE=1`, `local_files_only=True`) y no descarga nada al arrancar. Cuando carga el modelo, el motor solicita la revisión fijada únicamente a la caché local y comprueba sus módulos, el pooling, la dimensión, el dtype y el dispositivo. El SHA-256 de `model.safetensors` lo comprueban las pruebas marcadas `model` (`pytest -m model`, con el modelo descargado), no el arranque.

El ejecutable `hf` viene con `huggingface_hub`, que instala `backend/requirements.txt`. Activa el entorno virtual donde lo instalaste (por ejemplo `.\.venv\Scripts\Activate.ps1`) o llámalo por su ruta (`.\.venv\Scripts\hf.exe`). Los dos comandos siguientes son independientes, con la misma revisión y los mismos nueve nombres de archivo. **A no descarga nada; B sí descarga.**

A. Simulacro (no descarga nada):

```powershell
hf download `
  --revision a9cb5338491faf32b73dd17b714a31821c021bbf `
  --dry-run `
  ibm-granite/granite-embedding-278m-multilingual `
  "1_Pooling/config.json" `
  "config.json" `
  "model.safetensors" `
  "modules.json" `
  "sentence_bert_config.json" `
  "sentencepiece.bpe.model" `
  "special_tokens_map.json" `
  "tokenizer.json" `
  "tokenizer_config.json"
```

B. Descarga (el mismo comando sin la línea `--dry-run`):

```powershell
hf download `
  --revision a9cb5338491faf32b73dd17b714a31821c021bbf `
  ibm-granite/granite-embedding-278m-multilingual `
  "1_Pooling/config.json" `
  "config.json" `
  "model.safetensors" `
  "modules.json" `
  "sentence_bert_config.json" `
  "sentencepiece.bpe.model" `
  "special_tokens_map.json" `
  "tokenizer.json" `
  "tokenizer_config.json"
```

## Ejecución local

Dos procesos en el mismo equipo, cada uno en su propia terminal. Detalles: [`backend/README.md`](backend/README.md) y [`frontend/README.md`](frontend/README.md), ambos en inglés. Probado solo en Windows: los comandos de ejemplo usan PowerShell y rutas de Windows como `..\.venv\Scripts\python.exe`.

0. Solo la primera vez, desde la raíz del repositorio: crea el entorno virtual `.venv` con Python 3.12 e instala las dependencias del backend (`requirements-dev.txt` instala además las herramientas de pruebas):

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
   ```

   Después descarga el modelo ([Obtención del modelo](#obtención-del-modelo)) y ejecuta `npm ci` en `frontend/`. Las pruebas del backend que no necesitan ni el modelo ni datos privados se ejecutan desde `backend/` con `..\.venv\Scripts\python.exe -B -m pytest -m "not model"` (`backend/README.md`, sección Tests).

1. Backend, desde `backend/` (Python 3.12 en `.venv`; el modelo ya debe estar en la caché local de Hugging Face, véase [Obtención del modelo](#obtención-del-modelo)):

   ```powershell
   ..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --lifespan on --loop asyncio --http h11 --no-access-log --timeout-graceful-shutdown 10
   ```

2. Interfaz, desde `frontend/` (Node 24.15 o posterior; `npm ci` la primera vez):

   ```powershell
   npm run dev
   ```

   Después abre `http://127.0.0.1:5173`.

## Licencias y terceros

Este repositorio no concede por ahora ninguna licencia sobre sus materiales originales. No se concede ningún permiso general para reutilizar, modificar ni redistribuir esos materiales. Los componentes de terceros siguen sujetos a sus respectivas licencias; véanse `NOTICE` y `THIRD_PARTY_NOTICES.md`, y `docs/third-party-review.md` para la revisión detallada.

## Asistencia de IA

Durante el desarrollo se usaron herramientas de IA:

- **ChatGPT** (OpenAI) ayudó a redactar el documento inicial de contexto del proyecto, que no forma parte de esta distribución, y las instrucciones dadas al asistente de programación.
- **Claude Code** (Anthropic) generó y modificó código, pruebas y documentación durante la implementación, siguiendo esas instrucciones.

El propietario del proyecto fijó los objetivos y el alcance, tomó las decisiones del proyecto y autorizó cada etapa del trabajo. Esta sección describe cómo se construyó el proyecto; no atribuye autoría ni derechos a ninguna herramienta de IA.
