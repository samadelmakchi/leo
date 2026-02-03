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
            fetch('/api/cron/jobs/real')
                .then(response => {
                    if (!response.ok) {
                        return fetch('/api/cron/jobs/test');
                    }
                    return response;
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // ذخیره jobs در متغیر داخلی
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
            // اول از لیست داخلی جستجو کن
            const job = currentJobs.find(j => j.id == jobId);
            if (job) {
                resolve({ status: 'success', job: job });
                return;
            }

            // اگر پیدا نکردی، از API بگیر
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
        return new Promise((resolve, reject) => {
            fetch('/api/cron/logs')
                .then(response => {
                    // اول مطمئن شو response معتبر است
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    // بررسی کن که content-type درست باشد
                    const contentType = response.headers.get("content-type");
                    if (!contentType || !contentType.includes("application/json")) {
                        throw new Error("پاسخ سرور JSON معتبر نیست");
                    }

                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        // اگر خطا بود، لاگ‌های نمونه بده
                        resolve(getSampleLogs(limit));
                    }
                })
                .catch(error => {
                    console.error('Error getting cron logs:', error);
                    // در صورت خطا، لاگ‌های نمونه برگردان
                    resolve(getSampleLogs(limit));
                });
        });
    }

    /**
     * دریافت لاگ‌های نمونه
     */
    function getSampleLogs(limit) {
        const sampleLogs = [
            { timestamp: new Date().toISOString(), message: "Cron daemon started successfully", type: "success" },
            { timestamp: new Date(Date.now() - 3600000).toISOString(), message: "(root) CMD (system maintenance)", type: "info" },
            { timestamp: new Date(Date.now() - 7200000).toISOString(), message: "Hourly cron jobs completed", type: "success" },
            { timestamp: new Date(Date.now() - 10800000).toISOString(), message: "Disk space check: OK", type: "info" },
            { timestamp: new Date(Date.now() - 14400000).toISOString(), message: "Log rotation in progress", type: "warning" }
        ];

        return {
            status: 'success',
            logs: sampleLogs.slice(0, limit),
            simulated: true
        };
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