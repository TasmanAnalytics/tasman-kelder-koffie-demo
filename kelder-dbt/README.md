# Kelder analytics

dbt project for Kelder Coffee's warehouse. Shopify, Recharge, Klaviyo and the ad platforms land
in the warehouse through Fivetran (`raw_*` schemas). This project turns them into staging views,
intermediate tables and the marts in `main`.

## Layout

- `models/staging/<source>/`: one model per raw table. Renames, types, JSON parsing, channel grouping.
- `models/intermediate/`: subscriptions unified across Shopify and Recharge, billing, the event stream.
- `models/marts/`: facts, dimensions and the governed `metrics_*` models. Report numbers from these.
- `seeds/`: small reference tables.
- `tests/`: singular tests. Generic tests live next to the models in YAML.

## Running

```
export KELDER_DUCKDB_PATH=/path/to/warehouse.duckdb
export DBT_PROFILES_DIR=.
dbt build
```

All timestamps in the warehouse are UTC. Reporting uses Amsterdam time: months start at 00:00
Europe/Amsterdam. The reporting date is the `as_of_date` variable in `dbt_project.yml`.

## Conventions

- Subscription key: `shp-<Shopify contract id>` or `rch-<Recharge subscription id>`. A subscription
  keeps one key for its whole life.
- Money is EUR, including VAT.
- Gift subscriptions are prepaid and sit outside subscriber metrics.
