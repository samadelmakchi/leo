/**
 * UI Module for Docker Networks Section
 */

const DockerNetworksUI = (function () {
    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Networks section
     */
    function initNetworksSection() {
        console.log('Initializing Networks section...');

        // بارگذاری لیست شبکه‌ها
        loadNetworks();

        // بارگذاری آمار
        refreshStats();

        // تنظیم event listeners
        setupEventListeners();

        return Promise.resolve();
    }

    /**
     * Load networks list
     */
    function loadNetworks() {
        showToast('در حال بارگذاری لیست شبکه‌ها...', 'info');

        return DockerNetworksModule.loadNetworks()
            .then(data => {
                displayNetworks(data.networks);
                showToast(`${data.count} شبکه بارگذاری شد`, 'success');
                return data;
            })
            .catch(error => {
                console.error('Error loading networks:', error);
                showToast(`خطا در بارگذاری شبکه‌ها: ${error.message}`, 'error');

                // نمایش پیام خطا در جدول
                const tbody = document.getElementById('networksTableBody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="8" class="text-center text-danger">
                                <div class="py-4">
                                    <i class="bi bi-exclamation-triangle fs-1"></i>
                                    <h5 class="mt-2">خطا در بارگذاری شبکه‌ها</h5>
                                    <p class="text-muted">${error.message}</p>
                                    <button class="btn btn-primary mt-2" onclick="DockerNetworksUI.loadNetworks()">
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
     * Display networks in table
     */
    function displayNetworks(networks) {
        const tbody = document.getElementById('networksTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!networks || networks.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        هیچ شبکه‌ای یافت نشد
                    </td>
                </tr>
            `;
            document.getElementById('networksCount').textContent = '0';
            return;
        }

        networks.forEach((network, index) => {
            const row = document.createElement('tr');

            // تعیین کلاس بر اساس نوع درایور
            let driverClass = 'bg-light';
            if (network.driver === 'bridge') driverClass = 'bg-info bg-opacity-10';
            if (network.driver === 'overlay') driverClass = 'bg-warning bg-opacity-10';

            // تعیین بج وضعیت
            let statusBadge = '';
            if (network.internal) {
                statusBadge = '<span class="badge bg-dark">داخلی</span>';
            } else {
                statusBadge = '<span class="badge bg-success">عمومی</span>';
            }

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <strong>${network.name}</strong>
                    ${network.attachable ? '<span class="badge bg-secondary ms-1">قابل اتصال</span>' : ''}
                </td>
                <td>
                    <span class="badge bg-dark font-monospace" title="${network.id}">
                        ${network.id.substring(0, 12)}
                    </span>
                </td>
                <td>
                    <span class="badge ${driverClass}">${network.driver}</span>
                </td>
                <td>
                    ${network.containers > 0 ?
                    `<span class="badge bg-primary">${network.containers} کانتینر</span>` :
                    '<span class="text-muted">خالی</span>'
                }
                </td>
                <td>
                    <small class="text-muted">${_formatDate(network.created)}</small>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info" 
                                onclick="DockerNetworksUI.showNetworkDetails('${network.id}')"
                                title="مشاهده جزئیات">
                            👁️
                        </button>
                        <button class="btn btn-outline-warning"
                                onclick="DockerNetworksUI.showContainers('${network.id}')"
                                title="کانتینرهای متصل">
                            📦
                        </button>
                        <button class="btn btn-outline-danger"
                                onclick="DockerNetworksUI.confirmRemoveNetwork('${network.id}')"
                                title="حذف شبکه">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        document.getElementById('networksCount').textContent = networks.length;
    }

    /**
     * Refresh networks and stats
     */
    function refreshNetworks() {
        showToast('در حال بروزرسانی شبکه‌ها...', 'info');

        Promise.all([
            loadNetworks(),
            refreshStats()
        ])
            .then(() => {
                showToast('اطلاعات شبکه‌ها بروزرسانی شد', 'success');
            })
            .catch(error => {
                showToast('خطا در بروزرسانی اطلاعات', 'error');
            });
    }

    /**
     * Refresh statistics
     */
    function refreshStats() {
        return DockerNetworksModule.getNetworkStats()
            .then(stats => {
                document.getElementById('totalNetworks').textContent = stats.total;
                document.getElementById('bridgeNetworks').textContent = stats.bridge;
                document.getElementById('overlayNetworks').textContent = stats.overlay;
                return stats;
            })
            .catch(error => {
                console.error('Error refreshing stats:', error);
                return {};
            });
    }

    /**
     * Show network details
     */
    function showNetworkDetails(networkId) {
        DockerNetworksModule.getNetworkDetails(networkId)
            .then(data => {
                const network = data.network;
                const detailsCard = document.getElementById('networkDetailsCard');
                const detailsContent = document.getElementById('networkDetailsContent');

                if (detailsCard && detailsContent) {
                    detailsContent.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6>اطلاعات پایه</h6>
                                <table class="table table-sm">
                                    <tr><th>نام:</th><td>${network.name}</td></tr>
                                    <tr><th>ID:</th><td><code>${network.id}</code></td></tr>
                                    <tr><th>درایور:</th><td>${network.attrs.Driver || 'bridge'}</td></tr>
                                    <tr><th>Scope:</th><td>${network.attrs.Scope || 'local'}</td></tr>
                                    <tr><th>Internal:</th><td>${network.attrs.Internal ? 'بله' : 'خیر'}</td></tr>
                                    <tr><th>Attachable:</th><td>${network.attrs.Attachable ? 'بله' : 'خیر'}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h6>تنظیمات IPAM</h6>
                                ${network.attrs.IPAM ? `
                                    <pre class="bg-light p-2 rounded" style="max-height: 200px; overflow-y: auto;">
${JSON.stringify(network.attrs.IPAM, null, 2)}
                                    </pre>
                                ` : '<p class="text-muted">بدون تنظیمات IPAM</p>'}
                                
                                ${network.attrs.Labels && Object.keys(network.attrs.Labels).length > 0 ? `
                                    <h6 class="mt-3">Labels</h6>
                                    <div class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto;">
                                        ${Object.entries(network.attrs.Labels).map(([key, value]) => `
                                            <div><strong>${key}:</strong> ${value}</div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-outline-primary" onclick="DockerNetworksUI.showContainers('${networkId}')">
                                مشاهده کانتینرهای متصل
                            </button>
                        </div>
                    `;

                    detailsCard.style.display = 'block';
                }
            })
            .catch(error => {
                showToast(`خطا در دریافت جزئیات شبکه: ${error.message}`, 'error');
            });
    }

    /**
     * Show connected containers
     */
    function showContainers(networkId) {
        DockerNetworksModule.getNetworkContainers(networkId)
            .then(data => {
                const modalHtml = `
                    <div class="modal fade" id="networkContainersModal" tabindex="-1">
                        <div class="modal-dialog modal-lg">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title">کانتینرهای متصل به شبکه ${data.network}</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body">
                                    ${data.containers_count > 0 ? `
                                        <div class="table-responsive">
                                            <table class="table table-sm">
                                                <thead>
                                                    <tr>
                                                        <th>نام کانتینر</th>
                                                        <th>ID</th>
                                                        <th>IPv4</th>
                                                        <th>IPv6</th>
                                                        <th>MAC Address</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${data.containers.map(container => `
                                                        <tr>
                                                            <td>${container.name}</td>
                                                            <td><code>${container.id}</code></td>
                                                            <td>${container.ipv4 || '-'}</td>
                                                            <td>${container.ipv6 || '-'}</td>
                                                            <td>${container.mac_address || '-'}</td>
                                                        </tr>
                                                    `).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    ` : `
                                        <div class="alert alert-info">
                                            هیچ کانتینری به این شبکه متصل نیست
                                        </div>
                                    `}
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                // ایجاد و نمایش مودال
                let modalContainer = document.getElementById('networksModalContainer');
                if (!modalContainer) {
                    modalContainer = document.createElement('div');
                    modalContainer.id = 'networksModalContainer';
                    document.body.appendChild(modalContainer);
                }
                modalContainer.innerHTML = modalHtml;

                const modal = new bootstrap.Modal(document.getElementById('networkContainersModal'));
                modal.show();
            })
            .catch(error => {
                showToast(`خطا در دریافت کانتینرها: ${error.message}`, 'error');
            });
    }

    /**
     * Create new network
     */
    function createNetwork() {
        const name = document.getElementById('networkName').value;
        const driver = document.getElementById('networkDriver').value;
        const internal = document.getElementById('networkInternal').checked;
        const attachable = document.getElementById('networkAttachable').checked;
        const ipamConfig = document.getElementById('networkIPAM').value;

        if (!name) {
            showToast('لطفاً نام شبکه را وارد کنید', 'warning');
            return;
        }

        let ipam = null;
        if (ipamConfig) {
            ipam = DockerNetworksModule.validateIPAMConfig(ipamConfig);
            if (!ipam) {
                showToast('تنظیمات IPAM نامعتبر است', 'error');
                return;
            }
        }

        showToast(`در حال ایجاد شبکه ${name}...`, 'info');

        DockerNetworksModule.createNetwork(name, driver, internal, attachable, {}, ipam)
            .then(data => {
                showToast(`شبکه ${name} با موفقیت ایجاد شد`, 'success');

                // بستن مودال
                const modal = bootstrap.Modal.getInstance(document.getElementById('createNetworkModal'));
                modal.hide();

                // رفرش لیست
                refreshNetworks();
            })
            .catch(error => {
                showToast(`خطا در ایجاد شبکه: ${error.message}`, 'error');
            });
    }

    /**
     * Show create network modal
     */
    function showCreateNetworkModal() {
        // ریست فرم
        document.getElementById('networkName').value = '';
        document.getElementById('networkDriver').value = 'bridge';
        document.getElementById('networkInternal').checked = false;
        document.getElementById('networkAttachable').checked = true;
        document.getElementById('networkIPAM').value = '';

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('createNetworkModal'));
        modal.show();
    }

    /**
     * Show IPAM config section
     */
    function showIPAMConfig() {
        const ipamConfig = document.getElementById('ipamConfig');
        if (ipamConfig.style.display === 'none') {
            ipamConfig.style.display = 'block';
        } else {
            ipamConfig.style.display = 'none';
        }
    }

    /**
     * Confirm network removal
     */
    function confirmRemoveNetwork(networkId) {
        const networks = DockerNetworksModule._getCurrentNetworks();
        const network = networks.find(n => n.id === networkId);

        if (!network) return;

        if (network.containers > 0) {
            showToast('این شبکه دارای کانتینر است و قابل حذف نیست', 'warning');
            return;
        }

        if (confirm(`آیا از حذف شبکه "${network.name}" اطمینان دارید؟`)) {
            showToast(`در حال حذف شبکه ${network.name}...`, 'info');

            DockerNetworksModule.removeNetwork(networkId)
                .then(() => {
                    showToast('شبکه با موفقیت حذف شد', 'success');
                    refreshNetworks();
                })
                .catch(error => {
                    showToast(`خطا در حذف شبکه: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Remove network by ID/name
     */
    function removeNetwork() {
        const networkId = document.getElementById('networkIdToRemove').value;

        if (!networkId) {
            showToast('لطفاً ID یا نام شبکه را وارد کنید', 'warning');
            return;
        }

        // پیدا کردن شبکه
        const networks = DockerNetworksModule._getCurrentNetworks();
        const network = networks.find(n =>
            n.id.includes(networkId) || n.name === networkId
        );

        if (!network) {
            showToast('شبکه یافت نشد', 'error');
            return;
        }

        if (confirm(`آیا از حذف شبکه "${network.name}" اطمینان دارید؟`)) {
            showToast(`در حال حذف شبکه ${network.name}...`, 'info');

            DockerNetworksModule.removeNetwork(network.id)
                .then(() => {
                    showToast('شبکه با موفقیت حذف شد', 'success');
                    refreshNetworks();
                    document.getElementById('networkIdToRemove').value = '';
                })
                .catch(error => {
                    showToast(`خطا در حذف شبکه: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Prune unused networks
     */
    function pruneNetworks() {
        if (confirm('آیا از حذف شبکه‌های بدون استفاده اطمینان دارید؟')) {
            showToast('در حال حذف شبکه‌های بدون استفاده...', 'info');

            DockerNetworksModule.pruneNetworks()
                .then(data => {
                    showToast(`${data.deleted_count} شبکه حذف شد`, 'success');
                    refreshNetworks();
                })
                .catch(error => {
                    showToast(`خطا در حذف شبکه‌ها: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Search networks
     */
    function searchNetworks() {
        const searchTerm = document.getElementById('searchNetwork').value;
        const networks = DockerNetworksModule._getCurrentNetworks();
        const filtered = DockerNetworksModule.searchNetworks(searchTerm, networks);

        displayNetworks(filtered);
        document.getElementById('networksCount').textContent = `${filtered.length} (فیلتر شده)`;
    }

    /**
     * Show advanced settings
     */
    function showAdvancedSettings() {
        showToast('تنظیمات پیشرفته شبکه', 'info');
        // می‌توانید مودال تنظیمات پیشرفته اضافه کنید
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // جستجوی شبکه
        const searchInput = document.getElementById('searchNetwork');
        if (searchInput) {
            searchInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    searchNetworks();
                }
            });
        }

        // حذف شبکه
        const removeInput = document.getElementById('networkIdToRemove');
        if (removeInput) {
            removeInput.addEventListener('keyup', function (e) {
                if (e.key === 'Enter') {
                    removeNetwork();
                }
            });
        }

        // کلیدهای میانبر
        document.addEventListener('keydown', function (e) {
            // Ctrl+N برای ایجاد شبکه جدید
            if (e.ctrlKey && e.key === 'n' && currentSection === 'networks') {
                e.preventDefault();
                showCreateNetworkModal();
            }

            // Ctrl+R برای رفرش
            if (e.ctrlKey && e.key === 'r' && currentSection === 'networks') {
                e.preventDefault();
                refreshNetworks();
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
        initNetworksSection,
        loadNetworks,
        refreshNetworks,
        refreshStats,
        showNetworkDetails,
        showContainers,
        createNetwork,
        showCreateNetworkModal,
        showIPAMConfig,
        confirmRemoveNetwork,
        removeNetwork,
        pruneNetworks,
        searchNetworks,
        showAdvancedSettings
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerNetworksUI = DockerNetworksUI;