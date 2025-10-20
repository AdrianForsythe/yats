// Dashboard JavaScript functionality

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Add any global dashboard initialization here
    console.log('Dashboard initialized');
}

// Utility function to format numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Utility function to format time duration
function formatDuration(hours) {
    if (hours < 24) {
        return hours.toFixed(1) + 'h';
    } else {
        const days = Math.floor(hours / 24);
        const remainingHours = hours % 24;
        if (remainingHours > 0) {
            return days + 'd ' + remainingHours.toFixed(1) + 'h';
        }
        return days + 'd';
    }
}

// Function to update dashboard stats
function updateDashboardStats(data) {
    const elements = {
        'total-tickets': data.total_tickets,
        'open-tickets': data.open_tickets,
        'closed-tickets': data.closed_tickets,
        'recent-activity': data.recent_tickets
    };
    
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = formatNumber(elements[id]);
        }
    });
}

// Function to animate number counting
function animateNumber(element, target, duration = 1000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current).toString();
    }, 16);
}

// Function to load and display recent activity
function loadRecentActivity() {
    fetch('/dashboard/api/timeline/')
        .then(response => response.json())
        .then(data => {
            displayRecentActivity(data.tickets.slice(0, 10)); // Show only 10 most recent
        })
        .catch(error => {
            console.error('Error loading recent activity:', error);
            document.getElementById('recent-activity-list').innerHTML = 
                '<div class="error">Error loading recent activity</div>';
        });
}

// Function to display recent activity
function displayRecentActivity(tickets) {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;
    
    if (tickets.length === 0) {
        container.innerHTML = '<div class="no-activity">No recent activity</div>';
        return;
    }
    
    const html = tickets.map(ticket => {
        const date = new Date(ticket.created);
        const statusClass = ticket.closed_status ? 'closed' : 'open';
        const statusText = ticket.closed_status ? 'Closed' : 'Open';
        
        return `
            <div class="activity-item ${statusClass}">
                <div class="activity-icon">
                    <i class="fas fa-ticket-alt"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">
                        <a href="/tickets/view/${ticket.id}/">#${ticket.id} - ${ticket.caption}</a>
                    </div>
                    <div class="activity-meta">
                        <span class="activity-status">${statusText}</span>
                        <span class="activity-date">${date.toLocaleDateString()}</span>
                        ${ticket.type ? `<span class="activity-type">${ticket.type}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

// Function to handle dashboard data loading
function loadDashboardData() {
    // Load basic analytics data
    fetch('/dashboard/api/analytics/')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
        });
    
    // Load recent activity
    loadRecentActivity();
}

// Export functions for use in other scripts
window.DashboardUtils = {
    formatNumber,
    formatDuration,
    updateDashboardStats,
    loadDashboardData,
    loadRecentActivity
};
