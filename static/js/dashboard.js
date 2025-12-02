const chartColors = {
  cpu: ['#d9534f', '#5cb85c'],
  memory: ['#0275d8', '#5bc0de'],
  disk: ['#5bc0de'],
  networkRx: '#6f42c1',
  networkTx: '#f0ad4e',
};

const charts = {};
let lastNetworkTotals = null;
let lastNetworkTimestamp = null;
const maxNetworkPoints = 20;

function formatBytes(bytes) {
  if (bytes === 0) return '0 B/s';
  const sizes = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), sizes.length - 1);
  const value = bytes / 1024 ** i;
  return `${value.toFixed(1)} ${sizes[i]}`;
}

function initCpuChart(ctx) {
  charts.cpu = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Genutzt', 'Idle'],
      datasets: [
        {
          data: [0, 100],
          backgroundColor: chartColors.cpu,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => `${context.label}: ${context.parsed.toFixed(1)}%`,
          },
        },
        legend: { position: 'bottom' },
      },
      cutout: '60%',
    },
  });
}

function initMemoryChart(ctx) {
  charts.memory = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Belegt', 'Frei'],
      datasets: [
        {
          data: [0, 100],
          backgroundColor: chartColors.memory,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => `${context.label}: ${context.parsed.toFixed(1)}%`,
          },
        },
        legend: { position: 'bottom' },
      },
      cutout: '60%',
    },
  });
}

function initDiskChart(ctx) {
  charts.disk = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Belegt',
          data: [],
          backgroundColor: 'rgba(0, 123, 255, 0.5)',
          borderColor: '#007bff',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: (value) => `${value}%`,
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => `${context.raw}%` ,
          },
        },
        legend: { display: false },
      },
    },
  });
}

function initNetworkChart(ctx) {
  charts.network = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'RX',
          data: [],
          borderColor: chartColors.networkRx,
          backgroundColor: 'rgba(111, 66, 193, 0.2)',
          tension: 0.3,
          fill: true,
        },
        {
          label: 'TX',
          data: [],
          borderColor: chartColors.networkTx,
          backgroundColor: 'rgba(240, 173, 78, 0.2)',
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { intersect: false, mode: 'index' },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => formatBytes(value),
          },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${formatBytes(context.parsed.y)}`,
          },
        },
        legend: { position: 'bottom' },
      },
    },
  });
}

function updateCpuChart(cpu) {
  if (!charts.cpu || !cpu) return;
  const used = cpu.usage?.usage ?? 0;
  charts.cpu.data.datasets[0].data = [used, Math.max(0, 100 - used)];
  charts.cpu.update();
}

function updateMemoryChart(memory) {
  if (!charts.memory || !memory) return;
  const used = memory.percent || 0;
  charts.memory.data.datasets[0].data = [used, Math.max(0, 100 - used)];
  charts.memory.update();
}

function updateDiskChart(disk) {
  if (!charts.disk || !disk) return;
  const labels = (disk.entries || []).map((entry) => `${entry.mount}`);
  const values = (disk.entries || []).map((entry) => entry.percent);
  charts.disk.data.labels = labels;
  charts.disk.data.datasets[0].data = values;
  charts.disk.update();
}

function updateNetworkChart(networkStats) {
  if (!charts.network || !networkStats) return;
  const now = Date.now();

  if (lastNetworkTotals && lastNetworkTimestamp) {
    const deltaSeconds = (now - lastNetworkTimestamp) / 1000;
    if (deltaSeconds > 0) {
      const rxRate = (networkStats.rx_bytes - lastNetworkTotals.rx_bytes) / deltaSeconds;
      const txRate = (networkStats.tx_bytes - lastNetworkTotals.tx_bytes) / deltaSeconds;
      const label = new Date().toLocaleTimeString();

      charts.network.data.labels.push(label);
      charts.network.data.datasets[0].data.push(Math.max(0, rxRate));
      charts.network.data.datasets[1].data.push(Math.max(0, txRate));

      if (charts.network.data.labels.length > maxNetworkPoints) {
        charts.network.data.labels.shift();
        charts.network.data.datasets.forEach((dataset) => dataset.data.shift());
      }

      charts.network.update();
    }
  }

  lastNetworkTotals = { rx_bytes: networkStats.rx_bytes, tx_bytes: networkStats.tx_bytes };
  lastNetworkTimestamp = now;
}

async function fetchData() {
  const response = await fetch('/api/sysinfo');
  if (!response.ok) throw new Error('Fehler beim Abrufen der Systemdaten');
  return response.json();
}

function updateTimestamp() {
  const target = document.getElementById('lastUpdated');
  const timestamp = new Date().toLocaleTimeString();
  if (target) {
    target.textContent = `Zuletzt aktualisiert: ${timestamp}`;
  }
}

async function pollData() {
  try {
    const data = await fetchData();
    updateCpuChart(data.CPU);
    updateMemoryChart(data.Memory);
    updateDiskChart(data.Disk);
    updateNetworkChart(data.NetworkStats);
    updateTimestamp();
  } catch (error) {
    console.error(error);
  }
}

function initCharts() {
  initCpuChart(document.getElementById('cpuChart'));
  initMemoryChart(document.getElementById('memoryChart'));
  initDiskChart(document.getElementById('diskChart'));
  initNetworkChart(document.getElementById('networkChart'));
}

window.addEventListener('DOMContentLoaded', () => {
  initCharts();
  pollData();
  setInterval(pollData, 8000);
});
