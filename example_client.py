import requests
import json
import argparse

def scrape_jobs(api_url, search_term=None, location=None, country_indeed=None, site_names=None, company_name=None):
    """
    Scrape jobs using the API
    """
    if site_names is None:
        site_names = ["indeed", "linkedin"]
    
    payload = {
        "site_names": site_names,
        "search_term": search_term,
        "google_search_term": f"{search_term} jobs near {location}" if search_term and location else None,
        "location": location,
        "results_wanted": 100,
        "hours_old": 72,
        "country_indeed": country_indeed,
        "save_to_db": True,
        "company_name": company_name
    }
    
    response = requests.post(f"{api_url}/scrape", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Successfully scraped {result['jobs_found']} jobs")
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def get_jobs(api_url, search=None, limit=10, offset=0):
    """
    Get jobs from the database
    """
    params = {
        "limit": limit,
        "offset": offset
    }
    
    if search:
        params["search"] = search
    
    response = requests.get(f"{api_url}/jobs", params=params)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Retrieved {len(result['data'])} jobs (total: {result['total']})")
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def display_jobs(jobs_data):
    """
    Display job listings in a readable format
    """
    if not jobs_data or "data" not in jobs_data:
        print("No jobs to display")
        return
    
    for i, job in enumerate(jobs_data["data"], 1):
        print(f"\n--- Job {i} ---")
        print(f"Title: {job.get('title')}")
        print(f"Company: {job.get('company')}")
        print(f"Location: {job.get('location')}")
        print(f"Date Posted: {job.get('date_posted')}")
        
        if job.get('min_amount') and job.get('max_amount'):
            print(f"Salary: {job.get('min_amount')} - {job.get('max_amount')} {job.get('currency')} {job.get('interval')}")
        
        print(f"URL: {job.get('job_url')}")
        print(f"Type: {job.get('job_type')}")
        print(f"Remote: {job.get('is_remote')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobSpy API Client")
    parser.add_argument("--api-url", default="http://localhost:5000", help="API URL")
    parser.add_argument("--mode", choices=["scrape", "get"], default="get", help="Mode: scrape or get")
    
    # Scrape mode arguments
    parser.add_argument("--search-term", help="Job search term")
    parser.add_argument("--location", help="Job location")
    parser.add_argument("--country-indeed", help="Country for Indeed")
    parser.add_argument("--site-names", nargs="+", default=["indeed", "linkedin"], 
                        help="List of job sites to scrape (e.g., indeed linkedin ycombinator)")
    parser.add_argument("--company-name", help="Company name for YCombinator scraping")
    
    # Get mode arguments
    parser.add_argument("--search", help="Search term for filtering jobs")
    parser.add_argument("--limit", type=int, default=10, help="Number of jobs to retrieve")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    
    args = parser.parse_args()
    
    if args.mode == "scrape":
        # Check if required parameters are provided based on site selection
        requires_search_location = not all(site == "ycombinator" for site in args.site_names)
        requires_company = "ycombinator" in args.site_names
        
        if requires_search_location and (not args.search_term or not args.location):
            print("Error: --search-term and --location are required for scraping Indeed/LinkedIn/Google")
            exit(1)
        
        if requires_company and not args.company_name:
            print("Error: --company-name is required when including 'ycombinator' in site-names")
            exit(1)
        
        result = scrape_jobs(
            api_url=args.api_url,
            search_term=args.search_term,
            location=args.location,
            country_indeed=args.country_indeed,
            site_names=args.site_names,
            company_name=args.company_name
        )
        
        if result and result.get("jobs_data"):
            print("\nSample of jobs found:")
            for i, job in enumerate(result["jobs_data"][:5], 1):
                print(f"{i}. {job.get('title')} at {job.get('company')} in {job.get('location', 'Unknown')}")
    
    elif args.mode == "get":
        result = get_jobs(
            api_url=args.api_url,
            search=args.search,
            limit=args.limit,
            offset=args.offset
        )
        
        if result:
            display_jobs(result) 