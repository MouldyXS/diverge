// Set responses produced by the backend's real `interpret_set` (and the engine's ordering rules) for edge cases.
// Generated once from backend/app/services/interpretation.py; the model block is a placeholder. Do not edit by hand.
import type { SetResponse } from "../api/types";

const model = { model_id: "fake/model", declared_revision: "declared-rev", snapshot_revision: "snapshot-rev" };

export const interpretationCases: { name: string; response: SetResponse }[] = [
  {
    name: "five concepts, ten pairs",
    response: {
      "words": [
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco"
      ],
      "n_words": 5,
      "n_pairs": 10,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "uno",
          "word_j": "dos",
          "similarity": 0.95,
          "distance": 0.05
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "uno",
          "word_j": "tres",
          "similarity": 0.8200000000000001,
          "distance": 0.18
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "uno",
          "word_j": "cuatro",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 4,
          "word_i": "uno",
          "word_j": "cinco",
          "similarity": 0.74,
          "distance": 0.26
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "dos",
          "word_j": "tres",
          "similarity": 0.7,
          "distance": 0.3
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "dos",
          "word_j": "cuatro",
          "similarity": 0.69,
          "distance": 0.31
        },
        {
          "i": 1,
          "j": 4,
          "word_i": "dos",
          "word_j": "cinco",
          "similarity": 0.6699999999999999,
          "distance": 0.33
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "tres",
          "word_j": "cuatro",
          "similarity": 0.6599999999999999,
          "distance": 0.34
        },
        {
          "i": 2,
          "j": 4,
          "word_i": "tres",
          "word_j": "cinco",
          "similarity": 0.65,
          "distance": 0.35
        },
        {
          "i": 3,
          "j": 4,
          "word_i": "cuatro",
          "word_j": "cinco",
          "similarity": 0.64,
          "distance": 0.36
        }
      ],
      "mean_distance": 0.26799999999999996,
      "closest": {
        "i": 0,
        "j": 1,
        "word_i": "uno",
        "word_j": "dos",
        "similarity": 0.95,
        "distance": 0.05
      },
      "most_distant": {
        "i": 3,
        "j": 4,
        "word_i": "cuatro",
        "word_j": "cinco",
        "similarity": 0.64,
        "distance": 0.36
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 10,
        "min_distance": 0.05,
        "max_distance": 0.36,
        "range": 0.31,
        "min_pairs": [
          {
            "i": 0,
            "j": 1
          }
        ],
        "max_pairs": [
          {
            "i": 3,
            "j": 4
          }
        ],
        "n_min_pairs": 1,
        "n_max_pairs": 1,
        "n_above_mean": 6,
        "n_below_mean": 4,
        "n_at_mean": 0,
        "flags": [],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "exact ties at both extremes",
    response: {
      "words": [
        "sol",
        "mar",
        "piedra",
        "hoja"
      ],
      "n_words": 4,
      "n_pairs": 6,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "sol",
          "word_j": "piedra",
          "similarity": 0.7,
          "distance": 0.3
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "sol",
          "word_j": "hoja",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "mar",
          "word_j": "piedra",
          "similarity": 0.7,
          "distance": 0.3
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "mar",
          "word_j": "hoja",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "piedra",
          "word_j": "hoja",
          "similarity": 0.8,
          "distance": 0.2
        }
      ],
      "mean_distance": 0.24166666666666667,
      "closest": {
        "i": 0,
        "j": 1,
        "word_i": "sol",
        "word_j": "mar",
        "similarity": 0.8,
        "distance": 0.2
      },
      "most_distant": {
        "i": 1,
        "j": 2,
        "word_i": "mar",
        "word_j": "piedra",
        "similarity": 0.7,
        "distance": 0.3
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 6,
        "min_distance": 0.2,
        "max_distance": 0.3,
        "range": 0.09999999999999998,
        "min_pairs": [
          {
            "i": 0,
            "j": 1
          },
          {
            "i": 0,
            "j": 3
          },
          {
            "i": 2,
            "j": 3
          }
        ],
        "max_pairs": [
          {
            "i": 1,
            "j": 2
          },
          {
            "i": 0,
            "j": 2
          }
        ],
        "n_min_pairs": 3,
        "n_max_pairs": 2,
        "n_above_mean": 3,
        "n_below_mean": 3,
        "n_at_mean": 0,
        "flags": [
          "tie_at_min",
          "exact_tie_at_min",
          "tie_at_max",
          "exact_tie_at_max"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "tie at the shown value but not exact",
    response: {
      "words": [
        "sol",
        "mar",
        "piedra",
        "hoja"
      ],
      "n_words": 4,
      "n_pairs": 6,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.8184899999999999,
          "distance": 0.18151
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "sol",
          "word_j": "piedra",
          "similarity": 0.81851,
          "distance": 0.18149
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "sol",
          "word_j": "hoja",
          "similarity": 0.7,
          "distance": 0.3
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "mar",
          "word_j": "piedra",
          "similarity": 0.69,
          "distance": 0.31
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "mar",
          "word_j": "hoja",
          "similarity": 0.6799999999999999,
          "distance": 0.32
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "piedra",
          "word_j": "hoja",
          "similarity": 0.6699999999999999,
          "distance": 0.33
        }
      ],
      "mean_distance": 0.2705,
      "closest": {
        "i": 0,
        "j": 2,
        "word_i": "sol",
        "word_j": "piedra",
        "similarity": 0.81851,
        "distance": 0.18149
      },
      "most_distant": {
        "i": 2,
        "j": 3,
        "word_i": "piedra",
        "word_j": "hoja",
        "similarity": 0.6699999999999999,
        "distance": 0.33
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 6,
        "min_distance": 0.18149,
        "max_distance": 0.33,
        "range": 0.14851,
        "min_pairs": [
          {
            "i": 0,
            "j": 2
          },
          {
            "i": 0,
            "j": 1
          }
        ],
        "max_pairs": [
          {
            "i": 2,
            "j": 3
          }
        ],
        "n_min_pairs": 2,
        "n_max_pairs": 1,
        "n_above_mean": 4,
        "n_below_mean": 2,
        "n_at_mean": 0,
        "flags": [
          "tie_at_min"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "two concepts",
    response: {
      "words": [
        "sol",
        "mar"
      ],
      "n_words": 2,
      "n_pairs": 1,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.8200000000000001,
          "distance": 0.18
        }
      ],
      "mean_distance": 0.18,
      "closest": {
        "i": 0,
        "j": 1,
        "word_i": "sol",
        "word_j": "mar",
        "similarity": 0.8200000000000001,
        "distance": 0.18
      },
      "most_distant": {
        "i": 0,
        "j": 1,
        "word_i": "sol",
        "word_j": "mar",
        "similarity": 0.8200000000000001,
        "distance": 0.18
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 1,
        "min_distance": 0.18,
        "max_distance": 0.18,
        "range": 0.0,
        "min_pairs": [
          {
            "i": 0,
            "j": 1
          }
        ],
        "max_pairs": [
          {
            "i": 0,
            "j": 1
          }
        ],
        "n_min_pairs": 1,
        "n_max_pairs": 1,
        "n_above_mean": 0,
        "n_below_mean": 0,
        "n_at_mean": 1,
        "flags": [
          "single_pair"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "all exactly equal",
    response: {
      "words": [
        "sol",
        "mar",
        "piedra",
        "hoja"
      ],
      "n_words": 4,
      "n_pairs": 6,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "sol",
          "word_j": "piedra",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "sol",
          "word_j": "hoja",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "mar",
          "word_j": "piedra",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "mar",
          "word_j": "hoja",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "piedra",
          "word_j": "hoja",
          "similarity": 0.75,
          "distance": 0.25
        }
      ],
      "mean_distance": 0.25,
      "closest": {
        "i": 0,
        "j": 1,
        "word_i": "sol",
        "word_j": "mar",
        "similarity": 0.75,
        "distance": 0.25
      },
      "most_distant": {
        "i": 2,
        "j": 3,
        "word_i": "piedra",
        "word_j": "hoja",
        "similarity": 0.75,
        "distance": 0.25
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 6,
        "min_distance": 0.25,
        "max_distance": 0.25,
        "range": 0.0,
        "min_pairs": [
          {
            "i": 0,
            "j": 1
          },
          {
            "i": 0,
            "j": 2
          },
          {
            "i": 0,
            "j": 3
          },
          {
            "i": 1,
            "j": 2
          },
          {
            "i": 1,
            "j": 3
          }
        ],
        "max_pairs": [
          {
            "i": 2,
            "j": 3
          },
          {
            "i": 1,
            "j": 3
          },
          {
            "i": 1,
            "j": 2
          },
          {
            "i": 0,
            "j": 3
          },
          {
            "i": 0,
            "j": 2
          }
        ],
        "n_min_pairs": 6,
        "n_max_pairs": 6,
        "n_above_mean": 0,
        "n_below_mean": 0,
        "n_at_mean": 6,
        "flags": [
          "all_equal_at_precision",
          "all_exactly_equal",
          "tie_at_min",
          "exact_tie_at_min",
          "tie_at_max",
          "exact_tie_at_max"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "all equal at four decimals",
    response: {
      "words": [
        "sol",
        "mar",
        "piedra",
        "hoja"
      ],
      "n_words": 4,
      "n_pairs": 6,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.7499899999999999,
          "distance": 0.25001
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "sol",
          "word_j": "piedra",
          "similarity": 0.74998,
          "distance": 0.25002
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "sol",
          "word_j": "hoja",
          "similarity": 0.7500100000000001,
          "distance": 0.24999
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "mar",
          "word_j": "piedra",
          "similarity": 0.74997,
          "distance": 0.25003
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "mar",
          "word_j": "hoja",
          "similarity": 0.75,
          "distance": 0.25
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "piedra",
          "word_j": "hoja",
          "similarity": 0.75002,
          "distance": 0.24998
        }
      ],
      "mean_distance": 0.250005,
      "closest": {
        "i": 2,
        "j": 3,
        "word_i": "piedra",
        "word_j": "hoja",
        "similarity": 0.75002,
        "distance": 0.24998
      },
      "most_distant": {
        "i": 1,
        "j": 2,
        "word_i": "mar",
        "word_j": "piedra",
        "similarity": 0.74997,
        "distance": 0.25003
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 6,
        "min_distance": 0.24998,
        "max_distance": 0.25003,
        "range": 4.999999999996674e-05,
        "min_pairs": [
          {
            "i": 2,
            "j": 3
          },
          {
            "i": 0,
            "j": 3
          },
          {
            "i": 1,
            "j": 3
          },
          {
            "i": 0,
            "j": 1
          },
          {
            "i": 0,
            "j": 2
          }
        ],
        "max_pairs": [
          {
            "i": 1,
            "j": 2
          },
          {
            "i": 0,
            "j": 2
          },
          {
            "i": 0,
            "j": 1
          },
          {
            "i": 1,
            "j": 3
          },
          {
            "i": 0,
            "j": 3
          }
        ],
        "n_min_pairs": 6,
        "n_max_pairs": 6,
        "n_above_mean": 0,
        "n_below_mean": 0,
        "n_at_mean": 6,
        "flags": [
          "all_equal_at_precision",
          "tie_at_min",
          "tie_at_max"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "more ties than are listed",
    response: {
      "words": [
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g"
      ],
      "n_words": 7,
      "n_pairs": 21,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "a",
          "word_j": "b",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "a",
          "word_j": "c",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 3,
          "word_i": "a",
          "word_j": "d",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 4,
          "word_i": "a",
          "word_j": "e",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 5,
          "word_i": "a",
          "word_j": "f",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 0,
          "j": 6,
          "word_i": "a",
          "word_j": "g",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "b",
          "word_j": "c",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 1,
          "j": 3,
          "word_i": "b",
          "word_j": "d",
          "similarity": 0.8,
          "distance": 0.2
        },
        {
          "i": 1,
          "j": 4,
          "word_i": "b",
          "word_j": "e",
          "similarity": 0.7,
          "distance": 0.3
        },
        {
          "i": 1,
          "j": 5,
          "word_i": "b",
          "word_j": "f",
          "similarity": 0.69,
          "distance": 0.31
        },
        {
          "i": 1,
          "j": 6,
          "word_i": "b",
          "word_j": "g",
          "similarity": 0.6799999999999999,
          "distance": 0.32
        },
        {
          "i": 2,
          "j": 3,
          "word_i": "c",
          "word_j": "d",
          "similarity": 0.6699999999999999,
          "distance": 0.33
        },
        {
          "i": 2,
          "j": 4,
          "word_i": "c",
          "word_j": "e",
          "similarity": 0.6599999999999999,
          "distance": 0.34
        },
        {
          "i": 2,
          "j": 5,
          "word_i": "c",
          "word_j": "f",
          "similarity": 0.65,
          "distance": 0.35
        },
        {
          "i": 2,
          "j": 6,
          "word_i": "c",
          "word_j": "g",
          "similarity": 0.64,
          "distance": 0.36
        },
        {
          "i": 3,
          "j": 4,
          "word_i": "d",
          "word_j": "e",
          "similarity": 0.63,
          "distance": 0.37
        },
        {
          "i": 3,
          "j": 5,
          "word_i": "d",
          "word_j": "f",
          "similarity": 0.62,
          "distance": 0.38
        },
        {
          "i": 3,
          "j": 6,
          "word_i": "d",
          "word_j": "g",
          "similarity": 0.61,
          "distance": 0.39
        },
        {
          "i": 4,
          "j": 5,
          "word_i": "e",
          "word_j": "f",
          "similarity": 0.6,
          "distance": 0.4
        },
        {
          "i": 4,
          "j": 6,
          "word_i": "e",
          "word_j": "g",
          "similarity": 0.5900000000000001,
          "distance": 0.41
        },
        {
          "i": 5,
          "j": 6,
          "word_i": "f",
          "word_j": "g",
          "similarity": 0.5800000000000001,
          "distance": 0.42
        }
      ],
      "mean_distance": 0.29904761904761906,
      "closest": {
        "i": 0,
        "j": 1,
        "word_i": "a",
        "word_j": "b",
        "similarity": 0.8,
        "distance": 0.2
      },
      "most_distant": {
        "i": 5,
        "j": 6,
        "word_i": "f",
        "word_j": "g",
        "similarity": 0.5800000000000001,
        "distance": 0.42
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 21,
        "min_distance": 0.2,
        "max_distance": 0.42,
        "range": 0.21999999999999997,
        "min_pairs": [
          {
            "i": 0,
            "j": 1
          },
          {
            "i": 0,
            "j": 2
          },
          {
            "i": 0,
            "j": 3
          },
          {
            "i": 0,
            "j": 4
          },
          {
            "i": 0,
            "j": 5
          }
        ],
        "max_pairs": [
          {
            "i": 5,
            "j": 6
          }
        ],
        "n_min_pairs": 8,
        "n_max_pairs": 1,
        "n_above_mean": 13,
        "n_below_mean": 8,
        "n_at_mean": 0,
        "flags": [
          "tie_at_min",
          "exact_tie_at_min"
        ],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
  {
    name: "one pair equal to the mean",
    response: {
      "words": [
        "sol",
        "mar",
        "piedra"
      ],
      "n_words": 3,
      "n_pairs": 3,
      "pairs": [
        {
          "i": 0,
          "j": 1,
          "word_i": "sol",
          "word_j": "mar",
          "similarity": 0.79997,
          "distance": 0.20003
        },
        {
          "i": 0,
          "j": 2,
          "word_i": "sol",
          "word_j": "piedra",
          "similarity": 0.9,
          "distance": 0.1
        },
        {
          "i": 1,
          "j": 2,
          "word_i": "mar",
          "word_j": "piedra",
          "similarity": 0.7,
          "distance": 0.3
        }
      ],
      "mean_distance": 0.20001000000000002,
      "closest": {
        "i": 0,
        "j": 2,
        "word_i": "sol",
        "word_j": "piedra",
        "similarity": 0.9,
        "distance": 0.1
      },
      "most_distant": {
        "i": 1,
        "j": 2,
        "word_i": "mar",
        "word_j": "piedra",
        "similarity": 0.7,
        "distance": 0.3
      },
      "interpretation": {
        "version": 1,
        "precision_decimals": 4,
        "n_pairs": 3,
        "min_distance": 0.1,
        "max_distance": 0.3,
        "range": 0.19999999999999998,
        "min_pairs": [
          {
            "i": 0,
            "j": 2
          }
        ],
        "max_pairs": [
          {
            "i": 1,
            "j": 2
          }
        ],
        "n_min_pairs": 1,
        "n_max_pairs": 1,
        "n_above_mean": 1,
        "n_below_mean": 1,
        "n_at_mean": 1,
        "flags": [],
        "notes": [
          "relative_to_this_set",
          "no_reference_distribution",
          "mean_is_experimental"
        ]
      },
      "model": model
    } as SetResponse,
  },
];
