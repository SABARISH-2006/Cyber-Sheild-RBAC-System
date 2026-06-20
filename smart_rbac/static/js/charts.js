document.addEventListener("DOMContentLoaded", function () {
    // Render charts only if canvas elements exist
    const roleCtx = document.getElementById("roleDistributionChart");
    const riskCtx = document.getElementById("riskDistributionChart");
    const actionCtx = document.getElementById("actionTrendChart");
    const alertCtx = document.getElementById("alertDistributionChart");

    if (!roleCtx && !riskCtx && !actionCtx && !alertCtx) {
        return; // Not on the dashboard or analytics page
    }

    // Load metrics from telemetry API
    fetch("/api/telemetry/charts")
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then(data => {
            if (roleCtx) {
                renderRoleDistribution(roleCtx, data.role_distribution);
            }
            if (riskCtx) {
                renderRiskDistribution(riskCtx, data.risk_distribution);
            }
            if (actionCtx) {
                renderActionTrend(actionCtx, data.action_distribution);
            }
            if (alertCtx) {
                renderAlertDistribution(alertCtx, data.alert_distribution);
            }
        })
        .catch(error => {
            console.error("Error loading telemetry charts:", error);
        });
});

function renderRoleDistribution(ctx, data) {
    const labels = Object.keys(data);
    const values = Object.values(data);

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#3b82f6', // Admin - Blue
                    '#10b981', // Manager - Emerald
                    '#f59e0b', // Employee - Amber
                    '#8b5cf6', // Auditor - Violet
                    '#64748b'  // Other - Slate
                ],
                borderWidth: 1,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 12 }
                    }
                }
            }
        }
    });
}

function renderRiskDistribution(ctx, data) {
    const labels = ['Low', 'Medium', 'High'];
    const values = [data.Low || 0, data.Medium || 0, data.High || 0];

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Login Evaluations',
                data: values,
                backgroundColor: [
                    'rgba(16, 185, 129, 0.65)',  // Low - Emerald
                    'rgba(245, 158, 11, 0.65)',  // Medium - Amber
                    'rgba(239, 68, 68, 0.65)'    // High - Rose
                ],
                borderColor: [
                    '#10b981',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                y: {
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' }, precision: 0 }
                }
            }
        }
    });
}

function renderActionTrend(ctx, data) {
    const labels = Object.keys(data);
    const values = Object.values(data);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Frequency',
                data: values,
                backgroundColor: 'rgba(59, 130, 246, 0.65)',
                borderColor: '#3b82f6',
                borderWidth: 1.5
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' }, precision: 0 }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                }
            }
        }
    });
}

function renderAlertDistribution(ctx, data) {
    const labels = Object.keys(data);
    const values = Object.values(data);

    new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(239, 68, 68, 0.65)',  // Brute Force
                    'rgba(245, 158, 11, 0.65)',  // Time Anomaly
                    'rgba(59, 130, 246, 0.65)',  // Suspect Logins
                    'rgba(16, 185, 129, 0.65)'
                ],
                borderColor: '#1e293b',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 11 }
                    }
                }
            },
            scales: {
                r: {
                    grid: { color: '#334155' },
                    angleLines: { color: '#334155' },
                    ticks: { display: false }
                }
            }
        }
    });
}
