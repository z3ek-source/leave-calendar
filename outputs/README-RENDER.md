# Render Setup

Use **Web Service**, not Static Site. The app needs a backend because all users must share one calendar.

Recommended settings:

- Runtime: Python
- Build Command: leave blank
- Start Command: `python3 outputs/leave-calendar-server.py`
- Environment Variable: `DATA_DIR=/var/data`
- Persistent Disk Mount Path: `/var/data`
- Disk Size: `1 GB`

After deployment, open:

`https://your-render-service-name.onrender.com/leave-application-calendar.html`

Use Safari's Share button, then **Add to Home Screen**.
