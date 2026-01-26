/**
 * ماژول منطق مدیریت شبکه‌های Docker
 */

const DockerNetworksModule = (function () {
    // متغیرهای داخلی ماژول
    let currentNetworks = [];

    // ============================================================================
    // Public Functions - Networks
    // ============================================================================

    /**
     * بارگذاری لیست شبکه‌های Docker
     */
    function loadNetworks() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/networks')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        currentNetworks = data.networks;
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت لیست شبکه‌ها'));
                    }
                })
                .catch(error => {
                    console.error('Error loading networks:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت جزئیات یک شبکه
     */
    function getNetworkDetails(networkId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/networks/${networkId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت جزئیات شبکه ${networkId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting network details:', error);
                    reject(error);
                });
        });
    }

    /**
     * ایجاد شبکه جدید
     */
    function createNetwork(name, driver = 'bridge', internal = false, attachable = true, labels = {}, ipam = null) {
        return new Promise((resolve, reject) => {
            const payload = {
                name: name,
                driver: driver,
                internal: internal,
                attachable: attachable,
                labels: labels
            };

            if (ipam) {
                payload.ipam = ipam;
            }

            fetch('/api/docker/networks/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در ایجاد شبکه'));
                    }
                })
                .catch(error => {
                    console.error('Error creating network:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف شبکه
     */
    function removeNetwork(networkId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/networks/${networkId}/remove`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف شبکه'));
                    }
                })
                .catch(error => {
                    console.error('Error removing network:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف شبکه‌های بدون استفاده
     */
    function pruneNetworks() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/networks/prune', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف شبکه‌های بدون استفاده'));
                    }
                })
                .catch(error => {
                    console.error('Error pruning networks:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت کانتینرهای متصل به شبکه
     */
    function getNetworkContainers(networkId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/networks/${networkId}/containers`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت کانتینرهای شبکه ${networkId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting network containers:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت آمار شبکه‌ها
     */
    function getNetworkStats() {
        return new Promise((resolve) => {
            if (!currentNetworks || currentNetworks.length === 0) {
                resolve({ total: 0, bridge: 0, overlay: 0, others: 0 });
                return;
            }

            const stats = {
                total: currentNetworks.length,
                bridge: currentNetworks.filter(n => n.driver === 'bridge').length,
                overlay: currentNetworks.filter(n => n.driver === 'overlay').length,
                others: currentNetworks.filter(n => !['bridge', 'overlay'].includes(n.driver)).length
            };

            resolve(stats);
        });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * جستجوی شبکه‌ها
     */
    function searchNetworks(searchTerm, networks = currentNetworks) {
        if (!searchTerm) return networks;

        const term = searchTerm.toLowerCase();
        return networks.filter(network => {
            return network.name.toLowerCase().includes(term) ||
                network.id.toLowerCase().includes(term) ||
                network.driver.toLowerCase().includes(term);
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
     * بررسی معتبر بودن تنظیمات IPAM
     */
    function validateIPAMConfig(ipamConfig) {
        if (!ipamConfig) return null;

        try {
            const config = typeof ipamConfig === 'string' ? JSON.parse(ipamConfig) : ipamConfig;
            return config;
        } catch (e) {
            console.error('Invalid IPAM config:', e);
            return null;
        }
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع مدیریت شبکه‌ها
        loadNetworks,
        getNetworkDetails,
        createNetwork,
        removeNetwork,
        pruneNetworks,
        getNetworkContainers,
        getNetworkStats,

        // توابع Helper
        searchNetworks,
        validateIPAMConfig,

        // دسترسی به داده‌های داخلی
        _getCurrentNetworks: () => currentNetworks
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerNetworksModule = DockerNetworksModule;