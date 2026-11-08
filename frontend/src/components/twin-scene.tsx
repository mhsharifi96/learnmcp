"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/* "Digital twin" hero scene: a learner model drawn as a network of knowledge nodes.
   Turquoise = mastered, saffron = weak spot, white = new. A scan band sweeps the model
   (the twin being updated), packets travel an orbit (data syncing in).
   Perf: capped DPR, alpha canvas over CSS background, paused offscreen / in hidden tabs,
   one static frame under prefers-reduced-motion, full dispose on unmount. */

const TURQ = new THREE.Color("#3fd1c7");
const SAFF = new THREE.Color("#f2b45a");
const PALE = new THREE.Color("#dbe8ff");

const vertex = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute vec3 aColor;
  uniform float uTime;
  uniform float uScan;
  uniform float uPixelRatio;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float scan = smoothstep(0.32, 0.0, abs(position.y - uScan));
    float pulse = 0.72 + 0.28 * sin(uTime * 1.7 + aPhase);
    gl_PointSize = aSize * uPixelRatio * (pulse + scan * 1.4) * (7.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
    vColor = mix(aColor, vec3(1.0), scan * 0.55);
    vAlpha = 0.5 + 0.5 * pulse;
  }
`;

const fragment = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(vColor, a * a * vAlpha);
  }
`;

function fibonacciSphere(n: number, r: number) {
  const pts: THREE.Vector3[] = [];
  const g = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const rad = Math.sqrt(1 - y * y);
    const th = g * i;
    // small jitter so it reads organic, not a perfect lattice
    const j = 1 + (Math.random() - 0.5) * 0.06;
    pts.push(new THREE.Vector3(Math.cos(th) * rad * r * j, y * r * j, Math.sin(th) * rad * r * j));
  }
  return pts;
}

export default function TwinScene({ rtl }: { rtl: boolean }) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const small = window.matchMedia("(max-width: 767px)").matches;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      return; // no WebGL: the CSS gradient behind stays as the fallback
    }
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    renderer.domElement.style.display = "block";

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0, 7.2);

    const rig = new THREE.Group(); // parallax + side offset
    const twin = new THREE.Group(); // slow spin
    rig.add(twin);
    scene.add(rig);

    // ---- knowledge nodes
    const N = small ? 280 : 460;
    const R = 1.75;
    const pts = fibonacciSphere(N, R);
    const pos = new Float32Array(N * 3);
    const col = new Float32Array(N * 3);
    const size = new Float32Array(N);
    const phase = new Float32Array(N);
    pts.forEach((p, i) => {
      pos.set([p.x, p.y, p.z], i * 3);
      const r = Math.random();
      const c = r < 0.14 ? SAFF : r < 0.22 ? PALE : TURQ;
      col.set([c.r, c.g, c.b], i * 3);
      size[i] = c === SAFF ? 5.5 + Math.random() * 3 : 3 + Math.random() * 2.5;
      phase[i] = Math.random() * Math.PI * 2;
    });
    const nodeGeo = new THREE.BufferGeometry();
    nodeGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    nodeGeo.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
    nodeGeo.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
    nodeGeo.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
    const uniforms = { uTime: { value: 0 }, uScan: { value: 0 }, uPixelRatio: { value: dpr } };
    const nodeMat = new THREE.ShaderMaterial({
      vertexShader: vertex,
      fragmentShader: fragment,
      uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    twin.add(new THREE.Points(nodeGeo, nodeMat));

    // ---- synapses: each node to its 3 nearest neighbours
    const seg: number[] = [];
    for (let i = 0; i < N; i++) {
      const near: [number, number][] = [];
      for (let k = 0; k < N; k++) {
        if (k === i) continue;
        const d = pts[i].distanceToSquared(pts[k]);
        if (near.length < 3) near.push([d, k]);
        else {
          let w = 0;
          for (let m = 1; m < 3; m++) if (near[m][0] > near[w][0]) w = m;
          if (d < near[w][0]) near[w] = [d, k];
        }
      }
      for (const [, k] of near) if (k > i) seg.push(pts[i].x, pts[i].y, pts[i].z, pts[k].x, pts[k].y, pts[k].z);
    }
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(seg, 3));
    const lineMat = new THREE.LineBasicMaterial({ color: TURQ, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false });
    twin.add(new THREE.LineSegments(lineGeo, lineMat));

    // ---- inner core: wireframe icosahedron (the model inside the mirror)
    const coreGeo = new THREE.IcosahedronGeometry(0.85, 1);
    const coreMat = new THREE.MeshBasicMaterial({ color: "#6b8fd6", wireframe: true, transparent: true, opacity: 0.28, blending: THREE.AdditiveBlending, depthWrite: false });
    const core = new THREE.Mesh(coreGeo, coreMat);
    twin.add(core);

    // ---- orbit rings + data packets
    const ringMat = new THREE.LineBasicMaterial({ color: "#8fb3ff", transparent: true, opacity: 0.22, depthWrite: false });
    const rings: { line: THREE.LineLoop; curve: THREE.EllipseCurve }[] = [];
    const ringGeos: THREE.BufferGeometry[] = [];
    [
      { r: 2.45, tiltX: 1.2, tiltZ: 0.35 },
      { r: 2.8, tiltX: 1.45, tiltZ: -0.55 },
    ].forEach(({ r, tiltX, tiltZ }) => {
      const curve = new THREE.EllipseCurve(0, 0, r, r, 0, Math.PI * 2);
      const g = new THREE.BufferGeometry().setFromPoints(curve.getPoints(160));
      ringGeos.push(g);
      const line = new THREE.LineLoop(g, ringMat);
      line.rotation.set(tiltX, 0, tiltZ);
      rig.add(line);
      rings.push({ line, curve });
    });
    const P = 6;
    const pktPos = new Float32Array(P * 3);
    const pktGeo = new THREE.BufferGeometry();
    pktGeo.setAttribute("position", new THREE.BufferAttribute(pktPos, 3));
    const pktMat = new THREE.PointsMaterial({ color: "#ffd38a", size: 0.12, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false });
    const packets = new THREE.Points(pktGeo, pktMat);
    rig.add(packets);
    const tmp = new THREE.Vector3();

    // ---- star dust
    const S = small ? 260 : 520;
    const starPos = new Float32Array(S * 3);
    for (let i = 0; i < S; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(5 + Math.random() * 9);
      starPos.set([v.x, v.y, v.z - 4], i * 3);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: "#9fb6d9", size: 0.03, transparent: true, opacity: 0.55, depthWrite: false });
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // ---- layout: model sits on the "end" side on wide screens
    const resize = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      const wide = w >= 768;
      rig.position.x = wide ? (rtl ? -1 : 1) * Math.min(2.6, camera.aspect * 1.25) : 0;
      rig.position.y = 0;
      rig.scale.setScalar(wide ? 1 : 0.78);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    // ---- pointer parallax (desktop)
    const target = { x: 0, y: 0 };
    const onMove = (e: PointerEvent) => {
      target.x = (e.clientX / window.innerWidth - 0.5) * 0.5;
      target.y = (e.clientY / window.innerHeight - 0.5) * 0.3;
    };
    if (!reduced) window.addEventListener("pointermove", onMove, { passive: true });

    const clock = new THREE.Clock();
    const draw = (t: number) => {
      uniforms.uTime.value = t;
      uniforms.uScan.value = Math.sin(t * 0.55) * (R + 0.2);
      twin.rotation.y = t * 0.12;
      core.rotation.x = t * 0.18;
      core.rotation.z = t * 0.09;
      rig.rotation.y += (target.x - rig.rotation.y) * 0.04;
      rig.rotation.x += (target.y - rig.rotation.x) * 0.04;
      stars.rotation.y = t * 0.01;
      for (let i = 0; i < P; i++) {
        const ring = rings[i % rings.length];
        const u = (t * (0.05 + (i % 3) * 0.015) + i / P) % 1;
        const p2 = ring.curve.getPoint(u);
        tmp.set(p2.x, p2.y, 0).applyEuler(ring.line.rotation);
        pktPos.set([tmp.x, tmp.y, tmp.z], i * 3);
      }
      pktGeo.attributes.position.needsUpdate = true;
      renderer.render(scene, camera);
    };

    let raf = 0;
    let visible = true;
    let elapsed = 0; // accumulated, so pausing never makes the scene jump
    const loop = () => {
      raf = requestAnimationFrame(loop);
      elapsed += Math.min(clock.getDelta(), 0.05);
      draw(elapsed);
    };
    const start = () => {
      if (!raf && visible && !document.hidden) {
        clock.getDelta();
        loop();
      }
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };

    let io: IntersectionObserver | undefined;
    const onVis = () => (document.hidden ? stop() : start());
    if (reduced) {
      draw(4.2); // one calm static frame
    } else {
      io = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        if (visible) start();
        else stop();
      });
      io.observe(el);
      document.addEventListener("visibilitychange", onVis);
      start();
    }
    requestAnimationFrame(() => el.classList.add("is-ready"));

    return () => {
      stop();
      io?.disconnect();
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("visibilitychange", onVis);
      [nodeGeo, lineGeo, coreGeo, pktGeo, starGeo, ...ringGeos].forEach((g) => g.dispose());
      [nodeMat, lineMat, coreMat, ringMat, pktMat, starMat].forEach((m) => m.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [rtl]);

  return <div ref={host} aria-hidden="true" className="twin-canvas absolute inset-0" />;
}
