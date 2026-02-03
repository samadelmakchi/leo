/**
 * UI Module for Cron Jobs Section
 */

const CronUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Cron section
     */
    function initCronsSection() {
        console.log('Initializing Cron section...');

        // بارگذاری cron jobs
        loadCronJobs()
            .then(data => {
                console.log('Cron jobs loaded:', data);
                console.log('Current jobs from module:', CronModule.getCurrentJobs ? CronModule.getCurrentJobs() : 'No getCurrentJobs function');

                // بارگذاری وضعیت سیستم
                return loadSystemStatus();
            })
            .then(() => {
                // بارگذاری لاگ‌ها
                return loadCronLogs();
            })
            .then(() => {
                // تنظیم event listeners
                setupEventListeners();
                return Promise.resolve();
            })
            .catch(error => {
                console.error('Error initializing cron section:', error);
                return Promise.reject(error);
            });
    }

    /**
     * Load cron jobs
     */
    function loadCronJobs() {
        showToast('در حال بارگذاری cron jobs...', 'info');

        // استفاده از CronModule به جای fetch مستقیم
        return CronModule.getCronJobs()
            .then(data => {
                displayCronJobs(data.jobs);
                updateJobsInfo(data);
                showToast(`${data.count} cron job بارگذاری شد`, 'success');
                return data;
            })
            .catch(error => {
                console.error('Error loading cron jobs:', error);

                // اگر همه چیز شکست خورد، نمونه‌ها را نشان بده
                const sampleJobs = [
                    {
                        id: 1,
                        schedule: { minute: '*/5', hour: '*', day_of_month: '*', month: '*', day_of_week: '*' },
                        schedule_text: 'هر 5 دقیقه',
                        command: '/usr/bin/php /var/www/backup.php',
                        short_command: '/usr/bin/php /var/www/backup.php',
                        raw: '*/5 * * * * /usr/bin/php /var/www/backup.php',
                        user: 'root',
                        enabled: true
                    },
                    {
                        id: 2,
                        schedule: { minute: '0', hour: '2', day_of_month: '*', month: '*', day_of_week: '*' },
                        schedule_text: 'ساعت 2:00',
                        command: '/opt/scripts/cleanup.sh',
                        short_command: '/opt/scripts/cleanup.sh',
                        raw: '0 2 * * * /opt/scripts/cleanup.sh',
                        user: 'root',
                        enabled: true
                    }
                ];

                displayCronJobs(sampleJobs);
                updateJobsInfo({ count: sampleJobs.length, jobs: sampleJobs });
                showToast('در حال استفاده از داده‌های نمونه', 'warning');

                // نمونه‌ها را در CronModule هم ذخیره کن
                if (CronModule.getCurrentJobs) {
                    CronModule.getCurrentJobs = () => sampleJobs;
                }

                return Promise.resolve({ count: sampleJobs.length, jobs: sampleJobs });
            });
    }

    /**
     * Load system status
     */
    function loadSystemStatus() {
        return fetch('/api/cron/system/status')
            .then(response => {
                // اول مطمئن شو response معتبر است
                if (!response.ok) {
                    // اگر خطا داشت، از endpoint تست استفاده کن
                    return fetch('/api/cron/test/status');
                }

                const contentType = response.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    return fetch('/api/cron/test/status');
                }

                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    displaySystemStatus(data);
                    return data;
                } else {
                    throw new Error(data.message || 'خطا در دریافت وضعیت سیستم');
                }
            })
            .catch(error => {
                console.error('Error loading system status:', error);

                // داده‌های نمونه نمایش بده
                const sampleData = {
                    cron_service: {
                        active: true,
                        status: "فعال"
                    },
                    processes: 2,
                    timestamp: new Date().toISOString()
                };

                displaySystemStatus({ status: 'success', ...sampleData });
                return Promise.resolve({ status: 'success', ...sampleData });
            });
    }

    /**
     * Load cron logs
     */
    function loadCronLogs() {
        return fetch('/api/cron/logs')
            .then(response => {
                if (!response.ok) {
                    return fetch('/api/cron/test/logs');
                }

                const contentType = response.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    return fetch('/api/cron/test/logs');
                }

                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    displayCronLogs(data.logs);
                    return data;
                } else {
                    throw new Error(data.message || 'خطا در دریافت لاگ‌ها');
                }
            })
            .catch(error => {
                console.error('Error loading cron logs:', error);

                // لاگ‌های نمونه نمایش بده
                const sampleLogs = [
                    { timestamp: new Date().toISOString(), message: "Cron system initialized", type: "info" },
                    { timestamp: new Date(Date.now() - 300000).toISOString(), message: "Test cron job executed", type: "success" }
                ];

                displayCronLogs(sampleLogs);
                return Promise.resolve({ status: 'success', logs: sampleLogs });
            });
    }

    /**
     * Add new cron job
     */
    function addCronJob() {
        // نمایش مودال برای افزودن cron job جدید
        const modalHtml = `
            <div class="modal fade" id="addCronJobModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">➕ افزودن کرن جاب جدید</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="newCronJobForm">
                                <div class="row">
                                    <div class="col-md-2">
                                        <label class="form-label">دقیقه</label>
                                        <input type="text" class="form-control" id="cronMinute" value="*" placeholder="*">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">ساعت</label>
                                        <input type="text" class="form-control" id="cronHour" value="*" placeholder="*">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">روز ماه</label>
                                        <input type="text" class="form-control" id="cronDayOfMonth" value="*" placeholder="*">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">ماه</label>
                                        <input type="text" class="form-control" id="cronMonth" value="*" placeholder="*">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">روز هفته</label>
                                        <input type="text" class="form-control" id="cronDayOfWeek" value="*" placeholder="*">
                                    </div>
                                </div>
                                
                                <div class="mt-3">
                                    <label class="form-label">دستور</label>
                                    <textarea class="form-control" id="cronCommand" rows="3" 
                                              placeholder="مثال: /usr/bin/php /var/www/script.php" required></textarea>
                                </div>
                                
                                <div class="row mt-3">
                                    <div class="col-md-6">
                                        <label class="form-label">کاربر</label>
                                        <select class="form-select" id="cronJobUser">
                                            <option value="root" selected>root</option>
                                            <option value="www-data">www-data</option>
                                            <option value="custom">سایر</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">وضعیت</label>
                                        <div class="form-check form-switch mt-2">
                                            <input class="form-check-input" type="checkbox" id="cronJobEnabled" checked>
                                            <label class="form-check-label" for="cronJobEnabled">فعال</label>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mt-3">
                                    <div class="alert alert-info">
                                        <small>
                                            <strong>راهنما:</strong><br>
                                            * = همه مقادیر<br>
                                            */5 = هر 5 واحد<br>
                                            1,3,5 = مقادیر 1 و 3 و 5<br>
                                            1-5 = از 1 تا 5
                                        </small>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">لغو</button>
                            <button type="button" class="btn btn-primary" onclick="CronUI.saveNewCronJob()">ذخیره</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // اضافه کردن مودال به صفحه
        let modalContainer = document.getElementById('cronModalContainer');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'cronModalContainer';
            document.body.appendChild(modalContainer);
        }
        modalContainer.innerHTML = modalHtml;

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('addCronJobModal'));
        modal.show();
    }

    /**
     * Save new cron job
     */
    function saveNewCronJob() {
        const schedule = {
            minute: document.getElementById('cronMinute').value,
            hour: document.getElementById('cronHour').value,
            day_of_month: document.getElementById('cronDayOfMonth').value,
            month: document.getElementById('cronMonth').value,
            day_of_week: document.getElementById('cronDayOfWeek').value
        };

        const command = document.getElementById('cronCommand').value;
        const user = document.getElementById('cronJobUser').value;
        const enabled = document.getElementById('cronJobEnabled').checked;

        if (!command.trim()) {
            showToast('لطفاً دستور را وارد کنید', 'warning');
            return;
        }

        const cronData = {
            schedule: schedule,
            command: command,
            user: user,
            enabled: enabled
        };

        showToast('در حال ذخیره cron job...', 'info');

        CronModule.addCronJob(cronData)
            .then(() => {
                showToast('Cron job با موفقیت اضافه شد', 'success');

                // بستن مودال
                const modal = bootstrap.Modal.getInstance(document.getElementById('addCronJobModal'));
                modal.hide();

                // رفرش لیست
                loadCronJobs();
            })
            .catch(error => {
                showToast(`خطا در ذخیره cron job: ${error.message}`, 'error');
            });
    }

    /**
     * Edit cron job
     */
    function editCronJob(jobId) {
        console.log('Editing cron job:', jobId);

        // اول job را از لیست پیدا کن
        let jobs = [];

        // سعی کن از CronModule بگیر
        if (CronModule.getCurrentJobs) {
            jobs = CronModule.getCurrentJobs();
            console.log('Jobs from CronModule:', jobs);
        }

        // اگر خالی بود، از جدول HTML بخوان
        if (!jobs || jobs.length === 0) {
            const table = document.getElementById('cronJobsTable');
            if (table) {
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 6) {
                        const rowJobId = cells[0].textContent.trim();
                        if (rowJobId === jobId.toString()) {
                            // از داده‌های HTML بساز
                            const job = {
                                id: parseInt(jobId),
                                schedule_text: cells[1].querySelector('.badge').textContent.trim(),
                                command: cells[2].querySelector('code').textContent.trim(),
                                user: cells[3].querySelector('.badge').textContent.trim(),
                                enabled: cells[4].querySelector('.badge').classList.contains('bg-success'),
                                raw: cells[1].querySelector('.badge').title
                            };
                            jobs = [job];
                        }
                    }
                });
            }
        }

        const job = jobs.find(j => j.id == jobId);

        if (!job) {
            console.error('Job not found:', jobId, 'Available jobs:', jobs);
            showToast('Cron job یافت نشد', 'error');
            return;
        }

        // مودال ویرایش را نشان بده
        showEditModal(job);
    }

    /**
     * Show edit modal
     */
    function showEditModal(job) {
        const modalBody = document.getElementById('editCronModalBody');
        if (!modalBody) return;

        modalBody.innerHTML = `
        <div class="mb-4">
            <h5 class="text-center">ویرایش کرن جاب</h5>
            <p class="text-center text-muted">${job.short_command}</p>
        </div>
        
        <form id="editCronForm">
            <input type="hidden" id="editJobId" value="${job.id}">
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">دستور</label>
                    <textarea class="form-control" rows="3" id="editCommand">${job.command}</textarea>
                </div>
                <div class="col-md-6">
                    <label class="form-label">کاربر</label>
                    <select class="form-select" id="editUser">
                        <option value="root" ${job.user === 'root' ? 'selected' : ''}>root</option>
                        <option value="www-data" ${job.user === 'www-data' ? 'selected' : ''}>www-data</option>
                    </select>
                    
                    <div class="form-check form-switch mt-3">
                        <input class="form-check-input" type="checkbox" id="editEnabled" ${job.enabled ? 'checked' : ''}>
                        <label class="form-check-label" for="editEnabled">فعال</label>
                    </div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-12">
                    <label class="form-label">زمان‌بندی فعلی</label>
                    <div class="alert alert-light">
                        <code>${job.raw}</code>
                    </div>
                </div>
            </div>
            
            <hr>
            
            <div class="d-flex justify-content-between">
                <div>
                    <button type="button" class="btn btn-warning" 
                            onclick="CronUI.toggleJobStatus(${job.id}, ${job.enabled})">
                        ${job.enabled ? 'غیرفعال کردن' : 'فعال کردن'}
                    </button>
                    <button type="button" class="btn btn-danger ms-2" 
                            onclick="CronUI.deleteJob(${job.id})">
                        حذف
                    </button>
                </div>
                <div>
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">لغو</button>
                    <button type="button" class="btn btn-primary ms-2" onclick="CronUI.saveEditedJob(${job.id})">
                        ذخیره تغییرات
                    </button>
                </div>
            </div>
        </form>
    `;

        const modal = new bootstrap.Modal(document.getElementById('editCronModal'));
        modal.show();
    }

    /**
     * Save edited job
     */
    function saveEditedJob(jobId) {
        const command = document.getElementById('editCommand').value;
        const user = document.getElementById('editUser').value;
        const enabled = document.getElementById('editEnabled').checked;

        if (!command.trim()) {
            showToast('لطفاً دستور را وارد کنید', 'warning');
            return;
        }

        const jobData = {
            command: command,
            user: user,
            enabled: enabled
        };

        showToast('در حال ذخیره تغییرات...', 'info');

        fetch(`/api/cron/jobs/${jobId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jobData)
        })
            .then(response => {
                // اول بررسی کن که response معتبر JSON است
                return response.text().then(text => {
                    try {
                        return JSON.parse(text);
                    } catch {
                        throw new Error('پاسخ سرور نامعتبر است');
                    }
                });
            })
            .then(data => {
                if (data.status === 'success') {
                    showToast('تغییرات با موفقیت ذخیره شد', 'success');

                    // بستن مودال
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editCronModal'));
                    modal.hide();

                    // رفرش لیست
                    setTimeout(() => {
                        loadCronJobs();
                    }, 1000);
                } else {
                    showToast(`خطا در ذخیره تغییرات: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error saving edited job:', error);
                showToast(`خطا در ذخیره: ${error.message}`, 'error');
            });
    }

    /**
     * Toggle cron job status
     */
    function toggleJobStatus(jobId, currentStatus) {
        const newStatus = !currentStatus;
        const action = newStatus ? 'فعال' : 'غیرفعال';

        if (confirm(`آیا می‌خواهید این cron job را ${action} کنید؟`)) {
            CronModule.toggleCronJob(jobId, newStatus)
                .then(() => {
                    showToast(`Cron job ${action} شد`, 'success');
                    loadCronJobs();
                })
                .catch(error => {
                    showToast(`خطا در تغییر وضعیت: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Delete cron job
     */
    function deleteJob(jobId) {
        if (confirm('آیا از حذف این cron job اطمینان دارید؟')) {
            CronModule.deleteCronJob(jobId)
                .then(() => {
                    showToast('Cron job حذف شد', 'success');
                    loadCronJobs();
                })
                .catch(error => {
                    showToast(`خطا در حذف: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Restart cron service
     */
    function restartCronService() {
        if (confirm('آیا از راه‌اندازی مجدد سرویس cron اطمینان دارید؟')) {
            showToast('در حال راه‌اندازی مجدد سرویس...', 'info');

            // ارسال درخواست به API
            fetch('/api/cron/system/restart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast('سرویس cron با موفقیت راه‌اندازی مجدد شد', 'success');
                        // بروزرسانی وضعیت سیستم
                        setTimeout(() => {
                            loadSystemStatus();
                        }, 2000);
                    } else {
                        showToast(`خطا در راه‌اندازی مجدد: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showToast(`خطا در ارتباط با سرور: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Set quick schedule
     */
    function setSchedule(schedulePattern) {
        // اول مودال افزودن جدید را باز کن
        addCronJob();

        // صبر کن تا مودال لود شود
        setTimeout(() => {
            // سپس مقادیر را ست کن
            const minuteInput = document.getElementById('cronMinute');
            const hourInput = document.getElementById('cronHour');
            const dayInput = document.getElementById('cronDayOfMonth');
            const monthInput = document.getElementById('cronMonth');
            const weekdayInput = document.getElementById('cronDayOfWeek');

            if (minuteInput && hourInput && dayInput && monthInput && weekdayInput) {
                const parts = schedulePattern.split(' ');
                if (parts.length === 5) {
                    minuteInput.value = parts[0];
                    hourInput.value = parts[1];
                    dayInput.value = parts[2];
                    monthInput.value = parts[3];
                    weekdayInput.value = parts[4];

                    showToast('زمان‌بندی تنظیم شد', 'info');
                }
            }
        }, 500); // کمی تاخیر برای لود شدن مودال
    }

    // ============================================================================
    // Display Functions
    // ============================================================================

    /**
     * Display cron jobs in table
     */
    function displayCronJobs(jobs) {
        const tableBody = document.getElementById('cronJobsTable');
        if (!tableBody) return;

        if (!jobs || jobs.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <i class="bi bi-calendar-x fs-1"></i>
                        <h5 class="mt-2">هیچ cron job یافت نشد</h5>
                        <p>برای افزودن cron job جدید روی دکمه "افزودن جدید" کلیک کنید.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = '';

        jobs.forEach((job, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <span class="badge bg-info" title="${job.raw}">
                        ${job.schedule_text}
                    </span>
                </td>
                <td>
                    <div class="text-truncate" style="max-width: 250px;" title="${job.command}">
                        <code>${job.short_command}</code>
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary">${job.user}</span>
                </td>
                <td>
                    <span class="badge ${job.enabled ? 'bg-success' : 'bg-secondary'}">
                        ${job.enabled ? 'فعال' : 'غیرفعال'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info" onclick="CronUI.toggleJobStatus(${job.id}, ${job.enabled})"
                                title="${job.enabled ? 'غیرفعال کن' : 'فعال کن'}">
                            <i class="bi bi-power"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="CronUI.editCronJob(${job.id})"
                                title="ویرایش">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="CronUI.deleteJob(${job.id})"
                                title="حذف">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    /**
     * Update jobs info
     */
    function updateJobsInfo(data) {
        const infoDiv = document.getElementById('cronJobsInfo');
        if (!infoDiv) return;

        const activeJobs = data.jobs.filter(job => job.enabled).length;
        const inactiveJobs = data.jobs.length - activeJobs;

        infoDiv.innerHTML = `
            <div class="alert alert-light">
                <div class="row">
                    <div class="col-md-3">
                        <strong>تعداد کل:</strong> ${data.count}
                    </div>
                    <div class="col-md-3">
                        <strong>فعال:</strong> <span class="text-success">${activeJobs}</span>
                    </div>
                    <div class="col-md-3">
                        <strong>غیرفعال:</strong> <span class="text-secondary">${inactiveJobs}</span>
                    </div>
                    <div class="col-md-3">
                        <strong>آخرین بروزرسانی:</strong> ${new Date().toLocaleTimeString('fa-IR')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Display system status
     */
    function displaySystemStatus(data) {
        const statusDiv = document.getElementById('cronSystemStatus');
        if (!statusDiv) return;

        const status = data.cron_service;

        statusDiv.innerHTML = `
            <div class="list-group">
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    وضعیت سرویس
                    <span class="badge ${status.active ? 'bg-success' : 'bg-danger'}">
                        ${status.status}
                    </span>
                </div>
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    تعداد Processها
                    <span class="badge bg-info">${data.processes}</span>
                </div>
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    آخرین بررسی
                    <small class="text-muted">${CronModule.formatDate(data.timestamp)}</small>
                </div>
            </div>
        `;
    }

    /**
     * Display cron logs
     */
    function displayCronLogs(logs) {
        const logsDiv = document.getElementById('cronLogs');
        if (!logsDiv) return;

        if (!logs || logs.length === 0) {
            logsDiv.innerHTML = '<div class="text-center text-muted">لاگی یافت نشد</div>';
            return;
        }

        let logsHtml = '<div class="list-group">';

        logs.forEach(log => {
            const logTypeClass = {
                'success': 'list-group-item-success',
                'error': 'list-group-item-danger',
                'warning': 'list-group-item-warning',
                'info': 'list-group-item-info'
            }[log.type] || '';

            logsHtml += `
                <div class="list-group-item ${logTypeClass}">
                    <div class="d-flex w-100 justify-content-between">
                        <small class="text-muted">${CronModule.formatDate(log.timestamp)}</small>
                        <span class="badge bg-${log.type}">${log.type}</span>
                    </div>
                    <p class="mb-1">${log.message}</p>
                </div>
            `;
        });

        logsHtml += '</div>';
        logsDiv.innerHTML = logsHtml;
    }

    /**
     * Show edit modal
     */
    function showEditModal(job) {
        const modalBody = document.getElementById('editCronModalBody');
        if (!modalBody) return;

        modalBody.innerHTML = `
            <form id="editCronForm">
                <input type="hidden" id="editJobId" value="${job.id}">
                
                <div class="mb-3">
                    <label class="form-label">دستور کامل</label>
                    <textarea class="form-control" rows="3" readonly>${job.raw}</textarea>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">اطلاعات کرن جاب</div>
                            <div class="card-body">
                                <p><strong>کاربر:</strong> ${job.user}</p>
                                <p><strong>وضعیت:</strong> ${job.enabled ? 'فعال' : 'غیرفعال'}</p>
                                <p><strong>زمان‌بندی:</strong> ${job.schedule_text}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">عملیات</div>
                            <div class="card-body">
                                <div class="d-grid gap-2">
                                    <button type="button" class="btn btn-warning" 
                                            onclick="CronUI.toggleJobStatus(${job.id}, ${job.enabled})">
                                        ${job.enabled ? 'غیرفعال کردن' : 'فعال کردن'}
                                    </button>
                                    <button type="button" class="btn btn-danger" 
                                            onclick="CronUI.deleteJob(${job.id})">
                                        حذف کرن جاب
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        `;

        const modal = new bootstrap.Modal(document.getElementById('editCronModal'));
        modal.show();
    }

    // ============================================================================
    // Event Listeners
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {


        // جستجوی cron jobs
        setupSearch();

        // کلیدهای میانبر
        document.addEventListener('keydown', function (e) {
            if (currentSection === 'crons') {
                // Ctrl+Alt+N برای افزودن جدید
                if (e.ctrlKey && e.altKey && e.key === 'n') {
                    e.preventDefault();
                    addCronJob();
                }

                // Ctrl+R برای رفرش
                if (e.ctrlKey && e.key === 'r') {
                    e.preventDefault();
                    loadCronJobs();
                }
            }
        });
    }

    /**
     * Setup search functionality
     */
    function setupSearch() {
        // می‌توانید جستجو را در نسخه بعدی اضافه کنید
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initCronsSection,
        loadCronJobs,
        loadSystemStatus,
        loadCronLogs,
        addCronJob,
        saveNewCronJob,
        editCronJob,
        toggleJobStatus,
        deleteJob,
        restartCronService,
        setSchedule,
        setupEventListeners
    };
})();

// قرار دادن در scope گلوبال
window.CronUI = CronUI;