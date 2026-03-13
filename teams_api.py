import os
import time
import requests
from db import Database

db = Database()


_TOKEN_URL = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token"

_client_id = os.getenv("AZURE_CLIENT_ID")
_client_secret = os.getenv("AZURE_CLIENT_SECRET")


def get_valid_access_token():
    """
    Fetch tokens from DB, refresh if expired, update DB, and return valid access token.
    
    Args:
        None
        
    Returns:
        str: valid access token
    """

    # Fetch from DB
    token_data = db.fetch_access_token()

    access_token = token_data.get("accessToken") if token_data else None
    access_token_expiry = token_data.get("accessTokenExpiry") if token_data else 0
    refresh_token = token_data.get("refreshToken") if token_data else None

    current_time = int(time.time())

    # If token still valid return it
    if access_token_expiry > current_time:
        return access_token

    # Refresh token
    payload = {
        "client_id": _client_id,
        "client_secret": _client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/.default"
    }

    response = requests.post(_TOKEN_URL, data=payload)
    response.raise_for_status()

    token_response = response.json()

    new_access_token = token_response["access_token"]
    new_refresh_token = token_response.get("refresh_token", refresh_token)
    expires_in = token_response["expires_in"]

    new_expiry = int(time.time()) + expires_in - 30 # Subtract 30 seconds to account for any delays

    # Update DB
    db.update_access_token(
        access_token=new_access_token,
        access_token_expiry=new_expiry,
        refresh_token=new_refresh_token
    )

    return new_access_token

def send_message_to_teams_chat(chat_id, message):
    """
    Send a message to a Microsoft Teams chat using Graph API.
    
    Args:
        chat_id (str): The ID of the Teams chat to send the message to
        message (str): The message content to send
    """
    access_token = get_valid_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    message_payload = {
        "body": {
            "contentType": "text",
            "content": message
        }
    }

    graph_url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
    response = requests.post(graph_url, headers=headers, json=message_payload)
    response.raise_for_status()

    return {
        "id": response.json().get("id"),
        "createdDateTime": response.json().get("createdDateTime"),
    }

def fetch_latest_messages(chat_id):
    """
    Fetch latest 10 messages for a given MS Teams chat ID.

    Args:
        chat_id (str): Teams chat ID

    Returns:
        list[dict]: List of messages with id, chatId, and body
    """

    access_token = get_valid_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    results = []

    url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages?$top=10"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    for msg in data.get("value", []):
        if msg.get("body", {}).get("contentType") == "html" and msg.get("body", {}).get("content").startswith("<p>"):
            # Convert to text if not already
            msg["body"]["content"] = msg["body"]["content"].replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")

        if not msg.get("body", {}).get("content"):
            continue

        results.append({
            "id": msg.get("id"),
            "chatId": chat_id,
            "createdDateTime": msg.get("createdDateTime"),
            "role": "user" if msg.get("from", {}).get("user", {}).get("id") == os.getenv("SENDER_ID") else "assistant",
            "content": msg.get("body", {}).get("content", "")
        })

    return sorted(results, key=lambda x: x["createdDateTime"], reverse=True)[:10]