"""
Pipeline 1 of LinkedIn AI Lead Generation Agent

Pipeline 1 focuses on using the StaffSpy library to scrape profiles by searching 
based on role, company, location.

After scraping relevant profiles, send anywhere between 20-25 connection 
requests (random number recommended) after implementing random delays to prevent 
rate limiting by LinkedIn.

"""

# After this pipeline executes, results saved in csv.


import random
import logging
import os
import json
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import requests

# LinkedIn imports
from staffspy import LinkedInAccount, DriverType, BrowserType
from linkedin_api import Linkedin

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(log_dir, f'linkedin_pipeline_{timestamp}.log')

# Create logger
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

# Clear any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create file handler
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def initialize_linkedin_session():
    """Initialize LinkedIn session using StaffSpy"""
    logger.info("Initializing LinkedIn session")
    
    try:
        # Load credentials from .env
        load_dotenv()
        username = os.getenv("LINKEDIN_USERNAME")
        password = os.getenv("LINKEDIN_PASSWORD")
        
        if not username or not password:
            raise ValueError("LinkedIn credentials not found in environment variables")
        
        logger.info(f"Using username: {username}")
        
        # Initialize LinkedIn Account with minimal configuration
        try:
            account = LinkedInAccount(
                session_file="session_yash.pkl",
                log_level=2,  # Detailed logging
                driver_type=DriverType(browser_type=BrowserType.FIREFOX)
            )
            
            logger.info("LinkedIn account object created successfully")
            
            # Basic session validation
            if account and hasattr(account, 'session'):
                logger.info("Session appears to be valid")
            else:
                raise Exception("Session validation failed")
            
            logger.info("LinkedIn session initialized successfully")
            return account
            
        except Exception as session_err:
            logger.error(f"Failed to initialize LinkedIn session: {str(session_err)}")
            logger.error("Make sure Firefox is installed and updated")
            raise
    
    except Exception as e:
        logger.critical(f"Critical error in LinkedIn session initialization: {str(e)}")
        raise

def initialize_linkedin_api_session(account):
    """Initialize LinkedIn API session using StaffSpy session cookies"""
    logger.info("Initializing LinkedIn API session")
    
    # Load credentials from .env
    load_dotenv()
    username = os.getenv("LINKEDIN_USERNAME")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not username or not password:
        raise ValueError("LinkedIn credentials not found in environment variables")
    
    # Use the RequestsCookieJar directly from StaffSpy session
    cookies = account.session.cookies
    
    # Initialize LinkedIn API with saved cookies
    try:
        logger.info("Initializing LinkedIn API client with saved cookies")
        li = Linkedin(username=username, password=password, cookies=cookies, refresh_cookies=True, debug=True)
        logger.info("LinkedIn API client initialized successfully")
        return li
    except Exception as e:
        logger.error(f"Failed to initialize LinkedIn API client: {str(e)}")
        raise

def send_connection_request(api_client, profile_id, max_retries=3, retry_delay=5):
    """Send a connection request with retry logic"""
    for attempt in range(max_retries):
        try:
            # Add a small delay between retries
            if attempt > 0:
                time.sleep(retry_delay)
            
            # First, verify the profile exists and is accessible
            try:
                profile_data = api_client.get_profile(public_id=profile_id)
                if not profile_data:
                    return False, "Profile not found or not accessible"
                
                logger.debug(f"Found profile data: {profile_data.get('public_id')}")
                
            except Exception as profile_err:
                logger.warning(f"Error fetching profile data: {str(profile_err)}")
                if attempt == max_retries - 1:
                    return False, f"Could not fetch profile data: {str(profile_err)}"
                continue
            
            # Send the connection request
            response = api_client.add_connection(
                profile_public_id=profile_id
            )
            
            # The API returns True if request failed, False if successful
            if response is False:
                return True, "Connection request sent successfully"
            else:
                return False, "Failed to send connection request"
                
        except Exception as e:
            if attempt == max_retries - 1:
                return False, str(e)
            logger.warning(f"Error on attempt {attempt + 1}: {str(e)}, retrying...")
            continue
    
    return False, f"Failed after {max_retries} attempts"

def scrape_and_connect(account, api_client):
    """Main function to scrape profiles and send connection requests"""
    logger.info("----------------------------Starting LinkedIn lead generation pipeline----------------------------")
    
    # List of companies to scrape from
    companies = [
        'Capgemini India',
        'Tech Mahindra',
        'Infosys',
        'Accenture India',
        'Coforge',
        'Zensar Technologies',
        'LTI Mindtree',
        'Mphasis',
        'Persistent Systems',
        'Tata Consultancy Services',
        'Birlasoft',
        'HCL Technologies',
        'Hexaware Technologies',
        'Cognizant India',
        'Wipro'
    ]
    
    # Select random companies to avoid pattern detection
    num_companies = min(3, len(companies))  # Limit to 3 companies for testing
    selected_companies = random.sample(companies, num_companies)
    logger.debug(f"Selected companies: {selected_companies}")
    
    logger.info(f"Scraping profiles for {len(selected_companies)} companies")
    
    # Collect all scraped profiles
    all_scraped_profiles = []
    connection_attempts = []
    successful_connections = 0
    target_connections = 15  # Increased target number of successful connection requests
    max_attempts_per_company = 2  # Maximum number of attempts per company
    
    # Try to load previous connection attempts to avoid duplicates
    try:
        previous_attempts_file = "output/previous_connection_attempts.csv"
        if os.path.exists(previous_attempts_file):
            previous_attempts = pd.read_csv(previous_attempts_file)
            previous_profile_ids = set(previous_attempts['profile_id'].tolist())
            logger.info(f"Loaded {len(previous_profile_ids)} previous connection attempts")
        else:
            previous_profile_ids = set()
    except Exception as e:
        logger.warning(f"Could not load previous connection attempts: {str(e)}")
        previous_profile_ids = set()
    
    # Scrape profiles from each company
    for company in selected_companies:
        if successful_connections >= target_connections:
            logger.info(f"Reached target of {target_connections} successful connections")
            break
            
        try:
            logger.debug(f"Scraping profiles for company: {company}")
            
            # Use staffspy's scrape_staff method with connect=False
            staff_df = account.scrape_staff(
                company_name=company,
                search_term="software engineer",
                location="india",
                max_results=10,  # Increased to have more profiles to try
                extra_profile_data=True,
                connect=False  # Do NOT send connection requests during scraping
            )
            
            if not staff_df.empty:
                # Print column names for debugging
                logger.info(f"Columns in DataFrame: {list(staff_df.columns)}")
                
                # Save results to CSV
                output_dir = 'output'
                os.makedirs(output_dir, exist_ok=True)
                output_file = f"{output_dir}/{company}_staff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                staff_df.to_csv(output_file, index=False)
                logger.info(f"Saved {len(staff_df)} profiles to {output_file}")
                
                # Randomly shuffle profiles
                profiles_to_try = staff_df.sample(frac=1).to_dict('records')
                
                # Try each profile until we get enough successful connections
                attempts_for_company = 0
                for profile_to_connect in profiles_to_try:
                    if successful_connections >= target_connections:
                        break
                        
                    if attempts_for_company >= max_attempts_per_company:
                        logger.info(f"Reached maximum attempts for company {company}")
                        break
                        
                    try:
                        # Get profile ID and name from the correct fields
                        profile_id = profile_to_connect.get('profile_id') or profile_to_connect.get('profile_link', '').split('/')[-1]
                        full_name = profile_to_connect.get('name', 'Unknown')
                        company = profile_to_connect.get('current_company', 'Unknown Company')
                        
                        if not profile_id or profile_id == 'Unknown':
                            logger.warning(f"Skipping profile with no ID: {full_name}")
                            continue
                            
                        if profile_id in previous_profile_ids:
                            logger.info(f"Skipping {full_name} - already attempted connection")
                            continue
                            
                        logger.info(f"Attempting to connect with profile ID: {profile_id}")
                        attempts_for_company += 1
                        
                        # Send connection request
                        success, message = send_connection_request(api_client, profile_id)
                        
                        # Record the attempt
                        connection_attempts.append({
                            'profile_id': profile_id,
                            'full_name': full_name,
                            'company': company,
                            'timestamp': datetime.now().isoformat(),
                            'success': success,
                            'message': message
                        })
                        
                        if success:
                            successful_connections += 1
                            logger.info(f"Successfully sent connection request to {full_name} from {company}")
                        else:
                            logger.warning(f"Failed to send connection request to {full_name} from {company}: {message}")
                            # Continue with next profile even if this one failed
                            continue
                            
                        # Add a random delay between requests to avoid rate limiting
                        delay = random.uniform(45, 90)  # Increased delay between requests
                        logger.debug(f"Waiting {delay} seconds before next request")
                        time.sleep(delay)
                        
                    except Exception as e:
                        logger.error(f"Error processing profile: {str(e)}")
                        continue
                
                # Add to total scraped profiles
                all_scraped_profiles.extend(staff_df.to_dict('records'))
                
                # Random delay between companies
                delay = random.randint(60, 180)
                logger.debug(f"Waiting {delay} seconds before next company")
                time.sleep(delay)
            
        except Exception as e:
            logger.error(f"Error scraping profiles for {company}: {str(e)}")
            continue
    
    # Save the full list of scraped profiles
    if all_scraped_profiles:
        full_output_file = f"output/all_scraped_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        pd.DataFrame(all_scraped_profiles).to_csv(full_output_file, index=False)
        logger.info(f"Saved total of {len(all_scraped_profiles)} profiles to {full_output_file}")
    
    # Save connection attempts log
    if connection_attempts:
        # Save to timestamped file
        connection_log_file = f"output/connection_attempts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        pd.DataFrame(connection_attempts).to_csv(connection_log_file, index=False)
        logger.info(f"Saved {len(connection_attempts)} connection attempts to {connection_log_file}")
        
        # Update the master list of previous attempts
        try:
            all_attempts = []
            if os.path.exists(previous_attempts_file):
                all_attempts.extend(pd.read_csv(previous_attempts_file).to_dict('records'))
            all_attempts.extend(connection_attempts)
            pd.DataFrame(all_attempts).to_csv(previous_attempts_file, index=False)
            logger.info(f"Updated master list of connection attempts in {previous_attempts_file}")
        except Exception as e:
            logger.error(f"Error updating master connection attempts file: {str(e)}")
    
    logger.info(f"Connection request summary: {successful_connections} successful out of {target_connections} target")

def main():
    """Main entry point"""
    try:
        logger.info("Starting LinkedIn Lead Generation Pipeline")
        
        # Log the log filename
        logger.info(f"Logging to file: {log_filename}")
        
        # Initialize LinkedIn session
        account = initialize_linkedin_session()
        
        # Initialize LinkedIn API session using StaffSpy session cookies
        api_client = initialize_linkedin_api_session(account)
        
        # Run the scraping pipeline
        scrape_and_connect(account, api_client)
        
    except Exception as e:
        logger.critical(f"Critical error in pipeline execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()
