/**
 * ALL_CAREER interactive wireframe logo.
 * The PNG remains visible until WebGL and the Three.js modules are ready.
 */
(() => {
    const DEBUG = new URLSearchParams(window.location.search).has('logoDebug');
    const SIZE = DEBUG ? 400 : 88;
    const THREE_CDN = 'https://esm.sh/three@0.161.0';
    const EXAMPLES_CDN = 'https://esm.sh/three@0.161.0/examples/jsm';

    function createLogoShell() {
        document.getElementById('logo3d-wrapper')?.remove();
        const legacyLogo = Array.from(document.querySelectorAll('a[href="index.html"]'))
            .find(link => link.querySelector('img[src="String_Theory.png"]'));
        const wrapper = document.createElement('a');
        wrapper.id = 'logo3d-wrapper';
        wrapper.href = 'index.html';
        wrapper.setAttribute('aria-label', 'ALL_CAREER home');
        Object.assign(wrapper.style, {
            position: 'fixed', top: '14px', left: '20px', zIndex: '9999',
            display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none',
            cursor: 'pointer', padding: '5px 10px 5px 5px', borderRadius: '14px',
            background: 'rgba(7, 11, 25, 0.78)', border: '1px solid rgba(216,240,255,0.16)',
            boxShadow: '0 12px 32px rgba(0,0,0,0.28)', backdropFilter: 'blur(12px)'
        });
        wrapper.innerHTML = `
            <span class="logo3d-visual" aria-hidden="true" style="display:grid;place-items:center;width:${SIZE}px;height:${SIZE}px;overflow:hidden;flex:0 0 ${SIZE}px;background:#000000;border-radius:18px;box-shadow:0 0 22px rgba(216,240,255,0.14) inset,0 0 18px rgba(141,232,255,0.16);">
                <img class="logo3d-fallback" src="String_Theory.png" alt="" style="width:48px;height:48px;border-radius:12px;display:block;">
            </span>
            <span style="font-family:'Outfit',sans-serif;font-weight:800;font-size:0.95rem;color:#fff;letter-spacing:0.02em;white-space:nowrap;">ALL_CAREER</span>
        `;
        if (legacyLogo) legacyLogo.replaceWith(wrapper);
        else document.body.prepend(wrapper);
        return wrapper;
    }

    function hasWebGL() {
        try {
            const testCanvas = document.createElement('canvas');
            return Boolean(testCanvas.getContext('webgl2') || testCanvas.getContext('webgl'));
        } catch (_) {
            return false;
        }
    }

    function buildLobedGeometry(THREE, ImprovedNoise) {
        const geometry = new THREE.IcosahedronGeometry(1, DEBUG ? 4 : 3);
        const positions = geometry.attributes.position;
        const vertex = new THREE.Vector3();
        const normal = new THREE.Vector3();
        const lobeDirections = [
            new THREE.Vector3(0.92, 0.18, 0.34), new THREE.Vector3(-0.78, 0.50, 0.38),
            new THREE.Vector3(0.12, 0.95, -0.28), new THREE.Vector3(-0.38, -0.86, 0.36),
            new THREE.Vector3(0.56, -0.24, -0.79), new THREE.Vector3(-0.86, -0.10, -0.50)
        ].map(direction => direction.normalize());
        const perlin = new ImprovedNoise();

        for (let index = 0; index < positions.count; index += 1) {
            vertex.fromBufferAttribute(positions, index);
            normal.copy(vertex).normalize();
            const noiseA = perlin.noise(normal.x * 1.65 + 7.1, normal.y * 1.65 + 2.8, normal.z * 1.65 - 4.6);
            const noiseB = perlin.noise(normal.x * 3.8 - 1.4, normal.y * 3.8 + 6.2, normal.z * 3.8 + 0.7);
            let pull = 0;
            lobeDirections.forEach(direction => {
                const facing = Math.max(0, normal.dot(direction));
                pull += Math.pow(facing, 7) * 0.88;
            });
            const radius = 0.92 + noiseA * 0.17 + noiseB * 0.045 + pull;
            vertex.copy(normal).multiplyScalar(radius);
            positions.setXYZ(index, vertex.x, vertex.y, vertex.z);
        }

        positions.needsUpdate = true;
        geometry.computeVertexNormals();
        return { geometry, lobeDirections };
    }

    function makeRidgeTube(THREE, direction, index, material) {
        const up = Math.abs(direction.y) > 0.75 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
        const side = new THREE.Vector3().crossVectors(direction, up).normalize();
        const twist = new THREE.Vector3().crossVectors(direction, side).normalize();
        const points = [];

        for (let step = 0; step <= 18; step += 1) {
            const t = step / 18;
            const arc = Math.sin(t * Math.PI);
            const sweep = (t - 0.5) * (0.95 + index * 0.055);
            const radius = 0.58 + arc * 1.04;
            const point = new THREE.Vector3()
                .copy(direction).multiplyScalar(radius)
                .addScaledVector(side, Math.sin(sweep) * (0.42 + arc * 0.18))
                .addScaledVector(twist, Math.cos(sweep * 1.25) * 0.22 * arc);
            points.push(point);
        }

        const curve = new THREE.CatmullRomCurve3(points);
        const tubeGeometry = new THREE.TubeGeometry(curve, 40, 0.012, 6, false);
        const tube = new THREE.Mesh(tubeGeometry, material);
        tube.renderOrder = 3;
        return tube;
    }

    async function mountWireframeLogo(wrapper) {
        if (!hasWebGL()) return;
        const visual = wrapper.querySelector('.logo3d-visual');
        const fallback = wrapper.querySelector('.logo3d-fallback');
        let renderer;
        let frameId = 0;
        let running = false;
        let disposed = false;
        let pointerX = 0;
        let pointerY = 0;
        let smoothX = 0;
        let smoothY = 0;
        const disposableGeometries = [];
        const disposableMaterials = [];

        try {
            const [THREE, composerModule, renderPassModule, bloomModule, noiseModule, line2Module, lineMaterialModule, wireframe2Module] = await Promise.all([
                import(THREE_CDN),
                import(`${EXAMPLES_CDN}/postprocessing/EffectComposer.js`),
                import(`${EXAMPLES_CDN}/postprocessing/RenderPass.js`),
                import(`${EXAMPLES_CDN}/postprocessing/UnrealBloomPass.js`),
                import(`${EXAMPLES_CDN}/math/ImprovedNoise.js`),
                import(`${EXAMPLES_CDN}/lines/Line2.js?deps=three@0.161.0`),
                import(`${EXAMPLES_CDN}/lines/LineMaterial.js?deps=three@0.161.0`),
                import(`${EXAMPLES_CDN}/lines/WireframeGeometry2.js?deps=three@0.161.0`)
            ]);
            if (disposed) return;

            const { EffectComposer } = composerModule;
            const { RenderPass } = renderPassModule;
            const { UnrealBloomPass } = bloomModule;
            const { ImprovedNoise } = noiseModule;
            const { Line2 } = line2Module;
            const { LineMaterial } = lineMaterialModule;
            const { WireframeGeometry2 } = wireframe2Module;
            const canvas = document.createElement('canvas');
            canvas.width = SIZE;
            canvas.height = SIZE;
            canvas.style.cssText = `display:block;width:${SIZE}px;height:${SIZE}px;pointer-events:none;background:#000000;`;
            renderer = new THREE.WebGLRenderer({ canvas, alpha: false, antialias: true, powerPreference: 'high-performance' });
            const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
            renderer.setPixelRatio(pixelRatio);
            renderer.setSize(SIZE, SIZE, false);
            renderer.setClearColor(0x000000, 1);
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.75;

            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x000000);
            const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 20);
            camera.position.set(0, 0, 5.0);
            const group = new THREE.Group();
            group.scale.setScalar(0.48);
            scene.add(group);

            const { geometry, lobeDirections } = buildLobedGeometry(THREE, ImprovedNoise);
            disposableGeometries.push(geometry);

            const fillMaterial = new THREE.MeshBasicMaterial({
                color: 0x76dfff, transparent: true, opacity: 0.04, side: THREE.DoubleSide,
                depthWrite: false, blending: THREE.AdditiveBlending
            });
            const wireGeometry = new WireframeGeometry2(geometry);
            disposableGeometries.push(wireGeometry);
            const wireMaterial = new LineMaterial({
                color: 0xf2fbff, transparent: true, opacity: 0.98,
                linewidth: DEBUG ? 2.1 : 2.35,
                worldUnits: false,
                dashed: false
            });
            wireMaterial.resolution.set(SIZE, SIZE);
            const haloMaterial = new LineMaterial({
                color: 0x8fe8ff, transparent: true, opacity: DEBUG ? 0 : 0.14,
                linewidth: DEBUG ? 0.01 : 3.6,
                worldUnits: false,
                dashed: false
            });
            haloMaterial.resolution.set(SIZE, SIZE);
            disposableMaterials.push(fillMaterial, wireMaterial, haloMaterial);

            const fill = new THREE.Mesh(geometry, fillMaterial);
            const wire = new Line2(wireGeometry, wireMaterial);
            const halo = new Line2(wireGeometry, haloMaterial);
            wire.computeLineDistances();
            halo.computeLineDistances();
            halo.scale.setScalar(1.012);
            wire.renderOrder = 3;
            halo.renderOrder = 2;
            group.add(fill, halo, wire);
            group.rotation.set(0.18, -0.58, 0.24);

            const composer = new EffectComposer(renderer);
            composer.setPixelRatio(pixelRatio);
            composer.setSize(SIZE, SIZE);
            composer.addPass(new RenderPass(scene, camera));
            if (!DEBUG) {
                const bloom = new UnrealBloomPass(new THREE.Vector2(SIZE, SIZE), 0.5, 0.4, 0.35);
                bloom.threshold = 0.35;
                bloom.strength = 0.5;
                bloom.radius = 0.4;
                composer.addPass(bloom);
            }
            visual.prepend(canvas);
            fallback.style.display = 'none';
            const clock = new THREE.Clock();
            const onPointerMove = event => {
                const bounds = canvas.getBoundingClientRect();
                const x = (event.clientX - (bounds.left + bounds.width / 2)) / Math.max(bounds.width, 1);
                const y = (event.clientY - (bounds.top + bounds.height / 2)) / Math.max(bounds.height, 1);
                pointerX = THREE.MathUtils.clamp(x, -1, 1) * 0.20;
                pointerY = THREE.MathUtils.clamp(y, -1, 1) * 0.17;
            };
            const render = () => {
                if (!running || disposed) return;
                frameId = requestAnimationFrame(render);
                const elapsed = clock.getElapsedTime();
                smoothX += (pointerX - smoothX) * 0.06;
                smoothY += (pointerY - smoothY) * 0.06;
                group.rotation.y = -0.58 + elapsed * (Math.PI * 2 / 36);
                group.rotation.x = 0.18 + Math.sin(elapsed * 0.83) * 0.07 - smoothY;
                group.rotation.z = 0.24 + Math.sin(elapsed * 0.61 + 1.4) * 0.065 + smoothX;
                composer.render();
            };
            const setVisibility = () => {
                running = !document.hidden;
                if (running) {
                    clock.start();
                    cancelAnimationFrame(frameId);
                    render();
                } else {
                    cancelAnimationFrame(frameId);
                }
            };
            const cleanup = () => {
                if (disposed) return;
                disposed = true;
                running = false;
                cancelAnimationFrame(frameId);
                window.removeEventListener('mousemove', onPointerMove);
                document.removeEventListener('visibilitychange', setVisibility);
                disposableGeometries.forEach(item => item.dispose());
                disposableMaterials.forEach(item => item.dispose());
                composer.dispose();
                renderer.dispose();
                canvas.remove();
                fallback.style.display = 'block';
            };
            window.addEventListener('mousemove', onPointerMove, { passive: true });
            document.addEventListener('visibilitychange', setVisibility);
            window.addEventListener('pagehide', cleanup, { once: true });
            setVisibility();
        } catch (error) {
            console.warn('ALL_CAREER 3D logo unavailable; using static logo.', error);
            renderer?.dispose();
            fallback.style.display = 'block';
        }
    }

    function buildLogo() {
        const wrapper = createLogoShell();
        mountWireframeLogo(wrapper);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', buildLogo, { once: true });
    else buildLogo();
})();