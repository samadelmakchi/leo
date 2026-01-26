/**
 * UI Module for Docker Volumes Section
 */

const DockerVolumesUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Volumes section
     */
    function initVolumesSection() {
        console.log('Initializing Volumes section...');

        // بارگذاری لیست ولوم‌ها
        loadVolumes();

        // بارگذاری آمار
        refreshStats();

        // تنظیم event listeners
        setupEventListeners();

        return Promise.resolve();
    }

    /**
     * Load volumes list
     */
    function loadVolumes() {
        showToast('در حال بارگذاری لیست ولوم‌ها...', 'info');

        return DockerVolumesModule.loadVolumes()
            .then(data => {
                displayVolumes(data.volumes);
                showToast(`${data.count} ولوم بارگذاری شد`, 'success');
                return data;
            })
            .catch(error => {
                console.error('Error loading volumes:', error);
                showToast(`خطا در بارگذاری ولوم‌ها: ${error.message}`, 'error');

                // نمایش پیام خطا در جدول
                const tbody = document.getElementById('volumesTableBody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="7" class="text-center text-danger">
                                <div class="py-4">
                                    <i class="bi bi-exclamation-triangle fs-1"></i>
                                    <h5 class="mt-2">خطا در بارگذاری ولوم‌ها</h5>
                                    <p class="text-muted">${error.message}</p>
                                    <button class="btn btn-primary mt-2" onclick="DockerVolumesUI.loadVolumes()">
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
     * Display volumes in table
     */
    function displayVolumes(volumes) {
        const tbody = document.getElementById('volumesTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!volumes || volumes.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        هیچ ولومی یافت نشد
                    </td>
                </tr>
            `;
            document.getElementById('volumesCount').textContent = '0';
            return;
        }

        volumes.forEach((volume, index) => {
            const row = document.createElement('tr');

            // نمایش برچسب‌ها
            let labelsHtml = '-';
            if (volume.labels && Object.keys(volume.labels).length > 0) {
                const labelsArray = Object.entries(volume.labels).map(([key, value]) =>
                    `<span class="badge bg-secondary me-1" title="${key}: ${value}">${key}</span>`
                );
                labelsHtml = labelsArray.join('');
            }

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <strong>${volume.name}</strong>
                    ${volume.scope !== 'local' ?
                    `<span class="badge bg-warning ms-1">${volume.scope}</span>` : ''
                }
                </td>
                <td>
                    <span class="badge ${volume.driver === 'local' ? 'bg-info' : 'bg-warning'}">
                        ${volume.driver}
                    </span>
                </td>
                <td>
                    <small class="text-muted font-monospace" title="${volume.mountpoint}">
                        ${DockerVolumesModule._formatMountpoint(volume.mountpoint)}
                    </small>
                </td>
                <td>
                    <small class="text-muted">${_formatDate(volume.created)}</small>
                </td>
                <td>${labelsHtml}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info" 
                                onclick="DockerVolumesUI.showVolumeDetails('${volume.name}')"
                                title="مشاهده جزئیات">
                            👁️
                        </button>
                        <button class="btn btn-outline-primary"
                                onclick="DockerVolumesUI.inspectVolume('${volume.name}')"
                                title="مشاهده محتوا">
                            📂
                        </button>
                        <button class="btn btn-outline-danger"
                                onclick="DockerVolumesUI.confirmRemoveVolume('${volume.name}')"
                                title="حذف ولوم">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        document.getElementById('volumesCount').textContent = volumes.length;
    }

    /**
     * Refresh volumes and stats
     */
    function refreshVolumes() {
        showToast('در حال بروزرسانی ولوم‌ها...', 'info');

        Promise.all([
            loadVolumes(),
            refreshStats()
        ])
            .then(() => {
                showToast('اطلاعات ولوم‌ها بروزرسانی شد', 'success');
            })
            .catch(error => {
                showToast('خطا در بروزرسانی اطلاعات', 'error');
            });
    }

    /**
     * Refresh statistics
     */
    function refreshStats() {
        return DockerVolumesModule.getVolumesStats()
            .then(stats => {
                document.getElementById('totalVolumes').textContent = stats.total_volumes;
                document.getElementById('localVolumes').textContent = stats.local_driver;
                document.getElementById('labeledVolumes').textContent = stats.labeled_volumes;
                document.getElementById('reclaimedSpace').textContent = stats.estimated_size;
                document.getElementById('totalSpace').textContent = stats.estimated_size;
                return stats;
            })
            .catch(error => {
                console.error('Error refreshing stats:', error);
                // تنظیم مقادیر پیش‌فرض
                document.getElementById('totalVolumes').textContent = '-';
                document.getElementById('localVolumes').textContent = '-';
                document.getElementById('labeledVolumes').textContent = '-';
                document.getElementById('reclaimedSpace').textContent = '-';
                return {};
            });
    }

    /**
     * Show volume details
     */
    function showVolumeDetails(volumeName) {
        DockerVolumesModule.getVolumeDetails(volumeName)
            .then(data => {
                const volume = data.volume;
                const detailsCard = document.getElementById('volumeDetailsCard');
                const detailsContent = document.getElementById('volumeDetailsContent');

                if (detailsCard && detailsContent) {
                    detailsContent.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6>اطلاعات پایه</h6>
                                <table class="table table-sm">
                                    <tr><th>نام:</th><td>${volume.name}</td></tr>
                                    <tr><th>درایور:</th><td>${volume.attrs.Driver || 'local'}</td></tr>
                                    <tr><th>Scope:</th><td>${volume.attrs.Scope || 'local'}</td></tr>
                                    <tr><th>Mountpoint:</th><td><code>${volume.attrs.Mountpoint || ''}</code></td></tr>
                                    <tr><th>Created:</th><td>${_formatDate(volume.attrs.CreatedAt || '')}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>تنظیمات</h6>
                                ${volume.attrs.Options && Object.keys(volume.attrs.Options).length > 0 ? `
                                    <table class="table table-sm">
                                        ${Object.entries(volume.attrs.Options).map(([key, value]) => `
                                            <tr><th>${key}:</th><td>${value}</td></tr>
                                        `).join('')}
                                    </table>
                                ` : '<p class="text-muted">بدون تنظیمات خاص</p>'}
                                
                                ${volume.attrs.Labels && Object.keys(volume.attrs.Labels).length > 0 ? `
                                    <h6 class="mt-3">برچسب‌ها</h6>
                                    <div class="bg-light p-2 rounded">
                                        ${Object.entries(volume.attrs.Labels).map(([key, value]) => `
                                            <div><strong>${key}:</strong> ${value}</div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-outline-primary me-2" onclick="DockerVolumesUI.inspectVolume('${volumeName}')">
                                مشاهده محتوای ولوم
                            </button>
                            <button class="btn btn-outline-warning" onclick="DockerVolumesUI.backupVolume('${volumeName}')">
                                💾 بکاپ ولوم
                            </button>
                        </div>
                    `;

                    detailsCard.style.display = 'block';
                }
            })
            .catch(error => {
                showToast(`خطا در دریافت جزئیات ولوم: ${error.message}`, 'error');
            });
    }

    /**
     * Inspect volume content
     */
    function inspectVolume(volumeName) {
        DockerVolumesModule.inspectVolume(volumeName)
            .then(data => {
                const modalContent = document.getElementById('volumeInspectContent');
                if (!modalContent) return;

                if (data.files_count > 0) {
                    modalContent.innerHTML = `
                        <div class="alert alert-info">
                            <strong>مسیر:</strong> ${data.mountpoint}<br>
                            <strong>تعداد فایل‌ها:</strong> ${data.files_count}
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>مجوزها</th>
                                        <th>تعداد لینک</th>
                                        <th>مالک</th>
                                        <th>گروه</th>
                                        <th>سایز</th>
                                        <th>تاریخ</th>
                                        <th>نام</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.files.map(file => `
                                        <tr>
                                            <td><code>${file.permissions}</code></td>
                                            <td>${file.links}</td>
                                            <td>${file.owner}</td>
                                            <td>${file.group}</td>
                                            <td>${file.size}</td>
                                            <td>${file.month} ${file.day} ${file.time}</td>
                                            <td>${file.name}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        ${data.raw_output ? `
                            <div class="mt-3">
                                <h6>خروجی اصلی</h6>
                                <pre class="bg-light p-2 rounded">${data.raw_output}</pre>
                            </div>
                        ` : ''}
                    `;
                } else {
                    modalContent.innerHTML = `
                        <div class="alert alert-warning">
                            <h5>ولوم خالی است</h5>
                            <p>ولوم <strong>${volumeName}</strong> در مسیر <code>${data.mountpoint}</code> فایلی ندارد.</p>
                        </div>
                    `;
                }

                // نمایش مودال
                const modal = new bootstrap.Modal(document.getElementById('volumeInspectModal'));
                modal.show();
            })
            .catch(error => {
                showToast(`خطا در بررسی محتوای ولوم: ${error.message}`, 'error');
            });
    }

    /**
     * Create new volume
     */
    function createVolume() {
        const name = document.getElementById('volumeName').value;
        const driver = document.getElementById('volumeDriver').value;
        const driverOptsStr = document.getElementById('driverOptions').value;
        const labelsStr = document.getElementById('volumeLabels').value;

        if (!name) {
            showToast('لطفاً نام ولوم را وارد کنید', 'warning');
            return;
        }

        // بررسی تنظیمات درایور
        let driverOpts = {};
        if (driverOptsStr) {
            driverOpts = DockerVolumesModule.validateJSONConfig(driverOptsStr);
            if (driverOpts === null) {
                showToast('تنظیمات درایور نامعتبر است', 'error');
                return;
            }
        }

        // بررسی برچسب‌ها
        let labels = {};
        if (labelsStr) {
            labels = DockerVolumesModule.validateJSONConfig(labelsStr);
            if (labels === null) {
                showToast('برچسب‌ها نامعتبر هستند', 'error');
                return;
            }
        }

        showToast(`در حال ایجاد ولوم ${name}...`, 'info');

        DockerVolumesModule.createVolume(name, driver, driverOpts, labels)
            .then(data => {
                showToast(`ولوم ${name} با موفقیت ایجاد شد`, 'success');

                // بستن مودال
                const modal = bootstrap.Modal.getInstance(document.getElementById('createVolumeModal'));
                modal.hide();

                // رفرش لیست
                refreshVolumes();
            })
            .catch(error => {
                showToast(`خطا در ایجاد ولوم: ${error.message}`, 'error');
            });
    }

    /**
     * Show create volume modal
     */
    function showCreateVolumeModal() {
        // ریست فرم
        document.getElementById('volumeName').value = '';
        document.getElementById('volumeDriver').value = 'local';
        document.getElementById('driverOptions').value = '';
        document.getElementById('volumeLabels').value = '';
        document.getElementById('driverOptionsSection').style.display = 'none';

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('createVolumeModal'));
        modal.show();
    }

    /**
     * Show driver options based on selected driver
     */
    function toggleDriverOptions() {
        const driver = document.getElementById('volumeDriver').value;
        const optionsSection = document.getElementById('driverOptionsSection');

        if (driver === 'local') {
            optionsSection.style.display = 'none';
        } else {
            optionsSection.style.display = 'block';

            // تنظیم placeholder بر اساس درایور
            const optionsTextarea = document.getElementById('driverOptions');
            if (driver === 'nfs') {
                optionsTextarea.placeholder = '{"type": "nfs", "o": "addr=192.168.1.100,rw,nfsvers=4", "device": ":/path/to/share"}';
            } else if (driver === 'cifs') {
                optionsTextarea.placeholder = '{"type": "cifs", "o": "username=user,password=pass,domain=domain", "device": "//server/share"}';
            } else if (driver === 'tmpfs') {
                optionsTextarea.placeholder = '{"type": "tmpfs", "device": "tmpfs", "o": "size=100m,uid=1000"}';
            }
        }
    }

    /**
     * Confirm volume removal
     */
    function confirmRemoveVolume(volumeName) {
        if (confirm(`آیا از حذف ولوم "${volumeName}" اطمینان دارید؟`)) {
            const force = document.getElementById('forceRemoveVolume')?.checked || false;

            showToast(`در حال حذف ولوم ${volumeName}...`, 'info');

            DockerVolumesModule.removeVolume(volumeName, force)
                .then(() => {
                    showToast('ولوم با موفقیت حذف شد', 'success');
                    refreshVolumes();
                })
                .catch(error => {
                    showToast(`خطا در حذف ولوم: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Remove volume by name
     */
    function removeVolume() {
        const volumeName = document.getElementById('volumeNameToRemove').value;

        if (!volumeName) {
            showToast('لطفاً نام ولوم را وارد کنید', 'warning');
            return;
        }

        // پیدا کردن ولوم
        const volumes = DockerVolumesModule._getCurrentVolumes();
        const volume = volumes.find(v => v.name === volumeName);

        if (!volume) {
            showToast('ولوم یافت نشد', 'error');
            return;
        }

        if (confirm(`آیا از حذف ولوم "${volumeName}" اطمینان دارید؟`)) {
            const force = document.getElementById('forceRemoveVolume')?.checked || false;

            showToast(`در حال حذف ولوم ${volumeName}...`, 'info');

            DockerVolumesModule.removeVolume(volumeName, force)
                .then(() => {
                    showToast('ولوم با موفقیت حذف شد', 'success');
                    refreshVolumes();
                    document.getElementById('volumeNameToRemove').value = '';
                })
                .catch(error => {
                    showToast(`خطا در حذف ولوم: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Prune unused volumes
     */
    function pruneVolumes() {
        if (confirm('آیا از حذف ولوم‌های بدون استفاده اطمینان دارید؟')) {
            showToast('در حال حذف ولوم‌های بدون استفاده...', 'info');

            DockerVolumesModule.pruneVolumes()
                .then(data => {
                    showToast(`${data.deleted_count} ولوم حذف شد. فضای آزاد شده: ${data.space_reclaimed}`, 'success');
                    refreshVolumes();
                })
                .catch(error => {
                    showToast(`خطا در حذف ولوم‌ها: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Search volumes
     */
    function searchVolumes() {
        const searchTerm = document.getElementById('searchVolume').value;
        const volumes = DockerVolumesModule._getCurrentVolumes();
        const filtered = DockerVolumesModule.searchVolumes(searchTerm, volumes);

        displayVolumes(filtered);
        document.getElementById('volumesCount').textContent = `${filtered.length} (فیلتر شده)`;
    }

    /**
     * Backup volume (placeholder)
     */
    function backupVolume(volumeName) {
        showToast(`در حال آماده‌سازی بکاپ ولوم ${volumeName}...`, 'info');

        // این تابع نیاز به پیاده‌سازی دارد
        setTimeout(() => {
            showToast('عملکرد بکاپ در حال توسعه است', 'warning');
        }, 1000);
    }

    /**
     * Backup all volumes (placeholder)
     */
    function backupAllVolumes() {
        showToast('در حال آماده‌سازی بکاپ تمام ولوم‌ها...', 'info');

        // این تابع نیاز به پیاده‌سازی دارد
        setTimeout(() => {
            showToast('عملکرد بکاپ در حال توسعه است', 'warning');
        }, 1000);
    }

    /**
     * Cleanup orphaned volumes (placeholder)
     */
    function cleanupOrphanedVolumes() {
        if (confirm('آیا از پاکسازی ولوم‌های بی‌استفاده اطمینان دارید؟')) {
            showToast('در حال پاکسازی ولوم‌های بی‌استفاده...', 'info');

            // این تابع می‌تواند ولوم‌هایی که به هیچ کانتینری متصل نیستند را پیدا کند
            setTimeout(() => {
                showToast('عملکرد پاکسازی در حال توسعه است', 'warning');
            }, 1000);
        }
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // تغییر درایور
        const driverSelect = document.getElementById('volumeDriver');
        if (driverSelect) {
            driverSelect.addEventListener('change', toggleDriverOptions);
        }

        // جستجوی ولوم
        const searchInput = document.getElementById('searchVolume');
        if (searchInput) {
            searchInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    searchVolumes();
                }
            });
        }

        // حذف ولوم
        const removeInput = document.getElementById('volumeNameToRemove');
        if (removeInput) {
            removeInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    removeVolume();
                }
            });
        }

        // کلیدهای میانبر
        document.addEventListener('keydown', function (e) {
            // Ctrl+V برای ایجاد ولوم جدید
            if (e.ctrlKey && e.key === 'v' && currentSection === 'volumes') {
                e.preventDefault();
                showCreateVolumeModal();
            }

            // Ctrl+R برای رفرش
            if (e.ctrlKey && e.key === 'r' && currentSection === 'volumes') {
                e.preventDefault();
                refreshVolumes();
            }
        });
    }

    /**
     * Format date
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

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initVolumesSection,
        loadVolumes,
        refreshVolumes,
        refreshStats,
        showVolumeDetails,
        inspectVolume,
        createVolume,
        showCreateVolumeModal,
        toggleDriverOptions,
        confirmRemoveVolume,
        removeVolume,
        pruneVolumes,
        searchVolumes,
        backupVolume,
        backupAllVolumes,
        cleanupOrphanedVolumes
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerVolumesUI = DockerVolumesUI;