import os
import re
import ast
import pandas as pd
from collections import defaultdict
from scipy.stats import zscore

# ======== PATHS ========
ROOT_DIR = r"."
INPUT_FOLDER = os.path.join(ROOT_DIR, "Results")
OUTPUT_DIR   = os.path.join(ROOT_DIR, "Results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======== NORMALIZATION ========
_na_collapse = re.compile(r'[\s/]+')

def normalize_na(text: str) -> bool:
    t = str(text).strip().lower()
    if "n/a" in t or "not applicable" in t:
        return True
    t2 = _na_collapse.sub('', t)
    return t2 == "na"

def simplify(ans: str) -> str:
    if ans is None or (isinstance(ans, float) and pd.isna(ans)):
        return "n/a"
    a = str(ans).strip().lower()
    if "partial" in a:
        return "yes"
    if normalize_na(a):
        return "n/a"
    if a.startswith("insecure permissions") or a.startswith("see answer"):
        return "no"
    if a.startswith("yes"):
        return "yes"
    if a.startswith("no"):
        return "no"
    return "n/a"

# ---- Naming helpers ----
def to_question_id(section: str) -> str:
    # "section_1.1" -> "Question_01.1"
    if not isinstance(section, str) or not section.startswith("section_"):
        return section
    rest = section[len("section_"):]  # e.g., "1.1" or "6"
    if "." in rest:
        sec, sub = rest.split(".", 1)
        try:
            return f"Question_{int(sec):02d}.{sub}"
        except ValueError:
            return f"Question_{rest}"
    else:
        try:
            return f"Question_{int(rest):02d}"
        except ValueError:
            return f"Question_{rest}"

def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0

# ======== LOAD & MERGE (exclude GPT-5 for base analysis) ========
frames = []
for fn in os.listdir(INPUT_FOLDER):
    if fn.lower().endswith(".csv"):
        if "gpt-5" in fn.lower():
            continue  # <-- exclude GPT-5 here
        df = pd.read_csv(os.path.join(INPUT_FOLDER, fn))
        if "model" not in df.columns:
            df["model"] = os.path.splitext(fn)[0]
        frames.append(df)

if not frames:
    raise RuntimeError("No CSV files (non-GPT-5) found in INPUT_FOLDER.")

combined = pd.concat(frames, ignore_index=True)
section_cols = [c for c in combined.columns if c.startswith("section_")]
if not section_cols:
    raise RuntimeError("No 'section_*' columns found in combined CSVs.")

# ======== PER FILE/SECTION AGREEMENT (normalized) ========
rows = []
for section in section_cols:
    for filename, g in combined.groupby("filename", dropna=True):
        sub = g[["model", section]].copy()
        if sub.empty:
            continue

        sub["raw"]    = sub[section].astype(str)
        sub["simple"] = sub["raw"].apply(simplify)

        label_counts = sub["simple"].value_counts().to_dict()
        yes_total = int(label_counts.get("yes", 0))
        no_total  = int(label_counts.get("no", 0))
        na_total  = int(label_counts.get("n/a", 0))

        counts = sub["simple"].value_counts()
        if counts.empty:
            continue
        majority_label = counts.idxmax()

        agree_mask = sub["simple"].eq(majority_label)
        agree_models    = sub.loc[agree_mask, "model"].tolist()
        disagree_models = sub.loc[~agree_mask, "model"].tolist()

        agree = int(agree_mask.sum())
        total = int(len(sub))
        disagree = total - agree
        agreement_pct = round(100.0 * agree / total, 1) if total else 0.0

        dis_counts = sub.loc[~agree_mask, "simple"].value_counts().to_dict()
        yes_disagree = int(dis_counts.get("yes", 0))
        no_disagree  = int(dis_counts.get("no", 0))
        na_disagree  = int(dis_counts.get("n/a", 0))

        yes_agree = agree if majority_label == "yes" else 0
        no_agree  = agree if majority_label == "no"  else 0
        na_agree  = agree if majority_label == "n/a" else 0

        maj_example = (
            sub.loc[agree_mask, "raw"].str.lower().value_counts().index[0]
            if agree > 0 else ""
        )

        # True if ANY label (yes/no/n/a) has EXACTLY 2 models
        check_exact2 = (yes_total == 2) or (no_total == 2) or (na_total == 2)

        rows.append({
            "filename": filename,
            "section": "all_questions",  # All questions are the same now
            "Question_id": "all_questions",
            "models_total": total,

            "majority_answer": majority_label,           # yes/no/n/a
            "majority_full_example": maj_example,

            "agree_models": agree_models,
            "disagree_models": disagree_models,
            "agree_count": agree,
            "disagree_count": disagree,
            "agreement_percentage": agreement_pct,

            "yes_count": yes_total,
            "no_count": no_total,
            "na_count": na_total,

            "yes_agree_count": yes_agree,
            "no_agree_count": no_agree,
            "na_agree_count": na_agree,
            "yes_disagree_count": yes_disagree,
            "no_disagree_count": no_disagree,
            "na_disagree_count": na_disagree,

            "CHECK_exact2_any": check_exact2
        })

result = pd.DataFrame(rows)

# ======== SAVE MAIN BREAKDOWN ========
out_main = os.path.join(OUTPUT_DIR, "models_in_agreement_and_disagreement_v6.csv")
result.to_csv(out_main, index=False)
print("✅ Saved:", out_main)

# ======== EXACTLY-2 AGREEMENT (any label) ========
exact2_rows = result[result["CHECK_exact2_any"] == True].copy()
exact2_path = os.path.join(OUTPUT_DIR, "cases_with_exact2_any.csv")
exact2_rows.to_csv(exact2_path, index=False)
print("✅ Saved cases with exactly 2 agreeing models (any label):", exact2_path)

# ======== SUBSETS ========
full_agree  = result[result["agree_count"] == result["models_total"]].copy()
partial_any = result[(result["agree_count"] >= 1) & (result["agree_count"] < result["models_total"])].copy()
partial_min3 = result[(result["agree_count"] >= 3) & (result["agree_count"] < result["models_total"])].copy()
exactly_2   = result[(result["yes_count"] == 2) | (result["no_count"] == 2) | (result["na_count"] == 2)].copy()

full_agree.to_csv(os.path.join(OUTPUT_DIR, "full_agreement.csv"), index=False)
partial_any.to_csv(os.path.join(OUTPUT_DIR, "partial_agreement_any.csv"), index=False)
partial_min3.to_csv(os.path.join(OUTPUT_DIR, "partial_agreement_min3.csv"), index=False)
exactly_2.to_csv(os.path.join(OUTPUT_DIR, "exactly_2_agree_any_label.csv"), index=False)
print("✅ Saved full/partial/exact-2 subsets.")

# ======== HOLD-OUT VALIDATION WITH GPT-5 (standalone) ========
# Rebuild with source filename so we can isolate GPT-5 rows
frames2 = []
for fn in os.listdir(INPUT_FOLDER):
    if fn.lower().endswith(".csv"):
        df = pd.read_csv(os.path.join(INPUT_FOLDER, fn))
        if "model" not in df.columns:
            df["model"] = os.path.splitext(fn)[0]
        df["_source_csv"] = fn
        frames2.append(df)

combined_all = pd.concat(frames2, ignore_index=True)
mask_gpt5 = combined_all["_source_csv"].str.contains("gpt-5", case=False, na=False)
gpt5_df   = combined_all[mask_gpt5].copy()

# Build GPT-5 lookup using the SAME simplify()
# Since all questions are the same, use the first section column for lookup
gpt5_section_cols = [c for c in gpt5_df.columns if c.startswith("section_")]
gpt5_lookup = {}
for fn, grp in gpt5_df.groupby("filename"):
    row = grp.iloc[0]  # one GPT-5 row per file
    # Since all questions are the same, use the first section column
    if gpt5_section_cols:
        val = row.get(gpt5_section_cols[0], None)
        gpt5_lookup[fn] = simplify(val) if pd.notna(val) else "n/a"
    else:
        gpt5_lookup[fn] = "n/a"

def gpt5_answer_for(row):
    # All questions are the same, so just look up by filename
    return gpt5_lookup.get(row["filename"], None)

result["gpt5_answer"] = result.apply(gpt5_answer_for, axis=1)

# --- Build base (4-model) counts as a dict for decision logic
def base_counts(row):
    return {
        "yes": int(row.get("yes_count", 0)),
        "no":  int(row.get("no_count", 0)),
        "n/a": int(row.get("na_count", 0)),
    }

result["_base_counts"] = result.apply(base_counts, axis=1)

# Flag strict 2-majority (50%)
result["flag_2_agree_majority"] = (result["agree_count"] == 2)

# Helper to know the “2” labels (could be one or two labels if tie)
def labels_with_count(counts, k):
    return [lab for lab, c in counts.items() if c == k]

# New triage that follows your rules
def triage(row):
    gpt5 = row["gpt5_answer"]
    counts = row["_base_counts"]
    c_yes, c_no, c_na = counts["yes"], counts["no"], counts["n/a"]
    sorted_counts = sorted(counts.values())  # e.g., [1,1,2], [0,2,2], etc.

    # Only act when it's a 2-agree situation or a 2-2-0 tie
    is_211 = (sorted_counts == [1, 1, 2])
    is_220 = (sorted_counts == [0, 2, 2])

    if not (row["flag_2_agree_majority"] or is_220):
        return "not_flagged"

    # If GPT-5 missing, manual review
    if pd.isna(gpt5) or gpt5 is None:
        return "manual_check"

    # Case A: 2-1-1 (one clear 2, two 1s)
    if is_211:
        # label(s) that have count==2 (single label expected)
        majority_twos = labels_with_count(counts, 2)  # should be length 1
        maj2 = majority_twos[0] if majority_twos else None
        # If GPT-5 agrees with the "2" label => becomes 3-1-1 (fully agreed)
        return "true_positive" if gpt5 == maj2 else "manual_check"

    # Case B: 2-2-0 (tie between two labels)
    if is_220:
        # If GPT-5 picks one of the tied labels => becomes 3-2-0 (accept as true_positive)
        tie_labels = labels_with_count(counts, 2)  # length 2
        return "true_positive" if gpt5 in tie_labels else "manual_check"

    # Any other shape that still had agree_count==2 -> default to conservative rule you had
    return "true_positive" if (gpt5 == row["majority_answer"]) else "manual_check"

result["audit_verdict"] = result.apply(triage, axis=1)
result["manual_check"] = result["audit_verdict"].eq("manual_check")

# (Optional) store post-GPT-5 counts for traceability
def post_counts(row):
    counts = row["_base_counts"].copy()
    g = row["gpt5_answer"]
    if isinstance(g, str) and g in counts:
        counts[g] += 1
    return counts

post = result.apply(post_counts, axis=1)
result["post_yes"] = post.apply(lambda d: d["yes"])
result["post_no"]  = post.apply(lambda d: d["no"])
result["post_na"]  = post.apply(lambda d: d["n/a"])

# Save augmented main file & a focused audit list
out_aug = os.path.join(OUTPUT_DIR, "models_in_agreement_and_disagreement_v6_with_gpt5.csv")
result.to_csv(out_aug, index=False)

audit_focus = result[result["audit_verdict"].isin(["true_positive", "manual_check"])].copy()
audit_path  = os.path.join(OUTPUT_DIR, "audit_triage_gpt5_on_2agree.csv")
audit_focus.to_csv(audit_path, index=False)

print("✅ GPT-5 validation added with manual-analysis rules:")
print(" - Augmented main:", out_aug)
print(" - Audit triage:",  audit_path)
print("   (true_positive = GPT-5 picks the 2-label in 2-1-1, or one of the tied labels in 2-2-0; otherwise manual_check)")

# ======== OVERALL STATS (all questions are the same now) ========
# No grouping needed - calculate overall stats for all data
block_stats = pd.DataFrame({
    "items": [len(result)],
    "files": [result["filename"].nunique()],

    "agree_4_items": [(result["agree_count"] == 4).sum()],
    "agree_3_items": [(result["agree_count"] == 3).sum()],
    "agree_2_items": [(result["agree_count"] == 2).sum()],

    "agree_3_or_4_items": [((result["agree_count"] == 3) | (result["agree_count"] == 4)).sum()],
    "agree_only_2_items": [(result["agree_count"] == 2).sum()],

    "avg_agreement_pct": [result["agreement_percentage"].mean().round(1)],
    "majority_yes": [(result["majority_answer"] == "yes").sum()],
    "majority_no":  [(result["majority_answer"] == "no").sum()],
    "majority_na":  [(result["majority_answer"] == "n/a").sum()],
})

block_stats["pct_agree_4"]       = block_stats.apply(lambda r: pct(r["agree_4_items"],       r["items"]), axis=1)
block_stats["pct_agree_3"]       = block_stats.apply(lambda r: pct(r["agree_3_items"],       r["items"]), axis=1)
block_stats["pct_agree_2"]       = block_stats.apply(lambda r: pct(r["agree_2_items"],       r["items"]), axis=1)
block_stats["pct_agree_3_or_4"]  = block_stats.apply(lambda r: pct(r["agree_3_or_4_items"],  r["items"]), axis=1)
block_stats["pct_agree_only_2"]  = block_stats.apply(lambda r: pct(r["agree_only_2_items"],  r["items"]), axis=1)

block_stats_path = os.path.join(OUTPUT_DIR, "stats_agree_3_4_and_only2.csv")
block_stats.to_csv(block_stats_path, index=False)
print("✅ Saved overall stats (3&4 and only 2):", block_stats_path)

# ======== PER-MODEL AGREEMENT/DISAGREEMENT (normalized fairness) ========
def parse_list(x):
    if isinstance(x, list):
        return x
    if pd.isna(x):
        return []
    try:
        return ast.literal_eval(x)
    except Exception:
        return []

per_model = defaultdict(lambda: {
    "cases_total": 0,
    "full_agree_cases": 0,
    "partial_agree_cases": 0,  # ANY partial (1..total-1)
    "disagree_cases": 0
})

for _, row in result.iterrows():
    agree_models    = parse_list(row.get("agree_models", []))
    disagree_models = parse_list(row.get("disagree_models", []))
    agree_count     = int(row.get("agree_count", 0))
    models_total    = int(row.get("models_total", len(agree_models) + len(disagree_models)))

    is_full    = (agree_count == models_total)
    is_partial = (agree_count >= 1 and agree_count < models_total)

    for m in agree_models:
        per_model[m]["cases_total"] += 1
        if is_full:
            per_model[m]["full_agree_cases"] += 1
        elif is_partial:
            per_model[m]["partial_agree_cases"] += 1

    for m in disagree_models:
        per_model[m]["cases_total"] += 1
        per_model[m]["disagree_cases"] += 1

model_rows = []
for m, s in per_model.items():
    total = s["cases_total"] if s["cases_total"] else 1
    overall_agree = s["full_agree_cases"] + s["partial_agree_cases"]
    model_rows.append({
        "model": m,
        "cases_total": s["cases_total"],
        "full_agree_cases": s["full_agree_cases"],
        "partial_agree_cases": s["partial_agree_cases"],
        "disagree_cases": s["disagree_cases"],
        "full_agree_rate": round(100.0 * s["full_agree_cases"] / total, 1),
        "partial_agree_rate": round(100.0 * s["partial_agree_cases"] / total, 1),
        "overall_agreement_rate": round(100.0 * overall_agree / total, 1),
        "disagree_rate": round(100.0 * s["disagree_cases"] / total, 1),
    })

model_scores = pd.DataFrame(model_rows)

# z-score normalization for fairness & composite ranking
if not model_scores.empty:
    for col in ["full_agree_rate", "partial_agree_rate", "overall_agreement_rate", "disagree_rate"]:
        model_scores[f"{col}_z"] = zscore(model_scores[col]) if model_scores[col].std(ddof=0) != 0 else 0.0

    model_scores["composite_score"] = (
        0.6 * model_scores["full_agree_rate_z"] +
        0.3 * model_scores["partial_agree_rate_z"] -
        0.1 * model_scores["disagree_rate_z"]
    )

    model_scores = model_scores.sort_values(by=["composite_score", "overall_agreement_rate"], ascending=[False, False]).reset_index(drop=True)

model_scores_path = os.path.join(OUTPUT_DIR, "model_agreement_scores_normalized.csv")
model_scores.to_csv(model_scores_path, index=False)
print("✅ Saved normalized per-model agreement scores:", model_scores_path)

print("\n🔎 Sanity checks:")
print(" - models_in_agreement_and_disagreement_v6.csv:", out_main)
print(" - cases_with_exact2_any.csv:", exact2_path)
print(" - stats_agree_3_4_and_only2.csv:", block_stats_path)
print(" - model_agreement_scores_normalized.csv:", model_scores_path)

