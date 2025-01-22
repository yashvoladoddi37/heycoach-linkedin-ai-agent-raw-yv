import os
import logging
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from linkedin_api import Linkedin
from staffspy.linkedin.linkedin import LinkedInScraper
from staffspy import LinkedInAccount, DriverType, BrowserType
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/linkedin_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_llm_response(profile_data):
    """Generate personalized message using local LLM"""
    try:
        # Define the prompt template
        prompt = f'''
You're a career coach who's helped 100+ engineers land roles at MAANG companies. Write a compelling first message that creates immediate interest and urgency. The goal is to get their contact details in the first response.

About them:
• Name: {profile_data['name']}
• Role: {profile_data['current_position']} at {profile_data['company']}
• Experience: {profile_data['experiences']}
• Key skills: {', '.join(profile_data['skills'])}
• Certifications: {', '.join(profile_data['certifications'])}

Write a message that:
1. Opens with a specific observation about their experience trajectory from previous roles to current role so that it shows you've actually looked at their profile.
2. Also acknowledge them for any certifications they have IF THEY EXIST. If not, DO NOT hallucinate and mention it.
3. Help them understand how their profile fits into our program.
4. Creates FOMO by mentioning our track record (100+ engineers placed at MAANG)
5. Builds credibility by mentioning our mentors who work in MAANG companies and teach system design and Data Structures & Algorithms (DSA)
6. Includes a clear value proposition: "4-month focused mentorship from MAANG employee mentors to help you crack MAANG interviews"
7. Adds urgency: "We're selecting candidates for our next cohort starting soon"
8. Has TWO clear CTAs:
   • "I invite you to reply with your number for getting to know our program details and fee structure."
   • "You can also learn more at heycoach.in/super30."
7. Don't use emojis.
8. End the message with a warm and friendly closing along with: "Best Regards, Yashpreet"


Keep it a concise amount of characters. Make it feel personal yet professional. Focus on transformation - from where they are to where they could be.
'''
        
        # Prepare the payload
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 300,
            "stream": False
        }
        
        try:
            response = requests.post(
                'http://127.0.0.1:1234/v1/chat/completions',  
                headers={
                    "Content-Type": "application/json", 
                    "Accept": "application/json"
                },
                json=payload
            )
            
            response.raise_for_status()
            
            try:
                response_json = response.json()
                
                # Log the full response for debugging
                logger.debug(f"Full LLM response: {response_json}")
                
                # Extract message content
                message = response_json['choices'][0]['message']['content'].strip()
                
                logger.info(f"Generated message: {message}")
                return message
            
            except Exception as e:
                logger.error(f"Error processing LLM response: {e}")
                logger.error(f"Raw response: {response.text[:500]}")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to LM Studio. Ensure it's running on port 1234")
            return None
        except requests.exceptions.Timeout:
            logger.error("LM Studio request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"LLM API error: {e}")
            logger.error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error in LLM message generation: {e}")
        return None

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
                session_file="session_fake.pkl",
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

def main():
    try:
        # Initialize LinkedIn session
        account = initialize_linkedin_session()
        
        # Initialize LinkedIn API with the same session
        li = initialize_linkedin_api_session(account)
        
        # Create scraper instance
        logger.info("Creating LinkedIn Scraper")
        scraper = LinkedInScraper(session=account.session)
        
        # 1. Scrape recent connections
        logger.info("Scraping recent connections")
        connections = scraper.scrape_connections(max_results=1, extra_profile_data=True)
        
        # Process each connection
        for connection in connections:
            try:
                # Skip restricted profiles
                if connection.name == "LinkedIn Member":
                    continue
                
                # Debug log connection data
                logger.info(f"Processing connection: {connection.name}")
                logger.info(f"Connection URN: {connection.urn}")
                logger.info(f"Connection data: {connection.to_dict()}")
                
                # Debug log raw profile data
                logger.info("Raw profile data:")
                logger.info(f"Experiences: {connection.experiences}")
                logger.info(f"Skills: {connection.skills}")
                logger.info(f"Certifications: {connection.certifications}")
                
                # Construct proper LinkedIn URN
                profile_urn = connection.id
                
                # 2. Get detailed profile data
                profile_data = {
                    'name': connection.name,
                    'current_position': connection.experiences[0].title if connection.experiences else 'N/A',
                    'company': connection.experiences[0].company if connection.experiences else 'N/A',
                    'skills': [skill.name for skill in connection.skills] if connection.skills else [],
                    'experiences': [f"{exp.title} ({exp.duration})" for exp in connection.experiences] if connection.experiences else [],
                    'certifications': [cert.title for cert in connection.certifications] if connection.certifications else []
                }
                
                # Debug log processed profile data
                logger.info("Processed profile data:")
                logger.info(profile_data)
                
                # 3. Generate personalized message using LLM
                message = get_llm_response(profile_data)
                if not message:
                    logger.warning(f"Skipping message for {connection.name} due to LLM error")
                    continue
                
                # 4. Send personalized message
                logger.info(f"Sending message to {connection.name}")
                logger.info(f"Using profile URN: {profile_urn}")
                    
                retry_count = 0
                while True:
                    try:
                        error = li.send_message(
                            message_body=message,
                            recipients=[profile_urn]
                        )
                        
                        if error:
                            logger.error(f"Failed to send message to {connection.name} - API returned error")
                            retry_count += 1
                        else:
                            logger.info(f"Successfully sent message to {connection.name}")
                            break
                    except Exception as e:
                        logger.error(f"Failed to send message to {connection.name} - Exception: {str(e)}")
                        retry_count += 1
                    
                    # Exponential backoff with jitter
                    base_delay = 30  # Base delay of 30 seconds
                    max_delay = 150  # Maximum delay of 5 minutes
                    attempt = retry_count + 1  # Current attempt number
                    
                    # Calculate exponential backoff with jitter
                    delay = min(
                        max_delay, 
                        base_delay * (2 ** attempt) + random.uniform(0, base_delay)
                    )
                    
                    logger.info(f"Waiting {delay:.2f} seconds before sending message (Attempt {attempt})...")
                    time.sleep(delay)
                    
                # Exponential backoff with jitter before sending next message
                base_delay = 45  # Base delay of 45 seconds
                max_delay = 120  # Maximum delay of 2 minutes
                connection_index = connections.index(connection)
                
                # Calculate exponential backoff with jitter
                delay = min(
                    max_delay, 
                    base_delay * (2 ** connection_index) + random.uniform(0, base_delay)
                )
                
                logger.info(f"Waiting {delay:.2f} seconds before sending message to next connection (Connection {connection_index + 1}/{len(connections)})...")
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error processing connection {connection.name}: {e}")
                continue
            
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()