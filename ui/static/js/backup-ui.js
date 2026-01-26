/**
 * UI Module for Backup Section
 */

const BackupUI = (function () {
    // متغیرهای داخلی
    let backupData = {};

    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Backup section
     */
    function initBackupSection() {
        console.log('Initializing Backup section...');

        // بارگذاری لیست بک‌اپ‌ها
        return loadBackups()
            .then(() => {
                setupEventListeners();
                return Promise.resolve();
            })
            .catch(error => {
                console.error('Error initializing backup section:', error);
                showToast('خطا در بارگذاری لیست بک‌اپ‌ها', 'error');
                return Promise.reject(error);
            });
    }

    /**
     * Load backup list
     */
    function loadBackups() {
        showToast('در حال بارگذاری لیست بک‌اپ‌ها...', 'info');

        return fetch('/api/backup/list')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    backupData = data;
                    displayBackups(data.customers);
                    showToast('لیست بک‌اپ‌ها بارگذاری شد', 'success');
                    return data;
                } else {
                    throw new Error(data.message || 'خطا در دریافت لیست بک‌اپ‌ها');
                }
            })
            .catch(error => {
                console.error('Error loading backups:', error);
                showToast(`خطا در بارگذاری بک‌اپ‌ها: ${error.message}`, 'error');

                // نمایش پیام خطا
                const container = document.getElementById('backupTableBody');
                if (container) {
                    container.innerHTML = `
                        <tr>
                            <td colspan="7" class="text-center text-danger">
                                <div class="py-4">
                                    <i class="bi bi-exclamation-triangle fs-1"></i>
                                    <h5 class="mt-2">خطا در بارگذاری بک‌اپ‌ها</h5>
                                    <p class="text-muted">${error.message}</p>
                                    <button class="btn btn-primary mt-2" onclick="BackupUI.loadBackups()">
                                        تلاش مجدد
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                }
                return Promise.reject(error);
            });
    }

    /**
     * Display backups in table
     */
    function displayBackups(customers) {
        const tbody = document.getElementById('backupTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!customers || Object.keys(customers).length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        <div class="py-4">
                            <i class="bi bi-inbox fs-1"></i>
                            <h5 class="mt-2">هیچ بک‌اپی یافت نشد</h5>
                            <p>هنوز بک‌اپی برای هیچ مشتری ایجاد نشده است.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        let rowIndex = 0;

        Object.entries(customers).forEach(([customerId, customerData]) => {
            const customerName = customerData.name;

            if (customerData.backups.length === 0) {
                // اگر مشتری بک‌اپی ندارد
                tbody.innerHTML += `
                    <tr class="table-secondary">
                        <td>${++rowIndex}</td>
                        <td>
                            <span class="fw-bold">${customerName}</span>
                            <br><small class="text-muted">${customerId}</small>
                        </td>
                        <td colspan="6" class="text-center text-muted">
                            <i class="bi bi-info-circle"></i> هیچ بک‌اپی یافت نشد
                        </td>
                    </tr>
                `;
                return;
            }

            // نمایش هر بک‌اپ
            customerData.backups.forEach((backup, backupIndex) => {
                const isFirstBackup = backupIndex === 0;

                tbody.innerHTML += `
                    <tr ${isFirstBackup ? 'class="table-light"' : ''}>
                        ${isFirstBackup ? `
                            <td rowspan="${customerData.backups.length}">${++rowIndex}</td>
                            <td rowspan="${customerData.backups.length}">
                                <span class="fw-bold">${customerName}</span>
                                <br><small class="text-muted">${customerId}</small>
                                <br><small class="badge ${customerData.backup_enabled ? 'bg-success' : 'bg-secondary'}">
                                    ${customerData.backup_enabled ? 'فعال' : 'غیرفعال'}
                                </small>
                            </td>
                        ` : ''}
                        <td>
                            <span class="fw-bold">${backup.name}</span>
                            <br><small class="text-muted">${backup.full_date}</small>
                        </td>
                        <td>
                            <span class="badge bg-info">${backup.file_count} فایل</span>
                        </td>
                        <td>${backup.size_formatted}</td>
                        <td>
                            <span class="badge bg-primary">${backup.files.databases.length} دیتابیس</span>
                            <span class="badge bg-warning">${backup.files.volumes.length} ولوم</span>
                        </td>
                        <td>
                            <div class="btn-group btn-group-sm" role="group">
                                <button class="btn btn-outline-info" 
                                        onclick="BackupUI.showBackupDetails('${customerId}', '${backup.name}')"
                                        title="مشاهده جزئیات">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button class="btn btn-outline-success"
                                        onclick="BackupUI.downloadBackup('${customerId}', '${backup.name}')"
                                        title="دانلود بک‌اپ">
                                    <i class="bi bi-download"></i>
                                </button>
                                <button class="btn btn-outline-danger"
                                        onclick="BackupUI.confirmDeleteBackup('${customerId}', '${backup.name}', '${customerName}')"
                                        title="حذف بک‌اپ">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        });

        // آپدیت خلاصه اطلاعات
        updateBackupSummary(customers);
    }

    /**
     * Update backup summary
     */
    function updateBackupSummary(customers) {
        let totalCustomers = 0;
        let totalBackups = 0;
        let totalSize = 0;

        Object.values(customers).forEach(customer => {
            totalCustomers++;
            totalBackups += customer.total_backups || 0;
            totalSize += customer.total_size || 0;
        });

        document.getElementById('backupCustomerCount').textContent = totalCustomers;
        document.getElementById('backupTotalCount').textContent = totalBackups;

        const sizeGB = totalSize / (1024 * 1024 * 1024);
        document.getElementById('backupTotalSize').textContent =
            sizeGB >= 1 ? `${sizeGB.toFixed(2)} GB` : `${(totalSize / (1024 * 1024)).toFixed(2)} MB`;
    }

    /**
     * Show backup details
     */
    function showBackupDetails(customerId, backupName) {
        const customer = backupData.customers[customerId];
        if (!customer) return;

        const backup = customer.backups.find(b => b.name === backupName);
        if (!backup) return;

        // ایجاد مودال برای نمایش جزئیات
        const modalHtml = `
            <div class="modal fade" id="backupDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-archive"></i> جزئیات بک‌اپ
                                <small class="text-muted">${customer.name} - ${backup.name}</small>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h6>اطلاعات کلی</h6>
                                    <table class="table table-sm">
                                        <tr>
                                            <th>مشتری:</th>
                                            <td>${customer.name} <small class="text-muted">(${customerId})</small></td>
                                        </tr>
                                        <tr>
                                            <th>تاریخ ایجاد:</th>
                                            <td>${backup.full_date}</td>
                                        </tr>
                                        <tr>
                                            <th>تعداد فایل‌ها:</th>
                                            <td>${backup.file_count} فایل</td>
                                        </tr>
                                        <tr>
                                            <th>حجم کل:</th>
                                            <td>${backup.size_formatted}</td>
                                        </tr>
                                        <tr>
                                            <th>مسیر:</th>
                                            <td><small class="text-muted">${backup.path}</small></td>
                                        </tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>آمار فایل‌ها</h6>
                                    <div class="row">
                                        <div class="col-6">
                                            <div class="card bg-primary text-white">
                                                <div class="card-body text-center">
                                                    <h2>${backup.files.databases.length}</h2>
                                                    <p>دیتابیس</p>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-6">
                                            <div class="card bg-warning text-dark">
                                                <div class="card-body text-center">
                                                    <h2>${backup.files.volumes.length}</h2>
                                                    <p>ولوم</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <h6>فایل‌های دیتابیس</h6>
                            ${backup.files.databases.length > 0 ? `
                                <div class="table-responsive mb-4">
                                    <table class="table table-sm table-striped">
                                        <thead>
                                            <tr>
                                                <th>نام فایل</th>
                                                <th>حجم</th>
                                                <th>عملیات</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${backup.files.databases.map(file => `
                                                <tr>
                                                    <td><small>${file.name}</small></td>
                                                    <td>${file.size_formatted}</td>
                                                    <td>
                                                        <button class="btn btn-sm btn-outline-success"
                                                                onclick="BackupUI.downloadFile('${customerId}', '${backup.name}', '${file.name}')">
                                                            <i class="bi bi-download"></i> دانلود
                                                        </button>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : '<p class="text-muted">هیچ فایل دیتابیسی یافت نشد</p>'}
                            
                            <h6>فایل‌های ولوم</h6>
                            ${backup.files.volumes.length > 0 ? `
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped">
                                        <thead>
                                            <tr>
                                                <th>نام فایل</th>
                                                <th>حجم</th>
                                                <th>عملیات</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${backup.files.volumes.map(file => `
                                                <tr>
                                                    <td><small>${file.name}</small></td>
                                                    <td>${file.size_formatted}</td>
                                                    <td>
                                                        <button class="btn btn-sm btn-outline-success"
                                                                onclick="BackupUI.downloadFile('${customerId}', '${backup.name}', '${file.name}')">
                                                            <i class="bi bi-download"></i> دانلود
                                                        </button>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : '<p class="text-muted">هیچ فایل ولومی یافت نشد</p>'}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                            <button type="button" class="btn btn-danger" 
                                    onclick="BackupUI.confirmDeleteBackup('${customerId}', '${backup.name}', '${customer.name}')">
                                حذف این بک‌اپ
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // اضافه کردن مودال به صفحه
        let modalContainer = document.getElementById('backupModalContainer');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'backupModalContainer';
            document.body.appendChild(modalContainer);
        }
        modalContainer.innerHTML = modalHtml;

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('backupDetailsModal'));
        modal.show();
    }

    /**
     * Download backup file
     */
    function downloadBackup(customerId, backupName) {
        showToast('در حال آماده‌سازی دانلود...', 'info');

        // ایجاد یک لینک موقتی برای دانلود
        const url = `/api/backup/download?customer=${encodeURIComponent(customerId)}&backup_name=${encodeURIComponent(backupName)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `${customerId}_${backupName}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('دانلود آغاز شد', 'success');
    }

    /**
     * Download single file
     */
    function downloadFile(customerId, backupName, fileName) {
        const url = `/api/backup/download?customer=${encodeURIComponent(customerId)}&backup_name=${encodeURIComponent(backupName)}&file_name=${encodeURIComponent(fileName)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast(`فایل ${fileName} در حال دانلود است`, 'info');
    }

    /**
     * Confirm delete backup
     */
    function confirmDeleteBackup(customerId, backupName, customerName) {
        if (confirm(`آیا از حذف بک‌اپ "${backupName}" مربوط به مشتری "${customerName}" اطمینان دارید؟\n\nاین عمل غیرقابل بازگشت است!`)) {
            deleteBackup(customerId, backupName);
        }
    }

    /**
     * Delete backup
     */
    function deleteBackup(customerId, backupName) {
        showToast('در حال حذف بک‌اپ...', 'info');

        fetch('/api/backup/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer: customerId,
                backup_name: backupName
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('بک‌اپ با موفقیت حذف شد', 'success');
                    loadBackups(); // رفرش لیست
                } else {
                    showToast(`خطا در حذف بک‌اپ: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                showToast(`خطا در حذف بک‌اپ: ${error.message}`, 'error');
            });
    }

    /**
     * Refresh backup list
     */
    function refreshBackups() {
        return loadBackups();
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // دکمه بروزرسانی
        const refreshBtn = document.querySelector('#backupSection .btn-primary');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshBackups);
        }

        // جستجوی بک‌اپ
        const searchInput = document.getElementById('searchBackup');
        if (searchInput) {
            searchInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    searchBackups();
                }
            });
        }
    }

    /**
     * Search backups
     */
    function searchBackups() {
        const searchTerm = document.getElementById('searchBackup').value.toLowerCase();
        const rows = document.querySelectorAll('#backupTableBody tr');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initBackupSection,
        loadBackups,
        showBackupDetails,
        downloadBackup,
        downloadFile,
        confirmDeleteBackup,
        deleteBackup,
        refreshBackups,
        searchBackups
    };
})();

// قرار دادن ماژول در scope گلوبال
window.BackupUI = BackupUI;