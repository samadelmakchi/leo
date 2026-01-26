/**
 * ماژول منطق مدیریت کانتینرهای Docker
 */

const DockerContainersModule = (function () {
    // متغیرهای داخلی ماژول
    let currentContainers = [];
    let currentFilters = {
        status: '',
        search: '',
        sort: 'created_desc'
    };

    // ============================================================================
    // Public Functions - Containers
    // ============================================================================

    /**
     * بارگذاری لیست کانتینرهای Docker
     */
    function loadContainers() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/containers')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        currentContainers = data.containers;
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت لیست کانتینرها'));
                    }
                })
                .catch(error => {
                    console.error('Error loading containers:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت جزئیات یک کانتینر
     */
    function getContainerDetails(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت جزئیات کانتینر ${containerId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting container details:', error);
                    reject(error);
                });
        });
    }

    /**
     * شروع یک کانتینر
     */
    function startContainer(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/start`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در شروع کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error starting container:', error);
                    reject(error);
                });
        });
    }

    /**
     * توقف یک کانتینر
     */
    function stopContainer(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/stop`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در توقف کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error stopping container:', error);
                    reject(error);
                });
        });
    }

    /**
     * راه‌اندازی مجدد یک کانتینر
     */
    function restartContainer(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/restart`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در راه‌اندازی مجدد کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error restarting container:', error);
                    reject(error);
                });
        });
    }

    /**
     * مکث یک کانتینر
     */
    function pauseContainer(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/pause`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در مکث کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error pausing container:', error);
                    reject(error);
                });
        });
    }

    /**
     * ادامه یک کانتینر
     */
    function unpauseContainer(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/unpause`, {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در ادامه کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error unpausing container:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف یک کانتینر
     */
    function removeContainer(containerId, force = false, removeVolumes = false) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/remove`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    force: force,
                    v: removeVolumes
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error removing container:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت لاگ‌های یک کانتینر
     */
    function getContainerLogs(containerId, tail = '100', timestamps = false) {
        return new Promise((resolve, reject) => {
            let url = `/api/docker/containers/${containerId}/logs?tail=${tail}`;
            if (timestamps) {
                url += '&timestamps=true';
            }

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت لاگ‌های کانتینر ${containerId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting container logs:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت آمار یک کانتینر
     */
    function getContainerStats(containerId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/stats`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت آمار کانتینر ${containerId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting container stats:', error);
                    reject(error);
                });
        });
    }

    /**
     * اجرای دستور در یک کانتینر
     */
    function execContainerCommand(containerId, command) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/containers/${containerId}/exec`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ command: command })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در اجرای دستور'));
                    }
                })
                .catch(error => {
                    console.error('Error executing command:', error);
                    reject(error);
                });
        });
    }

    /**
     * ایجاد کانتینر جدید
     */
    function createContainer(config) {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/containers/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در ایجاد کانتینر'));
                    }
                })
                .catch(error => {
                    console.error('Error creating container:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف کانتینرهای متوقف شده
     */
    function pruneContainers() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/containers/prune', {
                method: 'POST'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف کانتینرهای متوقف شده'));
                    }
                })
                .catch(error => {
                    console.error('Error pruning containers:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت آمار تمام کانتینرها
     */
    function getAllContainersStats() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/containers/stats/all')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت آمار کانتینرها'));
                    }
                })
                .catch(error => {
                    console.error('Error getting all containers stats:', error);
                    reject(error);
                });
        });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * فیلتر کردن کانتینرها
     */
    function filterContainers(containers = currentContainers) {
        let filtered = [...containers];

        // فیلتر بر اساس وضعیت
        if (currentFilters.status) {
            filtered = filtered.filter(container => {
                if (currentFilters.status === 'exited') {
                    return container.status === 'exited' || container.status === 'stopped';
                }
                return container.status === currentFilters.status;
            });
        }

        // فیلتر بر اساس جستجو
        if (currentFilters.search) {
            const term = currentFilters.search.toLowerCase();
            filtered = filtered.filter(container => {
                return container.name.toLowerCase().includes(term) ||
                    container.image.toLowerCase().includes(term) ||
                    container.status.toLowerCase().includes(term) ||
                    container.command.toLowerCase().includes(term) ||
                    Object.keys(container.labels || {}).some(label =>
                        label.toLowerCase().includes(term) ||
                        container.labels[label].toString().toLowerCase().includes(term)
                    );
            });
        }

        // مرتب‌سازی
        filtered = sortContainersList(filtered, currentFilters.sort);

        return filtered;
    }

    /**
     * مرتب‌سازی کانتینرها
     */
    function sortContainersList(containers, sortType) {
        const sorted = [...containers];

        switch (sortType) {
            case 'created_desc':
                sorted.sort((a, b) => new Date(b.created) - new Date(a.created));
                break;
            case 'created_asc':
                sorted.sort((a, b) => new Date(a.created) - new Date(b.created));
                break;
            case 'name':
                sorted.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'status':
                sorted.sort((a, b) => a.status.localeCompare(b.status));
                break;
        }

        return sorted;
    }

    /**
     * جستجوی کانتینرها
     */
    function searchContainers(searchTerm, containers = currentContainers) {
        if (!searchTerm) return containers;

        const term = searchTerm.toLowerCase();
        return containers.filter(container => {
            return container.name.toLowerCase().includes(term) ||
                container.image.toLowerCase().includes(term) ||
                container.status.toLowerCase().includes(term) ||
                container.command.toLowerCase().includes(term);
        });
    }

    /**
     * فرمت کردن تاریخ
     */
    function _formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('fa-IR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateString;
        }
    }

    /**
     * فرمت کردن پورت‌ها
     */
    function _formatPorts(ports) {
        if (!ports || Object.keys(ports).length === 0) {
            return '-';
        }

        const formatted = [];
        for (const [containerPort, hostPorts] of Object.entries(ports)) {
            if (hostPorts) {
                const hostPort = Array.isArray(hostPorts) ? hostPorts[0]?.HostPort : hostPorts.HostPort;
                if (hostPort) {
                    formatted.push(`${hostPort}→${containerPort}`);
                }
            }
        }

        return formatted.join(', ') || '-';
    }

    /**
     * بررسی معتبر بودن تنظیمات JSON
     */
    function validateJSONConfig(configString, defaultValue = {}) {
        if (!configString || configString.trim() === '') {
            return defaultValue;
        }

        try {
            return JSON.parse(configString);
        } catch (e) {
            console.error('Invalid JSON config:', e);
            return null;
        }
    }

    /**
     * محاسبه آمار کانتینرها
     */
    function calculateContainerStats(containers = currentContainers) {
        const stats = {
            total: containers.length,
            running: containers.filter(c => c.status === 'running').length,
            exited: containers.filter(c => c.status === 'exited').length,
            stopped: containers.filter(c => c.status === 'stopped').length,
            paused: containers.filter(c => c.status === 'paused').length,
            restarting: containers.filter(c => c.status === 'restarting').length,
            uniqueImages: new Set(containers.map(c => c.image)).size
        };

        return stats;
    }

    /**
     * دریافت وضعیت با رنگ مناسب
     */
    function getStatusBadge(status) {
        switch (status) {
            case 'running':
                return '<span class="badge bg-success">در حال اجرا</span>';
            case 'exited':
                return '<span class="badge bg-secondary">متوقف شده</span>';
            case 'stopped':
                return '<span class="badge bg-danger">متوقف شده</span>';
            case 'paused':
                return '<span class="badge bg-warning">مکث شده</span>';
            case 'restarting':
                return '<span class="badge bg-info">در حال راه‌اندازی مجدد</span>';
            default:
                return `<span class="badge bg-light text-dark">${status}</span>`;
        }
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع مدیریت کانتینرها
        loadContainers,
        getContainerDetails,
        startContainer,
        stopContainer,
        restartContainer,
        pauseContainer,
        unpauseContainer,
        removeContainer,
        getContainerLogs,
        getContainerStats,
        execContainerCommand,
        createContainer,
        pruneContainers,
        getAllContainersStats,

        // توابع فیلتر و جستجو
        filterContainers,
        searchContainers,
        sortContainersList,

        // توابع Helper
        _formatDate,
        _formatPorts,
        validateJSONConfig,
        calculateContainerStats,
        getStatusBadge,

        // مدیریت فیلترها
        setFilter: function (type, value) {
            currentFilters[type] = value;
        },
        getFilters: function () {
            return currentFilters;
        },
        resetFilters: function () {
            currentFilters = {
                status: '',
                search: '',
                sort: 'created_desc'
            };
        },

        // دسترسی به داده‌های داخلی
        _getCurrentContainers: () => currentContainers,
        _getCurrentFilters: () => currentFilters
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerContainersModule = DockerContainersModule;