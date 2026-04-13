# MiniStack Multi-Cloud Dashboard

A real-time, interactive dashboard to monitor the status of all emulated cloud services across AWS, Azure, Huawei Cloud, and GCP.

## Accessing the Dashboard

Once MiniStack is running, open your browser and navigate to:

```
http://localhost:4566/
http://localhost:4566/dashboard
http://localhost:4566/_ministack/dashboard
```

## Features

### 📊 Real-Time Status
- **102 services** across 4 cloud providers displayed with live status
- Auto-refreshes every **30 seconds**
- Manual refresh button with animated loading indicator

### 🌩️ Multi-Cloud Support
| Cloud | Services | Color |
|-------|----------|-------|
| **AWS** | 56 | 🟠 Orange |
| **Azure** | 29 | 🔵 Blue |
| **Huawei Cloud** | 17 | 🔴 Red |
| **GCP** | 14 | 🔵 Google Blue |

### 🔍 Search & Filter
- **Search bar** — instantly filter services by name or key
- **Tab navigation** — switch between cloud providers
- **Summary cards** — quick overview per provider with direct links

### 📱 Responsive Design
- Works on desktop, tablet, and mobile
- Dark theme optimized for developer workflows
- Smooth hover animations and transitions

## Architecture

```
Dashboard (HTML/JS/CSS)
    │
    ├── Fetches: /_ministack/health  (AWS services)
    ├── Fetches: /_azure/health      (Azure services)
    ├── Fetches: /_huawei/health     (Huawei services)
    └── Fetches: /_gcp/health        (GCP services)
         │
         └── Consolidated view with status badges
```

## Files

| File | Description |
|------|-------------|
| `ministack/static/dashboard.html` | Dashboard UI (Bootstrap 5 + Font Awesome) |
| `ministack/app.py` | Route handler serving the dashboard |

## Technologies

- **Bootstrap 5.3** — Responsive grid and components
- **Font Awesome 6.5** — Cloud provider and service icons
- **Vanilla JS** — No frameworks, fast loading
- **CSS Variables** — Customizable dark theme

## Customization

### Adding a New Service to Dashboard

1. Add the service key to `serviceIcons` in `dashboard.html`:
   ```javascript
   my_new_service: { icon: 'fas fa-star', label: 'My Service' },
   ```

2. The service will automatically appear in the dashboard once it's registered in `SERVICE_HANDLERS` in `app.py`.

### Changing Theme Colors

Edit the CSS variables in `<style>` section:
```css
:root {
    --accent-aws: #ff9900;    /* AWS orange */
    --accent-azure: #0078d4;  /* Azure blue */
    --accent-huawei: #e6320a; /* Huawei red */
    --accent-gcp: #4285f4;    /* GCP blue */
}
```

## Screenshots

The dashboard displays:
- **Top bar** — Total service count per cloud provider
- **Summary cards** — Quick stats with "View Services" buttons
- **Service grid** — Cards for each service with icon, name, and status badge
- **Search field** — Real-time filtering

## API Endpoints Used

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/_ministack/health` | GET | AWS service status JSON |
| `/_azure/health` | GET | Azure service status JSON |
| `/_huawei/health` | GET | Huawei service status JSON |
| `/_gcp/health` | GET | GCP service status JSON |

## Development

To modify the dashboard locally:

1. Edit `ministack/static/dashboard.html`
2. Rebuild Docker: `docker compose up -d --build`
3. Refresh browser: `http://localhost:4566/dashboard`

No hot reload — changes require container rebuild.
