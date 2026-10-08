/**
 * SGP Makala — interactions globales
 */
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const body = document.body;
    const sidebarStateKey = 'sgp_sidebar_expanded';
    const isMobile = () => window.innerWidth < 992;

    function setSidebarExpanded(expanded, persist = true) {
        if (!sidebar) return;
        if (isMobile()) {
            sidebar.classList.toggle('show', expanded);
            sidebar.classList.toggle('collapsed', !expanded);
            body.classList.remove('sidebar-collapsed');
        } else {
            sidebar.classList.toggle('collapsed', !expanded);
            sidebar.classList.remove('show');
            body.classList.toggle('sidebar-collapsed', !expanded);
            if (persist) localStorage.setItem(sidebarStateKey, String(expanded));
        }
        if (sidebarToggle) {
            sidebarToggle.setAttribute('aria-expanded', String(expanded));
        }
    }

    if (sidebar && sidebarToggle) {
        if (isMobile()) {
            setSidebarExpanded(false, false);
        } else {
            setSidebarExpanded(localStorage.getItem(sidebarStateKey) !== 'false', false);
        }
        sidebarToggle.addEventListener('click', function (e) {
            e.preventDefault();
            const expanded = isMobile()
                ? !sidebar.classList.contains('show')
                : sidebar.classList.contains('collapsed');
            setSidebarExpanded(expanded);
        });
        document.addEventListener('click', function (e) {
            if (isMobile() && sidebar.classList.contains('show')) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    setSidebarExpanded(false, false);
                }
            }
        });
        window.addEventListener('resize', function () {
            if (isMobile()) setSidebarExpanded(false, false);
            else setSidebarExpanded(localStorage.getItem(sidebarStateKey) !== 'false', false);
        });
    }

    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover' });
    });

    document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            try { bootstrap.Alert.getOrCreateInstance(alert).close(); } catch (e) {}
        }, 6000);
    });

    document.querySelectorAll('.card-kpi').forEach(function (card, index) {
        card.style.animationDelay = (index * 0.07) + 's';
        card.classList.add('fade-in-up');
    });
});
