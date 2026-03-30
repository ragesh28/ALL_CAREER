/**
 * ALL_CAREER — Quantum String Theory 3D Logo Auto-Injector
 * Finds any generic logo <a> block and replaces it with the animated 3D version.
 */
(function () {
    // Inject the CSS link if not already present
    if (!document.querySelector('link[href="logo3d.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'logo3d.css';
        document.head.appendChild(link);
    }

    function buildLogo() {
        // Remove any existing plain logo anchor at top-left
        const existing = document.querySelector('a[href="index.html"][style*="position: absolute"]');
        if (existing) existing.remove();

        const a = document.createElement('a');
        a.href = 'index.html';
        a.className = 'logo-3d-wrapper';
        a.innerHTML = `
            <div class="logo-3d-stage">
                <div class="logo-3d-spin">
                    <img src="String_Theory.png" alt="ALL_CAREER Logo">
                </div>
                <div class="logo-3d-ring"></div>
                <div class="logo-3d-ring2"></div>
                <div class="logo-3d-dot"></div>
                <div class="logo-3d-dot2"></div>
            </div>
            <span class="logo-3d-text">ALL_CAREER</span>
        `;
        document.body.prepend(a);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', buildLogo);
    } else {
        buildLogo();
    }
})();
