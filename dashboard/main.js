try {
    $(document).ready(function() {
        const EIDO_API_BASE_URL = '/eido';
        const IDX_API_BASE_URL = '/idx';

        let map = L.map('mapid').setView([32.8801, -117.2340], 13);
        let incidentMarkers = {};
        let incidentChart = null; // Variable to hold the chart instance

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // EIDO Agent: Convert Raw Text
        $('#convert-eido').click(function() {
            const rawText = $('#raw-text').val();
            if (rawText) {
                fetch(`${EIDO_API_BASE_URL}/ingest_alert`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ alert_text: rawText }),
                })
                .then(response => response.json())
                .then(data => {
                    console.log('EIDO conversion response:', data);
                    alert('EIDO conversion successful!');
                    getEidoIncidents();
                })
                .catch(error => {
                    console.error('Error converting to EIDO:', error);
                    alert('Error converting to EIDO. See console for details.');
                });
            } else {
                alert('Please enter raw text to convert.');
            }
        });

        // EIDO Agent: Upload EIDO JSON
        $('#upload-eido').click(function() {
            const eidoFile = $('#eido-file')[0].files[0];
            if (eidoFile) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        const eidoData = JSON.parse(e.target.result);
                        fetch(`${EIDO_API_BASE_URL}/ingest`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(eidoData),
                        })
                        .then(response => response.json())
                        .then(data => {
                            console.log('EIDO upload response:', data);
                            alert('EIDO upload successful!');
                            getEidoIncidents();
                        })
                        .catch(error => {
                            console.error('Error uploading EIDO:', error);
                            alert('Error uploading EIDO. See console for details.');
                        });
                    } catch (error) {
                        console.error("Error parsing EIDO JSON:", error);
                        alert("Error parsing EIDO JSON. Please ensure it is a valid JSON file.");
                    }
                };
                reader.readAsText(eidoFile);
            } else {
                alert('Please select an EIDO JSON file to upload.');
            }
        });

        // EIDO Agent: Fetch and display incidents
        function getEidoIncidents() {
            fetch(`${EIDO_API_BASE_URL}/incidents`)
                .then(response => response.json())
                .then(data => {
                    const incidents = Array.isArray(data) ? data : [data];
                    const incidentList = $('#eido-incident-list');
                    incidentList.empty();
                    Object.values(incidentMarkers).forEach(marker => map.removeLayer(marker));
                    incidentMarkers = {};

                    if (incidents.length > 0 && incidents[0].incident_id) {
                        incidents.forEach(incident => {
                            const incidentCard = `
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <h5 class="card-title">${incident.incident_id}</h5>
                                        <p class="card-text">${incident.summary}</p>
                                        <p class="card-text"><small class="text-muted">Status: ${incident.status}</small></p>
                                        <button class="btn btn-sm btn-outline-primary export-eido" data-incident-id="${incident.incident_id}">Export EIDO</button>
                                    </div>
                                </div>
                            `;
                            incidentList.append(incidentCard);

                            if (incident.locations && incident.locations.length > 0) {
                                const location = incident.locations[0];
                                if(typeof location.latitude === 'number' && typeof location.longitude === 'number') {
                                    let marker = L.marker([location.latitude, location.longitude]).addTo(map)
                                        .bindPopup(`<b>${incident.incident_id}</b><br>${incident.summary}`);
                                    incidentMarkers[incident.incident_id] = marker;
                                }
                            }
                        });
                    } else {
                        incidentList.html('<p class="text-center">No incidents found.</p>');
                    }
                    updateDashboardMetrics(incidents);
                    updateFeed(incidents, 'eido');
                })
                .catch(error => {
                    console.error('Error fetching EIDO incidents:', error);
                    $('#eido-incident-list').html('<p class="text-center text-danger">Error fetching incidents. See console for details.</p>');
                });
        }

        // IDX Agent: Fetch and display incidents
        function getIdxIncidents() {
            fetch(`${IDX_API_BASE_URL}/incidents`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.text(); // Get raw text to debug
                })
                .then(text => {
                    console.log('Raw IDX incidents response:', text);
                    const data = JSON.parse(text);
                    const incidents = Array.isArray(data) ? data : [data];
                    const incidentList = $('#idx-incident-list');
                    incidentList.empty();
                    if (incidents.length > 0 && incidents[0].incident_id) {
                        incidents.forEach(incident => {
                            const incidentCard = `
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <h5 class="card-title">${incident.incident_id}</h5>
                                        <p class="card-text">${incident.description}</p>
                                        <p class="card-text"><small class="text-muted">Status: ${incident.status}</small></p>
                                    </div>
                                </div>
                            `;
                            incidentList.append(incidentCard);
                        });
                    } else {
                        incidentList.html('<p class="text-center">No correlated incidents found.</p>');
                    }
                    updateFeed(incidents, 'idx');
                })
                .catch(error => {
                    console.error('Error fetching IDX incidents:', error);
                    $('#idx-incident-list').html('<p class="text-center text-danger">Error fetching incidents. See console for details.</p>');
                });
        }

        // Export EIDO
        $(document).on('click', '.export-eido', function() {
            const incidentId = $(this).data('incident-id');
            fetch(`${EIDO_API_BASE_URL}/incidents/${incidentId}/eido`)
                .then(response => response.json())
                .then(data => {
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${incidentId}.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                })
                .catch(error => {
                    console.error('Error exporting EIDO:', error);
                    alert('Error exporting EIDO. See console for details.');
                });
        });

        // Dashboard Metrics & Chart
        function updateDashboardMetrics(incidents) {
            if (!Array.isArray(incidents) || incidents.length === 0 || !incidents[0].incident_id) {
                incidents = []; // Clear metrics if no valid incidents
            }

            const totalIncidents = incidents.length;
            const activeIncidents = incidents.filter(inc => inc.status === 'Active').length;
            const resolvedIncidents = incidents.filter(inc => inc.status === 'Resolved').length;

            $('#key-metrics').html(`
                <div class="col-4 text-center">
                    <h4>${totalIncidents}</h4>
                    <p>Total</p>
                </div>
                <div class="col-4 text-center">
                    <h4>${activeIncidents}</h4>
                    <p>Active</p>
                </div>
                <div class="col-4 text-center">
                    <h4>${resolvedIncidents}</h4>
                    <p>Resolved</p>
                </div>
            `);

            const statusCounts = incidents.reduce((acc, incident) => {
                acc[incident.status] = (acc[incident.status] || 0) + 1;
                return acc;
            }, {});

            if (incidentChart) {
                incidentChart.destroy();
            }

            const chartCtx = document.getElementById('incident-chart').getContext('2d');
            incidentChart = new Chart(chartCtx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statusCounts),
                    datasets: [{
                        data: Object.values(statusCounts),
                        backgroundColor: ['#ffc107', '#28a745', '#dc3545', '#6c757d'],
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                }
            });
        }

        // Feed Digest
        function updateFeed(incidents, source) {
            const feed = $('#feed-digest');
            if (Array.isArray(incidents) && incidents.length > 0 && incidents[0].incident_id) {
                incidents.forEach(incident => {
                    const feedItem = `
                        <div class="feed-item">
                            <div class="feed-source ${source}">${source.toUpperCase()}</div>
                            <div class="feed-content">
                                <div class="feed-title">${incident.incident_id}</div>
                                <div class="feed-summary">${incident.summary || incident.description}</div>
                            </div>
                        </div>
                    `;
                    feed.prepend(feedItem);
                });
            }
        }

        // Initial Load
        getEidoIncidents();
        getIdxIncidents();
    });
} catch (e) {
    console.error("An error occurred:", e);
}