/**
 * UI Module for Ansible/Inventory Section
 */

const AnsibleUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Customers section
     */
    function initCustomersSection() {
        console.log('Initializing Customers section...');

        // بارگذاری Inventory و پر کردن dropdown
        return AnsibleModule.loadInventory()
            .then(() => {
                return AnsibleModule.populateCustomerSelect('customerSelect');
            })
            .then(() => {
                // تنظیم event listener برای تغییر مشتری
                const select = document.getElementById('customerSelect');
                if (select) {
                    select.addEventListener('change', function () {
                        AnsibleModule.updateCustomerState('customerSelect', 'customerStateText');
                        renderCustomerTabs();
                    });

                    // بارگذاری اولیه تب‌ها اگر مشتری انتخاب شده باشد
                    if (select.value) {
                        AnsibleModule.updateCustomerState('customerSelect', 'customerStateText');
                        renderCustomerTabs();
                    }
                }

                // اضافه کردن این خط ↓
                setupEventListeners();

                return Promise.resolve();
            })
            .catch(error => {
                console.error('Error initializing customers section:', error);
                showToast('خطا در بارگذاری اطلاعات مشتریان', 'error');
                return Promise.reject(error);
            });
    }

    /**
     * Render customer tabs
     */
    function renderCustomerTabs() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) return;

        AnsibleModule.getCustomer(customer)
            .then(data => {
                const categorized = AnsibleModule.categorizeVars(data.vars);

                // رندر هر تب
                renderTab('modules', categorized.modules, true);
                renderTab('domain', categorized.domain);
                renderTab('backup', categorized.backup);
                renderTab('test', categorized.test);
                renderTab('database', categorized.database, true);
            })
            .catch(error => {
                console.error('Error rendering customer tabs:', error);
                showToast('خطا در بارگذاری اطلاعات مشتری', 'error');
            });
    }

    /**
     * Render a single tab
     */
    function renderTab(tabId, data, grouped = false) {
        const container = document.getElementById(tabId);
        if (!container) return;

        container.innerHTML = '';

        if (Object.keys(data).length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">هیچ داده‌ای یافت نشد</div>';
            return;
        }

        // استفاده از ماژول Labels اگر موجود باشد
        const labelsSource = (typeof LabelsModule !== 'undefined')
            ? LabelsModule.getAllAnsibleLabels()
            : (window.labelsFa || {});

        if (grouped) {
            Object.entries(data).forEach(([group, items]) => {
                const groupTitle = (typeof LabelsModule !== 'undefined')
                    ? LabelsModule.getLabel(group, group.charAt(0).toUpperCase() + group.slice(1))
                    : group.charAt(0).toUpperCase() + group.slice(1);

                container.innerHTML += `
                <div class="card mb-3">
                    <div class="card-header bg-light">
                        <h5 class="mb-0">${groupTitle}</h5>
                    </div>
                    <div class="card-body">
                        ${AnsibleModule.renderInputs(items, labelsSource)}
                    </div>
                </div>
            `;
            });
        } else {
            container.innerHTML = AnsibleModule.renderInputs(data, labelsSource);
        }
    }

    /**
     * Save customer variables
     */
    function saveCustomerVars() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        // جمع‌آوری داده‌ها از تمام تب‌ها
        const allData = {};
        ['modules', 'domain', 'backup', 'test', 'database'].forEach(tabId => {
            const tabData = AnsibleModule.collectFormData(`#${tabId}`);
            Object.assign(allData, tabData);
        });

        AnsibleModule.saveCustomerVars(customer, allData)
            .then(() => {
                showToast('تغییرات با موفقیت ذخیره شد', 'success');
                // بروزرسانی وضعیت مشتری
                AnsibleModule.updateCustomerState('customerSelect', 'customerStateText');
            })
            .catch(error => {
                showToast(`خطا در ذخیره تغییرات: ${error.message}`, 'error');
            });
    }

    /**
     * Run playbook
     */
    function runPlaybook() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        const modulesList = AnsibleModule.getModulesList();
        const vars = AnsibleModule.getCustomerVars(customer);

        const activeUpdates = {};
        modulesList.forEach(mod => {
            const key = `customer_${mod}_update`;
            if (vars[key]) {
                activeUpdates[key] = true;
            }
        });

        // اگر همه true باشند، extra_vars خالی است
        const extraVars = Object.keys(activeUpdates).length === modulesList.length ? {} : activeUpdates;

        AnsibleModule.runPlaybook(customer, extraVars)
            .then(data => {
                if (Object.keys(extraVars).length === 0) {
                    showToast('بروزرسانی کامل آغاز شد', 'success');
                } else {
                    showToast(`بروزرسانی ماژول‌های فعال آغاز شد`, 'success');
                }
            })
            .catch(error => {
                showToast(`خطا در اجرای پلی‌بوک: ${error.message}`, 'error');
            });
    }

    /**
     * Down customer
     */
    function downCustomer() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        AnsibleModule.downCustomer(customer)
            .then(() => {
                showToast('داون کردن مشتری آغاز شد', 'success');
            })
            .catch(error => {
                showToast(`خطا: ${error.message}`, 'error');
            });
    }

    /**
     * Backup customer
     */
    function backupCustomer() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        AnsibleModule.backupCustomer(customer)
            .then(() => {
                showToast('اجرای بکاپ آغاز شد', 'success');
            })
            .catch(error => {
                showToast(`خطا: ${error.message}`, 'error');
            });
    }

    /**
     * Full test with deploy
     */
    function testFull() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        AnsibleModule.testFull(customer)
            .then(() => {
                showToast('تست کامل با دپلوی آغاز شد', 'success');
            })
            .catch(error => {
                showToast(`خطا: ${error.message}`, 'error');
            });
    }

    /**
     * Test only
     */
    function testOnly() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        AnsibleModule.testOnly(customer)
            .then(() => {
                showToast('اجرای تست تنها آغاز شد', 'success');
            })
            .catch(error => {
                showToast(`خطا: ${error.message}`, 'error');
            });
    }

    /**
     * Test with fail-fast
     */
    function testFailFast() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        AnsibleModule.testFailFast(customer)
            .then(() => {
                showToast('تست کامل با fail-fast آغاز شد', 'success');
            })
            .catch(error => {
                showToast(`خطا: ${error.message}`, 'error');
            });
    }

    /**
     * Refresh customer data
     */
    function refreshCustomer() {
        const customer = document.getElementById('customerSelect').value;
        if (!customer) {
            showToast('لطفاً یک مشتری انتخاب کنید', 'warning');
            return;
        }

        showToast('در حال بروزرسانی اطلاعات مشتری...', 'info');

        AnsibleModule.getCustomer(customer)
            .then(data => {
                const categorized = AnsibleModule.categorizeVars(data.vars);

                // رندر هر تب
                renderTab('modules', categorized.modules, true);
                renderTab('domain', categorized.domain);
                renderTab('backup', categorized.backup);
                renderTab('test', categorized.test);
                renderTab('database', categorized.database, true);

                showToast('اطلاعات مشتری بروزرسانی شد', 'success');
            })
            .catch(error => {
                showToast(`خطا در بروزرسانی: ${error.message}`, 'error');
            });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners for customers section
     */
    function setupEventListeners() {
        // دکمه بروزرسانی
        const refreshBtn = document.querySelector('#customersSection .btn-primary');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshCustomer);
        }

        // جستجو در فیلدها
        setupSearchListeners();
    }

    /**
     * Setup search listeners for inputs
     */
    function setupSearchListeners() {
        // اضافه کردن event listener برای جستجوی سریع
        document.addEventListener('keydown', function (e) {
            // Ctrl+F برای فوکوس روی جستجو
            if (e.ctrlKey && e.key === 'f' && currentSection === 'customers') {
                e.preventDefault();
                const searchInput = document.querySelector('#customersSection input[type="search"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        initCustomersSection,
        renderCustomerTabs,
        saveCustomerVars,
        runPlaybook,
        downCustomer,
        backupCustomer,
        testFull,
        testOnly,
        testFailFast,
        refreshCustomer,
        setupEventListeners
    };
})();

// قرار دادن ماژول در scope گلوبال
window.AnsibleUI = AnsibleUI;