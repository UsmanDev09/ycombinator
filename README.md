# JobSpy + Y Combinator Scraper

This API provides endpoints to scrape job listings using JobSpy and Y Combinator's Work at a Startup platform, and to retrieve previously scraped job data from a PostgreSQL database.

## Features

- Scrape job listings from multiple sources:
  - Indeed
  - LinkedIn
  - Google Jobs
  - Y Combinator (WorkAtAStartup.com)
- Save scraped jobs to CSV and/or PostgreSQL database
- Query and search saved jobs

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up a PostgreSQL database (if you want to store the scraped data)
4. Set environment variables (optional - defaults provided):
   ```
   # Database settings
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=scraper
   export DB_USER=postgres
   export DB_PASSWORD=1234
   
   # Y Combinator authentication
   export login_username=your_username
   export login_password=your_password
   
   # Server settings
   export PORT=5000
   ```
   
   Alternatively, create a `.env` file with these variables.

## Y Combinator Configuration

To scrape jobs from Y Combinator's Work at a Startup, you need to provide your login credentials. There are two ways to do this:

1. Set environment variables:
   ```
   export login_username=your_username
   export login_password=your_password
   ```
   
2. Create a `.env` file in your project root with:
   ```
   login_username=your_username
   login_password=your_password
   ```

## API Endpoints

### Scrape Jobs

**Endpoint:** `POST /scrape`

**Request Body:**
```json
{
  "site_names": ["indeed", "linkedin", "ycombinator"],
  "search_term": "React Developer",
  "google_search_term": "React Developer jobs near London",
  "location": "London, UK",
  "results_wanted": 100,
  "hours_old": 72,
  "country_indeed": "UK",
  "linkedin_fetch_description": false,
  "output_csv": "jobs.csv",
  "save_to_db": true,
  "company_name": "arist"
}
```

**Notes:**
- `site_names` can include any combination of: "indeed", "linkedin", "google", "ycombinator"
- If "ycombinator" is included in `site_names`, you must provide a `company_name`
- `search_term` and `location` are required if scraping from Indeed, LinkedIn, or Google
- `company_name` is required if scraping from Y Combinator

**Response:**
```json
{
  "status": "success",
  "jobs_found": 25,
  "jobs_data": [...],
  "csv_path": "jobs.csv",
  "db_result": "Imported 25 rows into database."
}
```

### Get Jobs from Database

**Endpoint:** `GET /jobs`

**Query Parameters:**
- `limit` (optional): Maximum number of results to return (default: 100)
- `offset` (optional): Offset for pagination (default: 0)
- `search` (optional): Search term to filter results (searches title, company, location)

**Response:**
```json
{
  "status": "success",
  "total": 250,
  "limit": 100,
  "offset": 0,
  "data": [...]
}
```

## Command Line Usage

The `example_client.py` script provides a command-line interface for using the API.

### Scraping Jobs

```bash
# Scrape jobs from Indeed and LinkedIn
python example_client.py --mode scrape --search-term "Software Engineer" --location "San Francisco" --country-indeed "usa"

# Scrape jobs from Y Combinator only
python example_client.py --mode scrape --site-names ycombinator --company-name "arist"

# Scrape jobs from all sources
python example_client.py --mode scrape --search-term "Software Engineer" --location "Remote" --site-names indeed linkedin ycombinator --company-name "cohere"
```

### Retrieving Jobs from Database

```bash
# Get all jobs (default limit: 10)
python example_client.py --mode get

# Search for specific jobs with pagination
python example_client.py --mode get --search "React" --limit 20 --offset 0
```

## Test Script

The `test_ycombinator.py` script provides examples of using the API to scrape Y Combinator jobs:

```bash
python test_ycombinator.py
```

## Running the API

```bash
python app.py
```

The API will start at http://localhost:5000 by default.

## Docker (Optional)

A Dockerfile is included for containerization:

```bash
docker build -t jobspy-api .
docker run -p 5000:5000 -e DB_HOST=host.docker.internal jobspy-api
```

# job-scraper
