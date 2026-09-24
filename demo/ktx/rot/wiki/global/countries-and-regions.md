---
summary: "Kelder ships to 5 countries in 3 regions: Benelux (NL, BE, LU), DACH (DE), Other EU (FR)"
usage_mode: auto
sort_order: 0
tags:
  - logistics
---

## Countries and Regions

### Countries
Kelder ships to five countries:
- **NL**: Netherlands
- **BE**: Belgium
- **LU**: Luxembourg
- **DE**: Germany
- **FR**: France

### Reporting regions
Countries are grouped into three reporting regions:
- **Benelux**: Netherlands, Belgium, Luxembourg
- **DACH**: Germany
- **Other EU**: France

### Carriers
- **PostNL**: Netherlands
- **DHL**: All other countries

### Where used
- `dim_customers.country_code` (ISO 3166-1 alpha-2)
- `dim_customers.country_name`
- `dim_customers.region`
- `fct_orders.carrier`
- `seeds/countries.csv` (reference data)

### Validation
Country codes are validated with dbt `accepted_values` test.

### Related
- PostNL strike May 2026 (affected Dutch orders only)
