import os
import base64
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import email
import logging

# Set up logging
logging.basicConfig(filename='email_print_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Function to save email content to a file
def save_email(content, email_id):
    try:
        # Create a file to hold the email content
        with open(f"email_content_{email_id}.txt", "w", encoding="utf-8") as file:
            file.write(content)
        return True
    except Exception as e:
        logging.error(f"Saving email failed: {str(e)}")
        return False

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate(account_email):
    creds = None
    token_file = f'token_{account_email}.json'
    # The file token_{account_email}.json stores the user's access and refresh tokens
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_emails(service, account_email):
    messages = []
    try:
        results = service.users().messages().list(userId=account_email, maxResults=100).execute()
        messages = results.get('messages', [])
    except Exception as e:
        logging.error(f"Failed to fetch emails: {str(e)}")
    return messages

def handle_rate_limiting(e, attempt):
    if e.resp.status in [403, 429]:
        sleep_time = (2 ** attempt) + (random.randint(0, 1000) / 1000)
        logging.warning(f"Rate limit exceeded. Sleeping for {sleep_time} seconds before retrying...")
        time.sleep(sleep_time)
        return True
    return False

def main():
    account_email = os.getenv('ACCOUNT_EMAIL')
    fetch_interval = int(os.getenv('FETCH_INTERVAL', 300))  # Default to 300 seconds (5 minutes) if not set

    if not account_email:
        logging.error("Environment variable ACCOUNT_EMAIL must be set")
        return

    creds = authenticate(account_email)
    service = build('gmail', 'v1', credentials=creds)

    while True:
        logging.info("Fetching emails...")
        messages = fetch_emails(service, account_email)

        if not messages:
            logging.info("No messages found.")
        else:
            logging.info(f"Found {len(messages)} emails. Starting to process...")

            for i, msg in enumerate(messages):
                attempt = 0
                success = False
                while not success and attempt < 5:
                    try:
                        msg = service.users().messages().get(userId=account_email, id=msg['id']).execute()
                        email_data = msg['payload']
                        headers = email_data['headers']

                        subject = ''
                        sender = ''
                        for d in headers:
                            if d['name'] == 'Subject':
                                subject = d['value']
                            if d['name'] == 'From':
                                sender = d['value']

                        logging.info(f"Processing email {i+1}/{len(messages)}: From: {sender}, Subject: {subject}")

                        if 'parts' in email_data['body']:
                            for part in email_data['body']['parts']:
                                if part['mimeType'] == 'text/plain':
                                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                    if save_email(body, msg['id']):
                                        service.users().messages().delete(userId=account_email, id=msg['id']).execute()
                                        logging.info(f"Deleted email {i+1}/{len(messages)}: From: {sender}, Subject: {subject}")
                                    else:
                                        logging.error(f"Failed to save email {i+1}/{len(messages)}: From: {sender}, Subject: {subject}")
                        else:
                            body = base64.urlsafe_b64decode(email_data['body']['data']).decode('utf-8')
                            if save_email(body, msg['id']):
                                service.users().messages().delete(userId=account_email, id=msg['id']).execute()
                                logging.info(f"Deleted email {i+1}/{len(messages)}: From: {sender}, Subject: {subject}")
                            else:
                                logging.error(f"Failed to save email {i+1}/{len(messages)}: From: {sender}, Subject: {subject}")

                        success = True
                    except Exception as e:
                        logging.error(f"Failed to process email {i+1}/{len(messages)}: {str(e)}")
                        if handle_rate_limiting(e, attempt):
                            attempt += 1
                        else:
                            break

        logging.info(f"Sleeping for {fetch_interval} seconds...")
        time.sleep(fetch_interval)

if __name__ == '__main__':
    main()
