/**
 * ماژول منطق مدیریت ولوم‌های Docker
 */

const DockerVolumesModule = (function () {
    // متغیرهای داخلی ماژول
    let currentVolumes = [];

    // ============================================================================
    // Public Functions - Volumes
    // ============================================================================

    /**
     * بارگذاری لیست ولوم‌های Docker
     */
    function loadVolumes() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/volumes')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        currentVolumes = data.volumes;
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت لیست ولوم‌ها'));
                    }
                })
                .catch(error => {
                    console.error('Error loading volumes:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت جزئیات یک ولوم
     */
    function getVolumeDetails(volumeName) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/volumes/${volumeName}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت جزئیات ولوم ${volumeName}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting volume details:', error);
                    reject(error);
                });
        });
    }

    /**
     * ایجاد ولوم جدید
     */
    function createVolume(name, driver = 'local', driverOpts = {}, labels = {}) {
        return new Promise((resolve, reject) => {
            const payload = {
                name: name,
                driver: driver,
                driver_opts: driverOpts,
                labels: labels
            };

            fetch('/api/docker/volumes/create', {
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
                        reject(new Error(data.message || 'خطا در ایجاد ولوم'));
                    }
                })
                .catch(error => {
                    console.error('Error creating volume:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف ولوم
     */
    function removeVolume(volumeName, force = false) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/volumes/${volumeName}/remove`, {
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
                        reject(new Error(data.message || 'خطا در حذف ولوم'));
                    }
                })
                .catch(error => {
                    console.error('Error removing volume:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف ولوم‌های بدون استفاده
     */
    function pruneVolumes() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/volumes/prune', {
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
                        reject(new Error(data.message || 'خطا در حذف ولوم‌های بدون استفاده'));
                    }
                })
                .catch(error => {
                    console.error('Error pruning volumes:', error);
                    reject(error);
                });
        });
    }

    /**
     * بررسی محتوای ولوم
     */
    function inspectVolume(volumeName) {
        return new Promise((resolve, reject) => {
            fetch(`/api/docker/volumes/${volumeName}/inspect`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در بررسی ولوم ${volumeName}`));
                    }
                })
                .catch(error => {
                    console.error('Error inspecting volume:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت آمار ولوم‌ها
     */
    function getVolumesStats() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/volumes/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت آمار ولوم‌ها'));
                    }
                })
                .catch(error => {
                    console.error('Error getting volume stats:', error);
                    reject(error);
                });
        });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * جستجوی ولوم‌ها
     */
    function searchVolumes(searchTerm, volumes = currentVolumes) {
        if (!searchTerm) return volumes;

        const term = searchTerm.toLowerCase();
        return volumes.filter(volume => {
            return volume.name.toLowerCase().includes(term) ||
                volume.driver.toLowerCase().includes(term) ||
                Object.keys(volume.labels || {}).some(label =>
                    label.toLowerCase().includes(term) ||
                    volume.labels[label].toString().toLowerCase().includes(term)
                );
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
     * بررسی معتبر بودن تنظیمات JSON
     */
    function validateJSONConfig(configString) {
        if (!configString || configString.trim() === '') {
            return {};
        }

        try {
            return JSON.parse(configString);
        } catch (e) {
            console.error('Invalid JSON config:', e);
            return null;
        }
    }

    /**
     * فرمت کردن مسیر mount
     */
    function _formatMountpoint(mountpoint) {
        if (!mountpoint) return '-';

        // کوتاه کردن مسیرهای طولانی
        if (mountpoint.length > 50) {
            return mountpoint.substring(0, 25) + '...' + mountpoint.substring(mountpoint.length - 25);
        }

        return mountpoint;
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع مدیریت ولوم‌ها
        loadVolumes,
        getVolumeDetails,
        createVolume,
        removeVolume,
        pruneVolumes,
        inspectVolume,
        getVolumesStats,

        // توابع Helper
        searchVolumes,
        validateJSONConfig,
        _formatMountpoint,

        // دسترسی به داده‌های داخلی
        _getCurrentVolumes: () => currentVolumes
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerVolumesModule = DockerVolumesModule;