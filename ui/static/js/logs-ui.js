/**
 * UI Module for Logs Section
 */

const LogsUI = (function () {
    // متغیرهای داخلی
    let logsData = {};

    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Logs section
     */
    function initLogsSection() {
        console.log('Initializing Logs section...');

        // بارگذاری لیست لاگ‌ها
        return loadLogs()
            .then(() => {
                setupEventListeners();
                return Promise.resolve();
            })
            .catch(error => {
                console.error('Error initializing logs section:', error);
                showToast('خطا در بارگذاری لیست لاگ‌ها', 'error');
                return Promise.reject(error);
            });
    }

    /**
     * Load logs list
     */
    function loadLogs() {
        showToast('در حال بارگذاری لیست لاگ‌ها...', 'info');

        return fetch('/api/logs/list')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    logsData = data;
                    displayLogs(data.logs);
                    showToast('لیست لاگ‌ها بارگذاری شد', 'success');
                    return data;
                } else {
                    throw new Error(data.message || 'خطا در دریافت لیست لاگ‌ها');
                }
            })
            .catch(error => {
                console.error('Error loading logs:', error);
                showToast(`خطا در بارگذاری لاگ‌ها: ${error.message}`, 'error');

                // نمایش پیام خطا
                const container = document.getElementById('logsContent');
                if (container) {
                    container.innerHTML = `
                        <div class="alert alert-danger">
                            <h4>خطا در بارگذاری لاگ‌ها</h4>
                            <p>${error.message}</p>
                            <button class="btn btn-primary mt-2" onclick="LogsUI.loadLogs()">
                                تلاش مجدد
                            </button>
                        </div>
                    `;
                }
                return Promise.reject(error);
            });
    }

    /**
     * Display logs in tabs
     */
    function displayLogs(logs) {
        const container = document.getElementById('logsContent');
        if (!container) return;

        container.innerHTML = `
            <ul class="nav nav-tabs mb-3" id="logsTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="customer-logs-tab" data-bs-toggle="tab" 
                            data-bs-target="#customer-logs" type="button" role="tab">
                        <i class="bi bi-people"></i> لاگ مشتریان
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="backup-logs-tab" data-bs-toggle="tab" 
                            data-bs-target="#backup-logs" type="button" role="tab">
                        <i class="bi bi-archive"></i> لاگ‌های بک‌اپ
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="cron-log-tab" data-bs-toggle="tab" 
                            data-bs-target="#cron-log" type="button" role="tab">
                        <i class="bi bi-clock"></i> لاگ Cron
                    </button>
                </li>
            </ul>
            
            <div class="tab-content" id="logsTabContent">
                <div class="tab-pane fade show active" id="customer-logs" role="tabpanel">
                    <div id="customerLogsContent"></div>
                </div>
                <div class="tab-pane fade" id="backup-logs" role="tabpanel">
                    <div id="backupLogsContent"></div>
                </div>
                <div class="tab-pane fade" id="cron-log" role="tabpanel">
                    <div id="cronLogContent"></div>
                </div>
            </div>
        `;

        // پر کردن تب‌ها
        displayCustomerLogs(logs.customers, document.getElementById('customerLogsContent'));
        displayBackupLogs(logs.backup, document.getElementById('backupLogsContent'));
        displayCronLog(logs.cron, document.getElementById('cronLogContent'));
    }

    /**
     * Display customer logs
     */
    function displayCustomerLogs(customers, container) {
        if (!container) return;

        if (!customers || Object.keys(customers).length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    هیچ لاگ مشتری یافت نشد
                </div>
            `;
            return;
        }

        let html = '';

        Object.entries(customers).forEach(([customerId, customerData]) => {
            html += `
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-0">
                                <i class="bi bi-person-circle"></i> ${customerData.name}
                                <small class="text-muted">(${customerId})</small>
                            </h5>
                            <small class="text-muted">${customerData.total_logs} فایل لاگ</small>
                        </div>
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="LogsUI.viewAllCustomerLogs('${customerId}')">
                            مشاهده همه
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="row">
            `;

            customerData.logs.forEach(log => {
                const badgeClass = log.type === 'databases' ? 'bg-primary' :
                    log.type === 'volumes' ? 'bg-warning' : 'bg-secondary';

                html += `
                    <div class="col-md-6 mb-2">
                        <div class="card h-100">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h6 class="card-title">
                                            <span class="badge ${badgeClass}">${log.type === 'databases' ? 'دیتابیس' : 'ولوم'}</span>
                                            ${log.name}
                                        </h6>
                                        <p class="card-text small text-muted mb-1">
                                            <i class="bi bi-clock"></i> ${log.modified}
                                        </p>
                                        <p class="card-text small mb-1">
                                            <i class="bi bi-file-text"></i> ${log.line_count} خط | 
                                            <i class="bi bi-hdd"></i> ${log.size_formatted}
                                        </p>
                                    </div>
                                    <div class="btn-group btn-group-sm">
                                        <button class="btn btn-outline-info" 
                                                onclick="LogsUI.viewLog('${log.path}')"
                                                title="مشاهده">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                        <button class="btn btn-outline-success"
                                                onclick="LogsUI.downloadLog('${log.path}')"
                                                title="دانلود">
                                            <i class="bi bi-download"></i>
                                        </button>
                                    </div>
                                </div>
                                
                                ${log.analysis ? `
                                    <div class="mt-2">
                                        <small class="d-block">
                                            <span class="badge bg-success">${log.analysis.success_count || 0} موفق</span>
                                            <span class="badge bg-danger">${log.analysis.error_count || 0} خطا</span>
                                            <span class="badge bg-warning">${log.analysis.warning_count || 0} هشدار</span>
                                        </small>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    /**
     * Display backup logs
     */
    function displayBackupLogs(backupLogs, container) {
        if (!container) return;

        if (!backupLogs || Object.keys(backupLogs).length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    هیچ فایل لاگ بک‌اپ یافت نشد
                </div>
            `;
            return;
        }

        let html = `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead>
                        <tr>
                            <th>نام فایل</th>
                            <th>سایز</th>
                            <th>تعداد خطوط</th>
                            <th>آخرین تغییر</th>
                            <th>عملیات</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        Object.entries(backupLogs).forEach(([logName, logInfo]) => {
            html += `
                <tr>
                    <td>
                        <strong>${logName}</strong>
                        <br>
                        <small class="text-muted">${logInfo.path}</small>
                    </td>
                    <td>${logInfo.size_formatted}</td>
                    <td>${logInfo.line_count} خط</td>
                    <td>${logInfo.modified}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-info" 
                                    onclick="LogsUI.viewLog('${logInfo.path}')"
                                    title="مشاهده">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-outline-success"
                                    onclick="LogsUI.downloadLog('${logInfo.path}')"
                                    title="دانلود">
                                <i class="bi bi-download"></i>
                            </button>
                            <button class="btn btn-outline-danger"
                                    onclick="LogsUI.confirmClearLog('${logInfo.path}', '${logName}')"
                                    title="پاک کردن">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Display cron log
     */
    function displayCronLog(cronLog, container) {
        if (!container) return;

        if (!cronLog || Object.keys(cronLog).length === 0) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    فایل لاگ Cron یافت نشد
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-clock"></i> ${cronLog.name}
                        <small class="text-muted">(${cronLog.size_formatted})</small>
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3>${cronLog.line_count}</h3>
                                    <p class="mb-0">خط</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h3>${cronLog.size_formatted}</h3>
                                    <p class="mb-0">حجم</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card bg-light">
                                <div class="card-body">
                                    <p class="mb-1"><strong>آخرین تغییر:</strong> ${cronLog.modified}</p>
                                    <p class="mb-0"><strong>مسیر:</strong> <small class="text-muted">${cronLog.path}</small></p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="d-flex gap-2 mb-3">
                        <button class="btn btn-primary" onclick="LogsUI.viewLog('${cronLog.path}', true, 100)">
                            <i class="bi bi-eye"></i> مشاهده 100 خط آخر
                        </button>
                        <button class="btn btn-success" onclick="LogsUI.downloadLog('${cronLog.path}')">
                            <i class="bi bi-download"></i> دانلود
                        </button>
                        <button class="btn btn-danger" onclick="LogsUI.confirmClearLog('${cronLog.path}', '${cronLog.name}')">
                            <i class="bi bi-trash"></i> پاک کردن
                        </button>
                    </div>
                    
                    <div id="cronLogPreview"></div>
                </div>
            </div>
        `;

        // بارگذاری پیش‌نمایش لاگ
        viewLog(cronLog.path, true, 50, 'cronLogPreview');
    }

    /**
     * View all logs for a customer
     */
    function viewAllCustomerLogs(customerId) {
        if (!logsData.logs || !logsData.logs.customers || !logsData.logs.customers[customerId]) {
            showToast('اطلاعات مشتری یافت نشد', 'warning');
            return;
        }

        const customer = logsData.logs.customers[customerId];

        // ایجاد مودال برای نمایش همه لاگ‌های مشتری
        const modalHtml = `
            <div class="modal fade" id="customerLogsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-person-circle"></i> همه لاگ‌های ${customer.name}
                                <small class="text-muted">(${customerId})</small>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <ul class="nav nav-tabs mb-3" id="customerLogTabs">
                                ${customer.logs.map((log, index) => `
                                    <li class="nav-item">
                                        <button class="nav-link ${index === 0 ? 'active' : ''}" 
                                                data-bs-toggle="tab" 
                                                data-bs-target="#log-${customerId}-${index}">
                                            ${log.type === 'databases' ? 'دیتابیس' : 'ولوم'}
                                        </button>
                                    </li>
                                `).join('')}
                            </ul>
                            
                            <div class="tab-content">
                                ${customer.logs.map((log, index) => `
                                    <div class="tab-pane fade ${index === 0 ? 'show active' : ''}" 
                                         id="log-${customerId}-${index}">
                                        <div class="d-flex justify-content-between align-items-center mb-3">
                                            <h6>${log.name}</h6>
                                            <div class="btn-group">
                                                <button class="btn btn-sm btn-outline-success"
                                                        onclick="LogsUI.downloadLog('${log.path}')">
                                                    <i class="bi bi-download"></i> دانلود
                                                </button>
                                            </div>
                                        </div>
                                        <div id="logContent-${customerId}-${index}" 
                                             class="log-preview" 
                                             style="max-height: 400px; overflow-y: auto;">
                                            <div class="text-center text-muted py-4">
                                                <i class="bi bi-hourglass-split"></i>
                                                <p class="mt-2">در حال بارگذاری...</p>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // اضافه کردن مودال به صفحه
        let modalContainer = document.getElementById('logsModalContainer');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'logsModalContainer';
            document.body.appendChild(modalContainer);
        }
        modalContainer.innerHTML = modalHtml;

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('customerLogsModal'));
        modal.show();

        // بارگذاری محتوای اولین تب
        if (customer.logs.length > 0) {
            setTimeout(() => {
                viewLog(customer.logs[0].path, true, 100, `logContent-${customerId}-0`);
            }, 100);
        }

        // اضافه کردن event listener برای تغییر تب‌ها
        setTimeout(() => {
            document.querySelectorAll('#customerLogTabs .nav-link').forEach((tab, index) => {
                tab.addEventListener('shown.bs.tab', () => {
                    viewLog(customer.logs[index].path, true, 100, `logContent-${customerId}-${index}`);
                });
            });
        }, 200);
    }

    /**
     * View log content
     */
    function viewLog(logPath, tail = true, lines = 100, targetElementId = null) {
        showToast('در حال بارگذاری لاگ...', 'info');

        const url = `/api/logs/view?path=${encodeURIComponent(logPath)}&tail=${tail}&lines=${lines}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    let content = '';

                    if (targetElementId) {
                        // نمایش در المنت خاص
                        const target = document.getElementById(targetElementId);
                        if (target) {
                            content = formatLogContent(data.content, data.analysis);
                            target.innerHTML = content;
                        }
                    } else {
                        // نمایش در مودال جدید
                        showLogInModal(data, logPath);
                    }

                    showToast('لاگ بارگذاری شد', 'success');
                } else {
                    showToast(`خطا: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                showToast(`خطا در بارگذاری لاگ: ${error.message}`, 'error');
            });
    }

    /**
     * Show log in modal
     */
    function showLogInModal(logData, logPath) {
        const modalHtml = `
            <div class="modal fade" id="logViewModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-file-text"></i> ${logData.filename}
                                <small class="text-muted">(${logData.total_lines} خط)</small>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-12">
                                    <div class="btn-group mb-2">
                                        <button class="btn btn-sm btn-outline-primary" 
                                                onclick="LogsUI.viewLog('${logPath}', false, 100)">
                                            <i class="bi bi-arrow-up"></i> ابتدا
                                        </button>
                                        <button class="btn btn-sm btn-outline-primary" 
                                                onclick="LogsUI.viewLog('${logPath}', true, 100)">
                                            <i class="bi bi-arrow-down"></i> انتها
                                        </button>
                                        <button class="btn btn-sm btn-outline-success"
                                                onclick="LogsUI.downloadLog('${logPath}')">
                                            <i class="bi bi-download"></i> دانلود
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger"
                                                onclick="LogsUI.confirmClearLog('${logPath}', '${logData.filename}')">
                                            <i class="bi bi-trash"></i> پاک کردن
                                        </button>
                                    </div>
                                    
                                    ${logData.analysis && (logData.analysis.errors.length > 0 || logData.analysis.warnings.length > 0) ? `
                                        <div class="alert alert-warning">
                                            <strong>تحلیل لاگ:</strong>
                                            ${logData.analysis.errors.length > 0 ? `
                                                <span class="badge bg-danger me-2">${logData.analysis.errors.length} خطا</span>
                                            ` : ''}
                                            ${logData.analysis.warnings.length > 0 ? `
                                                <span class="badge bg-warning me-2">${logData.analysis.warnings.length} هشدار</span>
                                            ` : ''}
                                            ${logData.analysis.successes.length > 0 ? `
                                                <span class="badge bg-success me-2">${logData.analysis.successes.length} موفق</span>
                                            ` : ''}
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                            
                            <div class="log-content" style="max-height: 500px; overflow-y: auto; font-family: monospace; font-size: 0.9em;">
                                ${formatLogContent(logData.content, logData.analysis)}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // اضافه کردن مودال به صفحه
        let modalContainer = document.getElementById('logsModalContainer');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'logsModalContainer';
            document.body.appendChild(modalContainer);
        }
        modalContainer.innerHTML = modalHtml;

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('logViewModal'));
        modal.show();
    }

    /**
     * Format log content with highlighting
     */
    function formatLogContent(content, analysis) {
        if (!content) return '<div class="text-muted">(خالی)</div>';

        const lines = content.split('\n');
        let formatted = '';

        lines.forEach((line, index) => {
            const lineNumber = index + 1;
            let lineClass = '';

            // بررسی خطاها و هشدارها
            if (analysis) {
                const isError = analysis.errors.some(e => e.line_number === lineNumber);
                const isWarning = analysis.warnings.some(w => w.line_number === lineNumber);
                const isSuccess = analysis.successes.some(s => s.line_number === lineNumber);

                if (isError) lineClass = 'text-danger bg-danger-light';
                else if (isWarning) lineClass = 'text-warning bg-warning-light';
                else if (isSuccess) lineClass = 'text-success bg-success-light';
            }

            // هایلایت کردن تاریخ‌ها و خطوط مهم
            let formattedLine = line;

            // هایلایت تاریخ (مثل: 2025-12-10 13:36:07)
            formattedLine = formattedLine.replace(
                /(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/g,
                '<span class="text-primary fw-bold">$1</span>'
            );

            // هایلایت کلمات کلیدی
            const keywords = {
                'ERROR': 'text-danger fw-bold',
                'SUCCESS': 'text-success fw-bold',
                'WARNING': 'text-warning fw-bold',
                'START': 'text-info fw-bold',
                'FINISH': 'text-info fw-bold',
                'FAILED': 'text-danger fw-bold'
            };

            Object.entries(keywords).forEach(([keyword, className]) => {
                const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
                formattedLine = formattedLine.replace(
                    regex,
                    `<span class="${className}">${keyword}</span>`
                );
            });

            formatted += `
                <div class="log-line ${lineClass} border-bottom pb-1 mb-1">
                    <span class="text-muted me-3" style="width: 40px; display: inline-block;">${lineNumber}</span>
                    <span>${formattedLine || '&nbsp;'}</span>
                </div>
            `;
        });

        return formatted;
    }

    /**
     * Download log file
     */
    function downloadLog(logPath) {
        const url = `/api/logs/download?path=${encodeURIComponent(logPath)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = logPath.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('دانلود لاگ آغاز شد', 'success');
    }

    /**
     * Confirm clear log
     */
    function confirmClearLog(logPath, logName) {
        if (confirm(`آیا از پاک کردن لاگ "${logName}" اطمینان دارید؟\n\nاین عمل فقط محتوای فایل را پاک می‌کند.`)) {
            clearLog(logPath, logName);
        }
    }

    /**
     * Clear log file
     */
    function clearLog(logPath, logName) {
        showToast('در حال پاک کردن لاگ...', 'info');

        fetch('/api/logs/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                path: logPath
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('لاگ با موفقیت پاک شد', 'success');
                    loadLogs(); // رفرش لیست
                } else {
                    showToast(`خطا در پاک کردن لاگ: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                showToast(`خطا در پاک کردن لاگ: ${error.message}`, 'error');
            });
    }

    /**
     * Refresh logs list
     */
    function refreshLogs() {
        return loadLogs();
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // دکمه بروزرسانی
        const refreshBtn = document.querySelector('#logsSection .btn-primary');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshLogs);
        }
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initLogsSection,
        loadLogs,
        viewAllCustomerLogs,
        viewLog,
        downloadLog,
        confirmClearLog,
        clearLog,
        refreshLogs,
        formatLogContent
    };
})();

// قرار دادن ماژول در scope گلوبال
window.LogsUI = LogsUI;