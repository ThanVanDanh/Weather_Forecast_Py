import * as THREE from 'https://cdn.skypack.dev/three@0.136.0';

function createRenderer(container) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.innerHTML = '';
  container.appendChild(renderer.domElement);
  return renderer;
}

function sizeFor(container) {
  const width = container.clientWidth || window.innerWidth;
  const height = container.clientHeight || window.innerHeight;
  return { width, height };
}

function createCloudTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');

  // Vẽ nhiều hình tròn chồng lên nhau tạo dạng mây cumulus (bông)
  function drawPuff(x, y, radius, alpha) {
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `rgba(255,255,255,${alpha})`);
    gradient.addColorStop(0.5, `rgba(255,255,255,${alpha * 0.7})`);
    gradient.addColorStop(0.8, `rgba(245,245,245,${alpha * 0.3})`);
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  // Tạo hình dạng mây bông: nhiều cục tròn chồng lên nhau
  // Hàng dưới (đế mây)
  drawPuff(100, 180, 70, 0.9);
  drawPuff(180, 185, 80, 0.95);
  drawPuff(260, 180, 75, 0.9);
  drawPuff(340, 185, 70, 0.85);
  drawPuff(420, 180, 65, 0.8);

  // Hàng giữa (thân mây, lớn hơn)
  drawPuff(130, 130, 85, 0.95);
  drawPuff(220, 120, 95, 1.0);
  drawPuff(320, 125, 90, 0.95);
  drawPuff(400, 135, 80, 0.9);

  // Hàng trên (đỉnh mây, bông nhô lên)
  drawPuff(180, 70, 70, 0.9);
  drawPuff(260, 55, 80, 0.95);
  drawPuff(340, 65, 75, 0.9);

  // Đỉnh cao nhất
  drawPuff(270, 30, 50, 0.85);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function initFog(container) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 1, 1000);
  camera.position.z = 6;
  camera.position.y = 1.5;

  const renderer = createRenderer(container);

  const cloudTexture = createCloudTexture();

  const sprites = [];
  const cloudCount = 12;
  for (let i = 0; i < cloudCount; i++) {
    const material = new THREE.SpriteMaterial({
      map: cloudTexture,
      transparent: true,
      opacity: 0.80 + Math.random() * 0.20,
      depthWrite: false,
      depthTest: false,
      color: 0xffffff
    });

    const sprite = new THREE.Sprite(material);

    // Phân bố mây đều, tách xa nhau (hạ xuống để không bị cắt đỉnh)
    const yTop = 2.0;
    const yBottom = 0.2;
    
    // Chia đều vị trí ngang để mây không chồng lên nhau
    const spreadX = 30;
    const startX = -spreadX / 2;
    const segmentWidth = spreadX / cloudCount;
    const baseX = startX + i * segmentWidth + (Math.random() - 0.5) * segmentWidth * 0.5;
    
    sprite.position.set(
      baseX,
      yBottom + Math.random() * (yTop - yBottom),
      -1 - Math.random() * 3
    );

    const scaleX = 2.0 + Math.random() * 2.0;
    const scaleY = scaleX * 0.5;
    sprite.scale.set(scaleX, scaleY, 1);

    scene.add(sprite);
    sprites.push({
      sprite,
      speed: 0.06 + Math.random() * 0.08,
      drift: 0,
      spin: 0
    });
  }

  function resize() {
    const { width, height } = sizeFor(container);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  resize();

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const dt = clock.getDelta();

    for (const item of sprites) {
      const s = item.sprite;
      s.position.x += item.speed * dt;
      s.position.y += item.drift * dt;
      // Không xoay (mây chỉ trôi ngang)

      if (s.position.x > 18) {
        s.position.x = -18;
        const yTop = 2.0;
        const yBottom = 0.2;
        s.position.y = yBottom + Math.random() * (yTop - yBottom);
        s.position.z = -1 - Math.random() * 3;
      }
    }

    renderer.render(scene, camera);
  }

  animate();
  return { resize };
}

const starsContainer = document.getElementById('fx-stars');
const fogContainer = document.getElementById('fx-fog');

if (!fogContainer) {
  throw new Error('Missing container: #fx-fog');
}

const fog = initFog(fogContainer);

window.addEventListener('resize', () => {
  fog.resize();
});
