/**
 * UI Module for Docker Images Section
 */

const DockerUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Images section
     */
    function initImagesSection() {
        console.log('Initializing Images section...');

        // بررسی وضعیت Docker
        DockerModule.checkDockerStatus()
            .then(status => {
                if (status.status === 'error') {
                    showToast('⚠️ Docker در دسترس نیست. لطفاً مطمئن شوید Docker در حال اجرا است.', 'warning');
                }
            })
            .catch(() => {
                showToast('⚠️ خطا در اتصال به Docker', 'warning');
            });

        // بارگذاری لیست ایمیج‌ها
        loadImages();

        // بارگذاری اطلاعات سیستم
        loadSystemInfo();

        // تنظیم event listeners
        setupEventListeners();

        return Promise.resolve();
    }

    /**
     * Load images list
     */
    function loadImages() {
        showToast('در حال بارگذاری لیست ایمیج‌ها...', 'info');

        return DockerModule.loadImages()
            .then(data => {
                const summary = DockerModule.displayImages('imagesTableBody', data.images);

                // آپدیت خلاصه اطلاعات
                document.getElementById('imagesCount').textContent = data.count;
                if (summary) {
                    const totalSizeMB = summary.totalSize / (1024 * 1024);
                    document.getElementById('totalSize').textContent = `${totalSizeMB.toFixed(2)} MB`;
                }

                showToast(`${data.count} ایمیج بارگذاری شد`, 'success');
                return data;
            })
            .catch(error => {
                console.error('Error loading images:', error);
                showToast(`خطا در بارگذاری ایمیج‌ها: ${error.message}`, 'error');

                // نمایش پیام خطا در جدول
                const tbody = document.getElementById('imagesTableBody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="7" class="text-center text-danger">
                                <div class="py-4">
                                    <i class="bi bi-exclamation-triangle fs-1"></i>
                                    <h5 class="mt-2">خطا در بارگذاری ایمیج‌ها</h5>
                                    <p class="text-muted">${error.message}</p>
                                    <button class="btn btn-primary mt-2" onclick="DockerUI.loadImages()">
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
     * Load system info
     */
    function loadSystemInfo() {
        return DockerModule.getSystemInfo()
            .then(data => {
                document.getElementById('sysImageCount').textContent = data.images_count;
                document.getElementById('sysDiskUsage').textContent = data.disk_usage;
                return data;
            })
            .catch(error => {
                console.error('Error loading system info:', error);
                document.getElementById('sysImageCount').textContent = 'خطا';
                document.getElementById('sysDiskUsage').textContent = 'خطا';
                return Promise.reject(error);
            });
    }

    /**
     * Refresh images and system info
     */
    function refreshImages() {
        showToast('در حال بروزرسانی اطلاعات...', 'info');

        Promise.all([
            loadImages(),
            loadSystemInfo()
        ])
            .then(() => {
                showToast('اطلاعات بروزرسانی شد', 'success');
            })
            .catch(error => {
                showToast('خطا در بروزرسانی اطلاعات', 'error');
            });
    }

    /**
     * Search images
     */
    function searchImages() {
        const searchTerm = document.getElementById('searchImage').value;
        const images = DockerModule._getCurrentImages();
        const filtered = DockerModule.searchImages(searchTerm, images);

        DockerModule.displayImages('imagesTableBody', filtered);
        document.getElementById('imagesCount').textContent = `${filtered.length} (فیلتر شده)`;
    }

    /**
     * Prune unused images
     */
    function pruneImages() {
        if (confirm('آیا از حذف ایمیج‌های بدون استفاده اطمینان دارید؟')) {
            showToast('در حال حذف ایمیج‌های بدون استفاده...', 'info');

            DockerModule.pruneImages()
                .then(data => {
                    showToast(`${data.deleted_count} ایمیج حذف شد. فضای آزاد شده: ${data.space_reclaimed}`, 'success');
                    loadImages();
                    loadSystemInfo();
                })
                .catch(error => {
                    showToast(`خطا در حذف ایمیج‌ها: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Remove specific image
     */
    function removeImage() {
        const imageId = document.getElementById('imageIdToRemove').value;
        const force = document.getElementById('forceRemove').checked;

        if (!imageId) {
            showToast('لطفاً ID یا نام ایمیج را وارد کنید', 'warning');
            return;
        }

        if (confirm(`آیا از حذف ایمیج "${imageId}" اطمینان دارید؟`)) {
            DockerModule.removeImage(imageId, force)
                .then(() => {
                    showToast('ایمیج با موفقیت حذف شد', 'success');
                    loadImages();
                    loadSystemInfo();
                    document.getElementById('imageIdToRemove').value = '';
                })
                .catch(error => {
                    showToast(`خطا در حذف ایمیج: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Pull new image
     */
    function pullNewImage(repository = '') {
        const imageName = prompt(
            'لطفاً نام کامل ایمیج را وارد کنید (مثال: nginx:latest یا ubuntu:20.04):',
            repository || ''
        );

        if (imageName && imageName.trim()) {
            showToast(`در حال دانلود ایمیج ${imageName}...`, 'info');

            DockerModule.pullImage(imageName.trim())
                .then(data => {
                    showToast('ایمیج با موفقیت دانلود شد', 'success');
                    loadImages();
                })
                .catch(error => {
                    showToast(`خطا در دانلود ایمیج: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Show image details
     */
    function showImageDetails(imageId) {
        DockerModule.showImageDetails(imageId);
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners for images section
     */
    function setupEventListeners() {
        // دکمه بروزرسانی
        const refreshBtn = document.querySelector('#imagesSection .btn-primary');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshImages);
        }

        // جستجوی ایمیج
        const searchInput = document.getElementById('searchImage');
        if (searchInput) {
            searchInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    searchImages();
                }
            });
        }

        // حذف ایمیج
        const removeInput = document.getElementById('imageIdToRemove');
        if (removeInput) {
            removeInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    removeImage();
                }
            });
        }

        // کلیدهای میانبر
        document.addEventListener('keydown', function (e) {
            // Ctrl+R برای رفرش
            if (e.ctrlKey && e.key === 'r' && currentSection === 'images') {
                e.preventDefault();
                refreshImages();
            }

            // Ctrl+P برای Pull
            if (e.ctrlKey && e.key === 'p' && currentSection === 'images') {
                e.preventDefault();
                pullNewImage();
            }
        });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initImagesSection,
        loadImages,
        loadSystemInfo,
        refreshImages,
        searchImages,
        pruneImages,
        removeImage,
        pullNewImage,
        showImageDetails,
        setupEventListeners
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerUI = DockerUI;