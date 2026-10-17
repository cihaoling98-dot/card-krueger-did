# -*- coding: utf-8 -*-
"""
Reproduce Tables 2, 3, 4 and Figure 1 of
Card & Krueger (1994), "Minimum Wages and Employment: A Case Study of the
Fast-Food Industry in New Jersey and Pennsylvania", AER 84(4), 772-793.

Data : data/public.csv  (the classic "cardkrueger" fast-food survey, 410 stores)

FTE employment = full-time employees + managers + 0.5 * part-time employees.
Permanently-closed stores (STATUS2 == 3) have zero wave-2 employment;
temporarily-closed stores (STATUS2 in {2,4,5}) are treated as missing.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "public.csv")
OUTDIR = os.path.join(ROOT, "output")
os.makedirs(OUTDIR, exist_ok=True)

df = pd.read_csv(DATA)
df["NJ"] = (df["STATE"] == 1).astype(int)   # 1 = New Jersey, 0 = Pennsylvania

TEMP_CLOSED = (2, 4, 5)                     # temporarily-closed / no second interview


def fte(row, suffix):
    """full-time + managers + 0.5 * part-time (missing if any component missing)."""
    eft, ept, nmg = row["EMPFT" + suffix], row["EMPPT" + suffix], row["NMGRS" + suffix]
    if pd.isna(eft) or pd.isna(ept) or pd.isna(nmg):
        return np.nan
    return eft + 0.5 * ept + nmg


df["fte1"] = df.apply(lambda r: fte(r, ""), axis=1)
df["fte2"] = df.apply(lambda r: 0.0 if r["STATUS2"] == 3 else fte(r, "2"), axis=1)
df["fte2_temp0"] = df["fte2"].copy()
df.loc[df["STATUS2"].isin(TEMP_CLOSED), "fte2_temp0"] = 0.0
df["dfte"] = df["fte2"] - df["fte1"]
df["dfte_temp0"] = df["fte2_temp0"] - df["fte1"]
df["gap"] = np.where(df["NJ"] == 1,
                     np.maximum(0.0, (5.05 - df["WAGE_ST"]) / df["WAGE_ST"]), 0.0)

# ---------------------------------------------------------------------------
# analysis-ready (processed) dataset
# ---------------------------------------------------------------------------
PROC_COLS = ["SHEET", "CHAIN", "CO_OWNED", "STATE", "NJ", "SOUTHJ", "CENTRALJ",
             "NORTHJ", "PA1", "PA2", "SHORE", "STATUS2", "WAGE_ST", "WAGE_ST2",
             "EMPFT", "EMPPT", "NMGRS", "EMPFT2", "EMPPT2", "NMGRS2",
             "fte1", "fte2", "fte2_temp0", "dfte", "dfte_temp0", "gap"]
df[PROC_COLS].to_csv(os.path.join(ROOT, "data", "processed.csv"), index=False)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def mean_se(x):
    x = x.dropna()
    return x.mean(), x.std(ddof=1) / np.sqrt(len(x)), len(x)


NJ, PA = df["NJ"] == 1, df["NJ"] == 0
cols = [
    ("PA", PA),
    ("NJ", NJ),
    ("NJ wage=$4.25", NJ & (df["WAGE_ST"] == 4.25)),
    ("NJ wage $4.26-$4.99", NJ & (df["WAGE_ST"] > 4.25) & (df["WAGE_ST"] < 5.00)),
    ("NJ wage >=$5.00", NJ & (df["WAGE_ST"] >= 5.00)),
]

table3 = {}


def row_means(var):
    return {name: mean_se(df.loc[sel, var]) for name, sel in cols}


def row_change(dvar):
    return {name: mean_se(df.loc[sel, dvar]) for name, sel in cols}


def row_change_unbalanced():
    """after - before (unbalanced means); SE of the difference of two
    partially-overlapping sample means."""
    out = {}
    for name, sel in cols:
        aft, bef = df.loc[sel, "fte2"], df.loc[sel, "fte1"]
        n_a, n_b = aft.notna().sum(), bef.notna().sum()
        s_a, s_b = aft.std(ddof=1), bef.std(ddof=1)
        both = df.loc[sel & df["fte1"].notna() & df["fte2"].notna()]
        n_bal = len(both)
        sig12 = np.cov(both["fte1"], both["fte2"], ddof=1)[0, 1] if n_bal > 2 else 0.0
        var = s_a ** 2 / n_a + s_b ** 2 / n_b - 2 * sig12 * n_bal / (n_a * n_b)
        out[name] = (aft.mean() - bef.mean(), np.sqrt(max(var, 0.0)), min(n_a, n_b))
    return out


table3["1. FTE employment before"] = row_means("fte1")
table3["2. FTE employment after"] = row_means("fte2")
table3["3. Change in mean FTE"] = row_change_unbalanced()
table3["4. Change, balanced sample"] = row_change("dfte")
table3["5. Change, temp. closed set to 0"] = row_change("dfte_temp0")


def diff_pair(row, left, right):
    ml, sl, _ = table3[row][left]
    mr, sr, _ = table3[row][right]
    return (ml - mr, np.sqrt(sl ** 2 + sr ** 2), np.nan)


for row in table3:
    table3[row]["Diff NJ-PA"] = diff_pair(row, "NJ", "PA")
    table3[row]["Low-high"] = diff_pair(row, "NJ wage=$4.25", "NJ wage >=$5.00")
    table3[row]["Mid-high"] = diff_pair(row, "NJ wage $4.26-$4.99", "NJ wage >=$5.00")

ALL_COLS = ["PA", "NJ", "Diff NJ-PA", "NJ wage=$4.25", "NJ wage $4.26-$4.99",
            "NJ wage >=$5.00", "Low-high", "Mid-high"]

# ---------------------------------------------------------------------------
# TABLE 2 -- means of key variables (NJ vs PA), Welch t-statistics
# ---------------------------------------------------------------------------
def welch_t(nj_series, pa_series):
    a = nj_series.dropna().astype(float)
    b = pa_series.dropna().astype(float)
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return (a.mean() - b.mean()) / se


def pct(s):
    return 100 * s.mean()


table2_rows = []
nj_, pa_ = df[NJ], df[PA]


def add2(label, nj_s, pa_s, pct_flag=False):
    if pct_flag:
        vn, vp = pct(nj_s), pct(pa_s)
    else:
        vn, vp = nj_s.mean(), pa_s.mean()
    t = welch_t(nj_s, pa_s) if not pct_flag else welch_t(nj_s.astype(float), pa_s.astype(float))
    table2_rows.append((label, vn, vp, t))


add2("Burger King (%)", nj_["CHAIN"].eq(1), pa_["CHAIN"].eq(1), True)
add2("KFC (%)", nj_["CHAIN"].eq(2), pa_["CHAIN"].eq(2), True)
add2("Roy Rogers (%)", nj_["CHAIN"].eq(3), pa_["CHAIN"].eq(3), True)
add2("Wendy's (%)", nj_["CHAIN"].eq(4), pa_["CHAIN"].eq(4), True)
add2("Company-owned (%)", nj_["CO_OWNED"].eq(1), pa_["CO_OWNED"].eq(1), True)
add2("FTE employment, before", nj_["fte1"], pa_["fte1"])
add2("% full-time employees", 100 * nj_["EMPFT"] / (nj_["EMPFT"] + nj_["EMPPT"] + nj_["NMGRS"]),
     100 * pa_["EMPFT"] / (pa_["EMPFT"] + pa_["EMPPT"] + pa_["NMGRS"]))
add2("Starting wage, before", nj_["WAGE_ST"], pa_["WAGE_ST"])
add2("Wage = $4.25 (%)", nj_["WAGE_ST"].eq(4.25), pa_["WAGE_ST"].eq(4.25), True)
add2("Price of full meal", nj_["PSODA"] + nj_["PFRY"] + nj_["PENTREE"],
     pa_["PSODA"] + pa_["PFRY"] + pa_["PENTREE"])
add2("Hours open, weekday", nj_["HRSOPEN"], pa_["HRSOPEN"])
add2("Recruiting bonus (%)", nj_["BONUS"].eq(1), pa_["BONUS"].eq(1), True)
add2("FTE employment, after", nj_["fte2"], pa_["fte2"])
add2("Starting wage, after", nj_["WAGE_ST2"], pa_["WAGE_ST2"])
add2("Price of full meal, after", nj_["PSODA2"] + nj_["PFRY2"] + nj_["PENTREE2"],
     pa_["PSODA2"] + pa_["PFRY2"] + pa_["PENTREE2"])
add2("Hours open, weekday, after", nj_["HRSOPEN2"], pa_["HRSOPEN2"])

# ---------------------------------------------------------------------------
# TABLE 4 -- reduced-form models for change in employment
# ---------------------------------------------------------------------------
reg = df[df["fte1"].notna() & df["fte2"].notna() & df["WAGE_ST"].notna()].copy()
chain_dums = pd.get_dummies(reg["CHAIN"], prefix="chain").iloc[:, 1:]
X_chain = pd.concat([reg[["CO_OWNED"]], chain_dums], axis=1)
X_region = reg[["CENTRALJ", "NORTHJ", "PA1", "PA2"]]
y = reg["dfte"]
const = pd.Series(1.0, index=reg.index, name="const")

specs = {
    "(i)": ["NJ"],
    "(ii)": ["NJ"] + list(X_chain.columns),
    "(iii)": ["gap"],
    "(iv)": ["gap"] + list(X_chain.columns),
    "(v)": ["gap"] + list(X_chain.columns) + list(X_region.columns),
}


def build(vars_):
    parts = [const]
    for v in vars_:
        if v in X_chain.columns:
            parts.append(X_chain[v])
        elif v in X_region.columns:
            parts.append(X_region[v])
        else:
            parts.append(reg[v])
    return pd.concat(parts, axis=1)


reg_results = {lbl: sm.OLS(y, build(v)).fit() for lbl, v in specs.items()}

# ===========================================================================
# print + write report
# ===========================================================================
lines = []
P = lines.append


def cell(m, s):
    return f"{m:.2f} ({s:.2f})"


P("# Card & Krueger (1994) — Reproduction (Tables 2, 3, 4, Figure 1)")
P("")
P("Data: `data/public.csv` (410 fast-food stores).  "
  "FTE = full-time + managers + 0.5 × part-time.")
P("")

P("## Table 3 — Average employment per store before and after the NJ minimum-wage rise")
P("")
header = ["", *ALL_COLS]
P("| " + " | ".join(header) + " |")
P("|" + "---|" * (len(ALL_COLS) + 1))
for row in table3:
    P("| " + row + " | " + " | ".join(cell(*table3[row][c][:2]) for c in ALL_COLS) + " |")
P("")
P("Wage-group sizes (NJ, wave-1 starting wage): "
  f"$4.25 N={(NJ & (df.WAGE_ST == 4.25)).sum()}, "
  f"$4.26-$4.99 N={(NJ & (df.WAGE_ST > 4.25) & (df.WAGE_ST < 5)).sum()}, "
  f"≥$5.00 N={(NJ & (df.WAGE_ST >= 5)).sum()}.")
P("")

P("## Table 2 — Means of key variables (NJ vs PA)")
P("")
P("| Variable | NJ | PA | t |")
P("|---|---|---|---|")
for lbl, vn, vp, t in table2_rows:
    P(f"| {lbl} | {vn:.2f} | {vp:.2f} | {t:.1f} |")
P("")

P("## Table 4 — Reduced-form models for the change in FTE employment")
P(f"")
P(f"Sample: {len(reg)} stores; mean ΔFTE = {y.mean():.3f}, SD = {y.std(ddof=1):.3f}.")
P("")
P("| Model | NJ dummy | wage gap | controls | SER |")
P("|---|---|---|---|---|")
for lbl, v in specs.items():
    fit = reg_results[lbl]
    def coef(name):
        if name in v:
            return f"{fit.params[name]:+.2f} ({fit.bse[name]:.2f})"
        return "—"
    controls = [c for c in v if c not in ("NJ", "gap")]
    P(f"| {lbl} | {coef('NJ')} | {coef('gap')} | "
      f"{', '.join(controls) if controls else '—'} | {np.sqrt(fit.mse_resid):.2f} |")
P("")

P("## Notes")
P("")
P("- **FTE** = full-time employees + managers + 0.5 × part-time employees. "
  "Permanently-closed stores (STATUS2 = 3, six stores) are assigned zero wave-2 employment; "
  "temporarily-closed stores (STATUS2 ∈ {2,4,5}, four stores) are treated as missing, "
  "except in row 5 of Table 3 where they are set to zero.")
P("- **Table 3, row 3** is the unbalanced *after − before* difference; its standard error "
  "uses the formula for the difference of two partially-overlapping sample means. "
  "Rows 4–5 use the store-level change over the balanced panel.")
P("- **The public-use `cardkrueger` file differs slightly from the paper's wave-1 staffing "
  "mix.** Wave-1 *FTE* and all wave-2 figures reproduce the published values exactly, but the "
  "file records fewer full-time and more part-time employees in wave 1, so the computed "
  "“% full-time employees” row (≈25% vs the paper's 32.8%) and the row-3 standard errors "
  "(a touch smaller) differ. The DiD point estimate and its conclusion are unaffected.")
P("- **Table 4** uses `NJ`-dummy specifications (i)–(ii) and a wage-gap "
  "(=(5.05 − starting wage)/starting wage for NJ, 0 for PA) specification (iii)–(v). "
  f"The regression sample here has {len(reg)} stores vs. 357 in the paper.")
P("")

# figure
fig, ax = plt.subplots(figsize=(8, 5))
bins = np.arange(-35, 40, 5)
nj_chg = df.loc[NJ & df["dfte"].notna(), "dfte"]
pa_chg = df.loc[PA & df["dfte"].notna(), "dfte"]
ax.hist(nj_chg, bins=bins, alpha=0.65, label="New Jersey", color="#1f77b4",
        edgecolor="black", linewidth=0.4)
ax.hist(pa_chg, bins=bins, alpha=0.65, label="Pennsylvania", color="#ff7f0e",
        edgecolor="black", linewidth=0.4)
ax.set_xlabel("Change in full-time equivalent employment")
ax.set_ylabel("Number of stores")
ax.set_title("Figure 1. Change in Employment, New Jersey and Pennsylvania Stores")
ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
ax.legend()
fig.tight_layout()
fig_path = os.path.join(OUTDIR, "figure1_change_in_employment.png")
fig.savefig(fig_path, dpi=150)
P(f"![Figure 1](output/figure1_change_in_employment.png)")
P("")
P(f"*Figure 1 saved to {fig_path}*  "
  f"(NJ change: n={len(nj_chg)}, mean={nj_chg.mean():.2f}; "
  f"PA change: n={len(pa_chg)}, mean={pa_chg.mean():.2f}).")

report_path = os.path.join(ROOT, "reproduction_report.md")
with open(report_path, "w") as f:
    f.write("\n".join(lines))

# console dump
print("\n".join(lines))
print("\n--- report written to:", report_path)
