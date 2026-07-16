import json
from datetime import datetime


async def update_job(pool, job_id: str, **kwargs):
    kwargs.setdefault("updated_at", datetime.utcnow())
    fields = []
    values = []
    i = 1
    for k, v in kwargs.items():
        if k == "result" and isinstance(v, dict):
            fields.append(f"{k} = ${i}::jsonb")
            values.append(json.dumps(v))
        else:
            fields.append(f"{k} = ${i}")
            values.append(v)
        i += 1
    values.append(job_id)
    await pool.execute(
        f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id = ${i}",
        *values,
    )
