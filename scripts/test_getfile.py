import asyncio
import json
import sys
from pathlib import Path

import aiohttp
from sqlalchemy import select

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from shared.config import get_settings
from shared.db import SessionLocal
from db.models import Form


async def main(form_id: int) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        row = (await session.execute(select(Form).where(Form.id == form_id))).scalar_one_or_none()
    if not row:
        print({"error": "form_not_found", "form_id": form_id})
        return
    file_id = (row.repost_photo_file_id or "").strip()
    if not file_id:
        print({"error": "no_file_id", "form_id": form_id})
        return
    token = settings.BOT1_TOKEN
    if not token:
        print({"error": "no_bot1_token"})
        return

    api_base = f"https://api.telegram.org/bot{token}"
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{api_base}/getFile", params={"file_id": file_id}) as r1:
            text = await r1.text()
            print("getFile:", r1.status, text[:500])
            if r1.status != 200:
                return
            data = await r1.json(content_type=None)
            fp = data.get("result", {}).get("file_path")
            if not fp:
                print({"error": "no_file_path", "payload": data})
                return
        file_url = f"https://api.telegram.org/file/bot{token}/{fp}"
        async with http.get(file_url) as r2:
            print("download:", r2.status, r2.headers.get("Content-Type"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_getfile.py <form_id>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1])))


