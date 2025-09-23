# YATS Dashboard

A comprehensive dashboard for the YATS (Yet Another Ticket System) Django application, providing analytics and calendar/timeline functionality.

## Features

### Analytics Dashboard
- **Key Metrics**: Total tickets, open tickets, closed tickets, recent activity
- **Interactive Charts**: Ticket activity over time, tickets by type/priority
- **Organization Analytics**: Top organizations by ticket count
- **Resolution Time**: Average ticket resolution time
- **Date Range Selection**: Filter analytics by time period (7, 30, 90, 365 days)

### Calendar & Timeline
- **Timeline View**: Visual timeline of ticket creation and updates
- **Calendar View**: Calendar-based view of scheduled tickets
- **Scheduled Tickets**: View tickets with specific show_start dates
- **Recently Closed**: List of recently closed tickets with close dates

## Installation

1. The dashboard is automatically included when you add `'dashboard'` to your `INSTALLED_APPS`
2. Include the dashboard URLs in your main `urls.py`:
   ```python
   re_path(r'^dashboard/', include('dashboard.urls')),
   ```
3. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

## Usage

### Accessing the Dashboard
- Navigate to `/dashboard/` in your browser
- The dashboard link is automatically added to the main navigation menu

### Dashboard Views
- **Home** (`/dashboard/`): Overview with key metrics and navigation cards
- **Analytics** (`/dashboard/analytics/`): Detailed analytics with charts
- **Calendar** (`/dashboard/calendar/`): Calendar and timeline views

### API Endpoints
- `/dashboard/api/analytics/`: JSON data for analytics charts
- `/dashboard/api/timeline/`: JSON data for timeline view

## Customization

### Adding New Metrics
1. Modify `dashboard/views.py` to add new analytics calculations
2. Update the templates to display new metrics
3. Add corresponding JavaScript for interactive features

### Styling
- CSS files are located in `dashboard/static/dashboard/css/`
- The dashboard uses a modern, responsive design
- Colors and styling can be customized in `dashboard.css`

### Charts
- Uses Chart.js for interactive charts
- Charts are automatically responsive
- Data is loaded via AJAX for real-time updates

## Dependencies

- Django (already included in YATS)
- Chart.js (loaded from CDN)
- Font Awesome (already included in YATS)
- Bootstrap (already included in YATS)

## Technical Details

### Models Used
- `tickets`: Main ticket model
- `ticket_type`: Ticket type classification
- `ticket_priority`: Ticket priority levels
- `organisation`: Customer organizations
- `ticket_flow`: Ticket workflow states

### Key Features
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Data**: AJAX-powered updates
- **Performance Optimized**: Efficient database queries
- **User-friendly**: Intuitive navigation and clear visualizations

## Future Enhancements

Potential improvements could include:
- Export functionality for analytics data
- Custom date range selection
- Advanced filtering options
- Real-time notifications
- Integration with external calendar systems
- Advanced reporting features
