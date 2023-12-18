import os.path
import sqlite3
import json
from bs4 import BeautifulSoup
from datetime import datetime
import base64
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

config_dir = os.path.abspath("config")
conn = sqlite3.connect(f"{config_dir}/emails.db")
# If modifying these scopes, delete the file token.json
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAILBOX_TYPES = ['INBOX', 'STARRED']

def convert_string_to_datetime(date_string):
    # Remove any additional timezone information, e.g., (IST), (PST), etc.
    date_string_cleaned = date_string.split('(')[0].strip()

    # Parse the cleaned date string
    date_object =  datetime.strptime(date_string_cleaned, '%a, %d %b %Y %H:%M:%S %z')
    date_string = date_object.strftime("%Y-%m-%d %H:%M:%S.%f")
    return date_string


def get_google_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(f"{config_dir}/token.json"):
        creds = Credentials.from_authorized_user_file(f"{config_dir}/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                f"{config_dir}/client_secret.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(f"{config_dir}/token.json", "w") as token:
                token.write(creds.to_json())
    return creds


def get_gmail_service():
    creds = get_google_creds()
    service = build("gmail", "v1", credentials=creds)
    return service


def get_emails(query, maxResults = 10):
    try:
        print(f"Getting emails based on the query - {query}")
        mails = []
        service = get_gmail_service()
        response = service.users().messages().list(userId='me', q=query, maxResults=maxResults).execute()
        messages = response.get('messages', [])
        if not messages:
            print("No messages found.")
            return []
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute() 
            # Use try-except to avoid any Errors 
            try:
                id = txt['id']
                labels = txt['labelIds']
                payload = txt['payload']
                headers = payload['headers']
                
                status = 'UNREAD' if 'UNREAD' in labels else 'READ'
                mailbox = next((type for type in MAILBOX_TYPES if type in labels), None)

                for d in headers:
                    if d['name'] == 'Subject':
                        subject = d['value']
                    if d['name'] == 'From': 
                        sender = re.search(r'[\w\.-]+@[\w\.-]+', d['value']).group() if re.search(r'[\w\.-]+@[\w\.-]+', d['value']) else None
                    if d['name'] == 'Date': 
                        date = convert_string_to_datetime(d['value'])

                # The Body of the message is in Encrypted format. So, we have to decode it. 
                # Get the data and decode it with base 64 decoder. 
                parts = payload.get('parts')[0]
                data = parts['body']['data'] 
                data = data.replace("-","+").replace("_","/") 
                decoded_data = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                # decoded_data = base64.b64decode(data) 

                # Now, the data obtained is in lxml. So, we will parse  
                # it with BeautifulSoup library 
                # soup = BeautifulSoup(decoded_data , "lxml") 
                # body = soup.body()
                mails.append({
                    "id": id,
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "body": decoded_data,
                    "status": status,
                    "mailbox": mailbox
                })
            except Exception as ex: 
                print(f"Exception - {ex}")
                pass
        return mails
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def store_emails(emails):
    cursor = conn.cursor()
    # Iterate through the list of emails and insert them into the 'emails' table
    for email in emails:
        try:
            cursor.execute('''
                INSERT INTO emails (id, subject, date, sender, body, status, mailbox)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                email.get('id', None),  # Assuming 'id' is included in the email dictionary
                email.get('subject', ''),
                email.get('date', ''),
                email.get('from', ''),
                email.get('body', ''),
                email.get('status', ''),
                email.get('mailbox', ''),
            ))
        except Exception as ex:
            print(ex)
            continue
    conn.commit()


def create_table():
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            date TIMESTAMP,
            body TEXT,
            status TEXT,
            mailbox TEXT
        )
    ''')
    conn.commit()


def main():
    create_table()
    emails = get_emails('in:inbox')
    store_emails(emails)
    conn.close()

if __name__ == '__main__':
    main()