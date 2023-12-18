# HF-GmailSearch
Interview assesment repository for Happy Fox

# Project Setup

## Installation Steps

### Google Auth

1. Follow the [Google Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python) to setup OAuth for your account and download credentials file

2. Install the `google-auth` library using pip:

    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```

3. Make sure to download the Google client secret file (`client_secret.json`) and save it inside the `config` folder.


### BeautifulSoup

Install the `beautifulsoup4` library using pip:

```bash
pip install beautifulsoup4
```

# Getting Started

1. Run the script to fetch emails:

    ```bash
    python src/fetch-emails.py
    ```

2. Edit the rules in the config/rules.json file.
3. Run the script to apply rules:
    ```bash
    python src/apply-rules.py
    ```

