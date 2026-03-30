/**
 * ALL_CAREER — Logo injector (plain image, no animation)
 */
(function () {
    function buildLogo() {
        // Remove any existing static logo
        document.querySelectorAll('a[href="index.html"]').forEach(el => {
            if (el.querySelector('img[src="String_Theory.png"]')) el.remove();
        });
        const existing = document.getElementById('logo3d-wrapper');
        if (existing) existing.remove();

        const a = document.createElement('a');
        a.href = 'index.html';
        a.id   = 'logo3d-wrapper';
        Object.assign(a.style, {
            position: 'fixed', top: '14px', left: '20px', zIndex: '9999',
            display: 'flex', alignItems: 'center', gap: '12px',
            textDecoration: 'none', cursor: 'pointer',
        });
        a.innerHTML = `
            <img src="String_Theory.png" alt="Logo"
                style="width:38px;height:38px;border-radius:10px;
                       box-shadow:0 4px 15px rgba(0,0,0,0.3);display:block;">
            <span style="font-family:'Outfit',sans-serif;font-weight:800;
                         font-size:1.4rem;color:#ffffff;letter-spacing:1px;
                         text-shadow:0 2px 10px rgba(0,0,0,0.5);">ALL_CAREER</span>
        `;
        document.body.prepend(a);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', buildLogo);
    } else {
        buildLogo();
    }
})();
