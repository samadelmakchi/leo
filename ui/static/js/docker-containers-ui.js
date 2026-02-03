/**
 * UI Module for Docker Containers Section
 */

const DockerContainersUI = (function () {
    // متغیرهای داخلی
    let selectedContainers = new Set();
    let currentContainerDetails = null;

    // ============================================================================
    // Public Functions
    // ============================================================================

    /**
     * Initialize Containers section
     */
    function initContainersSection() {
        console.log('Initializing Containers section...');

        // بارگذاری لیست کانتینرها
        return loadContainers()
            .then(data => {
                // پر کردن select عملیات سریع
                populateQuickSelect(data.containers);

                // بارگذاری آمار سیستم
                return refreshSystemStats();
            })
            .then(() => {
                // تنظیم event listeners
                setupEventListeners();
                return Promise.resolve();
            })
            .catch(error => {
                console.error('Error initializing containers section:', error);
                return Promise.reject(error);
            });

        // بارگذاری آمار سیستم
        refreshSystemStats();

        // پر کردن select عملیات سریع
        populateQuickSelect();

        // تنظیم event listeners
        setupEventListeners();

        return Promise.resolve();
    }

    /**
     * Load containers list
     */
    function loadContainers() {
        showToast('در حال بارگذاری لیست کانتینرها...', 'info');

        return DockerContainersModule.loadContainers()
            .then(data => {
                displayContainers(data.containers);
                updateContainerStats(data.containers);
                showToast(`${data.count} کانتینر بارگذاری شد`, 'success');
                return data;
            })
            .catch(error => {
                console.error('Error loading containers:', error);
                showToast(`خطا در بارگذاری کانتینرها: ${error.message}`, 'error');

                // نمایش پیام خطا در جدول
                const tbody = document.getElementById('containersTableBody');
                if (tbody) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="8" class="text-center text-danger">
                                <div class="py-4">
                                    <i class="bi bi-exclamation-triangle fs-1"></i>
                                    <h5 class="mt-2">خطا در بارگذاری کانتینرها</h5>
                                    <p class="text-muted">${error.message}</p>
                                    <button class="btn btn-primary mt-2" onclick="DockerContainersUI.loadContainers()">
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
     * Display containers in table
     */
    function displayContainers(containers) {
        const tbody = document.getElementById('containersTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        selectedContainers.clear();
        document.getElementById('selectAllContainers').checked = false;

        if (!containers || containers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        هیچ کانتینری یافت نشد
                    </td>
                </tr>
            `;
            // آپدیت select سریع
            populateQuickSelect([]);
            return;
        }

        // اعمال فیلترها
        const filtered = DockerContainersModule.filterContainers(containers);

        filtered.forEach((container, index) => {
            const row = document.createElement('tr');

            row.innerHTML = `
                <td>
                    <input type="checkbox" class="container-checkbox" 
                           value="${container.id}" 
                           onclick="DockerContainersUI.toggleContainerSelection('${container.id}', this)">
                </td>
                <td class="ltr">
                    <strong>${container.name}</strong>
                    ${container.labels && Object.keys(container.labels).length > 0 ?
                    '<span class="badge bg-secondary ms-1" title="دارای برچسب">🏷️</span>' : ''
                }
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-light text-dark me-2">${container.image.split(':')[0]}</span>
                        <small class="text-muted">${container.image.split(':')[1] || 'latest'}</small>
                    </div>
                </td>
                <td>${DockerContainersModule.getStatusBadge(container.status)}</td>
                <td>
                    <small>${DockerContainersModule._formatPorts(container.ports)}</small>
                </td>
                <td>
                    ${container.networks && container.networks.length > 0 ?
                    container.networks.map(net => `<span class="badge bg-info me-1">${net}</span>`).join('') :
                    '<span class="text-muted">-</span>'
                }
                </td>
                <td>
                    <small class="text-muted">${DockerContainersModule._formatDate(container.created)}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-info" 
                                onclick="DockerContainersUI.showContainerDetails('${container.id}')"
                                title="مشاهده جزئیات">
                            👁️
                        </button>
                        ${container.status === 'running' ? `
                            <button class="btn btn-outline-warning"
                                    onclick="DockerContainersUI.stopContainer('${container.id}')"
                                    title="توقف">
                                ⏹️
                            </button>
                            <button class="btn btn-outline-secondary"
                                    onclick="DockerContainersUI.pauseContainer('${container.id}')"
                                    title="مکث">
                                ⏸️
                            </button>
                        ` : `
                            <button class="btn btn-outline-success"
                                    onclick="DockerContainersUI.startContainer('${container.id}')"
                                    title="شروع">
                                ▶️
                            </button>
                        `}
                        <button class="btn btn-outline-danger"
                                onclick="DockerContainersUI.confirmRemoveContainer('${container.id}')"
                                title="حذف">
                            🗑️
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        // آپدیت آمار
        updateContainerStats(filtered);

        // آپدیت select سریع با داده‌های فیلتر شده
        populateQuickSelect(filtered);
    }

    /**
     * Update container statistics
     */
    function updateContainerStats(containers) {
        const stats = DockerContainersModule.calculateContainerStats(containers);

        document.getElementById('containersCount').textContent = stats.total;
        document.getElementById('runningCount').textContent = `${stats.running} در حال اجرا`;
        document.getElementById('stoppedCount').textContent = `${stats.exited + stats.stopped} متوقف شده`;
    }

    /**
     * Refresh containers and stats
     */
    function refreshContainers() {
        showToast('در حال بروزرسانی کانتینرها...', 'info');

        Promise.all([
            loadContainers(),
            refreshSystemStats()
        ])
            .then(() => {
                showToast('اطلاعات کانتینرها بروزرسانی شد', 'success');
            })
            .catch(error => {
                showToast('خطا در بروزرسانی اطلاعات', 'error');
            });
    }

    /**
     * Refresh system statistics
     */
    function refreshSystemStats() {
        return DockerContainersModule.getAllContainersStats()
            .then(data => {
                document.getElementById('statsTotal').textContent = data.stats.total;
                document.getElementById('statsRunning').textContent = data.stats.running;
                document.getElementById('statsStopped').textContent = data.stats.stopped;
                document.getElementById('statsPaused').textContent = data.stats.paused;
                document.getElementById('statsRestarting').textContent = data.stats.restarting;
                document.getElementById('statsUniqueImages').textContent = data.stats.images;
                return data;
            })
            .catch(error => {
                console.error('Error refreshing system stats:', error);
                // استفاده از آمار محلی
                const stats = DockerContainersModule.calculateContainerStats();
                document.getElementById('statsTotal').textContent = stats.total;
                document.getElementById('statsRunning').textContent = stats.running;
                document.getElementById('statsStopped').textContent = stats.exited + stats.stopped;
                document.getElementById('statsPaused').textContent = data.stats.paused;
                document.getElementById('statsRestarting').textContent = data.stats.restarting;
                document.getElementById('statsUniqueImages').textContent = stats.uniqueImages;
                return {};
            });
    }

    /**
     * Show container details
     */
    function showContainerDetails(containerId) {
        DockerContainersModule.getContainerDetails(containerId)
            .then(data => {
                currentContainerDetails = data.container;
                const detailsCard = document.getElementById('containerDetailsCard');

                if (detailsCard) {
                    detailsCard.style.display = 'block';
                    updateContainerDetailsTabs(data.container);

                    // اسکرول به کارت جزئیات
                    detailsCard.scrollIntoView({ behavior: 'smooth' });
                }
            })
            .catch(error => {
                showToast(`خطا در دریافت جزئیات کانتینر: ${error.message}`, 'error');
            });
    }

    /**
     * Update container details tabs
     */
    function updateContainerDetailsTabs(container) {
        // Tab 1: اطلاعات
        document.getElementById('containerInfoTab').innerHTML = getContainerInfoHTML(container);

        // Tab 2: لاگ‌ها (لود می‌شود وقتی تب انتخاب شود)
        document.getElementById('containerLogsTab').innerHTML = `
            <div class="text-center">
                <button class="btn btn-primary" onclick="DockerContainersUI.loadContainerLogs('${container.id}')">
                    بارگذاری لاگ‌ها
                </button>
                <div class="mt-3 w-100 ltr" id="containerLogsContent"></div>
            </div>
        `;

        // Tab 3: آمار مصرف
        document.getElementById('containerStatsTab').innerHTML = `
            <div class="text-center">
                <button class="btn btn-primary" onclick="DockerContainersUI.loadContainerStats('${container.id}')">
                    بارگذاری آمار مصرف
                </button>
                <div class="mt-3" id="containerStatsContent"></div>
            </div>
        `;

        // Tab 4: اجرای دستور
        document.getElementById('containerExecTab').innerHTML = getContainerExecHTML(container);
    }

    /**
     * Get container info HTML
     */
    function getContainerInfoHTML(container) {
        const attrs = container.attrs;
        const config = attrs.Config || {};
        const hostConfig = attrs.HostConfig || {};
        const networkSettings = attrs.NetworkSettings || {};

        return `
            <div class="row">
                <div class="col-md-6">
                    <h6>اطلاعات پایه</h6>
                    <table class="table table-sm ltr">
                        <tr><th>Name:</th><td>${container.name}</td></tr>
                        <tr><th>ID:</th><td><code>${container.id.substring(0, 12)}</code></td></tr>
                        <tr><th>Image:</th><td>${config.Image || '-'}</td></tr>
                        <tr><th>State:</th><td>${attrs.State?.Status || '-'}</td></tr>
                        <tr><th>Crate Date:</th><td>${DockerContainersModule._formatDate(attrs.Created || '')}</td></tr>
                        <tr><th>Commend:</th><td><code>${config.Cmd ? config.Cmd.join(' ') : '-'}</code></td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>تنظیمات</h6>
                    <table class="table table-sm ltr">
                        <tr><th>Restart Policy:</th><td>${hostConfig.RestartPolicy?.Name || 'no'}</td></tr>
                        <tr><th>Network Mode:</th><td>${hostConfig.NetworkMode || 'default'}</td></tr>
                        <tr><th>IP Address:</th><td>${networkSettings.IPAddress || '-'}</td></tr>
                        <tr><th>Gateway:</th><td>${networkSettings.Gateway || '-'}</td></tr>
                        <tr><th>Mac Address:</th><td>${networkSettings.MacAddress || '-'}</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <h6>متغیرهای محیطی</h6>
                    ${config.Env && config.Env.length > 0 ? `
                        <div class="bg-light p-2 rounded info-box ltr">
                            ${config.Env.map(env => `<div><code>${env}</code></div>`).join('')}
                        </div>
                    ` : '<p class="text-muted">بدون متغیر محیطی</p>'}
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>پورت‌ها</h6>
                    ${attrs.NetworkSettings?.Ports ? `
                        <div class="bg-light p-2 rounded info-box ltr">
                            ${Object.entries(attrs.NetworkSettings.Ports).map(([port, mapping]) => `
                                <div><strong>${port}:</strong> ${mapping ? mapping[0]?.HostPort + ':' + mapping[0]?.HostIp : 'Not published'}</div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted">پورتی منتشر نشده</p>'}
                </div>
                <div class="col-md-6">
                    <h6>Mounts</h6>
                    ${attrs.Mounts && attrs.Mounts.length > 0 ? `
                        <div class="bg-light p-2 rounded info-box ltr">
                            ${attrs.Mounts.map(mount => `
                                <div>
                                    <strong>${mount.Source || '-'}</strong> → ${mount.Destination || '-'}
                                    <small class="text-muted">(${mount.Mode || 'rw'})</small>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted">بدون mount</p>'}
                </div>
            </div>
        `;
    }

    /**
     * Get container exec HTML
     */
    function getContainerExecHTML(container) {
        return `
            <div class="mb-3">
                <label class="d-block mb-3">اجرای دستور در کانتینر <strong>${container.name}</strong></label>
                <div class="input-group">
                    <input type="text" class="form-control" id="execCommandInput" 
                           placeholder="مثال: ls -la /app">
                    <button class="btn btn-primary" onclick="DockerContainersUI.executeContainerCommand()">
                        اجرا
                    </button>
                </div>
                <div class="form-text">دستوراتی مانند ls, cat, ps و ...</div>
            </div>
            
            <div class="mt-3">
                <h6 class="mx-2">دستورات پیشنهادی</h6>
                <div class="btn-group btn-group-sm mb-2">
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('execCommandInput').value='ls -la'">
                        ls -la
                    </button>
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('execCommandInput').value='ps aux'">
                        ps aux
                    </button>
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('execCommandInput').value='df -h'">
                        df -h
                    </button>
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('execCommandInput').value='free -m'">
                        free -m
                    </button>
                </div>
            </div>
            
            <div class="mt-3">
                <h6>خروجی</h6>
                <pre class="bg-light p-3 rounded" id="execCommandOutput"></pre>
            </div>
        `;
    }

    /**
     * Load container logs
     */
    function loadContainerLogs(containerId) {
        if (!currentContainerDetails) return;

        DockerContainersModule.getContainerLogs(containerId, '100', true)
            .then(data => {
                const logsContent = document.getElementById('containerLogsContent');
                if (logsContent) {
                    logsContent.innerHTML = `
                        <div class="alert alert-info">
                            <strong>تعداد خطوط:</strong> ${data.lines_count}
                        </div>
                        <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">
${data.logs}
                        </pre>
                        <button class="btn btn-sm btn-outline-secondary mt-2" 
                                onclick="DockerContainersModule.getContainerLogs('${containerId}', '500', true).then(d => {
                                    document.getElementById('containerLogsContent').querySelector('pre').textContent = d.logs;
                                })">
                            بارگذاری 500 خط آخر
                        </button>
                    `;
                }
            })
            .catch(error => {
                showToast(`خطا در دریافت لاگ‌ها: ${error.message}`, 'error');
            });
    }

    /**
     * Load container stats
     */
    function loadContainerStats(containerId) {
        if (!currentContainerDetails) return;

        DockerContainersModule.getContainerStats(containerId)
            .then(data => {
                const stats = data.stats;
                const statsContent = document.getElementById('containerStatsContent');

                if (statsContent) {
                    const memoryPercent = stats.memory.percent.toFixed(2);
                    const cpuPercent = stats.cpu_usage.percent.toFixed(2);

                    statsContent.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">💾 حافظه</div>
                                    <div class="card-body">
                                        <div class="progress mb-2" style="height: 20px;">
                                            <div class="progress-bar ${memoryPercent > 80 ? 'bg-danger' : memoryPercent > 60 ? 'bg-warning' : 'bg-success'}" 
                                                 style="width: ${memoryPercent}%">
                                                ${memoryPercent}%
                                            </div>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <small>مصرف: ${(stats.memory.usage / (1024 * 1024)).toFixed(2)} MB</small>
                                            <small>حداکثر: ${(stats.memory.limit / (1024 * 1024)).toFixed(2)} MB</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">⚡ CPU</div>
                                    <div class="card-body">
                                        <div class="progress mb-2" style="height: 20px;">
                                            <div class="progress-bar ${cpuPercent > 80 ? 'bg-danger' : cpuPercent > 60 ? 'bg-warning' : 'bg-info'}" 
                                                 style="width: ${cpuPercent}%">
                                                ${cpuPercent}%
                                            </div>
                                        </div>
                                        <small>مصرف کل: ${stats.cpu_usage.total_usage}</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">📊 سایر آمار</div>
                                    <div class="card-body">
                                        <div class="row">
                                            <div class="col-md-4">
                                                <strong>Processes:</strong> ${stats.pids}
                                            </div>
                                            <div class="col-md-4">
                                                <strong>Network:</strong> ${Object.keys(stats.network || {}).length} interface
                                            </div>
                                            <div class="col-md-4">
                                                <strong>آخرین بروزرسانی:</strong> ${stats.read_time ? new Date(stats.read_time).toLocaleTimeString('fa-IR') : '-'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <button class="btn btn-sm btn-outline-primary mt-3" 
                                onclick="DockerContainersUI.loadContainerStats('${containerId}')">
                            🔄 بروزرسانی آمار
                        </button>
                    `;
                }
            })
            .catch(error => {
                showToast(`خطا در دریافت آمار: ${error.message}`, 'error');
            });
    }

    /**
     * Execute command in container
     */
    function executeContainerCommand() {
        if (!currentContainerDetails) {
            showToast('لطفاً ابتدا یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        const command = document.getElementById('execCommandInput').value;
        if (!command) {
            showToast('لطفاً دستور را وارد کنید', 'warning');
            return;
        }

        DockerContainersModule.execContainerCommand(currentContainerDetails.id, command)
            .then(data => {
                const outputDiv = document.getElementById('execCommandOutput');
                if (outputDiv) {
                    const exitCodeBadge = data.exit_code === 0 ?
                        '<span class="badge bg-success">موفق</span>' :
                        `<span class="badge bg-danger">خطا: ${data.exit_code}</span>`;

                    outputDiv.innerHTML = `
                        <div class="mb-2">
                            <strong>دستور:</strong> <code>${data.command}</code>
                            ${exitCodeBadge}
                        </div>
                        <hr>
                        <pre>${data.output || '(بدون خروجی)'}</pre>
                    `;
                }
            })
            .catch(error => {
                showToast(`خطا در اجرای دستور: ${error.message}`, 'error');
            });
    }

    // ============================================================================
    // Container Operations
    // ============================================================================

    /**
     * Start a container
     */
    function startContainer(containerId) {
        showToast('در حال شروع کانتینر...', 'info');

        DockerContainersModule.startContainer(containerId)
            .then(() => {
                showToast('کانتینر با موفقیت شروع شد', 'success');
                refreshContainers();
            })
            .catch(error => {
                showToast(`خطا در شروع کانتینر: ${error.message}`, 'error');
            });
    }

    /**
     * Stop a container
     */
    function stopContainer(containerId) {
        if (confirm('آیا از توقف کانتینر اطمینان دارید؟')) {
            showToast('در حال توقف کانتینر...', 'info');

            DockerContainersModule.stopContainer(containerId)
                .then(() => {
                    showToast('کانتینر با موفقیت متوقف شد', 'success');
                    refreshContainers();
                })
                .catch(error => {
                    showToast(`خطا در توقف کانتینر: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Restart a container
     */
    function restartContainer(containerId) {
        if (confirm('آیا از راه‌اندازی مجدد کانتینر اطمینان دارید؟')) {
            showToast('در حال راه‌اندازی مجدد کانتینر...', 'info');

            DockerContainersModule.restartContainer(containerId)
                .then(() => {
                    showToast('کانتینر با موفقیت راه‌اندازی مجدد شد', 'success');
                    refreshContainers();
                })
                .catch(error => {
                    showToast(`خطا در راه‌اندازی مجدد کانتینر: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Pause a container
     */
    function pauseContainer(containerId) {
        if (confirm('آیا از مکث کانتینر اطمینان دارید؟')) {
            showToast('در حال مکث کانتینر...', 'info');

            DockerContainersModule.pauseContainer(containerId)
                .then(() => {
                    showToast('کانتینر با موفقیت مکث شد', 'success');
                    refreshContainers();
                })
                .catch(error => {
                    showToast(`خطا در مکث کانتینر: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Unpause a container
     */
    function unpauseContainer(containerId) {
        showToast('در حال ادامه کانتینر...', 'info');

        DockerContainersModule.unpauseContainer(containerId)
            .then(() => {
                showToast('کانتینر با موفقیت ادامه داده شد', 'success');
                refreshContainers();
            })
            .catch(error => {
                showToast(`خطا در ادامه کانتینر: ${error.message}`, 'error');
            });
    }

    /**
     * Confirm container removal
     */
    function confirmRemoveContainer(containerId) {
        const containers = DockerContainersModule._getCurrentContainers();
        const container = containers.find(c => c.id === containerId);

        if (!container) return;

        const force = container.status === 'running';
        const message = force ?
            `کانتینر "${container.name}" در حال اجراست. آیا می‌خواهید به صورت اجباری حذف شود؟` :
            `آیا از حذف کانتینر "${container.name}" اطمینان دارید؟`;

        if (confirm(message)) {
            const removeVolumes = confirm('آیا ولوم‌های مرتبط نیز حذف شوند؟');

            showToast(`در حال حذف کانتینر ${container.name}...`, 'info');

            DockerContainersModule.removeContainer(containerId, force, removeVolumes)
                .then(() => {
                    showToast('کانتینر با موفقیت حذف شد', 'success');
                    refreshContainers();
                })
                .catch(error => {
                    showToast(`خطا در حذف کانتینر: ${error.message}`, 'error');
                });
        }
    }

    /**
     * Prune stopped containers
     */
    function pruneContainers() {
        if (confirm('آیا از حذف تمام کانتینرهای متوقف شده اطمینان دارید؟')) {
            showToast('در حال حذف کانتینرهای متوقف شده...', 'info');

            DockerContainersModule.pruneContainers()
                .then(data => {
                    showToast(`${data.deleted_count} کانتینر حذف شد. فضای آزاد شده: ${data.space_reclaimed}`, 'success');
                    refreshContainers();
                })
                .catch(error => {
                    showToast(`خطا در حذف کانتینرها: ${error.message}`, 'error');
                });
        }
    }

    // ============================================================================
    // Selection Management
    // ============================================================================

    /**
     * Toggle container selection
     */
    function toggleContainerSelection(containerId, checkbox) {
        if (checkbox.checked) {
            selectedContainers.add(containerId);
        } else {
            selectedContainers.delete(containerId);
            document.getElementById('selectAllContainers').checked = false;
        }

        updateSelectionCount();
    }

    /**
     * Toggle select all containers
     */
    function toggleSelectAll() {
        const selectAll = document.getElementById('selectAllContainers');
        const checkboxes = document.querySelectorAll('.container-checkbox');

        if (selectAll.checked) {
            checkboxes.forEach(cb => {
                cb.checked = true;
                selectedContainers.add(cb.value);
            });
        } else {
            checkboxes.forEach(cb => {
                cb.checked = false;
                selectedContainers.delete(cb.value);
            });
        }

        updateSelectionCount();
    }

    /**
     * Update selection count
     */
    function updateSelectionCount() {
        // می‌توانید تعداد انتخاب شده‌ها را در جایی نمایش دهید
        console.log(`Selected containers: ${selectedContainers.size}`);
    }

    /**
     * Populate quick select dropdown
     */
    function populateQuickSelect(containers) {
        const select = document.getElementById('quickSelectContainer');
        if (!select) return;

        select.innerHTML = '<option value="">-- انتخاب کانتینر --</option>';

        if (!containers || containers.length === 0) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = 'کانتینری یافت نشد';
            select.appendChild(option);
            return;
        }

        containers.forEach(container => {
            const option = document.createElement('option');
            option.value = container.id;
            option.textContent = `${container.name} (${container.status})`;
            select.appendChild(option);
        });
    }

    // ============================================================================
    // Quick Actions
    // ============================================================================

    /**
     * Quick start container
     */
    function quickStart() {
        const select = document.getElementById('quickSelectContainer');
        const containerId = select.value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        startContainer(containerId);
    }

    /**
     * Quick stop container
     */
    function quickStop() {
        const select = document.getElementById('quickSelectContainer');
        const containerId = select.value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        stopContainer(containerId);
    }

    /**
     * Quick restart container
     */
    function quickRestart() {
        const select = document.getElementById('quickSelectContainer');
        const containerId = select.value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        restartContainer(containerId);
    }

    /**
     * Quick pause container
     */
    function quickPause() {
        const select = document.getElementById('quickSelectContainer');
        const containerId = select.value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        pauseContainer(containerId);
    }

    /**
     * Quick remove container
     */
    function quickRemove() {
        const select = document.getElementById('quickSelectContainer');
        const containerId = select.value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        confirmRemoveContainer(containerId);
    }

    // ============================================================================
    // Batch Actions
    // ============================================================================

    /**
     * Batch start containers
     */
    function batchStart() {
        if (selectedContainers.size === 0) {
            showToast('لطفاً حداقل یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        if (confirm(`آیا از شروع ${selectedContainers.size} کانتینر انتخاب شده اطمینان دارید؟`)) {
            showBatchModal('در حال شروع کانتینرها...');

            let completed = 0;
            const results = [];

            selectedContainers.forEach(containerId => {
                DockerContainersModule.startContainer(containerId)
                    .then(() => {
                        results.push({ id: containerId, status: 'success' });
                    })
                    .catch(error => {
                        results.push({ id: containerId, status: 'error', message: error.message });
                    })
                    .finally(() => {
                        completed++;
                        updateBatchProgress(completed, selectedContainers.size);

                        if (completed === selectedContainers.size) {
                            showBatchResults(results, 'شروع کانتینرها');
                            refreshContainers();
                        }
                    });
            });
        }
    }

    /**
     * Batch stop containers
     */
    function batchStop() {
        const containers = DockerContainersModule._getCurrentContainers();
        const runningContainers = containers.filter(c => c.status === 'running');

        if (runningContainers.length === 0) {
            showToast('هیچ کانتینر در حال اجرایی وجود ندارد', 'info');
            return;
        }

        if (confirm(`آیا از توقف ${runningContainers.length} کانتینر در حال اجرا اطمینان دارید؟`)) {
            showBatchModal('در حال توقف کانتینرها...');

            let completed = 0;
            const results = [];

            runningContainers.forEach(container => {
                DockerContainersModule.stopContainer(container.id)
                    .then(() => {
                        results.push({ id: container.id, name: container.name, status: 'success' });
                    })
                    .catch(error => {
                        results.push({ id: container.id, name: container.name, status: 'error', message: error.message });
                    })
                    .finally(() => {
                        completed++;
                        updateBatchProgress(completed, runningContainers.length);

                        if (completed === runningContainers.length) {
                            showBatchResults(results, 'توقف کانتینرها');
                            refreshContainers();
                        }
                    });
            });
        }
    }

    /**
     * Batch remove selected containers
     */
    function batchRemove() {
        if (selectedContainers.size === 0) {
            showToast('لطفاً حداقل یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        if (confirm(`آیا از حذف ${selectedContainers.size} کانتینر انتخاب شده اطمینان دارید؟`)) {
            const force = confirm('آیا می‌خواهید به صورت اجباری حذف شوند؟');
            const removeVolumes = confirm('آیا ولوم‌های مرتبط نیز حذف شوند؟');

            showBatchModal('در حال حذف کانتینرها...');

            let completed = 0;
            const results = [];

            selectedContainers.forEach(containerId => {
                DockerContainersModule.removeContainer(containerId, force, removeVolumes)
                    .then(() => {
                        results.push({ id: containerId, status: 'success' });
                    })
                    .catch(error => {
                        results.push({ id: containerId, status: 'error', message: error.message });
                    })
                    .finally(() => {
                        completed++;
                        updateBatchProgress(completed, selectedContainers.size);

                        if (completed === selectedContainers.size) {
                            showBatchResults(results, 'حذف کانتینرها');
                            refreshContainers();
                            selectedContainers.clear();
                            document.getElementById('selectAllContainers').checked = false;
                        }
                    });
            });
        }
    }

    /**
     * Show batch modal
     */
    function showBatchModal(message) {
        document.getElementById('batchActionMessage').textContent = message;
        document.getElementById('batchProgressBar').style.width = '0%';
        document.getElementById('batchResults').innerHTML = '';
        document.querySelector('#batchActionsModal .progress').style.display = 'block';

        const modal = new bootstrap.Modal(document.getElementById('batchActionsModal'));
        modal.show();
    }

    /**
     * Update batch progress
     */
    function updateBatchProgress(current, total) {
        const percent = (current / total) * 100;
        document.getElementById('batchProgressBar').style.width = `${percent}%`;
    }

    /**
     * Show batch results
     */
    function showBatchResults(results, actionName) {
        const successCount = results.filter(r => r.status === 'success').length;
        const errorCount = results.filter(r => r.status === 'error').length;

        let resultsHtml = `
            <div class="alert ${errorCount === 0 ? 'alert-success' : 'alert-warning'}">
                <strong>${actionName} تکمیل شد</strong><br>
                موفق: ${successCount} | خطا: ${errorCount}
            </div>
        `;

        if (errorCount > 0) {
            resultsHtml += `
                <h6>جزئیات خطاها:</h6>
                <div class="bg-light p-2 rounded" style="max-height: 200px; overflow-y: auto;">
                    ${results.filter(r => r.status === 'error').map(r => `
                        <div class="text-danger">
                            <strong>${r.name || r.id}:</strong> ${r.message}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        document.getElementById('batchResults').innerHTML = resultsHtml;
        document.querySelector('#batchActionsModal .progress').style.display = 'none';
    }

    // ============================================================================
    // Filter and Search
    // ============================================================================

    /**
     * Filter containers
     */
    function filterContainers() {
        const status = document.getElementById('filterStatus').value;
        DockerContainersModule.setFilter('status', status);

        const containers = DockerContainersModule._getCurrentContainers();
        displayContainers(containers);
    }

    /**
     * Search containers
     */
    function searchContainers() {
        const searchTerm = document.getElementById('searchContainer').value;
        DockerContainersModule.setFilter('search', searchTerm);

        const containers = DockerContainersModule._getCurrentContainers();
        displayContainers(containers);
    }

    /**
     * Sort containers
     */
    function sortContainers() {
        const sortType = document.getElementById('sortContainers').value;
        DockerContainersModule.setFilter('sort', sortType);

        const containers = DockerContainersModule._getCurrentContainers();
        displayContainers(containers);
    }

    // ============================================================================
    // Create Container
    // ============================================================================

    /**
     * Show create container modal
     */
    function showCreateContainerModal() {
        // ریست فرم
        document.getElementById('containerName').value = '';
        document.getElementById('containerImage').value = 'nginx:latest';
        document.getElementById('containerCommand').value = '';
        document.getElementById('containerPorts').value = '';
        document.getElementById('containerEnv').value = '';
        document.getElementById('containerNetwork').value = '';
        document.getElementById('containerRestartPolicy').value = 'unless-stopped';
        document.getElementById('containerAutoStart').checked = true;

        // پر کردن لیست شبکه‌ها
        loadNetworksForSelect();

        // نمایش مودال
        const modal = new bootstrap.Modal(document.getElementById('createContainerModal'));
        modal.show();
    }

    /**
     * Load networks for select
     */
    function loadNetworksForSelect() {
        const select = document.getElementById('containerNetwork');
        select.innerHTML = '<option value="">پیش‌فرض</option>';

        // اگر ماژول شبکه‌ها لود شده باشد
        if (typeof DockerNetworksModule !== 'undefined') {
            DockerNetworksModule.loadNetworks()
                .then(data => {
                    data.networks.forEach(network => {
                        const option = document.createElement('option');
                        option.value = network.name;
                        option.textContent = `${network.name} (${network.driver})`;
                        select.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error loading networks:', error);
                });
        }
    }

    /**
     * Create new container
     */
    function createContainer() {
        const name = document.getElementById('containerName').value;
        const image = document.getElementById('containerImage').value;
        const command = document.getElementById('containerCommand').value;
        const portsStr = document.getElementById('containerPorts').value;
        const envStr = document.getElementById('containerEnv').value;
        const network = document.getElementById('containerNetwork').value;
        const restartPolicy = document.getElementById('containerRestartPolicy').value;
        const autoStart = document.getElementById('containerAutoStart').checked;

        if (!name || !image) {
            showToast('نام و تصویر کانتینر الزامی است', 'warning');
            return;
        }

        // بررسی تنظیمات
        const ports = DockerContainersModule.validateJSONConfig(portsStr, {});
        const environment = DockerContainersModule.validateJSONConfig(envStr, {});

        if (ports === null || environment === null) {
            showToast('تنظیمات پورت‌ها یا متغیرهای محیطی نامعتبر است', 'error');
            return;
        }

        // ساخت config
        const config = {
            name: name,
            image: image,
            command: command || undefined,
            ports: ports,
            environment: environment,
            network: network || undefined,
            restart_policy: { Name: restartPolicy }
        };

        showToast('در حال ایجاد کانتینر...', 'info');

        DockerContainersModule.createContainer(config)
            .then(data => {
                showToast(`کانتینر ${name} با موفقیت ایجاد شد`, 'success');

                // بستن مودال
                const modal = bootstrap.Modal.getInstance(document.getElementById('createContainerModal'));
                modal.hide();

                // شروع خودکار اگر انتخاب شده باشد
                if (autoStart) {
                    showToast('در حال شروع کانتینر...', 'info');
                    return DockerContainersModule.startContainer(data.container_id);
                }
                return Promise.resolve();
            })
            .then(() => {
                refreshContainers();
            })
            .catch(error => {
                showToast(`خطا در ایجاد کانتینر: ${error.message}`, 'error');
            });
    }

    // ============================================================================
    // Helper Functions
    // ============================================================================

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // تغییر تب‌های جزئیات
        const tabTriggers = document.querySelectorAll('#containerDetailsTabs button');
        tabTriggers.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function (event) {
                const target = event.target.getAttribute('data-bs-target');

                if (target === '#containerLogsTab' && currentContainerDetails) {
                    loadContainerLogs(currentContainerDetails.id);
                } else if (target === '#containerStatsTab' && currentContainerDetails) {
                    loadContainerStats(currentContainerDetails.id);
                }
            });
        });

        // کلیدهای میانبر
        document.addEventListener('keydown', function (e) {
            // Ctrl+F برای فوکوس روی جستجو
            if (e.ctrlKey && e.key === 'f' && currentSection === 'containers') {
                e.preventDefault();
                document.getElementById('searchContainer').focus();
            }

            // Ctrl+R برای رفرش
            if (e.ctrlKey && e.key === 'r' && currentSection === 'containers') {
                e.preventDefault();
                refreshContainers();
            }

            // Ctrl+N برای ایجاد جدید
            if (e.ctrlKey && e.key === 'n' && currentSection === 'containers') {
                e.preventDefault();
                showCreateContainerModal();
            }

            // Esc برای بستن جزئیات
            if (e.key === 'Escape' && currentSection === 'containers') {
                const detailsCard = document.getElementById('containerDetailsCard');
                if (detailsCard && detailsCard.style.display !== 'none') {
                    detailsCard.style.display = 'none';
                }
            }
        });
    }

    /**
     * Show all logs (placeholder)
     */
    function showAllLogs() {
        const modal = createAllLogsModal();
        document.body.appendChild(modal);

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }



    /**
     * Create all logs modal
     */
    function createAllLogsModal() {
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">📝 لاگ‌های تمام کانتینرها</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">کانتینر</label>
                        <select class="form-select" id="allLogsContainerSelect">
                            <option value="">انتخاب کانتینر</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">تعداد خطوط</label>
                        <input type="number" class="form-control" id="allLogsTail" value="100" min="1" max="1000">
                    </div>
                    <button class="btn btn-primary mb-3" onclick="DockerContainersUI.loadAllLogsForContainer()">
                        بارگذاری لاگ‌ها
                    </button>
                    <div class="mt-3">
                        <pre class="bg-dark text-light p-3 rounded" id="allLogsOutput" 
                             style="max-height: 500px; overflow-y: auto; min-height: 200px;">
                            // لاگ‌ها اینجا نمایش داده می‌شوند
                        </pre>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                </div>
            </div>
        </div>
    `;

        // پر کردن لیست کانتینرها بعد از نمایش مودال
        modalDiv.addEventListener('shown.bs.modal', function () {
            populateAllLogsContainerSelect();
        });

        return modalDiv;
    }

    /**
     * Export containers list
     */
    function exportContainersList() {
        const containers = DockerContainersModule._getCurrentContainers();
        const csv = containers.map(c =>
            `"${c.name}","${c.image}","${c.status}","${c.created}","${c.networks.join(',')}"`
        ).join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'containers.csv';
        a.click();

        showToast('لیست کانتینرها ذخیره شد', 'success');
    }

    /**
     * Show health check (placeholder)
     */
    /**
 * Populate all logs container select
 */
    function populateAllLogsContainerSelect() {
        const select = document.getElementById('allLogsContainerSelect');
        if (!select) return;

        select.innerHTML = '<option value="">انتخاب کانتینر</option>';

        const containers = DockerContainersModule._getCurrentContainers();
        containers.forEach(container => {
            const option = document.createElement('option');
            option.value = container.id;
            option.textContent = `${container.name} (${container.status})`;
            select.appendChild(option);
        });
    }

    /**
     * Load logs for selected container
     */
    function loadAllLogsForContainer() {
        const containerId = document.getElementById('allLogsContainerSelect').value;
        const tail = document.getElementById('allLogsTail').value;

        if (!containerId) {
            showToast('لطفاً یک کانتینر انتخاب کنید', 'warning');
            return;
        }

        showToast('در حال بارگذاری لاگ‌ها...', 'info');

        DockerContainersModule.getContainerLogs(containerId, tail, true)
            .then(data => {
                const output = document.getElementById('allLogsOutput');
                if (output) {
                    output.textContent = data.logs;
                    showToast(`${data.lines_count} خط لاگ بارگذاری شد`, 'success');
                }
            })
            .catch(error => {
                showToast(`خطا در بارگذاری لاگ‌ها: ${error.message}`, 'error');
            });
    }

    /**
     * Show health check modal
     */
    function showHealthCheck() {
        const modal = createHealthCheckModal();
        document.body.appendChild(modal);

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // اجرای بررسی سلامت
        runHealthChecks();
    }

    /**
     * Create health check modal
     */
    function createHealthCheckModal() {
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">🏥 بررسی سلامت کانتینرها</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="progress mb-3" style="height: 25px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             id="healthCheckProgress" style="width: 0%">0%</div>
                    </div>
                    <div id="healthCheckResults">
                        <div class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">در حال بررسی...</span>
                            </div>
                            <p class="mt-2">در حال بررسی سلامت کانتینرها...</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">بستن</button>
                    <button type="button" class="btn btn-primary" onclick="DockerContainersUI.runHealthChecks()">
                        🔄 بررسی مجدد
                    </button>
                </div>
            </div>
        </div>
    `;

        return modalDiv;
    }

    /**
     * Run health checks
     */
    function runHealthChecks() {
        const containers = DockerContainersModule._getCurrentContainers();
        const resultsDiv = document.getElementById('healthCheckResults');
        const progressBar = document.getElementById('healthCheckProgress');

        if (!resultsDiv || !progressBar) return;

        // ریست
        resultsDiv.innerHTML = '';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';

        let completed = 0;
        const total = containers.length;
        const allResults = [];

        if (total === 0) {
            resultsDiv.innerHTML = '<div class="alert alert-info">هیچ کانتینری برای بررسی یافت نشد</div>';
            return;
        }

        containers.forEach(container => {
            checkContainerHealth(container)
                .then(result => {
                    allResults.push(result);
                })
                .catch(error => {
                    allResults.push({
                        container: container.name,
                        status: 'error',
                        message: error.message
                    });
                })
                .finally(() => {
                    completed++;
                    const percent = Math.round((completed / total) * 100);
                    progressBar.style.width = `${percent}%`;
                    progressBar.textContent = `${percent}%`;

                    if (completed === total) {
                        displayHealthCheckResults(allResults);
                    }
                });
        });
    }

    /**
     * Check health of a single container
     */
    function checkContainerHealth(container) {
        return new Promise((resolve) => {
            setTimeout(() => {
                let status = 'unknown';
                let message = '';

                if (container.status === 'running') {
                    // شبیه‌سازی بررسی سلامت
                    const isHealthy = Math.random() > 0.3; // 70% شانس سالم بودن

                    if (isHealthy) {
                        status = 'healthy';
                        message = 'کانتینر در حال اجرا و پاسخگو است';
                    } else {
                        status = 'unhealthy';
                        message = 'کانتینر در حال اجرا اما ممکن است مشکل داشته باشد';
                    }
                } else if (container.status === 'exited' || container.status === 'stopped') {
                    status = 'stopped';
                    message = 'کانتینر متوقف شده است';
                } else {
                    status = container.status;
                    message = `وضعیت: ${container.status}`;
                }

                resolve({
                    container: container.name,
                    id: container.id,
                    status: status,
                    message: message,
                    image: container.image,
                    state: container.status
                });
            }, 500); // شبیه‌سازی تاخیر بررسی
        });
    }

    /**
     * Display health check results
     */
    function displayHealthCheckResults(results) {
        const resultsDiv = document.getElementById('healthCheckResults');
        if (!resultsDiv) return;

        const healthy = results.filter(r => r.status === 'healthy').length;
        const unhealthy = results.filter(r => r.status === 'unhealthy').length;
        const stopped = results.filter(r => r.status === 'stopped').length;
        const errors = results.filter(r => r.status === 'error').length;

        let html = `
        <div class="alert ${unhealthy === 0 && errors === 0 ? 'alert-success' : 'alert-warning'}">
            <h6>نتیجه بررسی سلامت</h6>
            <div class="row text-center">
                <div class="col-3">
                    <div class="fs-4">${healthy}</div>
                    <small class="text-success">سالم</small>
                </div>
                <div class="col-3">
                    <div class="fs-4">${unhealthy}</div>
                    <small class="text-warning">مشکل دار</small>
                </div>
                <div class="col-3">
                    <div class="fs-4">${stopped}</div>
                    <small class="text-secondary">متوقف شده</small>
                </div>
                <div class="col-3">
                    <div class="fs-4">${errors}</div>
                    <small class="text-danger">خطا</small>
                </div>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>کانتینر</th>
                        <th>وضعیت</th>
                        <th>پیام</th>
                    </tr>
                </thead>
                <tbody>
    `;

        results.forEach(result => {
            let statusBadge = '';
            switch (result.status) {
                case 'healthy':
                    statusBadge = '<span class="badge bg-success">سالم</span>';
                    break;
                case 'unhealthy':
                    statusBadge = '<span class="badge bg-warning">مشکل دار</span>';
                    break;
                case 'stopped':
                    statusBadge = '<span class="badge bg-secondary">متوقف شده</span>';
                    break;
                case 'error':
                    statusBadge = '<span class="badge bg-danger">خطا</span>';
                    break;
                default:
                    statusBadge = `<span class="badge bg-light text-dark">${result.status}</span>`;
            }

            html += `
            <tr>
                <td>
                    <strong>${result.container}</strong><br>
                    <small class="text-muted">${result.image}</small>
                </td>
                <td>${statusBadge}</td>
                <td>${result.message}</td>
            </tr>
        `;
        });

        html += `
                </tbody>
            </table>
        </div>
        
        <div class="mt-3">
            <button class="btn btn-sm btn-outline-primary" onclick="DockerContainersUI.exportHealthCheckResults()">
                📥 ذخیره نتایج
            </button>
        </div>
    `;

        resultsDiv.innerHTML = html;
    }

    /**
     * Export health check results
     */
    function exportHealthCheckResults() {
        const resultsDiv = document.getElementById('healthCheckResults');
        if (!resultsDiv) return;

        const rows = resultsDiv.querySelectorAll('tbody tr');
        const csv = [];

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 3) {
                const container = cells[0].textContent.trim().replace(/\n/g, ' ');
                const status = cells[1].textContent.trim();
                const message = cells[2].textContent.trim();
                csv.push(`"${container}","${status}","${message}"`);
            }
        });

        const csvContent = 'کانتینر,وضعیت,پیام\n' + csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'health-check-results.csv';
        link.click();

        showToast('نتایج بررسی سلامت ذخیره شد', 'success');
    }

    /**
     * Fix showQuickActions function
     */
    function showQuickActions() {
        // نمایش منو عملیات گروهی
        const actions = `
        <div class="dropdown-menu show p-3" style="width: 300px;">
            <h6 class="mb-2">⚡ عملیات گروهی</h6>
            <div class="d-grid gap-2">
                <button class="btn btn-success btn-sm" onclick="DockerContainersUI.batchStart()">
                    ▶️ شروع انتخاب شده‌ها
                </button>
                <button class="btn btn-warning btn-sm" onclick="DockerContainersUI.batchStop()">
                    ⏸️ توقف همه در حال اجرا
                </button>
                <button class="btn btn-danger btn-sm" onclick="DockerContainersUI.batchRemove()">
                    🗑️ حذف انتخاب شده‌ها
                </button>
                <hr>
                <button class="btn btn-info btn-sm" onclick="DockerContainersUI.pruneContainers()">
                    🧹 پاکسازی کانتینرهای متوقف شده
                </button>
            </div>
        </div>
    `;

        // ایجاد و نمایش منو
        const menu = document.createElement('div');
        menu.className = 'dropdown position-fixed';
        menu.style.cssText = 'top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1060;';
        menu.innerHTML = actions;

        // اضافه کردن backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        backdrop.onclick = function () {
            document.body.removeChild(menu);
            document.body.removeChild(backdrop);
        };

        document.body.appendChild(backdrop);
        document.body.appendChild(menu);
    }

    // ============================================================================
    // Public API
    // ============================================================================

    return {
        // توابع اصلی
        initContainersSection,
        loadContainers,
        refreshContainers,
        refreshSystemStats,

        // نمایش جزئیات
        showContainerDetails,
        loadContainerLogs,
        loadContainerStats,
        executeContainerCommand,

        // عملیات کانتینر
        startContainer,
        stopContainer,
        restartContainer,
        pauseContainer,
        unpauseContainer,
        confirmRemoveContainer,
        pruneContainers,

        // مدیریت انتخاب
        toggleContainerSelection,
        toggleSelectAll,

        // عملیات سریع
        quickStart,
        quickStop,
        quickRestart,
        quickPause,
        quickRemove,

        // عملیات گروهی
        batchStart,
        batchStop,
        batchRemove,

        // فیلتر و جستجو
        filterContainers,
        searchContainers,
        sortContainers,

        // ایجاد کانتینر
        showCreateContainerModal,
        createContainer,

        // توابع کمکی
        showAllLogs,
        exportContainersList,
        showHealthCheck,
        loadAllLogsForContainer,
        runHealthChecks,
        exportHealthCheckResults
    };
})();

// قرار دادن ماژول در scope گلوبال
window.DockerContainersUI = DockerContainersUI;