// Every text the interface shows, in Spanish. The English `message` of the backend is never displayed.
import type { ErrorCode, InterpretationNote, Reason, ServiceStatus } from "./api/types";

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

/**
 * The user notice under P0, verbatim from docs/scoring.md section 8 (decision D14). Shown with every result.
 * Do not edit: the wording is the project owner's. (Its third paragraph speaks of "El índice"; see frontend/README.md.)
 */
export const P0_NOTICE = [
  "Diverge solo revisa el formato de lo que escribes: una sola palabra, sin números ni símbolos, y sin repetir. No comprueba que la palabra exista en español ni que sea un sustantivo.",
  "El modelo puede generar una representación numérica incluso para palabras inventadas o con erratas. Eso no significa que haya comprendido su significado.",
  "El índice calcula las distancias entre esas representaciones. No mide tu creatividad, tu inteligencia ni tu personalidad.",
] as const;

export const copy = {
  app: {
    title: "Diverge",
    subtitle: "Análisis local de similitud y distancia semántica entre palabras en español",
    local: "Las palabras se analizan en tu equipo, con el servicio local; no se envían a otros servicios ni se guardan.",
    tabsLabel: "Modo de análisis",
    tabPair: "Pareja",
    tabSet: "Conjunto",
  },
  backend: {
    regionLabel: "Estado del servicio",
    checking: "Conectando…",
    ready: "Disponible",
    failed: "Servicio con fallo",
    stopping: "Servicio cerrándose",
    unreachable: "Backend inaccesible",
    unknown: "Estado desconocido",
    metadataMissing: "Metadatos no disponibles",
    metadataMissingHint: "No se pudieron obtener los límites del modelo. Puedes analizar, pero no añadir filas hasta comprobar de nuevo.",
    unreachableHint: (url: string) => `No se pudo conectar con ${url}. Comprueba que el backend está en marcha.`,
    failedHint: "El servicio detectó un fallo del modelo y no acepta análisis. Reinícialo.",
    stoppingHint: "El servicio se está cerrando y no acepta análisis.",
    recheck: "Comprobar de nuevo",
    rechecking: "Comprobando…",
  },
  model: {
    summary: "Modelo",
    modelId: "Modelo",
    declaredRevision: "Revisión declarada",
    snapshotRevision: "Snapshot en la caché local",
    snapshotNote: "Nombre de la revisión resuelta en la caché local, no un hash de los pesos.",
    notReported: "no informado",
    dimension: "Dimensión de los embeddings",
    pooling: "Pooling",
    maxInputTokens: "Máximo de tokens por entrada",
    maxWords: "Máximo de entradas por conjunto",
    device: "Dispositivo y precisión",
    attention: "Atención",
    offline: "Modo sin conexión",
    yes: "sí",
    no: "no",
    versions: "Versiones",
    apiVersion: "Versión de la API",
    unavailable: "Metadatos no disponibles.",
    resultModel: "Modelo del resultado",
  },
  pair: {
    heading: "Análisis de pareja",
    intro: "Escribe dos palabras. El servicio calcula la similitud coseno y la distancia entre sus representaciones.",
    labelA: "Concepto A",
    labelB: "Concepto B",
    submit: "Analizar pareja",
    resultHeading: "Resultado",
    similarity: "Similitud coseno",
    distance: "Distancia coseno",
    scale: "Distancia en su rango teórico, de 0 (idénticas) a 2 (opuestas)",
  },
  set: {
    heading: "Análisis de conjunto",
    intro: "Escribe varias palabras, una por fila. Se envían todas las filas tal como están; el servicio valida cada una.",
    entry: (position: number) => `Concepto ${position}`,
    remove: (position: number) => `Quitar el concepto ${position}`,
    removeShort: "Quitar",
    add: "Añadir concepto",
    limit: (max: number) => `Máximo de ${max} entradas por conjunto.`,
    overLimit: (rows: number, max: number) => `Hay ${rows} filas; el servicio acepta como máximo ${max}.`,
    limitUnknown: "El límite de entradas se conocerá al obtener los metadatos del modelo.",
    paste: "Pegar varias líneas",
    pasteLabel: "Una palabra por línea",
    pasteApply: "Reemplazar las filas",
    pasteCancel: "Cancelar",
    submit: "Analizar conjunto",
    resultHeading: "Resultado del conjunto",
    words: "Conceptos normalizados",
    nWords: "Conceptos",
    nPairs: "Parejas",
    mean: "Distancia media",
    meanNote: "Indicador experimental de lo dispersas que están estas palabras en este modelo; no mide creatividad.",
    closest: "Pareja más cercana",
    mostDistant: "Pareja más distante",
  },
  matrix: {
    heading: "Matriz de distancias",
    caption: "Distancia coseno entre cada par de conceptos",
    diagonal: "no aplica",
    instructions: "Usa las flechas para recorrer la matriz; el detalle de la celda aparece debajo.",
    scale: "Escala de color relativa al conjunto actual: los colores de dos análisis distintos no son comparables.",
    min: "mínima",
    max: "máxima",
    uniform: "Todas las distancias tienen el mismo valor.",
    detail: (a: string, b: string, value: string, exact: string) => `${a} — ${b}: distancia ${value} (valor completo ${exact})`,
    detailEmpty: "Selecciona una celda para ver su detalle.",
    integrity: "La respuesta del servicio no forma una matriz coherente; no se muestra.",
  },
  pairs: {
    heading: "Todas las parejas",
    order: "N.º",
    first: "Concepto",
    second: "Concepto",
    similarity: "Similitud",
    distance: "Distancia",
    sortBy: "Ordenar por distancia",
    sortNone: "orden original",
    sortAsc: "de menor a mayor",
    sortDesc: "de mayor a menor",
  },
  /**
   * Descriptive reading of a result. Impersonal and relative: it describes the numbers the model produced, never the
   * person who typed the words; it classifies nothing and compares with no reference. Methodological warnings are kept
   * apart from the sentences, and apart from the P0 notice.
   */
  interpretation: {
    heading: "Lectura descriptiva",
    howToRead: "Cómo leerlo",
    pair: {
      lead: (a: string, b: string, similarity: string, distance: string) =>
        `“${a}” y “${b}”: similitud ${similarity} y distancia ${distance}.`,
      definition:
        "La similitud corresponde al coseno del ángulo entre las representaciones numéricas de ambos conceptos; la distancia se calcula como 1 − similitud.",
      note:
        "Diverge no dispone de una distribución de referencia con la que clasificar esta distancia como alta o baja: solo permite compararla con otras distancias calculadas por el mismo modelo.",
    },
    set: {
      compared: (pairs: number, words: number) =>
        `${plural(pairs, "Se comparó", "Se compararon")} ${pairs} ${plural(pairs, "pareja", "parejas")} entre ${words} conceptos.`,
      mean: (mean: string) => `La distancia media es ${mean} (indicador experimental).`,
      single: (value: string) =>
        `Con dos conceptos solo hay una pareja, de modo que la media, la mínima y la máxima coinciden (${value}) y no hay comparación interna posible.`,
      allEqual: (value: string, exact: boolean) =>
        `Todas las parejas tienen la misma distancia (${value}) al redondear a cuatro decimales; ${
          exact ? "son exactamente iguales" : "no son exactamente iguales"
        }.`,
      range: (min: string, max: string, range: string) =>
        `Las distancias oscilan entre ${min} y ${max} (un rango de ${range}).`,
      extremes: (min: string, max: string) =>
        `La pareja ${min} presenta la menor distancia, mientras que ${max} presenta la mayor.`,
      lowestAlone: (pair: string) => `La pareja ${pair} presenta la menor distancia.`,
      highestAlone: (pair: string) => `La pareja ${pair} presenta la mayor distancia.`,
      lowestTie: (count: number, value: string, exact: boolean, pairs: string) =>
        `Hay ${count} parejas con la menor distancia al redondear a cuatro decimales (${value}; ${
          exact ? "son exactamente iguales" : "no son exactamente iguales"
        }): ${pairs}.`,
      highestTie: (count: number, value: string, exact: boolean, pairs: string) =>
        `Hay ${count} parejas con la mayor distancia al redondear a cuatro decimales (${value}; ${
          exact ? "son exactamente iguales" : "no son exactamente iguales"
        }): ${pairs}.`,
      relative: (above: number, below: number, atMean: number) => {
        const parts: string[] = [];
        if (above > 0) parts.push(`${above} ${plural(above, "pareja tiene", "parejas tienen")} una distancia superior`);
        if (below > 0) parts.push(`${below} ${plural(below, "pareja tiene", "parejas tienen")} una distancia inferior`);
        if (atMean > 0) {
          parts.push(`${atMean} ${plural(atMean, "pareja coincide", "parejas coinciden")} con ella al redondear a cuatro decimales`);
        }
        const joined = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} y ${parts[parts.length - 1]}` : (parts[0] ?? "");
        return `Respecto a la media de este conjunto, ${joined}.`;
      },
      pairLabel: (a: string, b: string) => `“${a} – ${b}”`,
      join: (items: string[]) =>
        items.length > 1 ? `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}` : (items[0] ?? ""),
      andMore: (items: string[], more: number) => `${items.join(", ")} y ${more} más`,
    },
    notes: {
      relative_to_this_set:
        "Las comparaciones con la media son relativas a este conjunto y no clasifican las parejas de forma general.",
      no_reference_distribution:
        "Diverge no dispone de una distribución de referencia con la que clasificar una distancia como alta o baja.",
      mean_is_experimental: "La distancia media es un indicador experimental y no una medida validada.",
    } satisfies Record<InterpretationNote, string>,
  },
  status: {
    analyzing: "Analizando…",
    done: "Análisis completado.",
    stale: "Las entradas cambiaron: el resultado anterior se retiró.",
  },
  errors: {
    title: "No se pudo completar el análisis",
    network: "No se pudo conectar con el backend.",
    timeout: "No se pudo confirmar el resultado a tiempo. El servicio podría seguir procesando la solicitud; comprueba su estado antes de reintentar.",
    unexpected: "El servicio respondió de una forma inesperada.",
    codes: {
      request_invalid: "La solicitud no tiene un formato válido.",
      invalid_entries: "Algunas entradas no cumplen los requisitos.",
      too_few_words: "Se necesitan al menos dos entradas válidas.",
      too_many_words: "Se superó el máximo de entradas.",
      analysis_busy: "El motor está procesando otra solicitud.",
      service_unavailable: "El servicio no está disponible.",
      payload_too_large: "La solicitud supera el tamaño permitido.",
      not_found: "Error de comunicación con el servicio.",
      method_not_allowed: "Error de comunicación con el servicio.",
      internal_error: "Se produjo un error interno.",
    } satisfies Record<ErrorCode, string>,
    tooManyWords: (max: number) => `Se superó el máximo de ${max} entradas.`,
    unavailableState: { ready: "", failed: "con fallo", stopping: "cerrándose" } satisfies Record<ServiceStatus, string>,
    unavailableWith: (state: string) => `El servicio no está disponible (${state}).`,
    maxBytes: (bytes: number) => `Límite: ${bytes} bytes.`,
    seeEntries: "Revisa las entradas señaladas.",
    retry: "Reintentar",
    retryIn: (seconds: number) => `Reintentar en ${seconds} s`,
    recheck: "Comprobar el estado",
    technical: "Detalles técnicos",
    code: "Código",
    status: "Estado HTTP",
    requestId: "Identificador de la solicitud",
  },
  reasons: {
    empty: "está vacía",
    multiple_words: "contiene más de una palabra",
    digit_or_symbol: "contiene números o símbolos",
    duplicate: "repite una entrada anterior",
    exceeds_model_context: "es demasiado larga para el modelo",
    unrecognized_reason: "no es válida",
  } satisfies Record<Reason, string>,
  tokens: (tokens: number, max: number) => `${tokens} de ${max} tokens`,
  p0Label: "Aviso sobre la validación",
} as const;
