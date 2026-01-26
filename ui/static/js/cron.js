/**
 * ماژول منطق مدیریت Cron Jobs
 */

const CronModule = (function () {
    // متغیرهای داخلی
    let currentJobs = [];
    let currentJobId = null;

    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * دریافت لیست cron jobs
     */
    function getCronJobs() {
        return new Promise((resolve, reject) => {
            fetch('/api/cron/jobs')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        currentJobs = data.jobs;
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت cron jobs'));
                    }
                })
                .catch(error => {
                    console.error('Error getting cron jobs:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت یک cron job خاص
     */
    function getCronJob(jobId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/cron/jobs/${jobId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت cron job ${jobId}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting cron job:', error);
                    reject(error);
                });
        });
    }

    /**
     * اضافه کردن cron job جدید
     */
    function addCronJob(cronData) {
        return new Promise((resolve, reject) => {
            fetch('/api/cron/jobs/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(cronData)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در اضافه کردن cron job'));
                    }
                })
                .catch(error => {
                    console.error('Error adding cron job:', error);
                    reject(error);
                });
        });
    }

    /**
     * فعال/غیرفعال کردن cron job
     */
    function toggleCronJob(jobId, enabled) {
        return new Promise((resolve, reject) => {
            fetch(`/api/cron/jobs/${jobId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled: enabled })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در تغییر وضعیت cron job'));
                    }
                })
                .catch(error => {
                    console.error('Error toggling cron job:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف cron job
     */
    function deleteCronJob(jobId) {
        return new Promise((resolve, reject) => {
            fetch(`/api/cron/jobs/${jobId}`, {
                method: 'DELETE'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف cron job'));
                    }
                })
                .catch(error => {
                    console.error('Error deleting cron job:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت وضعیت سیستم cron
     */
    function getSystemStatus() {
        return new Promise((resolve, reject) => {
            fetch('/api/cron/system/status')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت وضعیت سیستم'));
                    }
                })
                .catch(error => {
                    console.error('Error getting system status:', error);
                    reject(error);
                });
        });
    }

    /**
     * اعتبارسنجی زمان‌بندی cron
     */
    function validateSchedule(schedule) {
        return new Promise((resolve, reject) => {
            fetch('/api/cron/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ schedule: schedule })
            })
                .then(response => response.json())
                .then(data => {
                    resolve(data);
                })
                .catch(error => {
                    console.error('Error validating schedule:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت لاگ‌های cron
     */
    function getCronLogs(limit = 50) {
        // در این نسخه ساده، از لاگ سیستم استفاده می‌کنیم
        // در نسخه پیشرفته‌تر می‌توانید endpoint جداگانه بسازید
        return new Promise((resolve, reject) => {
            // شبیه‌سازی لاگ‌ها
            const logs = [
                { timestamp: new Date().toISOString(), message: "Cron job 'backup' executed successfully", type: "success" },
                { timestamp: new Date(Date.now() - 3600000).toISOString(), message: "Cron job 'cleanup' started", type: "info" },
                { timestamp: new Date(Date.now() - 7200000).toISOString(), message: "Cron daemon restarted", type: "warning" },
                { timestamp: new Date(Date.now() - 10800000).toISOString(), message: "Error in cron job 'report': Permission denied", type: "error" }
            ];

            resolve({
                status: 'success',
                logs: logs.slice(0, limit)
            });
        });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * فرمت‌بندی تاریخ برای نمایش
     */
    function formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('fa-IR');
        } catch (e) {
            return dateString;
        }
    }

    /**
     * دریافت jobs فعلی
     */
    function getCurrentJobs() {
        return currentJobs;
    }

    /**
     * جستجوی cron jobs
     */
    function searchJobs(searchTerm) {
        if (!searchTerm) return currentJobs;

        const term = searchTerm.toLowerCase();
        return currentJobs.filter(job => {
            return job.command.toLowerCase().includes(term) ||
                job.schedule_text.toLowerCase().includes(term) ||
                job.user.toLowerCase().includes(term);
        });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع اصلی
        getCronJobs,
        getCronJob,
        addCronJob,
        toggleCronJob,
        deleteCronJob,
        getSystemStatus,
        validateSchedule,
        getCronLogs,

        // توابع helper
        getCurrentJobs,
        searchJobs,
        formatDate
    };
})();

// قرار دادن در scope گلوبال
window.CronModule = CronModule;