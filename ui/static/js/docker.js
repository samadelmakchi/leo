/**
 * ماژول مدیریت Docker - مدیریت ایمیج‌ها و کانتینرها
 */

const DockerModule = (function () {
    // متغیرهای داخلی ماژول
    let currentImages = [];

    // ============================================================================
    // Public Functions - Images
    // ============================================================================

    /**
     * بارگذاری لیست ایمیج‌های Docker
     */
    function loadImages() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/images')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        currentImages = data.images;
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت لیست ایمیج‌ها'));
                    }
                })
                .catch(error => {
                    console.error('Error loading images:', error);
                    reject(error);
                });
        });
    }

    /**
     * نمایش ایمیج‌ها در جدول
     */
    function displayImages(containerId, images) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        if (!images || images.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        هیچ ایمیجی یافت نشد
                    </td>
                </tr>
            `;
            return;
        }

        let totalSizeBytes = 0;

        images.forEach((image, index) => {
            totalSizeBytes += image.size_bytes;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <span class="badge bg-dark font-monospace" 
                          title="Full ID: ${image.full_id}"
                          style="cursor: pointer; font-size: 0.8em;">
                        ${image.id.substring(0, 12)}
                    </span>
                </td>
                <td>
                    <div class="text-truncate" style="max-width: 200px;" 
                         title="${image.repository}">
                        ${image.repository}
                    </div>
                </td>
                <td>
                    <span class="badge ${image.tag === 'latest' ? 'bg-success' : 'bg-info'}">
                        ${image.tag}
                    </span>
                </td>
                <td>
                    <span class="badge bg-secondary">
                        ${image.size}
                    </span>
                </td>
                <td>
                    <small class="text-muted">${_formatDate(image.created)}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info" 
                                onclick="DockerModule.showImageDetails('${image.id}')"
                                title="مشاهده جزئیات">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-warning"
                                onclick="DockerModule.pullImageDialog('${image.repository}')"
                                title="بروزرسانی ایمیج">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                        <button class="btn btn-outline-danger"
                                onclick="DockerModule.confirmRemoveImage('${image.id}')"
                                title="حذف ایمیج">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            container.appendChild(row);
        });

        // برگرداندن سایز کل برای استفاده خارجی
        return {
            totalSize: totalSizeBytes,
            count: images.length
        };
    }

    /**
     * حذف یک ایمیج
     */
    function removeImage(imageId, force = false) {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/images/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_id: imageId,
                    force: force
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در حذف ایمیج'));
                    }
                })
                .catch(error => {
                    console.error('Error removing image:', error);
                    reject(error);
                });
        });
    }

    /**
     * حذف ایمیج‌های بدون استفاده
     */
    function pruneImages() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/images/prune', {
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
                        reject(new Error(data.message || 'خطا در حذف ایمیج‌های بدون استفاده'));
                    }
                })
                .catch(error => {
                    console.error('Error pruning images:', error);
                    reject(error);
                });
        });
    }

    /**
     * Pull یک ایمیج جدید
     */
    function pullImage(imageName) {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/images/pull', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image: imageName
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در دانلود ایمیج'));
                    }
                })
                .catch(error => {
                    console.error('Error pulling image:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت اطلاعات سیستم Docker
     */
    function getSystemInfo() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/system')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
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
     * بررسی وضعیت Docker
     */
    function checkDockerStatus() {
        return new Promise((resolve, reject) => {
            fetch('/api/docker/ping')
                .then(response => response.json())
                .then(data => {
                    resolve(data);
                })
                .catch(error => {
                    reject(error);
                });
        });
    }

    // ============================================================================
    // UI Helper Functions
    // ============================================================================

    /**
     * نمایش دیالوگ حذف ایمیج
     */
    function confirmRemoveImage(imageId) {
        const image = currentImages.find(img => img.id === imageId);
        const imageName = image ? `${image.repository}:${image.tag}` : imageId;

        if (confirm(`آیا از حذف ایمیج "${imageName}" اطمینان دارید؟`)) {
            const forceRemove = confirm('آیا می‌خواهید به صورت اجباری حذف شود؟ (Force)');

            removeImage(imageId, forceRemove)
                .then(data => {
                    _showToast('ایمیج با موفقیت حذف شد', 'success');
                    // رفرش لیست
                    if (typeof window.loadImages === 'function') {
                        window.loadImages();
                    }
                })
                .catch(error => {
                    _showToast(`خطا در حذف ایمیج: ${error.message}`, 'error');
                });
        }
    }

    /**
     * نمایش دیالوگ pull ایمیج
     */
    function pullImageDialog(defaultRepo = '') {
        const imageName = prompt(
            'لطفاً نام کامل ایمیج را وارد کنید (مثال: nginx:latest یا ubuntu:20.04):',
            defaultRepo || ''
        );

        if (imageName && imageName.trim()) {
            _showToast(`در حال دانلود ایمیج ${imageName}...`, 'info');

            pullImage(imageName.trim())
                .then(data => {
                    _showToast('ایمیج با موفقیت دانلود شد', 'success');
                    // رفرش لیست
                    if (typeof window.loadImages === 'function') {
                        window.loadImages();
                    }
                })
                .catch(error => {
                    _showToast(`خطا در دانلود ایمیج: ${error.message}`, 'error');
                });
        }
    }

    /**
     * نمایش جزئیات ایمیج
     */
    function showImageDetails(imageId) {
        const image = currentImages.find(img => img.id === imageId);
        if (!image) {
            _showToast('ایمیج یافت نشد', 'warning');
            return;
        }

        // ایجاد مودال برای نمایش جزئیات
        const modalHtml = `
            <div class="modal fade" id="imageDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">جزئیات ایمیج</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-12">
                                    <h6>اطلاعات پایه</h6>
                                    <table class="table table-sm ltr">
                                        <tr>
                                            <th>ID:</th>
                                            <td><code>${image.id}</code></td>
                                        </tr>
                                        <tr>
                                            <th>Repository:</th>
                                            <td>${image.repository}</td>
                                        </tr>
                                        <tr>
                                            <th>Tag:</th>
                                            <td><span class="badge bg-info">${image.tag}</span></td>
                                        </tr>
                                        <tr>
                                            <th>Size:</th>
                                            <td>${image.size}</td>
                                        </tr>
                                        <tr>
                                            <th>Create Date:</th>
                                            <td>${_formatDate(image.created)}</td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-md-12">
                                    <h6>اطلاعات فنی</h6>
                                    <table class="table table-sm ltr">
                                        <tr>
                                            <th>Full ID:</th>
                                            <td><small><code>${image.full_id}</code></small></td>
                                        </tr>
                                        <tr>
                                            <th>Virtual Size:</th>
                                            <td>${(image.virtual_size / (1024 * 1024)).toFixed(2)} MB</td>
                                        </tr>
                                    </table>
                                    
                                    ${image.labels && Object.keys(image.labels).length > 0 ? `
                                        <h6 class="mt-3">Labels</h6>
                                        <div class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto;">
                                            ${Object.entries(image.labels).map(([key, value]) => `
                                                <div><strong>${key}:</strong> ${value}</div>
                                            `).join('')}
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                            <button type="button" class="btn btn-danger" 
                                    onclick="DockerModule.confirmRemoveImage('${image.id}')">
                                حذف ایمیج
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // اضافه کردن مودال به صفحه
        let modalContainer = document.getElementById('dockerModalContainer');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'dockerModalContainer';
            document.body.appendChild(modalContainer);
        }
        modalContainer.innerHTML = modalHtml;

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('imageDetailsModal'));
        modal.show();
    }

    /**
     * جستجوی ایمیج‌ها
     */
    function searchImages(searchTerm, images = currentImages) {
        if (!searchTerm) return images;

        const term = searchTerm.toLowerCase();
        return images.filter(image => {
            return image.repository.toLowerCase().includes(term) ||
                image.tag.toLowerCase().includes(term) ||
                image.id.toLowerCase().includes(term);
        });
    }

    // ============================================================================
    // Private Helper Functions
    // ============================================================================

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
     * نمایش نوتیفیکیشن
     */
    function _showToast(message, type = 'info') {
        // استفاده از تابع toast موجود در app.js یا ایجاد یک toast ساده
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            // ایجاد toast ساده
            const toast = document.createElement('div');
            toast.className = `alert alert-${type === 'error' ? 'danger' : type} 
                               alert-dismissible fade show position-fixed`;
            toast.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); ' +
                'z-index: 9999; min-width: 300px;';
            toast.innerHTML = `
                <strong>${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</strong>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            document.body.appendChild(toast);

            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 5000);
        }
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع مدیریت ایمیج‌ها
        loadImages,
        displayImages,
        removeImage,
        pruneImages,
        pullImage,

        // توابع اطلاعات سیستم
        getSystemInfo,
        checkDockerStatus,

        // توابع UI
        confirmRemoveImage,
        pullImageDialog,
        showImageDetails,
        searchImages,

        // دسترسی به داده‌های داخلی (برای دیباگ)
        _getCurrentImages: () => currentImages
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerModule = DockerModule;