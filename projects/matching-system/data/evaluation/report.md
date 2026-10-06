# Matching Quality Evaluation Report

Generated: 2026-07-01

## All Results

| Split | Mode | Query Type | N | P@1 | P@3 | R@1 | R@3 | nDCG@3 | Top1Hit |
|------|------|-----------|---|-----|-----|-----|-----|-------|---------|
| calibration | hybrid | job-to-resumes | 10 | 0.300 | 0.267 | 0.250 | 0.700 | 0.617 | 0.300 |
| calibration | hybrid | resume-to-jobs | 10 | 0.500 | 0.300 | 0.450 | 0.800 | 0.755 | 0.500 |
| calibration | hybrid_degraded | job-to-resumes | 10 | 0.300 | 0.233 | 0.250 | 0.600 | 0.567 | 0.300 |
| calibration | hybrid_degraded | resume-to-jobs | 10 | 0.500 | 0.300 | 0.450 | 0.800 | 0.747 | 0.500 |
| calibration | keyword | job-to-resumes | 10 | 0.200 | 0.100 | 0.150 | 0.250 | 0.258 | 0.200 |
| calibration | keyword | resume-to-jobs | 10 | 0.200 | 0.267 | 0.150 | 0.750 | 0.498 | 0.200 |
| test | hybrid | job-to-resumes | 5 | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 1.000 |
| test | hybrid | resume-to-jobs | 5 | 0.800 | 0.333 | 0.700 | 0.800 | 0.855 | 0.800 |
| test | hybrid_degraded | job-to-resumes | 5 | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 1.000 |
| test | hybrid_degraded | resume-to-jobs | 5 | 0.800 | 0.333 | 0.700 | 0.800 | 0.855 | 0.800 |
| test | keyword | job-to-resumes | 5 | 0.200 | 0.200 | 0.200 | 0.600 | 0.497 | 0.200 |
| test | keyword | resume-to-jobs | 5 | 0.400 | 0.267 | 0.400 | 0.700 | 0.617 | 0.400 |

## Requirement Check: Hybrid >= Keyword

| Split | Query Type | Metric | Keyword | Hybrid | Diff | Result |
|------|-----------|-------|-------|-------|------|--------|
| calibration | resume-to-jobs | precision@1 | 0.200 | 0.500 | +0.300 | ✓ |
| calibration | resume-to-jobs | recall@1 | 0.150 | 0.450 | +0.300 | ✓ |
| calibration | resume-to-jobs | ndcg@3 | 0.498 | 0.755 | +0.258 | ✓ |
| calibration | job-to-resumes | precision@1 | 0.200 | 0.300 | +0.100 | ✓ |
| calibration | job-to-resumes | recall@1 | 0.150 | 0.250 | +0.100 | ✓ |
| calibration | job-to-resumes | ndcg@3 | 0.258 | 0.617 | +0.359 | ✓ |
| test | resume-to-jobs | precision@1 | 0.400 | 0.800 | +0.400 | ✓ |
| test | resume-to-jobs | recall@1 | 0.400 | 0.700 | +0.300 | ✓ |
| test | resume-to-jobs | ndcg@3 | 0.617 | 0.855 | +0.238 | ✓ |
| test | job-to-resumes | precision@1 | 0.200 | 1.000 | +0.800 | ✓ |
| test | job-to-resumes | recall@1 | 0.200 | 1.000 | +0.800 | ✓ |
| test | job-to-resumes | ndcg@3 | 0.497 | 1.000 | +0.503 | ✓ |