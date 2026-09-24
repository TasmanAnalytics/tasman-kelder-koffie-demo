---
summary: Kelder ships to five countries (NL, BE, DE, LU, FR) grouped into three reporting regions
usage_mode: auto
sort_order: 0
tags:
  - logistics
  - geography
sl_refs:
  - dim_customers
  - fct_orders
---

## Shipping Countries and Regions

### Countries
Kelder ships to five countries:
- **NL**: Netherlands
- **BE**: Belgium
- **DE**: Germany
- **LU**: Luxembourg
- **FR**: France

### Reporting Regions
Countries are grouped into three reporting regions in `dim_customers.region`:
- **Benelux**: Netherlands, Belgium, Luxembourg
- **DACH**: Germany (Deutschland, Austria, Switzerland - but Kelder only ships to DE)
- **Other EU**: France

### Carriers
- **PostNL**: Netherlands
- **DHL**: All other countries (BE, DE, LU, FR)

### Data Sources
- `dim_customers.country_code`: ISO 3166-1 alpha-2 code
- `dim_customers.country_name`: Country name
- `dim_customers.region`: Reporting region
- `fct_orders.carrier`: PostNL or DHL
- `seeds/countries.csv`: Reference data for countries, regions, and carriers

### Source
See `stg_shopify__customers` and the `countries` seed for the country and region logic.
