# Smart-Grid Executive Summary

Generated: 2026-11-13 07:14:40

## Consumption overview

| Metric | Value |
| --- | ---: |
| Households | 10 |
| Meter readings | 60 |
| Total consumption | 19,628.00 kWh |
| Mean consumption | 327.13 kWh |
| Median consumption | 212.50 kWh |
| Average rate | ₱12.17/kWh |
| Total billed | ₱247,598.60 |
| IQR anomaly threshold | 1,174.38 kWh |
| Flagged readings | 0 |

## Anomaly review

No readings exceed the current IQR threshold.

## Consumer segments

| Account | Homeowner | Segment | Average usage | Average cost |
| --- | --- | --- | ---: | ---: |
| ACC-8001 | Maria Santos | Cluster 0: Eco-Consumers (Low Load) | 228.3 kWh | ₱2,684.96 |
| ACC-8002 | Juan Dela Cruz | Cluster 0: Eco-Consumers (Low Load) | 238.3 kWh | ₱2,801.83 |
| ACC-8003 | Roberto Gomez | Cluster 0: Eco-Consumers (Low Load) | 124.2 kWh | ₱1,460.50 |
| ACC-8004 | Elena Reyes | Cluster 2: Heavy / Peak Load | 716.7 kWh | ₱9,416.42 |
| ACC-8005 | Carlos Aquino | Cluster 0: Eco-Consumers (Low Load) | 195.8 kWh | ₱2,302.83 |
| ACC-8006 | Ana Marie Ramos | Cluster 0: Eco-Consumers (Low Load) | 187.5 kWh | ₱2,205.92 |
| ACC-8007 | Ruel Pascual | Cluster 0: Eco-Consumers (Low Load) | 158.3 kWh | ₱1,862.58 |
| ACC-8008 | Greenfield Store | Cluster 1: Moderate Residential | 566.7 kWh | ₱7,441.58 |
| ACC-8009 | Loida Villanueva | Cluster 0: Eco-Consumers (Low Load) | 105.5 kWh | ₱1,241.48 |
| ACC-8010 | Echague Mini-Mart | Cluster 2: Heavy / Peak Load | 750.0 kWh | ₱9,848.33 |

## Statistical analysis

- Residential mean: 176.86 kWh.
- Commercial mean: 677.78 kWh.
- Welch t-test p-value: 2.9144e-15.
- Significant at 0.05: yes.

### Demand forecast

- Last period: 2026-09.
- Projected next-period load: 3,585.33 kWh.
- Trend: Increasing.

## Disaster and outage incidents

| Date | Barangay | Incident | Severity |
| --- | --- | --- | --- |
| 2026-08-10 | Cabaruan, Santiago City | Severe Thunderstorm Outage | High |
| 2026-07-22 | Malitao, Echague | Transformer Overload | Medium |
| 2026-06-18 | San Fabian, Echague | Feeder Line Lightning Strike | High |
| 2026-06-02 | San Antonio, Echague | Downed Power Line | High |
| 2026-05-04 | Echague Proper, Echague | Localized Flooding | Medium |
| 2026-04-15 | Baluarte, Santiago City | Typhoon Ramil Wind Gusts | High |

## Recent audit activity

| Timestamp | Action | Target | Details |
| --- | --- | --- | --- |
| 2026-11-12 15:10:03 | ADMIN_LOGIN | admin | Administrator signed in |
| 2026-11-12 14:53:34 | SYSTEM_INIT | SYSTEM | Database seeded with 10 unclaimed households, 60 readings, 6 disasters. |
