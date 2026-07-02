# Vercel Hosting Note

This calendar can be opened on Vercel as a static PWA, but shared leave changes will not sync between users unless the backend is converted to use a Vercel-supported database or storage service.

The current shared version uses `outputs/leave-calendar-server.py`, which is a long-running Python server with a JSON data file. That fits Render with a persistent disk better than Vercel.

For Vercel with shared changes, convert the `/api/state` and `/api/confirm` endpoints to Vercel serverless functions and store the calendar state in Vercel Postgres, Redis/KV, or another database.
