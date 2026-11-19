# Staged YAML vs flat reference

State: complete

| Model | Task | Arm | Result | Autonomous pass | Seconds | LLM calls | Native reads | Script inspections |
|---|---|---|---|---|---|---|---|---|
| 31b | w3lib_264 | staged | fail | False | 619.2166811460047 | 48 | 0 | 23 |
| 31b | w3lib_264 | flat | pass | False | 910.2507261930004 | 34 | 27 | 0 |
| 31b | packaging_1125 | staged | fail | False | 307.59653758100467 | 48 | 0 | 42 |
| 31b | packaging_1125 | flat | fail | False | 613.0390900170023 | 48 | 33 | 0 |
| 31b | platformdirs_540 | staged | fail | False | 424.13679049799975 | 23 | 0 | 4 |
| 31b | platformdirs_540 | flat | fail | False | 363.274008487002 | 19 | 6 | 0 |
| 12b | w3lib_264 | staged | fail | False | 904.8485772809945 | 14 | 0 | 0 |
| 12b | w3lib_264 | flat | fail | False | 245.66301463500713 | 48 | 1 | 0 |
| 12b | packaging_1125 | staged | fail | False | 370.35320430999855 | 48 | 0 | 0 |
| 12b | packaging_1125 | flat | fail | False | 156.56701368000358 | 19 | 11 | 0 |
| 12b | platformdirs_540 | staged | fail | False | 414.80582536399015 | 48 | 0 | 0 |
| 12b | platformdirs_540 | flat | fail | False | 115.2326652030024 | 48 | 0 | 0 |

Script limits inspection execution, not LLM calls per stage. Planner has no tools; only submitter has submit_patch. Total session still shares 48 calls.
