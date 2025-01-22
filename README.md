# HeyCoach LinkedIn AI Agent

## Overview
This repository contains a set of Python scripts for automating LinkedIn lead generation and outreach. The system consists of three main pipelines that work together to:
1. Scrape profiles and send connection requests
2. Generate personalized messages using AI
3. Extract contact information from successful conversations

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Pipeline Details](#pipeline-details)
- [Usage Guide](#usage-guide)
- [Important Considerations](#important-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Firefox browser (latest version)
- 8GB RAM minimum
- Stable internet connection

### LinkedIn Account Requirements
- **IMPORTANT**: Create a dedicated LinkedIn account for automation
- **DO NOT** use your personal LinkedIn account
- Premium account recommended for better results
- Account must have:
  - Professional profile picture
  - Completed profile information
  - Some existing connections (50+)
  - Active for at least 1 month

### Local Environment
- Local LLM server running on port 1234 (for Pipeline 2)
- Sufficient disk space for storing session files and output data

## Installation

1. **Clone the Repository**
   ```bash
   git clone [<repository-url>](https://github.com/yashvoladoddi37/heycoach-linkedin-ai-agent-raw-yv)
   cd heycoach_linkedin_ai_agent_raw
   ```

2. **Create Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   LINKEDIN_USERNAME=your_automation_account@email.com
   LINKEDIN_PASSWORD=your_password
   ```

2. **Session Management**
   - Each pipeline maintains its own session file
   - Session files are stored as `.pkl` files
   - Default session files:
     - Pipeline 1: `session_yash.pkl`
     - Pipeline 2: `session_fake.pkl`
     - Pipeline 3: `session_personall.pkl`

3. **Output Directories**
   - Create the following directories:
     ```bash
     mkdir logs
     mkdir output
     ```

## Pipeline Details

### Pipeline 1: Profile Scraping (`pipe_1_final_jan17.py`)
- **Purpose**: Scrapes LinkedIn profiles and sends connection requests
- **Features**:
  - Targets specific companies (configurable list)
  - Implements random delays between requests
  - Sends 20-25 connection requests per run (configurable parameter)
  - Saves scraped profiles to CSV
- **Configuration**:
  ```python
  # Configurable companies list in the script
  companies = [
      'Capgemini India',
      'Tech Mahindra',
      # Add/remove companies as needed
  ]
  ```

### Pipeline 2: Message Generation (`pipe_2_final_jan17.py`)
- **Purpose**: Generates and sends personalized messages
- **Features**:
  - Uses local LLM for message generation
  - Personalizes based on profile information
  - Implements proper rate limiting
  - Logs all sent messages
- **LLM Requirements**:
  - Local LLM server running on port 1234
  - Supports chat completions API
  - Temperature set to 0.3 for consistent output

### Pipeline 3: Contact Extraction (`pipe_3_final_jan20.py`)
- **Purpose**: Extracts contact information from conversations
- **Features**:
  - Processes recent conversations
  - Extracts phone numbers and email addresses
  - Supports Indian phone number formats
  - Saves extracted data to CSV

## Usage Guide

### Running the Pipelines

1. **Pipeline 1: Initial Outreach**
   ```python
   python pipe_1_final_jan17.py
   ```
   - Runs for approximately 30-45 minutes
   - Automatically stops after sending 20-25 requests
   - Check `logs/linkedin_pipeline_{timestamp}.log` for progress

2. **Pipeline 2: Message Generation**
   ```python
   python pipe_2_final_jan17.py
   ```
   - Requires running LLM server
   - Processes recent connections
   - Check message quality in logs before scaling

3. **Pipeline 3: Data Extraction**
   ```python
   python pipe_3_final_jan20.py
   ```
   - Run daily to process new responses
   - Extracts from successful conversations
   - Updates contact database

### Output Files
- **Profile Data**: `scraped_profiles_{timestamp}.csv`
- **Message Logs**: `message_logs_{timestamp}.csv`
- **Contact Details**: `contact_details_{timestamp}.csv`
- **System Logs**: `logs/linkedin_pipeline_{timestamp}.log`

## Important Considerations

### Rate Limiting
- **Random Delays**: Built-in delays between actions
- **Daily Limits**: 
  - Connection requests: 15-20 per day
  - Messages: 10-15 per day
  - Profile views: 250-300 per day

### Account Safety
1. **Warm-up Period**
   - Start with lower limits
   - Gradually increase activity over weeks
   - Monitor for any warnings

2. **Activity Guidelines**
   - Don't run scripts 24/7
   - Maintain human-like patterns
   - Take breaks between sessions

3. **Profile Maintenance**
   - Regularly update profile
   - Engage with feed content
   - Accept incoming connections

### Data Management
- Regularly backup CSV files
- Clean up old session files
- Monitor disk space usage
- Secure storage of credentials

## Troubleshooting

### Common Issues

1. **Session Errors**
   - Delete corresponding `.pkl` file. This is usually the cookie file generated by manual login of LinkedIn
   - Restart browser (recommend using Firefox)
   - Check account status

2. **Rate Limiting**
   - Increase delay parameters
   - Reduce daily targets
   - Wait 24 hours before retry

3. **LLM Server Issues**
   - Verify server is running
   - Check port 1234 availability
   - Monitor server logs

### Error Logging
- Check `logs/` directory
- Look for error patterns
- Monitor LinkedIn warnings

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Submit pull request

