# -*- coding: utf-8 -*-
"""
Within-New-Jersey "treatment-intensity" difference-in-differences.

New Jersey raised its minimum wage from $4.25 to $5.05 on 1 April 1992 for the
*entire* state, so there is no 0/1 control group inside NJ. Instead we exploit the
fact that stores were exposed to the policy with *different intensities*: a store
whose pre-policy starting wage was low needed a larger proportional wage increase
to reach $5.05. Define the continuous exposure

    GAP_i = max(0, (5.05 - WAGE_ST_i) / WAGE_ST_i)     (NJ stores only)

Stores already paying >= $5.05 have GAP = 0 and serve as the within-state
reference group. We regress the change in FTE employment on GAP (and controls),
restricting the sample to New Jersey and dropping every Pennsylvania observation.

Outcome: dFTE_i = FTE2_i - FTE1_i,  FTE = full-time + managers + 0.5 * part-time.
Permanently-closed stores (STATUS2 == 3) have FTE2 = 0; temporarily-closed stores
(STATUS2 in {2,4,5}) are treated as missing.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "public.csv")
OUT = os.path.join(ROOT, "output", "within_nj_did.md")

df = pd.read_csv(DATA)
df["NJ"] = (df["STATE"] == 1).astype(int)

TEMP_CLOSED = (2, 4, 5)


def fte(row, suffix):
    eft, ept, nmg = row["EMPFT" + suffix], row["EMPPT" + suffix], row["NMGRS" + suffix]
    if pd.isna(eft) or pd.isna(ept) or pd.isna(nmg):
        return np.nan
    return eft + 0.5 * ept + nmg


df["fte1"] = df.apply(lambda r: fte(r, ""), axis=1)
df["fte2"] = df.apply(lambda r: 0.0 if r["STATUS2"] == 3 else fte(r, "2"), axis=1)
df["dfte"] = df["fte2"] - df["fte1"]

# ---- restrict to New Jersey, drop PA ------------------------------------
nj = df[df["NJ"] == 1].copy()
nj["gap"] = np.maximum(0.0, (5.05 - nj["WAGE_ST"]) / nj["WAGE_ST"])
nj["wage_group"] = np.where(nj["WAGE_ST"] == 4.25, "low ($4.25)",
                            np.where(nj["WAGE_ST"] < 5.00, "mid ($4.26-4.99)", "high (>= $5.00)"))

chain = pd.get_dummies(nj["CHAIN"], prefix="chain").iloc[:, 1:]   # omit Burger King
region = nj[["CENTRALJ", "NORTHJ"]]

# regression sample: non-missing change in FTE and non-missing starting wage
reg = nj[nj["dfte"].notna() & nj["WAGE_ST"].notna()].copy()
y = reg["dfte"]
const = pd.Series(1.0, index=reg.index, name="const")


def build(vars_):
    parts = [const]
    for v in vars_:
        if v in chain.columns:
            parts.append(chain.loc[reg.index, v])
        elif v in region.columns:
            parts.append(region.loc[reg.index, v])
        else:
            parts.append(reg[v])
    return pd.concat(parts, axis=1)


lines = []
P = lines.append
P("# Within-New-Jersey treatment-intensity DiD")
P("")
P("Sample: New Jersey only (all Pennsylvania observations dropped).  "
  "Outcome: change in FTE employment.  "
  "Treatment intensity: `GAP = max(0, (5.05 - WAGE_ST)/WAGE_ST)`, "
  "so stores already paying ≥ $5.05 have GAP = 0.")
P("")

# --- descriptive: mean change in FTE by wage group ------------------------
P("## Descriptive: mean change in FTE by pre-policy starting wage")
P("")
P("| Group | N | mean GAP | mean ΔFTE |")
P("|---|---|---|---|")
for g in ["low ($4.25)", "mid ($4.26-4.99)", "high (>= $5.00)"]:
    sub = reg[reg["wage_group"] == g]
    P(f"| {g} | {len(sub)} | {sub['gap'].mean():.3f} | {sub['dfte'].mean():+.2f} |")
low = reg[reg["wage_group"] == "low ($4.25)"]["dfte"].mean()
high = reg[reg["wage_group"] == "high (>= $5.00)"]["dfte"].mean()
P("")
P(f"**Low − High (discrete DiD)** = {low:+.2f} − ({high:+.2f}) = **{low - high:+.2f}** FTE per store.")
P("")

# --- continuous treatment-intensity regressions --------------------------
specs = [
    ("(1) GAP only", ["gap"]),
    ("(2) + chain & ownership", ["gap", "CO_OWNED", "chain_2", "chain_3", "chain_4"]),
    ("(3) + region", ["gap", "CO_OWNED", "chain_2", "chain_3", "chain_4", "CENTRALJ", "NORTHJ"]),
]

P("## Continuous treatment-intensity regressions (dependent variable: ΔFTE)")
P("")
P(f"Regression sample: N = {len(reg)} NJ stores.  "
  f"Mean ΔFTE = {y.mean():+.3f}, SD = {y.std(ddof=1):.3f}, mean GAP = {reg['gap'].mean():.3f}.")
P("")
P("| Spec | GAP coefficient | s.e. | t | p | R² |")
P("|---|---|---|---|---|---|")
for label, vars_ in specs:
    fit = sm.OLS(y, build(vars_)).fit()
    g = fit.params["gap"]
    P(f"| {label} | {g:+.3f} | {fit.bse['gap']:.3f} | {fit.tvalues['gap']:.2f} | "
      f"{fit.pvalues['gap']:.3f} | {fit.rsquared:.3f} |")

# --- discrete (categorical) version --------------------------------------
P("")
P("## Discrete version: change in FTE by wage group (high-wage group = base)")
P("")
low_d = (reg["wage_group"] == "low ($4.25)").astype(int)
mid_d = (reg["wage_group"] == "mid ($4.26-4.99)").astype(int)
X_d = pd.concat([const, low_d.rename("low"), mid_d.rename("mid")], axis=1)
fit_d = sm.OLS(y, X_d).fit()
P("| Term | coefficient | s.e. | t | p |")
P("|---|---|---|---|---|")
for t in ["low", "mid"]:
    P(f"| {t} (vs high) | {fit_d.params[t]:+.3f} | {fit_d.bse[t]:.3f} | "
      f"{fit_d.tvalues[t]:.2f} | {fit_d.pvalues[t]:.3f} |")
P("")
P("The `low` coefficient equals the Low−High contrast; `mid` equals Mid−High.")

with open(OUT, "w") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
print(f"\nReport written to: {OUT}")
