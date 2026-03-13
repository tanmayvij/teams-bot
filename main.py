from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

import os
from db import Database
import agent
import teams_api
import time
from datetime import datetime, timedelta, timezone

chat_ids = os.getenv("TEAMS_CHAT_IDS", "").split(",")  # Comma-separated chat IDs

def main():
    db = Database()

    for chat_id in chat_ids:
        db_messages = db.list_last_messages(chat_id=chat_id, limit=10)
        teams_messages = teams_api.fetch_latest_messages(chat_id=chat_id)

        # Check if teams contains messages not present in DB
        db_message_ids = set(m["message_id"] for m in db_messages)
        new_messages = [m for m in teams_messages if m["id"] not in db_message_ids]

        if new_messages:
            print(f"New messages found for chat {chat_id}: {len(new_messages)}")
            
            llm_context = [
                {"role": m["role"], "content": m.get("content", "")}
                for m in db_messages[-5:] + new_messages
            ]
            llm_context[-1]["content"] += f"\n\nCurrent time: {datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%H:%M:%S")}"  # Append current time to the last message content
            
            response = agent.generate_response(llm_context)
            
            created_msg = teams_api.send_message_to_teams_chat(chat_id, response)
            
            new_messages.append({
                "id": created_msg["id"],
                "chat_id": chat_id,
                "timestamp": datetime.strptime(created_msg["createdDateTime"], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp(),
                "role": "assistant",
                "content": response
            })

            db.append_messages([
                {
                    "message_id": m["id"],
                    "chat_id": chat_id,
                    "timestamp": datetime.strptime(m["createdDateTime"], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp(),
                    "role": m["role"],
                    "content": m.get("content", "")
                }
                for m in new_messages
            ])
        else:
            print(f"No new messages for chat {chat_id}")


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(10)