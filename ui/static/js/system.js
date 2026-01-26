/**
 * ماژول مدیریت اطلاعات سیستم
 */

const SystemModule = (function () {
    // متغیرهای داخلی
    let systemData = {};
    let resourceHistory = [];
    let monitoringInterval = null;
    let charts = {};

    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * دریافت اطلاعات کامل سیستم
     */
    function getSystemInfo() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/system/info')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        systemData = data.data;
                        resolve(data.data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت اطلاعات سیستم'));
                    }
                })
                .catch(error => {
                    console.error('Error getting system info:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت اطلاعات منابع مصرفی
     */
    function getSystemResources() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/system/resources')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // اضافه کردن به تاریخچه
                        resourceHistory.push(data.data);
                        if (resourceHistory.length > 20) {
                            resourceHistory.shift(); // حفظ 20 نمونه آخر
                        }
                        resolve(data.data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت اطلاعات منابع'));
                    }
                })
                .catch(error => {
                    console.error('Error getting system resources:', error);
                    reject(error);
                });
        });
    }

    /**
     * شروع مانیتورینگ زنده
     */
    function startMonitoring(interval = 3000) {
        stopMonitoring(); // توقف قبلی اگر وجود دارد

        monitoringInterval = setInterval(() => {
            getSystemResources()
                .then(data => {
                    updateResourceDisplays(data);
                    updateCharts(data);
                })
                .catch(error => {
                    console.error('Monitoring error:', error);
                });
        }, interval);

        console.log(`Monitoring started with ${interval}ms interval`);
        return true;
    }

    /**
     * توقف مانیتورینگ
     */
    function stopMonitoring() {
        if (monitoringInterval) {
            clearInterval(monitoringInterval);
            monitoringInterval = null;
            console.log('Monitoring stopped');
        }
        return true;
    }

    /**
     * به‌روزرسانی نمایش اطلاعات سیستم
     */
    function updateSystemDisplays() {
        if (!systemData) return;

        // ============ CPU ============
        document.getElementById('cpuUsage').textContent = `${systemData.cpu.usage.toFixed(1)}%`;
        document.getElementById('cpuProgress').style.width = `${systemData.cpu.usage}%`;
        document.getElementById('cpuCores').textContent = systemData.cpu.physical_cores;
        document.getElementById('cpuThreads').textContent = systemData.cpu.total_cores;

        // ============ Memory ============
        const memGB = systemData.memory.used / (1024 ** 3);
        const memTotalGB = systemData.memory.total / (1024 ** 3);
        document.getElementById('ramUsage').textContent = `${memGB.toFixed(2)}/${memTotalGB.toFixed(2)} GB`;
        document.getElementById('ramProgress').style.width = `${systemData.memory.percent}%`;
        document.getElementById('ramTotal').textContent = `${memTotalGB.toFixed(2)} GB`;
        document.getElementById('ramFree').textContent = `${(systemData.memory.free / (1024 ** 3)).toFixed(2)} GB`;

        // ============ Disk ============
        const diskGB = systemData.disk[0]?.used / (1024 ** 3) || 0;
        const diskTotalGB = systemData.disk[0]?.total / (1024 ** 3) || 0;
        document.getElementById('diskUsage').textContent = `${diskGB.toFixed(2)}/${diskTotalGB.toFixed(2)} GB`;
        document.getElementById('diskProgress').style.width = `${systemData.disk[0]?.percent || 0}%`;
        document.getElementById('diskTotal').textContent = `${diskTotalGB.toFixed(2)} GB`;
        document.getElementById('diskFree').textContent = `${((systemData.disk[0]?.free || 0) / (1024 ** 3)).toFixed(2)} GB`;

        // ============ Uptime ============
        const uptime = systemData.system.uptime;
        const days = Math.floor(uptime / 86400);
        const hours = Math.floor((uptime % 86400) / 3600);
        document.getElementById('uptime').textContent = `${days} روز ${hours} ساعت`;
        document.getElementById('bootTime').textContent = new Date(systemData.system.boot_time).toLocaleString('fa-IR');

        // ============ Summary Cards ============
        document.getElementById('loadAvg').textContent = systemData.load_average[0].toFixed(2);
        document.getElementById('processCount').textContent = systemData.processes.length;
        document.getElementById('userCount').textContent = '--'; // نیاز به پیاده‌سازی

        // ============ Hardware Details ============
        updateHardwareDetails();
        updateNetworkDetails();
        updateSoftwareDetails();
        updateProcessesTable();
        updateDiskList();
        updateNetworkInterfaces();
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    function updateHardwareDetails() {
        // CPU Details
        document.getElementById('cpuModel').textContent = systemData.system.os.processor || '--';
        document.getElementById('cpuFreq').textContent = systemData.cpu.frequency.current
            ? `${(systemData.cpu.frequency.current / 1000).toFixed(2)} GHz`
            : '--';
        document.getElementById('cpuCoresDetail').textContent = systemData.cpu.physical_cores;
        document.getElementById('cpuThreadsDetail').textContent = systemData.cpu.total_cores;
        document.getElementById('cpuArch').textContent = systemData.system.os.machine;

        // Memory Details
        document.getElementById('ramTotalDetail').textContent = `${(systemData.memory.total / (1024 ** 3)).toFixed(2)} GB`;
        document.getElementById('swapTotal').textContent = `${(systemData.memory.swap_total / (1024 ** 3)).toFixed(2)} GB`;
    }

    function updateNetworkDetails() {
        document.getElementById('hostname').textContent = systemData.system.hostname;

        // پیدا کردن IP اصلی
        let primaryIp = '--';
        for (const [interface, addrs] of Object.entries(systemData.network.interfaces)) {
            for (const addr of addrs) {
                if (addr.family === 'AddressFamily.AF_INET' && !addr.address.startsWith('127.')) {
                    primaryIp = addr.address;
                    break;
                }
            }
            if (primaryIp !== '--') break;
        }
        document.getElementById('primaryIp').textContent = primaryIp;

        // آمار شبکه
        const netStats = systemData.network.io_counters;
        document.getElementById('totalRx').textContent = `${(netStats.bytes_recv / (1024 ** 3)).toFixed(2)} GB`;
        document.getElementById('totalTx').textContent = `${(netStats.bytes_sent / (1024 ** 3)).toFixed(2)} GB`;
        document.getElementById('packetsRx').textContent = netStats.packets_recv.toLocaleString();
        document.getElementById('packetsTx').textContent = netStats.packets_sent.toLocaleString();
    }

    function updateSoftwareDetails() {
        // OS Details
        document.getElementById('osName').textContent = systemData.system.os.name;
        document.getElementById('osVersion').textContent = systemData.system.os.version;
        document.getElementById('osArch').textContent = systemData.system.os.machine;
        document.getElementById('kernel').textContent = systemData.system.os.release;

        // Docker Details
        if (systemData.docker && !systemData.docker.error) {
            document.getElementById('dockerVersion').textContent = systemData.docker.version;
            document.getElementById('dockerApi').textContent = '--';
        } else {
            document.getElementById('dockerVersion').textContent = 'غیرفعال';
        }
    }

    function updateProcessesTable() {
        const tbody = document.getElementById('processesTable');
        if (!tbody) return;

        tbody.innerHTML = '';

        systemData.processes.forEach(proc => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${proc.pid}</td>
                <td>${proc.name || 'N/A'}</td>
                <td>${proc.username || 'N/A'}</td>
                <td>${proc.cpu_percent?.toFixed(1) || '0.0'}%</td>
                <td>${proc.memory_percent?.toFixed(1) || '0.0'}%</td>
                <td>${(proc.memory_info?.rss / 1024 / 1024).toFixed(1) || '0.0'} MB</td>
                <td><span class="badge bg-${getProcessStatusBadge(proc.status)}">${proc.status || 'N/A'}</span></td>
                <td>${proc.create_time ? formatUptime(Date.now() - proc.create_time * 1000) : 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="SystemModule.killProcess(${proc.pid})">
                        ⛔
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

        document.getElementById('processCountDisplay').textContent = systemData.processes.length;
    }

    function updateDiskList() {
        const container = document.getElementById('disksList');
        if (!container) return;

        container.innerHTML = '';

        systemData.disk.forEach(disk => {
            const diskCard = document.createElement('div');
            diskCard.className = 'card mb-2';
            diskCard.innerHTML = `
                <div class="card-body">
                    <h6 class="card-title">${disk.mountpoint} (${disk.device})</h6>
                    <p class="card-text">
                        <small>
                            نوع: ${disk.fstype}<br>
                            کل: ${(disk.total / (1024 ** 3)).toFixed(2)} GB<br>
                            مصرف: ${disk.percent}%<br>
                            آزاد: ${(disk.free / (1024 ** 3)).toFixed(2)} GB
                        </small>
                    </p>
                    <div class="progress" style="height: 10px;">
                        <div class="progress-bar ${disk.percent > 90 ? 'bg-danger' : disk.percent > 70 ? 'bg-warning' : 'bg-success'}" 
                             style="width: ${disk.percent}%"></div>
                    </div>
                </div>
            `;
            container.appendChild(diskCard);
        });
    }

    function updateNetworkInterfaces() {
        const container = document.getElementById('networkInterfaces');
        if (!container) return;

        container.innerHTML = '';

        Object.entries(systemData.network.interfaces).forEach(([name, addrs]) => {
            const interfaceCard = document.createElement('div');
            interfaceCard.className = 'card mb-2';

            let ips = [];
            addrs.forEach(addr => {
                if (addr.family === 'AddressFamily.AF_INET') {
                    ips.push(`IPv4: ${addr.address}`);
                } else if (addr.family === 'AddressFamily.AF_INET6') {
                    ips.push(`IPv6: ${addr.address}`);
                }
            });

            interfaceCard.innerHTML = `
                <div class="card-body">
                    <h6 class="card-title">${name}</h6>
                    <p class="card-text">
                        <small>${ips.join('<br>')}</small>
                    </p>
                </div>
            `;
            container.appendChild(interfaceCard);
        });
    }

    function updateResourceDisplays(resourceData) {
        // آپدیت مقادیر لحظه‌ای در تب Overview
        document.getElementById('cpuUsage').textContent = `${resourceData.cpu.toFixed(1)}%`;
        document.getElementById('cpuProgress').style.width = `${resourceData.cpu}%`;

        const memPercent = resourceData.memory.percent;
        document.getElementById('ramUsage').textContent =
            `${(resourceData.memory.used / (1024 ** 3)).toFixed(2)}/${(systemData.memory.total / (1024 ** 3)).toFixed(2)} GB`;
        document.getElementById('ramProgress').style.width = `${memPercent}%`;

        document.getElementById('loadAvg').textContent = resourceData.load_average[0].toFixed(2);
        document.getElementById('processCount').textContent = resourceData.process_count;
    }

    function updateCharts(resourceData) {
        if (!charts.cpu || !charts.ram) return;

        // آپدیت نمودارها
        updateChartData(charts.cpu, resourceData.cpu);
        updateChartData(charts.ram, resourceData.memory.percent);
    }

    function initializeCharts() {
        // CPU Chart
        const cpuCtx = document.getElementById('cpuChart')?.getContext('2d');
        if (cpuCtx) {
            charts.cpu = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage %',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }

        // RAM Chart
        const ramCtx = document.getElementById('ramChart')?.getContext('2d');
        if (ramCtx) {
            charts.ram = new Chart(ramCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'RAM Usage %',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }
    }

    function updateChartData(chart, newValue) {
        if (!chart) return;

        chart.data.labels.push(new Date().toLocaleTimeString('fa-IR'));
        chart.data.datasets[0].data.push(newValue);

        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update('none');
    }

    // ============================================================================
    // Utility Functions
    // ============================================================================

    function getProcessStatusBadge(status) {
        const statusMap = {
            'running': 'success',
            'sleeping': 'info',
            'stopped': 'warning',
            'zombie': 'danger',
            'idle': 'secondary'
        };
        return statusMap[status?.toLowerCase()] || 'secondary';
    }

    function formatUptime(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    }

    function bytesToSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Byte';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        getSystemInfo,
        getSystemResources,
        startMonitoring,
        stopMonitoring,
        updateSystemDisplays,
        initializeCharts,

        // توابع اضافی
        killProcess: function (pid) {
            // پیاده‌سازی kill process
            console.log(`Killing process ${pid}`);
            // TODO: پیاده‌سازی endpoint kill process
        },

        refreshAll: function () {
            return Promise.all([
                this.getSystemInfo(),
                this.getSystemResources()
            ]).then(() => {
                this.updateSystemDisplays();
                return true;
            });
        }
    };
})();

window.SystemModule = SystemModule;