## Ebay Lite

A tiny fastapi app that manages listings


## Considerations and Trade Offs

- Using Postgres instead of SQLite due to native support for complex columns
- Using ENUM to represent `Property.type` instead of storing it in another table in case of scope creep
- `upsert_listings` is atomic. A different endpoint or an additonal param could give us partial failure support too.

## Doubts

- Table names: Why are they `test_*` ? I would have gone for `PropertyType`/`property_type`
- Unsure which fields are mandatory/cannot be empty and hence are needed via the request
