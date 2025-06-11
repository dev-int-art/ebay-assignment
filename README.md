# Listings API

![Py](https://img.shields.io/badge/Python%3A%203.13-blue)

A FastAPI-based application that provides endpoints to upsert and read listings with flexible filtering capabilities.

## Features

- **Upsert Listings**: Create or update multiple listings with properties and entities
- **Read Listings**: Retrieve listings with advanced filtering options
- **Database Setup**: PostgreSQL with SQLModel ORM
- **API Documentation**: Auto-generated OpenAPI documentation

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. **Clone this project**
   ```bash
   git clone https://github.com/dev-int-art/listings-api.git
   cd listings-api
   ```

2. **Start the application**
   ```bash
   docker compose up
   ```

3. **Access the API**
   - Interactive API documentation: `http://localhost:8000/docs`
   - The Listings API will be available at `http://localhost:8000/listings`
   - You can setup a [Bruno](https://www.usebruno.com/) collection from the bruno files in the repo
   - Alternatively you can run:
      ```
      curl --request PUT \
      --url http://0.0.0.0:8000/listings \
      --header 'content-type: application/json' \
      --data '{
      "listings": [
         {
            "listing_id": "1111224",
            "scan_date": "2025-01-05 15:30:50",
            "is_active": true,
            "image_hashes": [
            "4e32d4",
            "a54t459"
            ],
            "properties": [
            {
               "name": "Unit of Measure",
               "type": "str",
               "value": "Kg"
            },
            {
               "name": "Has Delivery",
               "type": "bool",
               "value": "false"
            }
            ],
            "entities": [
            {
               "name": "Quality Checks", 
               "data": {"pc10": 0.23, "pc5": 0.45}
            }
            ]
         }
      ]
      }'
      ```

> [!NOTE]
> There's no seed data. You might want to run the Upsert API first

## API Documentation

To access the API specs and schemas, go to `/docs` in your browser after starting the application.

## Testing

Run the test suite using:

```bash
docker compose run --rm -it api pytest
```

## Project Structure

```
app/
├── api/
│   └── listings.py          # Main API endpoints
|   └── utils.py             # Utility functions
├── models.py                # SQLModel database models
├── schemas/
│   ├── request.py           # Request schemas
│   └── response.py          # Response schemas
├── database.py              # Database configuration
└── main.py                  # FastAPI application
├── tests/
|   └── conftest.py               # Test configuration
|   └── test_listings_integration.py  # Integration tests
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string for production
- `TEST_DATABASE_URL`: PostgreSQL connection string for testing

## Development

The application uses:
- **FastAPI**: Modern web framework for APIs
- **SQLModel**: SQL databases in Python, designed for FastAPI
- **PostgreSQL**: Database with JSONB support
- **Pytest**: Testing framework

<hr>

## Considerations and Trade Offs

- Using Postgres instead of SQLite due to native support for complex columns.
- `upsert_listings` is atomic. A different endpoint or an additonal param could give us partial failure support too.

## Doubts

- Unsure which fields are mandatory/cannot be empty and hence are needed via the request for the upsert

## For Another Life

- Request level session management, destroy at request end
- Middleware to map more specific errors to error codes
- A Better test setup with classes and class level setups and teardowns