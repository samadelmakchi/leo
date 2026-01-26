/**
 * ماژول مدیریت لیبل‌های فارسی
 */

const LabelsModule = (function () {
    // لیبل‌های اصلی
    const labelsFa = {
        /* Tabs */
        modules: "ماژول‌ها",
        domain: "دامنه",
        backup: "بکاپ",
        test: "تست",
        database: "پایگاه داده",
        settings: "تنظیمات",
        run: "اجرا",

        /* Actions */
        update: "بروزرسانی",
        down: "داون کردن مشتری",
        backup_run: "بکاپ گرفتن",
        test_full: "تست کامل با دپلوی",
        test_fail_fast: "تست کامل با توقف در خطا",
        test_only: "فقط تست",
        save: "ذخیره در inventory",

        /* Modules */
        gateway: "گیت‌وی",
        portal: "پورتال",
        portal_frontend: "فرانت پورتال",
        lms: "LMS",
        file: "فایل",

        /* Database */
        file_mysql_db_name: "نام پایگاه داده",
        file_mysql_user: "نام کاربری پایگاه داده",
        file_mysql_password: "رمز پایگاه داده",
        file_mysql_root_password: "رمز اصلی پایگاه داده",

        gateway_mysql_db_name: "نام پایگاه داده",
        gateway_mysql_user: "نام کاربری پایگاه داده",
        gateway_mysql_password: "رمز پایگاه داده",
        gateway_mysql_root_password: "رمز اصلی پایگاه داده",

        lms_mysql_db_name: "نام پایگاه داده",
        lms_mysql_user: "نام کاربری پایگاه داده",
        lms_mysql_password: "رمز پایگاه داده",
        lms_mysql_root_password: "رمز اصلی پایگاه داده",

        portal_mysql_db_name: "نام پایگاه داده",
        portal_mysql_user: "نام کاربری پایگاه داده",
        portal_mysql_password: "رمز پایگاه داده",
        portal_mysql_root_password: "رمز اصلی پایگاه داده",

        /* State */
        customer_state: "وضعیت مشتری",

        /* Modules */
        customer_gateway_update: "بروزرسانی ماژول",
        customer_gateway_git_branches: "برنچ ماژول",
        customer_gateway_git_tags: "تگ ماژول",

        customer_portal_frontend_update: "بروزرسانی ماژول",
        customer_portal_frontend_git_branches: "برنچ ماژول",
        customer_portal_frontend_git_tags: "تگ ماژول",

        customer_portal_update: "بروزرسانی ماژول",
        customer_portal_git_branches: "برنچ ماژول",
        customer_portal_git_tags: "تگ ماژول",

        customer_file_update: "بروزرسانی ماژول",
        customer_file_git_branches: "برنچ ماژول",
        customer_file_git_tags: "تگ ماژول",

        customer_lms_update: "بروزرسانی ماژول",
        customer_lms_git_branches: "برنچ ماژول",
        customer_lms_git_tags: "تگ ماژول",

        /* Domain */
        customer_domain: "دامنه اصلی",
        customer_url: "آدرس IP",

        customer_subdomain_gateway: "آدرس ساب دومین Gateway",
        customer_subdomain_file: "آدرس ساب دومین File",
        customer_subdomain_lms: "آدرس ساب دومین LMS",
        customer_subdomain_portal: "آدرس ساب دومین Portal Frontend",
        customer_subdomain_backendportal: "آدرس ساب دومین Portal Backend",

        /* Backup */
        customer_backup_enabled: "فعال‌سازی بکاپ",
        customer_backup_keep: "تعداد نگهداری بکاپ",
        customer_backup_cron_volumes: "زمان‌بندی بکاپ Volume",
        customer_backup_cron_databases: "زمان‌بندی بکاپ Database",

        /* Test */
        customer_test_enabled: "فعال‌سازی تست",
        customer_test_fail_fast: "توقف در خطای اول",
    };

    // لیبل‌های Docker (می‌توانید اینجا اضافه کنید)
    const dockerLabels = {
        image_id: "شناسه ایمیج",
        repository: "مخزن",
        tag: "تگ",
        size: "سایز",
        created: "تاریخ ایجاد",
        actions: "عملیات",

        // Network labels
        network_id: "شناسه شبکه",
        network_name: "نام شبکه",
        driver: "درایور",
        scope: "اسکوپ",
        containers: "کانتینرها",
        internal: "داخلی",
        attachable: "قابل اتصال",
        ipam: "تنظیمات IPAM",
        subnet: "Subnet",
        gateway: "Gateway",

        // Network actions
        create_network: "ایجاد شبکه",
        remove_network: "حذف شبکه",
        prune_networks: "حذف شبکه‌های بدون استفاده",
        view_containers: "مشاهده کانتینرها",

        // Volume labels
        volume_id: "شناسه ولوم",
        volume_name: "نام ولوم",
        mountpoint: "مسیر Mount",
        driver: "درایور",
        scope: "اسکوپ",
        labels: "برچسب‌ها",
        options: "تنظیمات",
        created_at: "تاریخ ایجاد",

        // Volume actions
        create_volume: "ایجاد ولوم",
        remove_volume: "حذف ولوم",
        prune_volumes: "حذف ولوم‌های بدون استفاده",
        inspect_volume: "مشاهده محتوا",
        backup_volume: "بکاپ ولوم",

        // Driver types
        local: "Local",
        nfs: "NFS",
        cifs: "CIFS/SMB",
        tmpfs: "Tmpfs",

        // Container labels
        container_id: "شناسه کانتینر",
        container_name: "نام کانتینر",
        container_image: "تصویر",
        container_status: "وضعیت",
        container_ports: "پورت‌ها",
        container_networks: "شبکه‌ها",
        container_command: "دستور",
        container_created: "تاریخ ایجاد",
        container_health: "وضعیت سلامت",

        // Container statuses
        running: "در حال اجرا",
        exited: "متوقف شده",
        stopped: "متوقف شده",
        paused: "مکث شده",
        restarting: "در حال راه‌اندازی مجدد",
        dead: "مرده",

        // Container actions
        start_container: "شروع کانتینر",
        stop_container: "توقف کانتینر",
        restart_container: "راه‌اندازی مجدد کانتینر",
        pause_container: "مکث کانتینر",
        unpause_container: "ادامه کانتینر",
        remove_container: "حذف کانتینر",
        prune_containers: "حذف کانتینرهای متوقف شده",
        view_logs: "مشاهده لاگ‌ها",
        view_stats: "مشاهده آمار",
        exec_command: "اجرای دستور",

        // Container stats
        cpu_usage: "مصرف CPU",
        memory_usage: "مصرف حافظه",
        network_io: "ورودی/خروجی شبکه",
        disk_io: "ورودی/خروجی دیسک",

        // Batch operations
        batch_start: "شروع گروهی",
        batch_stop: "توقف گروهی",
        batch_restart: "راه‌اندازی مجدد گروهی",
        batch_remove: "حذف گروهی",
    };

    // ============================================================================
    // Public API
    // ============================================================================

    /**
     * دریافت لیبل فارسی برای یک کلید
     */
    function getLabel(key, defaultValue = '') {
        // اول در لیبل‌های Ansible جستجو کن
        if (labelsFa[key] !== undefined) {
            return labelsFa[key];
        }

        // سپس در لیبل‌های Docker جستجو کن
        if (dockerLabels[key] !== undefined) {
            return dockerLabels[key];
        }

        // اگر پیدا نشد، کلید را با فرمت مناسب برگردان
        return defaultValue || formatKey(key);
    }

    /**
     * فرمت کردن کلید به عنوان fallback
     */
    function formatKey(key) {
        // تبدیل snake_case به عبارت خوانا
        return key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace(/\bcustomer\b/gi, '')
            .replace(/\bgit\b/gi, 'Git')
            .replace(/\bmysql\b/gi, 'MySQL')
            .replace(/\bcron\b/gi, 'Cron')
            .replace(/\bupdate\b/gi, 'Update')
            .replace(/\bbranches\b/gi, 'Branches')
            .replace(/\btags\b/gi, 'Tags')
            .replace(/\benabled\b/gi, 'Enabled')
            .replace(/\bkeep\b/gi, 'Keep')
            .trim();
    }

    /**
     * دریافت تمام لیبل‌های Ansible
     */
    function getAllAnsibleLabels() {
        return { ...labelsFa };
    }

    /**
     * اضافه کردن لیبل جدید
     */
    function addLabel(key, value) {
        labelsFa[key] = value;
    }

    /**
     * اضافه کردن چندین لیبل
     */
    function addLabels(newLabels) {
        Object.assign(labelsFa, newLabels);
    }

    return {
        getLabel,
        getAllAnsibleLabels,
        addLabel,
        addLabels,
        formatKey
    };
})();

// قرار دادن در global scope برای backward compatibility
window.LabelsModule = LabelsModule;
window.labelsFa = LabelsModule.getAllAnsibleLabels();