"""
Claim Fraud Anomaly Detector - simple base project (pure Python, no libraries)

Idea: score each healthcare claim using
  1. Statistical outlier check (z-score of billed amount per procedure code)
  2. Business rules (duplicates, high-frequency provider, weekend/odd billing,
     service date after submission, round-number amounts)
Claims whose total risk score crosses a threshold are flagged for review.
"""

import statistics
from collections import defaultdict
from datetime import date

# ---------------------------------------------------------------
# 1. Sample claims (replace with parsed EDI 837 data / CSV / DB)
# ---------------------------------------------------------------
claims = [
    {"claim_id": "C1001", "provider": "P01", "patient": "A1", "cpt": "99213", "amount": 120.0, "service_date": date(2026, 10, 1), "submitted": date(2026, 10, 3)},
    {"claim_id": "C1002", "provider": "P01", "patient": "A2", "cpt": "99213", "amount": 115.0, "service_date": date(2026, 10, 2), "submitted": date(2026, 10, 4)},
    {"claim_id": "C1003", "provider": "P02", "patient": "A3", "cpt": "99213", "amount": 130.0, "service_date": date(2026, 10, 5), "submitted": date(2026, 10, 6)},
    {"claim_id": "C1004", "provider": "P02", "patient": "A4", "cpt": "99213", "amount": 125.0, "service_date": date(2026, 10, 6), "submitted": date(2026, 10, 8)},
    {"claim_id": "C1005", "provider": "P03", "patient": "A5", "cpt": "99213", "amount": 118.0, "service_date": date(2026, 10, 7), "submitted": date(2026, 10, 9)},
    {"claim_id": "C1006", "provider": "P03", "patient": "A6", "cpt": "99213", "amount": 122.0, "service_date": date(2026, 10, 8), "submitted": date(2026, 10, 10)},
    {"claim_id": "C1007", "provider": "P04", "patient": "A7", "cpt": "99213", "amount": 2500.0, "service_date": date(2026, 10, 10), "submitted": date(2026, 10, 11)},   # outlier amount
    {"claim_id": "C1008", "provider": "P01", "patient": "A1", "cpt": "99213", "amount": 120.0, "service_date": date(2026, 10, 1), "submitted": date(2026, 10, 5)},     # duplicate of C1001
    {"claim_id": "C1009", "provider": "P05", "patient": "A8", "cpt": "99213", "amount": 121.0, "service_date": date(2026, 11, 20), "submitted": date(2026, 10, 12)},  # future service date
]

# Add many claims from one provider to simulate high-frequency billing
for i in range(12):
    claims.append({
        "claim_id": f"C2{i:03d}", "provider": "P09", "patient": f"B{i}", "cpt": "99213",
        "amount": 119.0 + i, "service_date": date(2026, 10, 15), "submitted": date(2026, 10, 16),
    })

# ---------------------------------------------------------------
# 2. Configuration
# ---------------------------------------------------------------
Z_THRESHOLD = 2.0          # amount more than 2 std-devs from mean -> suspicious
DAILY_PROVIDER_LIMIT = 10  # claims per provider per service day
FLAG_SCORE = 40            # total score at/above which a claim is flagged

# ---------------------------------------------------------------
# 3. Detection logic
# ---------------------------------------------------------------
def build_stats(claims):
    """Mean and std-dev of billed amount per procedure code."""
    by_cpt = defaultdict(list)
    for c in claims:
        by_cpt[c["cpt"]].append(c["amount"])
    return {
        cpt: (statistics.mean(v), statistics.pstdev(v))
        for cpt, v in by_cpt.items()
    }


def score_claim(claim, stats, seen_keys, provider_day_counts):
    score, reasons = 0, []

    # Rule 1: statistical outlier (z-score)
    mean, std = stats[claim["cpt"]]
    if std > 0:
        z = (claim["amount"] - mean) / std
        if z > Z_THRESHOLD:
            score += 40
            reasons.append(f"Amount outlier (z={z:.1f})")

    # Rule 2: possible duplicate claim
    key = (claim["patient"], claim["provider"], claim["cpt"], claim["service_date"])
    if key in seen_keys:
        score += 50
        reasons.append(f"Duplicate of {seen_keys[key]}")
    else:
        seen_keys[key] = claim["claim_id"]

    # Rule 3: service date after submission date
    if claim["service_date"] > claim["submitted"]:
        score += 60
        reasons.append("Service date is after submission date")

    # Rule 4: provider billing too many claims in a day
    day_key = (claim["provider"], claim["service_date"])
    if provider_day_counts[day_key] > DAILY_PROVIDER_LIMIT:
        score += 30
        reasons.append("High daily claim volume for provider")

    # Rule 5: suspiciously round high amount
    if claim["amount"] >= 1000 and claim["amount"] % 100 == 0:
        score += 10
        reasons.append("Round-number high amount")

    return score, reasons


def detect(claims):
    stats = build_stats(claims)
    provider_day_counts = defaultdict(int)
    for c in claims:
        provider_day_counts[(c["provider"], c["service_date"])] += 1

    seen_keys = {}
    results = []
    for c in claims:
        score, reasons = score_claim(c, stats, seen_keys, provider_day_counts)
        results.append({**c, "score": score, "reasons": reasons, "flagged": score >= FLAG_SCORE})
    return results


# ---------------------------------------------------------------
# 4. Run and report
# ---------------------------------------------------------------
if __name__ == "__main__":
    results = detect(claims)
    flagged = [r for r in results if r["flagged"]]

    print(f"Total claims: {len(results)} | Flagged: {len(flagged)}\n")
    print(f"{'Claim':<8}{'Provider':<10}{'Amount':>10}{'Score':>7}  Reasons")
    print("-" * 70)
    for r in sorted(flagged, key=lambda x: -x["score"]):
        print(f"{r['claim_id']:<8}{r['provider']:<10}{r['amount']:>10.2f}{r['score']:>7}  {'; '.join(r['reasons'])}")
