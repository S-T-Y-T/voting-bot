import json
import os

DB_FILE = "votes.json"

async def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

async def export_votes():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def user_voted(user_id):
    votes = await export_votes()
    return any(v["id"] == user_id for v in votes)

async def save_vote(user_id, phone, vote):
    votes = await export_votes()
    votes.append({"id": user_id, "phone": phone, "vote": vote})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, ensure_ascii=False, indent=2)

async def get_votes():
    votes = await export_votes()
    options_count = {}
    for v in votes:
        options_count[v["vote"]] = options_count.get(v["vote"], 0) + 1
    result = [(i, options_count.get(i, 0)) for i in range(1, 11)]  # 10 участков
    return result