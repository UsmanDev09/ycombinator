from flask import Flask, request, jsonify
import pandas as pd
from jobspy import scrape_jobs
import os
import psycopg2
from psycopg2 import sql
import csv
from flask_cors import CORS
from dotenv import load_dotenv
from ycombinator_scraper import Scraper

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "scraper")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")

TABLE_NAME = "scraped_jobs"
COLUMNS = [
    ("job_id", "TEXT"),
    ("site", "TEXT"),
    ("job_url", "TEXT"),
    ("job_url_direct", "TEXT"),
    ("title", "TEXT"),
    ("company", "TEXT"),
    ("location", "TEXT"),
    ("date_posted", "TIMESTAMP"),
    ("job_type", "TEXT"),
    ("salary_source", "TEXT"),
    ("interval", "TEXT"),
    ("min_amount", "NUMERIC"),
    ("max_amount", "NUMERIC"),
    ("currency", "TEXT"),
    ("is_remote", "BOOLEAN"),
    ("job_level", "TEXT"),
    ("job_function", "TEXT"),
    ("listing_type", "TEXT"),
    ("emails", "TEXT"),
    ("description", "TEXT"),
    ("company_industry", "TEXT"),
    ("company_url", "TEXT"),
    ("company_logo", "TEXT"),
    ("company_url_direct", "TEXT"),
    ("company_addresses", "TEXT"),
    ("company_num_employees", "TEXT"),
    ("company_revenue", "TEXT"),
    ("company_description", "TEXT"),
    ("skills", "TEXT"),
    ("experience_range", "TEXT"),
    ("company_rating", "NUMERIC"),
    ("company_reviews_count", "INTEGER"),
    ("vacancy_count", "INTEGER"),
    ("work_from_home_type", "TEXT"),
]

# Function to scrape YCombinator jobs
def scrape_ycombinator_jobs(company_name=None):
    scraper = Scraper()
    
    # Login to YCombinator
    # scraper.login()
    
    # Build the URL
    base_url = "https://www.workatastartup.com/companies"
    if company_name:
        company_url = f"{base_url}/{company_name.lower()}"
    else:
        company_url = base_url
    
    # Scrape company data
    company_data = scraper.scrape_company_data(company_url=company_url)
    
    # Format jobs to match JobSpy structure
    jobs_list = []
    
    for job in company_data.job_data:
        # Parse salary range if available
        min_amount = None
        max_amount = None
        currency = None
        interval = None
        
        if job.job_salary_range:
            # Extract currency, min and max amount from salary range
            # Example: "$200K - $240K    0.05% - 0.20%"
            salary_parts = job.job_salary_range.split('-')
            if len(salary_parts) >= 2:
                min_salary = salary_parts[0].strip()
                max_salary = salary_parts[1].strip().split(' ')[0].strip()
                
                # Extract currency
                currency = None
                if min_salary:
                    # Handle common currency symbols
                    if min_salary[0] in ['$', '€', '£', '₹', '¥', '₽', '₺', '₴', '₦', '₩', '₫', '₱', 'R', '฿', 'د.إ', '৳', '₪', 'RM', 'CHF', 'A$', 'C$', 'HK$', 'S$']:
                        currency = min_salary[0]
                    # Handle currency codes at the start
                    elif len(min_salary) >= 3 and ' ' in min_salary:
                        currency_code = min_salary.split(' ')[0]
                        if currency_code in ['USD', 'EUR', 'GBP', 'INR', 'JPY', 'CNY', 'RUB', 'TRY', 'UAH', 'NGN', 'KRW', 'VND', 'PHP', 'ZAR', 'THB', 'AED', 'BDT', 'ILS', 'MYR', 'BRL', 'MXN', 'SGD', 'AUD', 'CAD', 'NZD']:
                            currency = currency_code
                if min_salary:
                    # Clean up currency symbols and codes
                    min_amount_str = min_salary
                    if currency:
                        if len(currency) == 1:
                            min_amount_str = min_amount_str.replace(currency, '', 1).strip()
                        else:
                            # For currency codes (e.g., USD, EUR)
                            min_amount_str = min_amount_str.replace(currency + ' ', '', 1).strip()
                    
                    try:
                        if 'K' in min_amount_str:
                            min_amount = float(min_amount_str.replace('K', '').strip()) * 1000
                        elif 'M' in min_amount_str:
                            min_amount = float(min_amount_str.replace('M', '').strip()) * 1000000
                        else:
                            # Remove any remaining non-numeric characters except decimal point
                            min_amount_str = ''.join(c for c in min_amount_str if c.isdigit() or c == '.')
                            if min_amount_str:
                                min_amount = float(min_amount_str)
                            else:
                                min_amount = None
                    except ValueError:
                        print(f"Could not convert salary to float: {min_amount_str}")
                        min_amount = None
                
                # Extract max amount (remove currency symbol and K/M)
                if max_salary:
                    # Clean up currency symbols and codes
                    max_amount_str = max_salary
                    if currency:
                        if len(currency) == 1:
                            max_amount_str = max_amount_str.replace(currency, '', 1).strip()
                        else:
                            # For currency codes (e.g., USD, EUR)
                            max_amount_str = max_amount_str.replace(currency + ' ', '', 1).strip()
                    
                    try:
                        if 'K' in max_amount_str:
                            max_amount = float(max_amount_str.replace('K', '').strip()) * 1000
                        elif 'M' in max_amount_str:
                            max_amount = float(max_amount_str.replace('M', '').strip()) * 1000000
                        else:
                            # Remove any remaining non-numeric characters except decimal point
                            max_amount_str = ''.join(c for c in max_amount_str if c.isdigit() or c == '.')
                            if max_amount_str:
                                max_amount = float(max_amount_str)
                            else:
                                max_amount = None
                    except ValueError:
                        print(f"Could not convert salary to float: {max_amount_str}")
                        max_amount = None
                
                # Assume yearly salary if not specified
                interval = "yearly"
        
        # Determine location and job type from tags
        location = None
        job_type = None
        is_remote = False
        experience_range = None
        
        if job.job_tags and len(job.job_tags) > 0:
            for tag_list in job.job_tags:
                for tag in tag_list:
                    if 'Remote' in tag:
                        is_remote = True
                        # Don't set location to "Remote" - we'll use the actual location
                    elif any(type_word in tag for type_word in ['Full-time', 'Part-time', 'Internship', 'Contract']):
                        job_type = tag.strip()
                    elif any(year in tag for year in ['years', 'year', '+', 'yr']):
                        experience_range = tag.strip()
                    elif location is None:  # If we haven't set location yet
                        location = tag.strip()
        
        # Extract company information from tags
        company_industry = None
        company_size = None
        company_location = None
        
        if company_data.company_tags:
            for tag in company_data.company_tags:
                if 'people' in tag:
                    company_size = tag.strip()
                elif any(loc in tag for loc in ['New York', 'San Francisco', 'Remote', 'London', 'Boston']):
                    company_location = tag.strip()
                else:
                    company_industry = tag.strip()
        
        # Create job entry
        job_entry = {
            "job_id": job.job_url.split('/')[-1],
            "site": "ycombinator",
            "job_url": job.job_url,
            "job_url_direct": job.job_url,
            "title": job.job_title,
            "company": company_data.company_name,
            "location": location if location else company_location,  # Use job location or company location
            "date_posted": None,  # YCombinator doesn't provide exact date
            "job_type": job_type,
            "salary_source": "ycombinator",
            "interval": interval,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "currency": currency,
            "is_remote": is_remote,
            "job_level": None,
            "job_function": None,
            "listing_type": None,
            "emails": None,
            "description": job.job_description,
            "company_industry": company_industry,
            "company_url": next((link for link in company_data.company_social_links 
                               if 'https://' in link and 'twitter' not in link and 'facebook' not in link), None),
            "company_logo": company_data.company_image,
            "company_url_direct": company_data.company_url,
            "company_addresses": company_location,  # Use company location for addresses
            "company_num_employees": company_size,
            "company_revenue": None,
            "company_description": company_data.company_description,
            "skills": None,
            "experience_range": experience_range,
            "company_rating": None,
            "company_reviews_count": None,
            "vacancy_count": len(company_data.job_data),
            "work_from_home_type": "remote" if is_remote else None,
        }
        
        jobs_list.append(job_entry)
    
    return jobs_list

# Function to connect to the database
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# Function to create the table if it doesn't exist
def create_table_if_not_exists():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create columns string for CREATE TABLE
    columns_str = ', '.join([f"{col[0]} {col[1]}" for col in COLUMNS])
    
    # Create table if not exists - we won't actually create the table since we're using an existing one
    # But we'll keep this for reference
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        {columns_str}
    )
    """
    
    # Check if the table exists first
    cursor.execute(f"SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = '{TABLE_NAME}')")
    exists = cursor.fetchone()[0]
    
    if not exists:
        cursor.execute(create_table_query)
        conn.commit()
    
    cursor.close()
    conn.close()

# Function to import CSV to database
def import_csv_to_db(csv_file_path):
    try:
        create_table_if_not_exists()
        
        # Read CSV file
        df = pd.read_csv(csv_file_path, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")
        
        # Connect to database
        conn = get_db_connection()
        
        # Insert rows
        inserted_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            # Each row gets its own transaction to avoid aborting everything on error
            cursor = conn.cursor()
            try:
                # Move id to job_id if it exists
                if 'id' in df.columns and not pd.isna(row.get('id')):
                    row['job_id'] = str(row.get('id'))
                
                # Generate a unique job_id if not present
                if pd.isna(row.get('job_id')) or not row.get('job_id'):
                    # Generate job_id based on job_url if missing
                    row['job_id'] = f"js-{abs(hash(str(row.get('job_url', ''))))}"
                
                # Add site column if missing
                if 'site' not in df.columns or pd.isna(row.get('site')):
                    row['site'] = 'jobspy'
                
                # Make sure job_url exists
                if pd.isna(row.get('job_url')):
                    print(f"Skipping row without URL: {row.get('title')}")
                    skipped_count += 1
                    continue
                    
                # Check if this exact job exists (by URL not just job_id)
                cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE job_url = %s", (row.get('job_url'),))
                if cursor.fetchone():
                    print(f"Skipping existing job: {row.get('job_url')}")
                    skipped_count += 1
                    continue
                    
                # Build column names and placeholders
                columns = []
                placeholders = []
                values = []
                
                # Get column names from our COLUMNS definition
                column_names = [col_name for col_name, _ in COLUMNS]
                
                # Process each column that exists in our definition
                for col_name in column_names:
                    val = None
                    
                    # Map 'id' column to 'job_id' if needed
                    if col_name == 'job_id' and 'id' in df.columns and not pd.isna(row.get('id')):
                        val = str(row.get('id'))
                    elif col_name in df.columns:
                        val = row.get(col_name)
                    
                    if val is not None and not pd.isna(val):  # Only include non-null values
                        # Convert boolean strings to actual booleans
                        if col_name == 'is_remote' and isinstance(val, str):
                            if val.lower() in ('true', 't', 'yes', 'y', '1'):
                                val = True
                            elif val.lower() in ('false', 'f', 'no', 'n', '0'):
                                val = False
                        
                        columns.append(col_name)
                        placeholders.append('%s')
                        values.append(val)
                
                # Skip rows that don't have enough data
                if len(columns) < 2:  # At least job_id and url should be present
                    print(f"Skipping row with insufficient data: {row.get('title')}")
                    skipped_count += 1
                    continue
                    
                # Build and execute INSERT query
                insert_query = f"""
                INSERT INTO {TABLE_NAME} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
                
                cursor.execute(insert_query, values)
                conn.commit()
                inserted_count += 1
                
            except Exception as e:
                print(f"Error processing row: {e}")
                conn.rollback()
                skipped_count += 1
            finally:
                cursor.close()
        
        conn.close()
        
        return f"Imported {inserted_count} rows into database. Skipped {skipped_count} rows."
    
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error importing CSV: {str(e)}"

# Function to save jobs data to database directly
def save_jobs_to_db(jobs_data):
    try:
        create_table_if_not_exists()
        
        # Connect to database
        conn = get_db_connection()
        
        # Insert rows
        inserted_count = 0
        skipped_count = 0
        
        for job in jobs_data:
            # Each job gets its own transaction to avoid aborting everything on error
            cursor = conn.cursor()
            try:
                # Move id to job_id if it exists
                if 'id' in job and job['id']:
                    job['job_id'] = str(job['id'])
                    del job['id']  # Remove id to avoid confusion
                
                # Make sure job has a job_id
                if not job.get('job_id'):
                    job['job_id'] = f"yc-{abs(hash(str(job.get('job_url', ''))))}"
                    
                # Make sure job_url exists
                if not job.get('job_url'):
                    print(f"Skipping job without URL: {job.get('title')}")
                    skipped_count += 1
                    continue
                    
                # Check if this job URL already exists
                cursor.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE job_url = %s", (job.get('job_url'),))
                if cursor.fetchone():
                    print(f"Skipping existing job: {job.get('job_url')}")
                    skipped_count += 1
                    continue
                    
                # Build column names and placeholders
                columns = []
                placeholders = []
                values = []
                
                column_names = [col_name for col_name, _ in COLUMNS]
                
                for col in column_names:
                    val = job.get(col)
                    if val is not None:  # Only include non-null values
                        # Handle booleans properly
                        if col == 'is_remote' and isinstance(val, str):
                            if val.lower() in ('true', 't', 'yes', 'y', '1'):
                                val = True
                            elif val.lower() in ('false', 'f', 'no', 'n', '0'):
                                val = False
                        
                        columns.append(col)
                        placeholders.append('%s')
                        values.append(val)
                
                # Skip jobs that don't have enough data
                if len(columns) < 2:  # At least job_id and url should be present
                    print(f"Skipping job with insufficient data: {job.get('title')}")
                    skipped_count += 1
                    continue
                    
                # Build and execute INSERT query
                insert_query = f"""
                INSERT INTO {TABLE_NAME} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
                
                cursor.execute(insert_query, values)
                conn.commit()
                inserted_count += 1
                
            except Exception as e:
                print(f"Error inserting job: {e} - Job URL: {job.get('job_url')}")
                conn.rollback()
                skipped_count += 1
            finally:
                cursor.close()
        
        conn.close()
        
        return f"Imported {inserted_count} rows into database. Skipped {skipped_count} rows."
    
    except Exception as e:
        print(f"Error saving jobs to database: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error saving jobs to database: {str(e)}"

@app.route('/scrape', methods=['POST'])
def scrape():
    """API endpoint to scrape jobs."""
    data = request.json
    
    # Extract parameters with defaults
    site_names = data.get('site_names', ["indeed", "linkedin", "google"])
    search_term = data.get('search_term', "")
    google_search_term = data.get('google_search_term', f"{search_term} jobs")
    location = data.get('location', "")
    results_wanted = data.get('results_wanted', 100)
    hours_old = data.get('hours_old', 72)
    country_indeed = data.get('country_indeed', "usa")  # Default to usa if not provided
    linkedin_fetch_description = data.get('linkedin_fetch_description', True)
    output_csv = data.get('output_csv', "jobs.csv")
    save_to_db = data.get('save_to_db', False)
    company_name = data.get('company_name')  # For YCombinator
    
    # Validate required parameters
    if not search_term and 'ycombinator' not in site_names:
        return jsonify({"error": "search_term is required"}), 400
    if not location and 'ycombinator' not in site_names:
        return jsonify({"error": "location is required"}), 400
    if 'ycombinator' in site_names and not company_name:
        return jsonify({"error": "company_name is required for YCombinator scraping"}), 400
    
    try:
        all_jobs = []
        
        # Scrape jobs from JobSpy supported sites
        jobspy_sites = [site for site in site_names if site != 'ycombinator']
        if jobspy_sites:
            print(f"Scraping JobSpy sites: {jobspy_sites}")
            jobs = scrape_jobs(
                site_name=jobspy_sites,
                search_term=search_term,
                google_search_term=google_search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=country_indeed,
                linkedin_fetch_description=linkedin_fetch_description,
            )
            
            print(f"Found {len(jobs)} jobs from JobSpy")
            
            # Ensure the jobs have a site attribute
            jobs_dict = jobs.to_dict(orient='records')
            for job in jobs_dict:
                if 'site' not in job or not job['site']:
                    job['site'] = 'jobspy'
                
                # Move 'id' to 'job_id' for consistency with our schema
                if 'id' in job and job['id']:
                    job['job_id'] = str(job['id'])
            
            # Save JobSpy results to CSV
            jobs.to_csv(output_csv, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
            print(f"Saved JobSpy results to {output_csv}")
            
            all_jobs.extend(jobs_dict)
        
        # Scrape YCombinator jobs if requested
        ycombinator_jobs = []
        if 'ycombinator' in site_names:
            print(f"Scraping YCombinator jobs for company: {company_name}")
            ycombinator_jobs = scrape_ycombinator_jobs(company_name)
            print(f"Found {len(ycombinator_jobs)} jobs from YCombinator")
            all_jobs.extend(ycombinator_jobs)
        
        # Save to database if requested
        db_result = None
        if save_to_db:
            if jobspy_sites:
                print(f"Saving JobSpy jobs to database from {output_csv}")
                db_result = import_csv_to_db(output_csv)
                print(f"JobSpy DB import result: {db_result}")
            
            if ycombinator_jobs:
                print(f"Saving {len(ycombinator_jobs)} YCombinator jobs to database")
                db_result_yc = save_jobs_to_db(ycombinator_jobs)
                print(f"YCombinator DB import result: {db_result_yc}")
                if db_result:
                    db_result += f" {db_result_yc}"
                else:
                    db_result = db_result_yc
        
        return jsonify({
            "status": "success",
            "jobs_found": len(all_jobs),
            "jobs_data": all_jobs,
            "csv_path": output_csv if jobspy_sites else None,
            "db_result": db_result
        })
    
    except Exception as e:
        print(f"Error in scrape endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/jobs', methods=['GET'])
def get_jobs():
    """API endpoint to retrieve jobs from database."""
    try:
        # Get query parameters
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        search = request.args.get('search', default=None, type=str)
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = f"SELECT * FROM {TABLE_NAME}"
        count_query = f"SELECT COUNT(*) FROM {TABLE_NAME}"
        
        # Add search condition if provided
        params = []
        if search:
            query += " WHERE title ILIKE %s OR company ILIKE %s OR location ILIKE %s"
            count_query += " WHERE title ILIKE %s OR company ILIKE %s OR location ILIKE %s"
            search_param = f"%{search}%"
            params = [search_param, search_param, search_param]
        
        # Add pagination
        query += f" ORDER BY id LIMIT {limit} OFFSET {offset}"
        
        # Get total count
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = {}
            for i, column in enumerate(columns):
                result[column] = row[i]
            results.append(result)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "data": results
        })
    
    except Exception as e:
        print(f"Error retrieving jobs: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True) 