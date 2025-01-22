from linkedin_api import Linkedin
import json
import logging
import os
import csv
import pandas as pd
from datetime import datetime
import re
from dotenv import load_dotenv
from staffspy.linkedin.linkedin import LinkedInScraper
from staffspy import LinkedInAccount, DriverType, BrowserType
import time
import random
from requests.cookies import RequestsCookieJar

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def extract_urn_id(participant_id):
    logger.debug(f"Extracting URN ID from: {participant_id}")
    if not participant_id:
        logger.warning("Received empty participant_id")
        return None
    urn_id = participant_id.split(':')[-1]
    logger.debug(f"Extracted URN ID: {urn_id}")
    return urn_id

def extract_contact_details(message_text):
    """Extract phone numbers and email addresses from message text"""
    logger.debug(f"Starting contact detail extraction from message: {message_text[:50]}...")
    
    # Indian phone number pattern (10 digits, may start with +91 or 0)
    phone_pattern = r'(?:(?:\+91|0)?[6789]\d{9})'
    # Email pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    contact_info = {
        'phone_numbers': [],
        'emails': []
    }
    
    # Find all matches
    phone_numbers = re.findall(phone_pattern, message_text)
    emails = re.findall(email_pattern, message_text)
    
    logger.debug(f"Found {len(phone_numbers)} phone numbers and {len(emails)} email addresses")
    
    # Clean phone numbers (remove +91 or leading 0)
    cleaned_numbers = [re.sub(r'^(?:\+91|0)', '', num) for num in phone_numbers]
    
    if cleaned_numbers:
        contact_info['phone_numbers'] = cleaned_numbers
        logger.info(f"Phone number(s) fetched successfully. Numbers found: {', '.join(cleaned_numbers)}")
    
    if emails:
        contact_info['emails'] = emails
        logger.info(f"Email ID(s) fetched successfully. Emails found: {', '.join(emails)}")
    
    return contact_info

def save_raw_json(data, filename, output_dir):
    logger.debug(f"Attempting to save raw data to file: {filename}")
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved raw data to {filepath}")
    except Exception as e:
        logger.error(f"Error saving raw data to {filepath}: {str(e)}")
        raise

def extract_conversation_data(conversation):
    logger.debug(f"Extracting data from conversation: {conversation.get('entityUrn', 'No URN')}")
    
    conversation_data = {
        'conversation_id': conversation.get('entityUrn', ''),
        'total_events': conversation.get('totalEventCount', 0),
        'unread_count': conversation.get('unreadCount', 0),
        'last_activity': datetime.fromtimestamp(conversation.get('lastActivityAt', 0)/1000).strftime('%Y-%m-%d %H:%M:%S'),
        'is_group_chat': conversation.get('groupChat', False),
        'inbox_type': conversation.get('inboxType', ''),
        'read_status': conversation.get('read', False)
    }
    
    logger.debug(f"Extracted conversation data: {conversation_data}")
    return conversation_data

def extract_participant_data(participant):
    logger.debug("Starting participant data extraction")
    
    member_data = participant.get('com.linkedin.voyager.messaging.MessagingMember', {})
    profile = member_data.get('miniProfile', {})
    
    participant_info = {
        'participant_id': member_data.get('entityUrn', ''),
        'first_name': profile.get('firstName', ''),
        'last_name': profile.get('lastName', ''),
        'occupation': profile.get('occupation', ''),
        'public_id': profile.get('publicIdentifier', ''),
        'profile_urn': profile.get('entityUrn', '')
    }
    
    logger.debug(f"Extracted participant data for: {participant_info['first_name']} {participant_info['last_name']}")
    return participant_info

def extract_message_data(events):
    """Extract message data from conversation events"""
    logger.debug(f"Starting message extraction from {len(events)} events")
    messages = []
    
    for idx, event in enumerate(events, 1):
        logger.debug(f"Processing event {idx}/{len(events)}")
        
        if 'eventContent' in event:
            content = event.get('eventContent', {})
            message_event = content.get('com.linkedin.voyager.messaging.event.MessageEvent', {})
            
            if message_event:
                message = {
                    'message_id': event.get('entityUrn', ''),
                    'created_at': datetime.fromtimestamp(event.get('createdAt', 0)/1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'text': message_event.get('attributedBody', {}).get('text', '')
                }
                logger.debug(f"Extracted message: ID={message['message_id']}, Created={message['created_at']}")
                messages.append(message)
            else:
                logger.debug("Event does not contain message data")
    
    logger.info(f"Extracted {len(messages)} messages from events")
    return messages

def send_response_message(api, conversation_urn):
    """Send a response message to a conversation"""
    logger.debug(f"Attempting to send response message to conversation: {conversation_urn}")
    
    try:
        # Extract conversation ID from URN
        conversation_id = conversation_urn.split(':')[-1]
        logger.debug(f"Extracted conversation ID: {conversation_id}")
        
        # Standard response message
        response_message = "Thank you for showing an interest in us. A career counseling expert will be contacting you shortly!"
        
        # Send the message
        api.send_message(
            message_body=response_message,
            conversation_urn_id=conversation_id
        )
        logger.info(f"Successfully sent response message to conversation {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending response message to {conversation_urn}: {str(e)}")
        return False

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
                session_file="session_personall.pkl",
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
    
    try:
        # Get cookies from StaffSpy session
        cookie_dict = account.session.cookies.get_dict()
        
        # Convert dict to RequestsCookieJar
        cookies = RequestsCookieJar()
        for name, value in cookie_dict.items():
            cookies.set(name, value, domain='.linkedin.com')
        
        # Initialize LinkedIn API with cookies
        api = Linkedin(
            username=os.getenv("LINKEDIN_USERNAME"),
            password=os.getenv("LINKEDIN_PASSWORD"),
            cookies=cookies,
            refresh_cookies=False,
            debug=True
        )
        
        logger.info("LinkedIn API session initialized successfully")
        return api
        
    except Exception as e:
        logger.error(f"Failed to initialize LinkedIn API session: {str(e)}")
        raise

def main():
    try:
        print(os.getcwd())
        logger.info("Starting LinkedIn message processing pipeline")
        
        # Create output directory if it doesn't exist
        output_dir = 'pipe3 output'
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created/verified output directory: {output_dir}")
        
        # Initialize LinkedIn sessions
        account = initialize_linkedin_session()
        api = initialize_linkedin_api_session(account)
        logger.info("LinkedIn sessions initialized successfully")

        # Get all conversations
        logger.info("Attempting to fetch conversations...")
        conversations = api.get_conversations()
        logger.info("Successfully fetched conversations from LinkedIn API")
        
        # Save raw conversations response
        save_raw_json(conversations, 'raw_conversations.json', output_dir)
        
        # Process conversations and participants
        conversation_data = []
        participant_data = []
        contact_details_data = []
        
        elements = conversations.get('elements', [])
        logger.info(f"Processing {len(elements)} conversations")
        
        for idx, conv in enumerate(elements, 1):
            logger.info(f"Processing conversation {idx}/{len(elements)}")
            
            conv_info = extract_conversation_data(conv)
            conversation_data.append(conv_info)
            
            # Only process messages if there are unread messages
            if conv_info['unread_count'] > 0:
                logger.info(f"Found {conv_info['unread_count']} unread messages in conversation {conv_info['conversation_id']}")
                
                # Extract messages from events
                events = conv.get('events', [])
                logger.debug(f"Found {len(events)} events in conversation")
                messages = extract_message_data(events)
                
                # Process each message for contact details
                logger.debug(f"Processing {len(messages)} messages for contact details")
                contact_found = False
                
                for msg_idx, message in enumerate(messages, 1):
                    logger.debug(f"Processing message {msg_idx}/{len(messages)}")
                    contact_details = extract_contact_details(message['text'])
                    
                    if contact_details['phone_numbers'] or contact_details['emails']:
                        contact_found = True
                        contact_data = {
                            'conversation_id': conv_info['conversation_id'],
                            'message_id': message['message_id'],
                            'timestamp': message['created_at'],
                            'phone_numbers': contact_details['phone_numbers'],
                            'emails': contact_details['emails']
                        }
                        logger.info(f"Found contact details in message: {contact_data}")
                        contact_details_data.append(contact_data)
                
                # Send response message if contact details were found
                if contact_found:
                    logger.info("Contact details found, sending response message...")
                    conversation_urn = conv_info['conversation_id']
                    send_response_message(api, conversation_urn)
            
            # Process participants
            participants = conv.get('participants', [])
            logger.info(f"Processing {len(participants)} participants in conversation")
            
            for part_idx, participant in enumerate(participants, 1):
                logger.debug(f"Processing participant {part_idx}/{len(participants)}")
                participant_info = extract_participant_data(participant)
                participant_data.append(participant_info)
                
                # Save individual participant details
                urn_id = extract_urn_id(participant_info['participant_id'])
                if urn_id:
                    save_raw_json(participant_info, f'participant_details_{urn_id}.json', output_dir)
        
        # Save processed data to CSV files
        logger.info("Saving processed data to CSV files...")
        
        # Save conversations data
        conversations_df = pd.DataFrame(conversation_data)
        conversations_df.to_csv(os.path.join(output_dir, 'conversations.csv'), index=False)
        logger.info("Saved conversations data to CSV")
        
        # Save participants data
        participants_df = pd.DataFrame(participant_data)
        participants_df.to_csv(os.path.join(output_dir, 'participants.csv'), index=False)
        logger.info("Saved participants data to CSV")
        
        # Save contact details data
        if contact_details_data:
            contact_details_df = pd.DataFrame(contact_details_data)
            contact_details_df.to_csv(os.path.join(output_dir, 'contact_details.csv'), index=False)
            logger.info("Saved contact details to CSV")
        else:
            logger.info("No contact details found to save")
        
        logger.info("LinkedIn message processing pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error in pipeline execution: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
