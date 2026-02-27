// dashboard.js

// Function to update the current date and time on the dashboard
function updateDateTime() {
    const now = new Date();
    const formattedDate = now.toISOString().slice(0, 19).replace('T', ' ');
    document.getElementById('currentDateTime').innerText = `Current Date and Time: ${formattedDate}`;
}

// Function to initialize and update dashboard interactivity
function initializeDashboard() {
    updateDateTime();
    setInterval(updateDateTime, 1000); // Update every second
}

window.onload = initializeDashboard;
