import os
import json
import sqlite3

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

config_dir = os.path.abspath("config")
conn = sqlite3.connect(f"{config_dir}/emails.db")
# If modifying these scopes, delete the file token.json
SCOPES = ["https://mail.google.com/"]


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

service = get_gmail_service()

def fetch_rules():
    with open(f"{config_dir}/rules.json", 'r') as f:
        data = json.load(f)
    return data


def generate_sql_query(root_predicate, rules):
    # Define the base SQL query
    base_query = "SELECT * FROM emails"

    # Generate the WHERE clause based on the rules
    conditions = []
    for rule in rules:
        field = rule["field"]
        predicate = rule["predicate"]
        value = rule["value"]

        # Handle string type fields
        if predicate in ["contains", "does not contain", "equals", "does not equal"]:
            if predicate == "contains":
                condition = f"{field} LIKE '%{value}%'"
            elif predicate == "does not contain":
                condition = f"{field} NOT LIKE '%{value}%'"
            elif predicate == "equals":
                condition = f"{field} = '{value}'"
            elif predicate == "does not equal":
                condition = f"{field} != '{value}'"
        # Handle date type field (Received) - Less than / Greater than for days / months
        elif predicate in ["less than", "greater than"]:
            operator = "<" if predicate == "less than" else ">"
            condition = f"{field} {operator} DATE('now', '-{value} days')"
        else:
            raise ValueError(f"Invalid predicate: {predicate}")
        conditions.append(condition)

    # Join conditions based on the root_predicate
    if root_predicate == "ALL":
        where_clause = " AND ".join(conditions)
    elif root_predicate == "ANY":
        where_clause = " OR ".join(conditions)
    else:
        raise ValueError("Invalid root_predicate. Use 'ALL' or 'ANY'.")
    # Concatenate the base query, SET clause, and WHERE clause
    full_query = f"{base_query} WHERE {where_clause}"
    return full_query


def apply_actions(emails, actions):
    email_ids = [email[0] for email in emails]
    for action in actions:
        if(action["action"] == 'Mark as' and action["field"] == "READ"):
            # Mark the email as read
            service.users().messages().batchModify( userId='me', body={'ids': email_ids, 'removeLabelIds': ['UNREAD']}).execute()
        elif(action["action"] == 'Mark as' and action["field"] == "UNREAD"):
            # Mark the email as unread
            service.users().messages().batchModify( userId='me', body={'ids': email_ids, 'addLabelIds': ['UNREAD']}).execute()
        elif(action["action"] == 'Move Message'):
            # Move the email to the 'IMPORTANT' mailbox
            service.users().messages().batchModify( userId='me', body={'ids': email_ids, 'addLabelIds': [action["field"]]}).execute()


def run_query(sql_query):
    cursor = conn.cursor()
    cursor.execute(sql_query)
    emails = cursor.fetchall()
    return emails


def apply_rules(rules):
    for rule in rules:
        print(f"Applying rule - {rule['id']}")
        sql_query = generate_sql_query(rule['root_predicate'], rule["rules"])
        print(f"Query - {sql_query}")
        emails = run_query(sql_query)
        apply_actions(emails, rule["actions"])


def main():
    rules = fetch_rules()
    apply_rules(rules)


if __name__ == '__main__':
    main()
    conn.close()
