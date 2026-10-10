/**
 * SGP Makala — navigation, accessibility and form previews.
 */
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const backdrop = document.getElementById('sidebarBackdrop');
    const body = document.body;
    const sidebarStateKey = 'sgp_sidebar_expanded';
    const isMobile = () => window.innerWidth < 992;
    let lastMobile = isMobile();

    function savedExpanded() {
        try { return localStorage.getItem(sidebarStateKey) !== 'false'; }
        catch (error) { return true; }
    }

    function setSidebarExpanded(expanded, persist = true) {
        if (!sidebar) return;
        const mobile = isMobile();
        sidebar.classList.toggle('show', mobile && expanded);
        sidebar.classList.toggle('collapsed', !expanded);
        sidebar.inert = !expanded;
        body.classList.toggle('sidebar-collapsed', !mobile && !expanded);
        body.classList.toggle('sidebar-mobile-open', mobile && expanded);
        if (backdrop) backdrop.hidden = !(mobile && expanded);
        if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', String(expanded));
        if (!mobile && persist) {
            try { localStorage.setItem(sidebarStateKey, String(expanded)); }
            catch (error) { /* Navigation also works when storage is disabled. */ }
        }
    }

    if (sidebar && sidebarToggle) {
        setSidebarExpanded(!isMobile() && savedExpanded(), false);
        sidebarToggle.addEventListener('click', function () {
            const expanded = isMobile()
                ? !sidebar.classList.contains('show')
                : sidebar.classList.contains('collapsed');
            setSidebarExpanded(expanded);
            if (expanded && isMobile()) sidebar.querySelector('a')?.focus();
        });
        backdrop?.addEventListener('click', () => setSidebarExpanded(false, false));
        document.addEventListener('keydown', function (event) {
            if (!isMobile() || !sidebar.classList.contains('show')) return;
            if (event.key === 'Escape') {
                setSidebarExpanded(false, false);
                sidebarToggle.focus();
            }
            if (event.key === 'Tab') {
                const focusable = Array.from(sidebar.querySelectorAll('a[href], button, [tabindex="0"]'))
                    .filter(element => element.getClientRects().length > 0);
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault(); last?.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault(); first?.focus();
                }
            }
        });
        window.addEventListener('resize', function () {
            const mobile = isMobile();
            if (mobile !== lastMobile) {
                setSidebarExpanded(!mobile && savedExpanded(), false);
                lastMobile = mobile;
            }
        });
    }

    if (window.bootstrap) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
            new bootstrap.Tooltip(element, { trigger: 'hover focus' });
        });
    }

    document.querySelectorAll('[data-print]').forEach(function (button) {
        button.addEventListener('click', () => window.print());
    });

    document.querySelectorAll('a[href="#documentUpload"]').forEach(function (link) {
        link.addEventListener('click', function () {
            const panel = document.getElementById('documentUpload');
            if (panel) panel.open = true;
        });
    });

    document.querySelectorAll('input[type="file"][name="photo"]').forEach(function (input) {
        let previewUrl;
        input.addEventListener('change', function () {
            let preview = input.parentElement.querySelector('.photo-preview');
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            const file = input.files[0];
            if (!file || !file.type.startsWith('image/')) {
                if (preview) preview.remove();
                return;
            }
            if (!preview) {
                preview = document.createElement('img');
                preview.className = 'photo-preview';
                preview.alt = 'Aperçu du portrait sélectionné';
                input.insertAdjacentElement('afterend', preview);
            }
            previewUrl = URL.createObjectURL(file);
            preview.src = previewUrl;
        });
    });

    // Labels in existing forms are linked to their controls without changing field names.
    document.querySelectorAll('.form-label:not([for])').forEach(function (label, index) {
        const control = label.parentElement.querySelector('input, select, textarea');
        if (!control) return;
        if (!control.id) control.id = 'sgpField' + index;
        label.htmlFor = control.id;
    });

    document.querySelectorAll('.table-responsive').forEach(function (wrapper) {
        let hint;
        function updateScrollHint() {
            const overflow = wrapper.scrollWidth > wrapper.clientWidth + 1;
            wrapper.tabIndex = overflow ? 0 : -1;
            if (overflow) wrapper.setAttribute('aria-label', 'Tableau défilant horizontalement');
            else wrapper.removeAttribute('aria-label');
            if (overflow && !hint) {
                hint = document.createElement('div');
                hint.className = 'table-scroll-hint no-print';
                hint.textContent = 'Faites défiler le tableau horizontalement pour afficher toutes les colonnes.';
                wrapper.insertAdjacentElement('beforebegin', hint);
            }
            if (hint) hint.hidden = !overflow;
        }
        updateScrollHint();
        if (window.ResizeObserver) new ResizeObserver(updateScrollHint).observe(wrapper);
    });
});
