# LinkedIn CAPTCHA Solver

This script automates LinkedIn login and handles CAPTCHA challenges using Playwright.

## Setup

1. Install Python 3.8 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers:
```bash
playwright install
```

## Usage

Run the script:
```bash
python linkedin_captcha_solver.py
```

## Features

- Automated LinkedIn login
- CAPTCHA detection and handling
- Human-like behavior simulation
- Configurable timeouts and delays
- Error handling and retry logic

## Important Notes

- The script runs in non-headless mode to allow visual monitoring
- CAPTCHA solving service integration needs to be implemented
- Current version includes placeholder for CAPTCHA solver response
- Use responsibly and in accordance with LinkedIn's terms of service

## Security

- Credentials should be stored in environment variables in production
- Do not share or commit credentials
- Use rate limiting and delays to avoid detection 