# Within-New-Jersey treatment-intensity DiD

Sample: New Jersey only (all Pennsylvania observations dropped).  Outcome: change in FTE employment.  Treatment intensity: `GAP = max(0, (5.05 - WAGE_ST)/WAGE_ST)`, so stores already paying ≥ $5.05 have GAP = 0.

## Descriptive: mean change in FTE by pre-policy starting wage

| Group | N | mean GAP | mean ΔFTE |
|---|---|---|---|
| low ($4.25) | 94 | 0.188 | +1.20 |
| mid ($4.26-4.99) | 132 | 0.097 | +0.71 |
| high (>= $5.00) | 67 | 0.006 | -2.16 |

**Low − High (discrete DiD)** = +1.20 − (-2.16) = **+3.36** FTE per store.

## Continuous treatment-intensity regressions (dependent variable: ΔFTE)

Regression sample: N = 293 NJ stores.  Mean ΔFTE = +0.213, SD = 8.076, mean GAP = 0.105.

| Spec | GAP coefficient | s.e. | t | p | R² |
|---|---|---|---|---|---|
| (1) GAP only | +13.081 | 6.600 | 1.98 | 0.048 | 0.013 |
| (2) + chain & ownership | +12.274 | 6.818 | 1.80 | 0.073 | 0.025 |
| (3) + region | +12.137 | 6.868 | 1.77 | 0.078 | 0.029 |

## Discrete version: change in FTE by wage group (high-wage group = base)

| Term | coefficient | s.e. | t | p |
|---|---|---|---|---|
| low (vs high) | +3.362 | 1.279 | 2.63 | 0.009 |
| mid (vs high) | +2.867 | 1.200 | 2.39 | 0.017 |

The `low` coefficient equals the Low−High contrast; `mid` equals Mid−High.