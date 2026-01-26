/**
 * ماژول مدیریت Ansible و Inventory
 */

const AnsibleModule = (function () {
    // متغیرهای داخلی ماژول
    let inventoryData = {};
    let currentCustomer = '';
    let modulesList = ["gateway", "portal", "portal_frontend", "lms", "file"];

    // ============================================================================
    // Public Functions - Inventory
    // ============================================================================

    /**
     * بارگذاری Inventory
     */
    function loadInventory() {
        return new Promise((resolve, reject) => {
            fetch('/api/inventory')
                .then(response => response.json())
                .then(data => {
                    inventoryData = data;
                    resolve(data);
                })
                .catch(error => {
                    console.error('Error loading inventory:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت لیست مشتریان
     */
    function getCustomers() {
        return new Promise((resolve, reject) => {
            fetch('/api/inventory/customers')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data.customers);
                    } else {
                        reject(new Error(data.message || 'خطا در دریافت لیست مشتریان'));
                    }
                })
                .catch(error => {
                    console.error('Error getting customers:', error);
                    reject(error);
                });
        });
    }

    /**
     * دریافت اطلاعات یک مشتری
     */
    function getCustomer(customerName) {
        return new Promise((resolve, reject) => {
            fetch(`/api/inventory/customer/${customerName}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || `خطا در دریافت اطلاعات مشتری ${customerName}`));
                    }
                })
                .catch(error => {
                    console.error('Error getting customer:', error);
                    reject(error);
                });
        });
    }

    /**
     * ذخیره متغیرهای مشتری
     */
    function saveCustomerVars(customer, vars) {
        return new Promise((resolve, reject) => {
            fetch('/api/inventory/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    customer: customer,
                    vars: vars
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در ذخیره تغییرات'));
                    }
                })
                .catch(error => {
                    console.error('Error saving customer vars:', error);
                    reject(error);
                });
        });
    }

    /**
     * اجرای پلی‌بوک
     */
    function runPlaybook(customer, extraVars = {}, tags = null) {
        return new Promise((resolve, reject) => {
            const payload = {
                customer: customer,
                extra_vars: extraVars
            };

            if (tags) {
                payload.tags = tags;
            }

            fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'started' || data.status === 'success') {
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'خطا در اجرای پلی‌بوک'));
                    }
                })
                .catch(error => {
                    console.error('Error running playbook:', error);
                    reject(error);
                });
        });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * دریافت متغیرهای ادغام شده یک مشتری
     */
    function getCustomerVars(customer) {
        if (!inventoryData.all || !inventoryData.all.hosts || !inventoryData.all.hosts[customer]) {
            return {};
        }

        const customerVars = inventoryData.all.hosts[customer]?.vars || {};
        const defaultVars = inventoryData.all.vars || {};
        return { ...defaultVars, ...customerVars };
    }

    /**
     * اعتبارسنجی ورودی‌ها
     */
    function validateInputs() {
        return {
            isEnglish: function (value) {
                return /^[\x00-\x7F]*$/.test(value);
            },
            isValidDomain: function (value) {
                return /^(?!:\/\/)([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$/.test(value);
            },
            isValidIP: function (value) {
                return /^(25[0-5]|2[0-4]\d|[01]?\d\d?)\.((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){2}(25[0-5]|2[0-4]\d|[01]?\d\d?)$/.test(value);
            }
        };
    }

    /**
     * دسته‌بندی متغیرها برای تب‌ها
     */
    function categorizeVars(vars) {
        const modules = {};
        const domain = {};
        const backup = {};
        const test = {};
        const database = {};

        Object.entries(vars).forEach(([key, value]) => {
            if (key === "customer_domain" || key === "customer_url" || key.startsWith("customer_subdomain_")) {
                domain[key] = value;
            }
            else if (key.startsWith("customer_backup_")) {
                backup[key] = value;
            }
            else if (key.startsWith("customer_test_")) {
                test[key] = value;
            }
            else if (key.includes("_mysql_")) {
                const service = key.split("_mysql_")[0];
                if (!database[service]) {
                    database[service] = {};
                }
                database[service][key] = value;
            }
            else if (key.startsWith("customer_") && !key.includes("subdomain") && key !== "customer_state") {
                let service = key.replace("customer_", "").split("_git")[0].split("_update")[0];

                if (modulesList.includes(service)) {
                    if (!modules[service]) {
                        modules[service] = {};
                    }
                    modules[service][key] = value;
                }
            }
        });

        return { modules, domain, backup, test, database };
    }

    /**
 * رندر کردن فیلدهای ورودی
 */
    function renderInputs(items, labels = {}) {
        const entries = Object.entries(items);

        // Boolean اول
        const booleans = entries.filter(([key, value]) => typeof value === "boolean");
        // Cron آخر
        const crons = entries.filter(([key, value]) => key.includes("cron_"));
        // بقیه متون
        const texts = entries.filter(([key, value]) => typeof value !== "boolean" && !key.includes("cron_"));

        const allItems = [...booleans, ...texts, ...crons];

        return allItems.map(([key, value]) => renderInput(key, value, labels)).join("");
    }

    /**
     * رندر یک فیلد ورودی
     */
    function renderInput(key, value, labels = {}) {
        const validator = validateInputs();

        // استفاده از ماژول Labels اگر موجود باشد
        const labelText = (typeof LabelsModule !== 'undefined')
            ? LabelsModule.getLabel(key, key)
            : (labels[key] || window.labelsFa?.[key] || key);  // اینجا labels هم استفاده می‌شود

        if (typeof value === "boolean") {
            return renderBooleanSwitch(key, value, labelText);
        }

        if (key.includes("cron_")) {
            return renderCron(key, value, labelText);
        }

        let extraValidation = "";
        let inputType = "text";

        if (key === "customer_domain") {
            extraValidation = `onblur="if(!AnsibleModule.validateInputs().isValidDomain(this.value)) alert('دامنه نامعتبر است')"`;
        } else if (key === "customer_url") {
            extraValidation = `onblur="if(!AnsibleModule.validateInputs().isValidIP(this.value)) alert('IP نامعتبر است')"`;
        } else if (key.includes("password") || key.includes("secret")) {
            inputType = "password";
        } else if (key.includes("email")) {
            inputType = "email";
        } else if (typeof value === "number") {
            inputType = "number";
        }

        const englishValidation = `oninput="if(!AnsibleModule.validateInputs().isEnglish(this.value)) this.value=this.value.replace(/[^\\x00-\\x7F]/g,'')"`;

        return `
            <div class="mb-3">
                <label class="form-label">${labels[key] || key}</label>
                <input type="${inputType}" 
                       class="form-control" 
                       value="${value}" 
                       ${englishValidation}
                       ${extraValidation}
                       data-key="${key}">
            </div>
        `;
    }

    /**
     * رندر سوئیچ boolean
     */
    function renderBooleanSwitch(name, value, labels = {}) {
        const id = `switch_${name}`;

        return `
            <div class="form-check form-switch mb-3">
                <input class="form-check-input" 
                       type="checkbox" 
                       id="${id}" 
                       ${value ? "checked" : ""}
                       data-key="${name}">
                <label class="form-check-label" for="${id}">
                    ${labels[name] || name}
                </label>
            </div>
        `;
    }

    /**
     * رندر فیلد cron
     */
    function renderCron(name, value, labels = {}) {
        const parts = value.split(" ");

        return `
            <hr>
            <div class="mb-3">
                <label class="form-label">${labels[name] || name}</label>
                <div class="row g-2">
                    <div class="col">
                        <label class="form-label small">دقیقه</label>
                        <input type="text" 
                               class="form-control" 
                               value="${parts[0] || "*"}" 
                               placeholder="دقیقه"
                               data-cron-part="minute"
                               data-cron-field="${name}">
                    </div>
                    <div class="col">
                        <label class="form-label small">ساعت</label>
                        <input type="text" 
                               class="form-control" 
                               value="${parts[1] || "*"}" 
                               placeholder="ساعت"
                               data-cron-part="hour"
                               data-cron-field="${name}">
                    </div>
                    <div class="col">
                        <label class="form-label small">روز ماه</label>
                        <input type="text" 
                               class="form-control" 
                               value="${parts[2] || "*"}" 
                               placeholder="روز ماه"
                               data-cron-part="day"
                               data-cron-field="${name}">
                    </div>
                    <div class="col">
                        <label class="form-label small">روز هفته</label>
                        <input type="text" 
                               class="form-control" 
                               value="${parts[4] || "*"}" 
                               placeholder="روز هفته"
                               data-cron-part="weekday"
                               data-cron-field="${name}">
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * جمع‌آوری داده‌های فرم
     */
    function collectFormData(containerSelector) {
        const container = document.querySelector(containerSelector);
        if (!container) return {};

        const inputs = container.querySelectorAll('input[data-key], input[data-cron-field]');
        const formData = {};

        inputs.forEach(input => {
            if (input.dataset.key) {
                // فیلدهای معمولی
                const value = input.type === 'checkbox' ? input.checked : input.value;
                formData[input.dataset.key] = value;
            } else if (input.dataset.cronField) {
                // فیلدهای cron
                const cronField = input.dataset.cronField;
                const cronPart = input.dataset.cronPart;

                if (!formData[cronField]) {
                    formData[cronField] = ["*", "*", "*", "*", "*"];
                }

                const index = { minute: 0, hour: 1, day: 2, month: 3, weekday: 4 }[cronPart];
                if (index !== undefined) {
                    formData[cronField][index] = input.value || "*";
                }
            }
        });

        // تبدیل آرایه‌های cron به رشته
        Object.keys(formData).forEach(key => {
            if (Array.isArray(formData[key])) {
                formData[key] = formData[key].join(" ");
            }
        });

        return formData;
    }

    // ============================================================================
    // UI Functions
    // ============================================================================

    /**
     * پر کردن select مشتریان
     */
    function populateCustomerSelect(selectId) {
        return new Promise((resolve, reject) => {
            getCustomers()
                .then(customers => {
                    const select = document.getElementById(selectId);
                    if (!select) {
                        reject(new Error(`Element #${selectId} not found`));
                        return;
                    }

                    select.innerHTML = '<option value="">-- انتخاب مشتری --</option>';

                    Object.entries(customers).forEach(([host, data]) => {
                        const option = document.createElement("option");
                        option.value = host;
                        option.textContent = `${data.name} (${data.state === "up" ? "فعال" : "غیرفعال"})`;
                        select.appendChild(option);
                    });

                    resolve(customers);
                })
                .catch(reject);
        });
    }

    /**
     * آپدیت وضعیت مشتری
     */
    function updateCustomerState(selectId, stateTextId) {
        const select = document.getElementById(selectId);
        const stateText = document.getElementById(stateTextId);

        if (!select || !stateText) return;

        const customer = select.value;
        if (!customer) {
            stateText.textContent = "---";
            return;
        }

        getCustomer(customer)
            .then(data => {
                const state = data.vars.customer_state === "up" ? "فعال" : "غیرفعال";
                stateText.textContent = state;

                // ذخیره مشتری فعلی
                currentCustomer = customer;
            })
            .catch(error => {
                console.error('Error updating customer state:', error);
                stateText.textContent = "خطا";
            });
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع مدیریت Inventory
        loadInventory,
        getCustomers,
        getCustomer,
        saveCustomerVars,
        getCustomerVars,

        // توابع اجرای Ansible
        runPlaybook,

        // توابع Helper
        validateInputs,
        categorizeVars,
        renderInputs,
        collectFormData,

        // توابع UI
        populateCustomerSelect,
        updateCustomerState,

        // متغیرهای داخلی برای دسترسی خارجی
        getModulesList: () => modulesList,
        getCurrentCustomer: () => currentCustomer,
        getInventoryData: () => inventoryData,

        // متدهای پشتیبانی از backward compatibility
        downCustomer: function (customer) {
            return this.runPlaybook(customer, { customer_state: "down" });
        },
        testFull: function (customer) {
            return this.runPlaybook(customer, { customer_test_enabled: true });
        },
        testOnly: function (customer) {
            return this.runPlaybook(customer, { customer_test_enabled: true }, "test");
        },
        testFailFast: function (customer) {
            return this.runPlaybook(customer, {
                customer_test_enabled: true,
                customer_test_fail_fast: true
            });
        },
        backupCustomer: function (customer) {
            return this.runPlaybook(customer, {}, "backup");
        }
    };
})();

// قرار دادن ماژول در scope گلوبال
window.AnsibleModule = AnsibleModule;