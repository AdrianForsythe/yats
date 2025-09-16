# YATS Local Development Setup

This guide will help you set up YATS for local development using `uv` and Python 3.11.

## Prerequisites

- Python 3.11
- `uv` package manager (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Quick Start

1. **Clone and setup the project:**
   ```bash
   git clone <your-fork-url>
   cd yats
   ```

2. **Initialize the environment:**
   ```bash
   uv init --python 3.11
   uv add --requirements requirements.txt
   ```

3. **Run the development server:**
   ```bash
   python dev_server.py
   ```

4. **Access the application:**
   - Main application: http://localhost:8000
   - Admin interface: http://localhost:8000/admin
   - Username: `admin`
   - Password: `admin`

## Project Structure

```
yats/
├── data/                    # Local development data
│   ├── db/                 # SQLite database
│   ├── files/              # Uploaded files
│   ├── logs/               # Application logs
│   ├── static/             # Static files
│   └── index/              # Search index
├── modules/                # YATS modules
│   ├── yats/              # Main YATS application
│   ├── bootstrap_toolkit/ # UI components
│   ├── simple_sso/        # SSO functionality
│   └── graph/             # Graph visualization
├── sites/                  # Django projects
│   ├── web/               # Main web application
│   └── caldav/            # CalDAV server
└── dev_server.py          # Development server script
```

## Configuration

### Local Development Settings

The project uses `sites/web/web/settings_local.py` for local development, which:

- Uses SQLite database in `data/db/yats_dev.sqlite`
- Stores uploaded files in `data/files/`
- Logs to `data/logs/`
- Uses dummy cache (no memcache required)
- Disables virus scanning
- Disables CalDAV functionality (due to Django 5.x compatibility)

### Environment Variables

The development server automatically sets:
- `PYTHONPATH` to include the `modules/` directory
- `DJANGO_SETTINGS_MODULE` to `web.settings_local`

## Available Commands

### Using the development script:
```bash
python dev_server.py
```

### Using Django management commands:
```bash
cd sites/web
PYTHONPATH=../../modules:../.. uv run python manage.py <command> --settings=web.settings_local
```

### Common Django commands:
```bash
# Run migrations
uv run python manage.py migrate --settings=web.settings_local

# Create superuser
uv run python manage.py createsuperuser --settings=web.settings_local

# Collect static files
uv run python manage.py collectstatic --settings=web.settings_local

# Run tests
uv run python manage.py test --settings=web.settings_local
```

## Features Available

✅ **Working:**
- User authentication and authorization
- Ticket management
- File uploads
- Search functionality
- Admin interface
- Background tasks
- Markdown support
- Bootstrap UI

⚠️ **Temporarily Disabled:**
- CalDAV integration (due to Django 5.x compatibility issues)
- Virus scanning (disabled for development)
- Memcache (using dummy cache)

## Troubleshooting

### Database Issues
If you encounter database errors, ensure the `data/db/` directory exists:
```bash
mkdir -p data/db
```

### Module Import Errors
Make sure the `PYTHONPATH` includes the modules directory:
```bash
export PYTHONPATH=/path/to/yats/modules:/path/to/yats:$PYTHONPATH
```

### Port Already in Use
If port 8000 is already in use, you can specify a different port:
```bash
cd sites/web
PYTHONPATH=../../modules:../.. uv run python manage.py runserver --settings=web.settings_local 0.0.0.0:8001
```

## Development Notes

- The project uses Django 5.x with Python 3.11
- All dependencies are managed through `uv`
- The database is SQLite for easy development
- Static files are served directly by Django in development mode
- Logs are written to `data/logs/django_request.log`

## Contributing

1. Make your changes
2. Test using the development server
3. Run tests: `uv run python manage.py test --settings=web.settings_local`
4. Submit a pull request

## Original Project

This is a fork of [YATS](https://github.com/mediafactory/yats) - Yet Another Trouble Ticketing System.

