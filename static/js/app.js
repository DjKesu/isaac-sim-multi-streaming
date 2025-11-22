// Isaac Sim Orchestration Dashboard

const API_BASE = '';
const REFRESH_INTERVAL = 5000; // 5 seconds

let refreshTimer = null;
let instances = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Isaac Sim Dashboard Initialized');
    
    // Setup event listeners
    document.getElementById('refresh-btn').addEventListener('click', refreshInstances);
    document.getElementById('cleanup-all-btn').addEventListener('click', cleanupAll);
    
    // Setup modal
    const modal = document.getElementById('logs-modal');
    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
    
    // Initial load
    checkHealth();
    refreshInstances();
    
    // Start auto-refresh
    startAutoRefresh();
});

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        const indicator = document.getElementById('status-indicator');
        if (data.status === 'healthy') {
            indicator.textContent = 'Connected';
            indicator.className = 'status-badge healthy';
        } else {
            indicator.textContent = 'Disconnected';
            indicator.className = 'status-badge unhealthy';
        }
    } catch (error) {
        console.error('Health check failed:', error);
        const indicator = document.getElementById('status-indicator');
        indicator.textContent = 'Error';
        indicator.className = 'status-badge unhealthy';
    }
}

// Refresh instances data
async function refreshInstances() {
    try {
        const response = await fetch(`${API_BASE}/api/instances`);
        const data = await response.json();
        instances = data.instances;
        renderInstances();
        checkHealth();
    } catch (error) {
        console.error('Failed to fetch instances:', error);
        showNotification('Failed to fetch instances', 'error');
    }
}

// Render instances grid
function renderInstances() {
    const grid = document.getElementById('instances-grid');
    grid.innerHTML = '';
    
    instances.forEach(instance => {
        const card = createInstanceCard(instance);
        grid.appendChild(card);
    });
}

// Create instance card HTML
function createInstanceCard(instance) {
    const card = document.createElement('div');
    card.className = 'instance-card';
    card.id = `instance-${instance.instance_id}`;
    
    const isRunning = instance.status === 'running';
    const statusClass = instance.status.toLowerCase().replace(' ', '_');
    
    card.innerHTML = `
        <div class="instance-header">
            <div class="instance-title">
                <h3>Instance ${instance.instance_id}</h3>
                <span class="instance-status ${statusClass}">${instance.status}</span>
            </div>
            <div class="instance-controls">
                <button class="btn btn-primary" onclick="startInstance(${instance.instance_id})" 
                        ${isRunning ? 'disabled' : ''}>
                    Start
                </button>
                <button class="btn btn-danger" onclick="stopInstance(${instance.instance_id})"
                        ${!isRunning ? 'disabled' : ''}>
                    Stop
                </button>
                <button class="btn btn-warning" onclick="restartInstance(${instance.instance_id})"
                        ${!isRunning ? 'disabled' : ''}>
                    Restart
                </button>
                <button class="btn btn-info" onclick="showLogs(${instance.instance_id})">
                    Logs
                </button>
            </div>
        </div>
        <div class="instance-body">
            <div class="instance-info">
                <div class="info-item">
                    <span class="info-label">HTTP Port</span>
                    <span class="info-value">${instance.ports.http}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">WebRTC Port</span>
                    <span class="info-value">${instance.ports.webrtc}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Native Port</span>
                    <span class="info-value">${instance.ports.native}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Container ID</span>
                    <span class="info-value">${instance.container_id || 'N/A'}</span>
                </div>
            </div>
            <div class="stream-container">
                ${isRunning ? 
                    `<iframe class="stream-iframe" src="${instance.webrtc_url}" allow="camera;microphone"></iframe>` :
                    `<div class="stream-placeholder">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <p>Instance not running</p>
                        <p style="font-size: 14px; margin-top: 8px;">Click "Start" to launch Isaac Sim</p>
                    </div>`
                }
            </div>
        </div>
    `;
    
    return card;
}

// Start instance
async function startInstance(instanceId) {
    try {
        showNotification(`Starting instance ${instanceId}...`, 'info');
        const response = await fetch(`${API_BASE}/api/instances/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instance_id: instanceId })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`Instance ${instanceId} started successfully`, 'success');
            // Wait a bit before refreshing to let container start
            setTimeout(refreshInstances, 2000);
        } else {
            showNotification(`Failed to start instance ${instanceId}`, 'error');
        }
    } catch (error) {
        console.error('Failed to start instance:', error);
        showNotification(`Error starting instance ${instanceId}`, 'error');
    }
}

// Stop instance
async function stopInstance(instanceId) {
    try {
        showNotification(`Stopping instance ${instanceId}...`, 'info');
        const response = await fetch(`${API_BASE}/api/instances/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instance_id: instanceId })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`Instance ${instanceId} stopped successfully`, 'success');
            refreshInstances();
        } else {
            showNotification(`Failed to stop instance ${instanceId}`, 'error');
        }
    } catch (error) {
        console.error('Failed to stop instance:', error);
        showNotification(`Error stopping instance ${instanceId}`, 'error');
    }
}

// Restart instance
async function restartInstance(instanceId) {
    try {
        showNotification(`Restarting instance ${instanceId}...`, 'info');
        const response = await fetch(`${API_BASE}/api/instances/restart`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instance_id: instanceId })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`Instance ${instanceId} restarted successfully`, 'success');
            setTimeout(refreshInstances, 2000);
        } else {
            showNotification(`Failed to restart instance ${instanceId}`, 'error');
        }
    } catch (error) {
        console.error('Failed to restart instance:', error);
        showNotification(`Error restarting instance ${instanceId}`, 'error');
    }
}

// Show logs
async function showLogs(instanceId) {
    try {
        const response = await fetch(`${API_BASE}/api/instances/${instanceId}/logs?tail=200`);
        const data = await response.json();
        
        const modal = document.getElementById('logs-modal');
        const logsContent = document.getElementById('logs-content');
        logsContent.textContent = data.logs || 'No logs available';
        modal.classList.add('show');
    } catch (error) {
        console.error('Failed to fetch logs:', error);
        showNotification(`Error fetching logs for instance ${instanceId}`, 'error');
    }
}

// Cleanup all instances
async function cleanupAll() {
    if (!confirm('Are you sure you want to stop and remove all instances?')) {
        return;
    }
    
    try {
        showNotification('Cleaning up all instances...', 'info');
        const response = await fetch(`${API_BASE}/api/cleanup`, {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('All instances cleaned up successfully', 'success');
            refreshInstances();
        } else {
            showNotification('Failed to cleanup instances', 'error');
        }
    } catch (error) {
        console.error('Failed to cleanup instances:', error);
        showNotification('Error during cleanup', 'error');
    }
}

// Show notification (simple implementation - could be enhanced with a toast library)
function showNotification(message, type) {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Could implement a toast notification system here
}

// Auto-refresh
function startAutoRefresh() {
    refreshTimer = setInterval(refreshInstances, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});


