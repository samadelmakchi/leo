/**
 * UI Module for System Information Section
 */

const SystemUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize System section
     */
    function initSystemSection() {
        console.log('Initializing System section...');

        // بارگذاری اطلاعات اولیه
        loadSystemInfo();

        // راه‌اندازی نمودارها
        SystemModule.initializeCharts();

        // شروع مانیتورینگ
        startLiveMonitoring();

        // تنظیم event listeners
        setupEventListeners();

        return Promise.resolve();
    }

    /**
     * Load system information
     */
    function loadSystemInfo() {
        showToast('در حال بارگذاری اطلاعات سیستم...', 'info');

        SystemModule.getSystemInfo()
            .then(() => {
                SystemModule.updateSystemDisplays();
                showToast('اطلاعات سیستم بارگذاری شد', 'success');
            })
            .catch(error => {
                console.error('Error loading system info:', error);
                showToast('خطا در بارگذاری اطلاعات سیستم', 'error');
            });
    }

    /**
     * Start live monitoring
     */
    function startLiveMonitoring() {
        const liveToggle = document.getElementById('liveMonitoring');
        if (liveToggle && liveToggle.checked) {
            SystemModule.startMonitoring(3000); // هر 3 ثانیه
        }
    }

    /**
     * Refresh resource charts
     */
    function refreshResourceCharts() {
        SystemModule.getSystemResources()
            .then(data => {
                SystemModule.updateResourceDisplays(data);
                showToast('نمودارها بروزرسانی شدند', 'success');
            })
            .catch(error => {
                console.error('Error refreshing charts:', error);
                showToast('خطا در بروزرسانی نمودارها', 'error');
            });
    }

    /**
     * Refresh processes list
     */
    function refreshProcesses() {
        SystemModule.getSystemInfo()
            .then(() => {
                SystemModule.updateProcessesTable();
                showToast('لیست پردازش‌ها بروزرسانی شد', 'success');
            })
            .catch(error => {
                console.error('Error refreshing processes:', error);
                showToast('خطا در بروزرسانی پردازش‌ها', 'error');
            });
    }

    /**
     * Search processes
     */
    function searchProcesses() {
        const searchTerm = document.getElementById('processSearch').value.toLowerCase();
        const rows = document.querySelectorAll('#processesTable tr');

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }

    // ============================================================================
    // Event Listeners
    // ============================================================================

    function setupEventListeners() {
        // Toggle live monitoring
        const liveToggle = document.getElementById('liveMonitoring');
        if (liveToggle) {
            liveToggle.addEventListener('change', function () {
                if (this.checked) {
                    SystemModule.startMonitoring(3000);
                    showToast('مانیتورینگ زنده فعال شد', 'success');
                } else {
                    SystemModule.stopMonitoring();
                    showToast('مانیتورینگ زنده غیرفعال شد', 'info');
                }
            });
        }

        // Tab change events
        const tabEl = document.querySelector('#systemTabs');
        if (tabEl) {
            tabEl.addEventListener('shown.bs.tab', function (event) {
                const activeTab = event.target.getAttribute('data-bs-target');
                console.log('Active tab:', activeTab);

                // اگر تب پردازش‌ها فعال شد، لیست را رفرش کن
                if (activeTab === '#processes') {
                    refreshProcesses();
                }

                // اگر تب منابع فعال شد، مانیتورینگ را چک کن
                if (activeTab === '#resources') {
                    const liveToggle = document.getElementById('liveMonitoring');
                    if (liveToggle && !liveToggle.checked) {
                        liveToggle.checked = true;
                        SystemModule.startMonitoring(3000);
                    }
                }
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', function (e) {
            if (currentSection === 'system') {
                // Ctrl+R برای رفرش
                if (e.ctrlKey && e.key === 'r') {
                    e.preventDefault();
                    SystemModule.refreshAll();
                }

                // Ctrl+M برای toggle monitoring
                if (e.ctrlKey && e.key === 'm') {
                    e.preventDefault();
                    const liveToggle = document.getElementById('liveMonitoring');
                    if (liveToggle) {
                        liveToggle.checked = !liveToggle.checked;
                        liveToggle.dispatchEvent(new Event('change'));
                    }
                }
            }
        });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initSystemSection,
        loadSystemInfo,
        refreshResourceCharts,
        refreshProcesses,
        searchProcesses,
        startLiveMonitoring
    };
})();

window.SystemUI = SystemUI;