import asyncio
from pathlib import Path
import sys
from sqlalchemy import select

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from shared.db import SessionLocal
from db.models import Form


async def main() -> None:
    async with SessionLocal() as session:
        rows = (await session.execute(select(Form))).scalars().all()
    total = len(rows)
    with_photo = [f for f in rows if (getattr(f, "repost_photo_file_id", "") or "").strip()]
    sample = [(f.id, f.repost_photo_file_id) for f in with_photo[:10]]
    print({
        "total_forms": total,
        "with_photo": len(with_photo),
        "sample": sample,
    })


if __name__ == "__main__":
    asyncio.run(main())


