import pandas as pd
import ast
from itertools import combinations
from statsmodels.stats.inter_rater import fleiss_kappa
from statsmodels.stats.contingency_tables import mcnemar
import os

ROOT_DIR = r"."
INPUT_FOLDER = os.path.join(ROOT_DIR, "Results")
OUTPUT_DIR   = os.path.join(ROOT_DIR, "Results")
# Load CSV
df = pd.read_csv(os.path.join(INPUT_FOLDER, "combined_results.csv"))

# Convert string lists to Python lists
def parse_list(value):
    try:
        if pd.isna(value):
            return []
        return ast.literal_eval(value)
    except:
        return []

df["agree_list"] = df["agree_models"].apply(parse_list)
df["disagree_list"] = df["disagree_models"].apply(parse_list)

# Extract unique models
all_models = set()
for lst in df["agree_list"]:
    all_models.update(lst)
for lst in df["disagree_list"]:
    all_models.update(lst)
all_models = sorted(list(all_models))

# ----------------------------------------------------------
# 1. Model performance
# ----------------------------------------------------------
model_stats = {m: {"agree":0, "total":0} for m in all_models}

for _, r in df.iterrows():
    for m in r["agree_list"]:
        model_stats[m]["agree"] += 1
        model_stats[m]["total"] += 1
    for m in r["disagree_list"]:
        model_stats[m]["total"] += 1

print("====== Model Performance ======\n")
print(f"{'Model':20} {'Agree':>5} {'Total':>5} {'Agreement Rate':>15}")
for m in all_models:
    agree = model_stats[m]["agree"]
    total = model_stats[m]["total"]
    rate = agree / total if total > 0 else 0
    print(f"{m:20} {agree:5} {total:5} {rate:15.3f}")

best_model = max(all_models, key=lambda m: model_stats[m]["agree"]/model_stats[m]["total"])
best_rate = model_stats[best_model]["agree"]/model_stats[best_model]["total"]
print(f"\nBest Performing Model: {best_model} (Agreement Rate: {best_rate:.3f})")

# ----------------------------------------------------------
# 2. Pairwise Agreement + McNemar
# ----------------------------------------------------------
qa_matrix = {}
for _, r in df.iterrows():
    qid = r["Question_id"]
    qa_matrix[qid] = {}
    for m in r["agree_list"]:
        qa_matrix[qid][m] = 1
    for m in r["disagree_list"]:
        qa_matrix[qid][m] = 0

def pairwise_agreement(model_a, model_b):
    shared = 0
    agree = 0
    for qid, answers in qa_matrix.items():
        if model_a in answers and model_b in answers:
            shared += 1
            if answers[model_a] == answers[model_b]:
                agree += 1
    return agree / shared if shared > 0 else None

print("\n====== Pairwise Agreement ======")
for a, b in combinations(all_models, 2):
    val = pairwise_agreement(a, b)
    if val is not None:
        print(f"{a:20} vs {b:20}: {val:.3f}")

# McNemar test
print("\n====== McNemar Tests ======")
for a, b in combinations(all_models, 2):
    # Build 2x2 contingency table
    a_b = 0  # model_a=1, model_b=0
    b_a = 0  # model_a=0, model_b=1
    for qid, answers in qa_matrix.items():
        if a in answers and b in answers:
            if answers[a] == 1 and answers[b] == 0:
                a_b += 1
            elif answers[a] == 0 and answers[b] == 1:
                b_a += 1
    # Only discordant pairs matter
    table = [[0, a_b],
             [b_a, 0]]
    if (a_b + b_a) > 0:
        result = mcnemar(table, exact=True)
        print(f"{a:20} vs {b:20}: McNemar p-value = {result.pvalue:.4f}")
    else:
        print(f"{a:20} vs {b:20}: No discordant pairs, cannot compute McNemar")

        
# ----------------------------------------------------------
# 3. Fleiss' Kappa
# ----------------------------------------------------------
vote_matrix = df[["yes_count", "no_count", "na_count"]].to_numpy()
kappa_value = fleiss_kappa(vote_matrix)
print(f"\nFleiss’ Kappa: {kappa_value:.3f}")
