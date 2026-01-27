// ============================================================================
// Menu
// ============================================================================

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const wrapper = document.getElementById("contentWrapper");

    sidebar.classList.toggle("open");
    wrapper.classList.toggle("shifted");
}

// ============================================================================
// Toast
// ============================================================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
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

document.addEventListener('DOMContentLoaded', function () {
    // مدیریت منوی ناوبری
    const navContainer = document.getElementById('sidebar');

    if (navContainer) {
        navContainer.addEventListener('click', function (e) {
            const link = e.target.closest('.nav-link');

            if (link && link.hasAttribute('data-section')) {
                e.preventDefault();

                const sectionId = link.getAttribute('data-section');
                const sectionTitle = link.getAttribute('data-title');

                showSection(sectionId, sectionTitle);
                toggleSidebar();
                updateActiveLink(link);
            }
        });
    }
});

function updateActiveLink(activeLink) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    activeLink.classList.add('active');
}

// ============================================================================
// Global variables
// ============================================================================

let currentSection = 'home';
let loadedSections = new Set(['home']); // بخش‌های لود شده

// ============================================================================
// Dynamic Content Loading
// ============================================================================

async function loadSection(sectionId) {
    // اگر قبلاً لود شده، فقط نمایش بده
    if (loadedSections.has(sectionId)) {
        document.getElementById(`${sectionId}Section`).style.display = 'block';
        return;
    }

    try {
        showToast(`در حال بارگذاری بخش ${sectionId}...`, 'info');

        const response = await fetch(`section/${sectionId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const html = await response.text();

        // ایجاد container برای بخش جدید
        const sectionDiv = document.createElement('div');
        sectionDiv.id = `${sectionId}Section`;
        sectionDiv.className = 'content-section';

        // اضافه کردن HTML دریافتی
        sectionDiv.innerHTML = html;

        // اضافه کردن به main content
        document.getElementById('mainContent').appendChild(sectionDiv);

        // اضافه کردن به لیست بخش‌های لود شده
        loadedSections.add(sectionId);

        showToast(`بخش ${sectionId} با موفقیت بارگذاری شد`, 'success');

    } catch (error) {
        console.error(`Error loading section ${sectionId}:`, error);

        // نمایش پیام خطا
        const errorDiv = document.createElement('div');
        errorDiv.id = `${sectionId}Section`;
        errorDiv.className = 'content-section';
        errorDiv.innerHTML = `
            <div class="container-fluid mt-3 mb-3">
                <div class="alert alert-danger">
                    <h4>خطا در بارگذاری بخش</h4>
                    <p>بخش "${sectionId}" قابل بارگذاری نیست.</p>
                    <button class="btn btn-primary mt-2" onclick="loadSection('${sectionId}')">
                        تلاش مجدد
                    </button>
                </div>
            </div>
        `;

        document.getElementById('mainContent').appendChild(errorDiv);
        loadedSections.add(sectionId);

        showToast(`خطا در بارگذاری بخش ${sectionId}`, 'error');
    }
}

function unloadSection(sectionId) {
    if (sectionId === 'home') return; // صفحه اصلی همیشه می‌ماند

    const section = document.getElementById(`${sectionId}Section`);
    if (section) {
        section.style.display = 'none';
        // یا می‌توانید کاملاً حذف کنید:
        // section.remove();
        // loadedSections.delete(sectionId);
    }
}

// ============================================================================
// Updated showSection function
// ============================================================================

function showSection(sectionId, title) {
    // مخفی کردن تمام بخش‌ها
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });

    // اگر بخش هنوز لود نشده، لود کن
    if (!loadedSections.has(sectionId)) {
        loadSection(sectionId).then(() => {
            // بعد از لود شدن، نمایش بده
            const targetSection = document.getElementById(sectionId + 'Section');
            if (targetSection) {
                targetSection.style.display = 'block';
                currentSection = sectionId;

                // فراخوانی تابع initialize مخصوص هر بخش
                initializeSection(sectionId);
            }
        });
    } else {
        // اگر قبلاً لود شده، فقط نمایش بده
        const targetSection = document.getElementById(sectionId + 'Section');
        if (targetSection) {
            targetSection.style.display = 'block';
            currentSection = sectionId;

            // فراخوانی تابع initialize مخصوص هر بخش
            initializeSection(sectionId);
        }
    }

    // آپدیت عنوان صفحه
    document.title = 'لئو | ' + title;
    document.getElementById("menu-title").innerText = title;
}

// ============================================================================
// Updated initializeSection function
// ============================================================================

function initializeSection(sectionId) {
    console.log(`Initializing section: ${sectionId}`);

    // Map section IDs to their initialization functions
    const initializationMap = {
        'customers': () => {
            if (typeof AnsibleUI !== 'undefined' && typeof AnsibleUI.initCustomersSection === 'function') {
                return AnsibleUI.initCustomersSection();
            } else {
                console.warn('AnsibleUI module not loaded');
                showToast('ماژول مدیریت مشتریان بارگذاری نشده است', 'warning');
            }
        },
        'images': () => {
            if (typeof DockerUI !== 'undefined' && typeof DockerUI.initImagesSection === 'function') {
                return DockerUI.initImagesSection();
            } else {
                console.warn('DockerUI module not loaded');
                showToast('ماژول مدیریت ایمیج‌ها بارگذاری نشده است', 'warning');
            }
        },
        'networks': () => {
            if (typeof DockerNetworksUI !== 'undefined' && typeof DockerNetworksUI.initNetworksSection === 'function') {
                return DockerNetworksUI.initNetworksSection();
            } else {
                console.warn('DockerNetworksUI module not loaded');
                showToast('ماژول مدیریت شبکه‌ها بارگذاری نشده است', 'warning');
            }
        },
        'volumes': () => {
            if (typeof DockerVolumesUI !== 'undefined' && typeof DockerVolumesUI.initVolumesSection === 'function') {
                return DockerVolumesUI.initVolumesSection();
            } else {
                console.warn('DockerVolumesUI module not loaded');
                showToast('ماژول مدیریت ولوم‌ها بارگذاری نشده است', 'warning');
            }
        },
        'containers': () => {
            if (typeof DockerContainersUI !== 'undefined' && typeof DockerContainersUI.initContainersSection === 'function') {
                return DockerContainersUI.initContainersSection();
            } else {
                console.warn('DockerContainersUI module not loaded');
                showToast('ماژول مدیریت کانتینرها بارگذاری نشده است', 'warning');
            }
        },
        'system': () => {
            if (typeof SystemUI !== 'undefined' && typeof SystemUI.initSystemSection === 'function') {
                return SystemUI.initSystemSection();
            } else {
                console.warn('SystemUI module not loaded');
                showToast('ماژول اطلاعات سیستم بارگذاری نشده است', 'warning');
            }
        },
        'crons': () => {
            if (typeof CronUI !== 'undefined' && typeof CronUI.initCronsSection === 'function') {
                return CronUI.initCronsSection();
            } else {
                console.warn('CronUI module not loaded');
                showToast('ماژول مدیریت cron jobs بارگذاری نشده است', 'warning');
            }
        },
        'backup': () => {
            if (typeof BackupUI !== 'undefined' && typeof BackupUI.initBackupSection === 'function') {
                return BackupUI.initBackupSection();
            } else {
                console.warn('BackupUI module not loaded');
                showToast('ماژول مدیریت بک‌اپ‌ها بارگذاری نشده است', 'warning');
            }
        },
        'logs': () => {
            if (typeof LogsUI !== 'undefined' && typeof LogsUI.initLogsSection === 'function') {
                return LogsUI.initLogsSection();
            } else {
                console.warn('LogsUI module not loaded');
                showToast('ماژول مدیریت لاگ‌ها بارگذاری نشده است', 'warning');
            }
        },
    };

    // Call the appropriate initialization function
    if (initializationMap[sectionId]) {
        try {
            const result = initializationMap[sectionId]();
            if (result && typeof result.then === 'function') {
                // Handle promise if returned
                result.catch(error => {
                    console.error(`Error initializing ${sectionId} section:`, error);
                });
            }
        } catch (error) {
            console.error(`Error initializing ${sectionId} section:`, error);
        }
    }
}

// ============================================================================
// Cache Management
// ============================================================================

function clearSectionCache() {
    const sectionsToRemove = [];

    loadedSections.forEach(sectionId => {
        if (sectionId !== 'home') {
            const section = document.getElementById(`${sectionId}Section`);
            if (section) {
                sectionsToRemove.push(section);
            }
        }
    });

    // حذف از DOM
    sectionsToRemove.forEach(section => {
        section.remove();
    });

    // پاک کردن cache
    loadedSections.clear();
    loadedSections.add('home');

    console.log('Section cache cleared');
    showToast('کش بخش‌ها پاک شد', 'info');
}

function preloadSections() {
    const importantSections = ['customers', 'images']; // بخش‌های مهم

    importantSections.forEach(sectionId => {
        if (!loadedSections.has(sectionId)) {
            loadSection(sectionId).then(() => {
                console.log(`Preloaded section: ${sectionId}`);
                // مخفی کردن بعد از لود
                document.getElementById(`${sectionId}Section`).style.display = 'none';
            });
        }
    });
}

// ============================================================================
// Event Listeners for dynamic content
// ============================================================================

function setupDynamicContentListeners() {
    // Event delegation برای المنت‌هایی که بعداً اضافه می‌شوند
    document.addEventListener('click', function (e) {
        // مدیریت تب‌های Bootstrap در محتوای دینامیک
        if (e.target.matches('[data-bs-toggle="tab"], [data-bs-toggle="tab"] *')) {
            const tabElement = e.target.closest('[data-bs-toggle="tab"]');
            if (tabElement) {
                const tab = new bootstrap.Tab(tabElement);
                tab.show();
            }
        }
    });

    // مدیریت فرم‌ها در محتوای دینامیک
    document.addEventListener('submit', function (e) {
        if (e.target.tagName === 'FORM') {
            e.preventDefault();
            // مدیریت submit فرم‌های دینامیک
            console.log('Form submitted:', e.target.id || e.target.name);
        }
    });
}

// ============================================================================
// Updated Application Initialization
// ============================================================================

function initializeApp() {
    console.log('Initializing application...');

    // Setup global event listeners
    setupGlobalEventListeners();
    setupDynamicContentListeners();

    // Show home section by default
    const homeLink = document.querySelector('.nav-link[data-section="home"]');
    if (homeLink) {
        homeLink.classList.add('active');
    }

    // Preload important sections
    setTimeout(preloadSections, 1000); // بعد از 1 ثانیه

    console.log('Application initialized successfully');
}

// ============================================================================
// Export new functions
// ============================================================================

window.loadSection = loadSection;
window.unloadSection = unloadSection;
window.clearSectionCache = clearSectionCache;
window.preloadSections = preloadSections;