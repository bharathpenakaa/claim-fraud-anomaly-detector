# Claim Fraud Anomaly Detector

Simple base project (AI in Healthcare, Claims, EDI). Pure Python, no dependencies.

## Run
    python3 claim_fraud_anomaly_detector.py

## Checks and scores
- Amount outlier (z-score > 2 per procedure code): +40
- Duplicate claim (patient, provider, CPT, service date): +50
- Service date after submission date: +60
- Provider daily claim volume above 10: +30
- Round-number high amount (>= 1000): +10

Claims with a total score >= 40 are flagged. Tune Z_THRESHOLD, DAILY_PROVIDER_LIMIT and FLAG_SCORE in the code.
