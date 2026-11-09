"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/* Hero story in 3D: the teacher (warm sphere) builds their Digital Twin (turquoise hologram).
   On load the twin's nodes fly out of the teacher and assemble; a stream of knowledge keeps
   flowing teacher -> twin. Students orbit the twin and practise with it: packets travel
   twin <-> student. Labels are HTML, positioned each frame from projected 3D anchors.
   Perf: capped DPR, alpha canvas over CSS background, paused offscreen / in hidden tabs,
   one static final frame under prefers-reduced-motion, full dispose on unmount. */

const TURQ = new THREE.Color("#3fd1c7");
const SAFF = new THREE.Color("#f2b45a");
const PALE = new THREE.Color("#dbe8ff");
const BLUE = new THREE.Color("#8fb3ff");

const BUILD_SECONDS = 3.6;

const vertex = /* glsl */ `
  attribute vec3 aStart;
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aPhase;
  attribute float aDelay;
  uniform float uTime;
  uniform float uBuild;
  uniform float uSpin;
  uniform float uScan;
  uniform float uScanOn;
  uniform float uPixelRatio;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float c = cos(uSpin), s = sin(uSpin);
    vec3 target = vec3(c * position.x + s * position.z, position.y, -s * position.x + c * position.z);
    float b = clamp(uBuild * 1.7 - aDelay * 0.7, 0.0, 1.0);
    b = b * b * (3.0 - 2.0 * b);
    vec3 p = mix(aStart, target, b);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float scan = uScanOn * smoothstep(0.28, 0.0, abs(position.y - uScan));
    float pulse = 0.72 + 0.28 * sin(uTime * 1.7 + aPhase);
    float travel = 1.0 + (1.0 - b) * b * 4.0; // nodes glow while in flight
    gl_PointSize = aSize * uPixelRatio * (pulse + scan * 1.4) * travel * (7.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
    vColor = mix(aColor, vec3(1.0), scan * 0.55 + (1.0 - b) * 0.4);
    vAlpha = (0.5 + 0.5 * pulse) * (0.25 + 0.75 * b);
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

/* Points on the surface of a human bust (head, neck, shoulders, torso, upper arms), facing +z.
   Height is `h`, centred on the origin. Nearest-neighbour lines between them read as a wireframe person. */
const HEAD_Y = 0.36; // head centre, as a share of the height above the origin
function humanFigure(n: number, h: number) {
  const k = h / 2.6; // the shape is designed 2.6 units tall
  const pts: THREE.Vector3[] = [];
  const rnd = (a: number, b: number) => a + Math.random() * (b - a);
  const head = () => {
    const d = new THREE.Vector3().randomDirection();
    return new THREE.Vector3(d.x * 0.27, d.y * 0.33 + HEAD_Y * 2.6, d.z * 0.29);
  };
  const neck = () => {
    const a = rnd(0, Math.PI * 2);
    return new THREE.Vector3(Math.cos(a) * 0.12, rnd(0.5, 0.66), Math.sin(a) * 0.11);
  };
  const torso = () => {
    // v: 0 at the bottom edge (-1.3) to 1 at the top of the shoulders (0.6)
    const v = Math.random();
    const y = -1.3 + v * 1.9;
    let rx = 0.42 + 0.16 * THREE.MathUtils.smoothstep(v, 0.35, 0.8);
    let rz = 0.26 + 0.04 * Math.sin(v * Math.PI);
    if (v > 0.82) {
      const q = Math.sqrt(Math.max(0, 1 - ((v - 0.82) / 0.18) ** 2));
      rx = 0.13 + (rx - 0.13) * q;
      rz = 0.12 + (rz - 0.12) * q;
    }
    const a = rnd(0, Math.PI * 2);
    return new THREE.Vector3(Math.cos(a) * rx, y, Math.sin(a) * rz);
  };
  const arm = () => {
    const side = Math.random() < 0.5 ? -1 : 1;
    const from = new THREE.Vector3(0.6 * side, 0.4, 0);
    const to = new THREE.Vector3(0.74 * side, -0.75, 0.04);
    const u = Math.random();
    const axis = new THREE.Vector3().subVectors(to, from).normalize();
    const ring = new THREE.Vector3().randomDirection().projectOnPlane(axis).normalize().multiplyScalar(0.13 - u * 0.03);
    return from.lerp(to, u).add(ring);
  };
  // shares roughly by surface area
  const parts: [number, () => THREE.Vector3][] = [[0.24, head], [0.05, neck], [0.53, torso], [0.18, arm]];
  for (let i = 0; i < n; i++) {
    let r = Math.random();
    let f = parts[parts.length - 1][1];
    for (const [w, fn] of parts) {
      if (r < w) {
        f = fn;
        break;
      }
      r -= w;
    }
    const p = f();
    const j = 1 + (Math.random() - 0.5) * 0.04;
    pts.push(p.multiplyScalar(k * j));
  }
  return pts;
}

type Labels = { teacher: string; twin: string; student: string };

export default function TwinScene({ rtl, labels }: { rtl: boolean; labels: Labels }) {
  const holder = useRef<HTMLDivElement>(null);
  const lTeacher = useRef<HTMLSpanElement>(null);
  const lTwin = useRef<HTMLSpanElement>(null);
  const lStudent = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = holder.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const small = window.matchMedia("(max-width: 767px)").matches;
    const sx = rtl ? -1 : 1; // mirror the story for right-to-left reading

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      return; // no WebGL: the CSS gradient behind stays as the fallback
    }
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.display = "block";
    el.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0, 7.2);
    const rig = new THREE.Group();
    scene.add(rig);

    const geos: THREE.BufferGeometry[] = [];
    const mats: THREE.Material[] = [];
    const time = { value: 0 };

    const TEACHER = new THREE.Vector3(-1.95 * sx, 1.05, -0.4);
    const TWIN = new THREE.Vector3(0.55 * sx, -0.15, 0);
    const R_T = 0.62; // teacher figure half-height
    const R_W = 1.3; // twin figure half-height

    // ---- node cloud factory (teacher + twin share one shader)
    const nodeCloud = (pts: THREE.Vector3[], pick: () => THREE.Color, starts: (p: THREE.Vector3) => THREE.Vector3, scanOn: number) => {
      const n = pts.length;
      const pos = new Float32Array(n * 3);
      const start = new Float32Array(n * 3);
      const col = new Float32Array(n * 3);
      const size = new Float32Array(n);
      const phase = new Float32Array(n);
      const delay = new Float32Array(n);
      pts.forEach((p, i) => {
        pos.set([p.x, p.y, p.z], i * 3);
        const s = starts(p);
        start.set([s.x, s.y, s.z], i * 3);
        const c = pick();
        col.set([c.r, c.g, c.b], i * 3);
        size[i] = c === SAFF ? 5 + Math.random() * 3 : 3 + Math.random() * 2.5;
        phase[i] = Math.random() * Math.PI * 2;
        delay[i] = Math.random();
      });
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      g.setAttribute("aStart", new THREE.BufferAttribute(start, 3));
      g.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
      g.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
      g.setAttribute("aPhase", new THREE.BufferAttribute(phase, 1));
      g.setAttribute("aDelay", new THREE.BufferAttribute(delay, 1));
      const u = {
        uTime: time,
        uBuild: { value: 1 },
        uSpin: { value: 0 },
        uScan: { value: 0 },
        uScanOn: { value: scanOn },
        uPixelRatio: { value: dpr },
      };
      const m = new THREE.ShaderMaterial({ vertexShader: vertex, fragmentShader: fragment, uniforms: u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
      geos.push(g);
      mats.push(m);
      return { points: new THREE.Points(g, m), u };
    };

    // ---- teacher
    const teacherGroup = new THREE.Group();
    teacherGroup.position.copy(TEACHER);
    rig.add(teacherGroup);
    const teacherPts = humanFigure(small ? 130 : 180, R_T * 2);
    const teacher = nodeCloud(teacherPts, () => (Math.random() < 0.7 ? SAFF : PALE), (p) => p, 0);
    teacherGroup.add(teacher.points);
    const haloGeo = new THREE.BufferGeometry().setFromPoints(new THREE.EllipseCurve(0, 0, R_T * 0.75, R_T * 0.75, 0, Math.PI * 2).getPoints(96));
    const haloMat = new THREE.LineBasicMaterial({ color: SAFF, transparent: true, opacity: 0.35, depthWrite: false });
    geos.push(haloGeo);
    mats.push(haloMat);
    const halo = new THREE.LineLoop(haloGeo, haloMat);
    halo.rotation.x = 1.35;
    halo.position.y = -R_T * 0.85;
    teacherGroup.add(halo);

    // ---- twin: nodes start inside the teacher and fly over to assemble
    const twinGroup = new THREE.Group();
    twinGroup.position.copy(TWIN);
    rig.add(twinGroup);
    const N = small ? 260 : 380;
    const twinPts = humanFigure(N, R_W * 2);
    const fromTeacher = new THREE.Vector3().subVectors(TEACHER, TWIN);
    const twin = nodeCloud(
      twinPts,
      () => {
        const r = Math.random();
        return r < 0.1 ? SAFF : r < 0.2 ? PALE : TURQ;
      },
      () => fromTeacher.clone().add(new THREE.Vector3().randomDirection().multiplyScalar(Math.random() * R_T)),
      1,
    );
    twinGroup.add(twin.points);

    // synapses (each node to its 3 nearest), fade in once the twin is assembled
    const seg: number[] = [];
    for (let i = 0; i < N; i++) {
      const near: [number, number][] = [];
      for (let k = 0; k < N; k++) {
        if (k === i) continue;
        const d = twinPts[i].distanceToSquared(twinPts[k]);
        if (near.length < 3) near.push([d, k]);
        else {
          let w = 0;
          for (let m = 1; m < 3; m++) if (near[m][0] > near[w][0]) w = m;
          if (d < near[w][0]) near[w] = [d, k];
        }
      }
      for (const [, k] of near) if (k > i) seg.push(twinPts[i].x, twinPts[i].y, twinPts[i].z, twinPts[k].x, twinPts[k].y, twinPts[k].z);
    }
    const synGeo = new THREE.BufferGeometry();
    synGeo.setAttribute("position", new THREE.Float32BufferAttribute(seg, 3));
    const synMat = new THREE.LineBasicMaterial({ color: TURQ, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(synGeo);
    mats.push(synMat);
    const synapses = new THREE.LineSegments(synGeo, synMat);
    twinGroup.add(synapses);

    // a small glowing "mind" inside the head
    const coreGeo = new THREE.IcosahedronGeometry(0.17, 1);
    const coreMat = new THREE.MeshBasicMaterial({ color: BLUE, wireframe: true, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(coreGeo);
    mats.push(coreMat);
    const core = new THREE.Mesh(coreGeo, coreMat);
    core.position.y = HEAD_Y * R_W * 2;
    twinGroup.add(core);

    // ---- knowledge stream teacher -> twin (quadratic bezier with an upward arc)
    const ctrl = new THREE.Vector3().addVectors(TEACHER, TWIN).multiplyScalar(0.5).add(new THREE.Vector3(0, 0.9, 0.6));
    const curve = new THREE.QuadraticBezierCurve3(TEACHER, ctrl, TWIN);
    const arcGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(64));
    const arcMat = new THREE.LineDashedMaterial({ color: SAFF, dashSize: 0.08, gapSize: 0.08, transparent: true, opacity: 0.3, depthWrite: false });
    geos.push(arcGeo);
    mats.push(arcMat);
    const arc = new THREE.Line(arcGeo, arcMat);
    arc.computeLineDistances();
    rig.add(arc);
    const M = small ? 18 : 28;
    const streamPos = new Float32Array(M * 3);
    const streamJit = Array.from({ length: M }, () => new THREE.Vector3().randomDirection().multiplyScalar(0.06 + Math.random() * 0.1));
    const streamGeo = new THREE.BufferGeometry();
    streamGeo.setAttribute("position", new THREE.BufferAttribute(streamPos, 3));
    const streamMat = new THREE.PointsMaterial({ color: "#ffd38a", size: 0.07, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(streamGeo);
    mats.push(streamMat);
    rig.add(new THREE.Points(streamGeo, streamMat));

    // ---- students orbiting the twin, practising with it
    const K = small ? 5 : 7;
    const ORBIT = 2.15;
    const orbitTilt = new THREE.Euler(1.18, 0, 0.28 * sx);
    const ringGeo = new THREE.BufferGeometry().setFromPoints(new THREE.EllipseCurve(0, 0, ORBIT, ORBIT, 0, Math.PI * 2).getPoints(160));
    const ringMat = new THREE.LineBasicMaterial({ color: BLUE, transparent: true, opacity: 0.18, depthWrite: false });
    geos.push(ringGeo);
    mats.push(ringMat);
    const ring = new THREE.LineLoop(ringGeo, ringMat);
    ring.rotation.copy(orbitTilt);
    twinGroup.add(ring);

    // students: small low-poly people (head + shoulders/body), solid core with a wireframe glow
    const headGeo = new THREE.IcosahedronGeometry(0.05, 1);
    headGeo.translate(0, 0.1, 0);
    const bodyGeo = new THREE.CylinderGeometry(0.035, 0.085, 0.14, 7, 1);
    bodyGeo.translate(0, -0.015, 0);
    const studentMat = new THREE.MeshBasicMaterial({ color: PALE });
    const glowHeadGeo = new THREE.IcosahedronGeometry(0.085, 1);
    glowHeadGeo.translate(0, 0.1, 0);
    const glowBodyGeo = new THREE.CylinderGeometry(0.06, 0.12, 0.2, 7, 1);
    glowBodyGeo.translate(0, -0.02, 0);
    const glowMat = new THREE.MeshBasicMaterial({ color: BLUE, wireframe: true, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(headGeo, bodyGeo, glowHeadGeo, glowBodyGeo);
    mats.push(studentMat, glowMat);
    const students = Array.from({ length: K }, (_, i) => {
      const m = new THREE.Group();
      m.add(new THREE.Mesh(headGeo, studentMat), new THREE.Mesh(bodyGeo, studentMat));
      m.add(new THREE.Mesh(glowHeadGeo, glowMat), new THREE.Mesh(glowBodyGeo, glowMat));
      twinGroup.add(m);
      return { mesh: m, a0: (i / K) * Math.PI * 2, speed: 0.07 + (i % 3) * 0.012 };
    });

    const beamPos = new Float32Array(K * 6);
    const beamGeo = new THREE.BufferGeometry();
    beamGeo.setAttribute("position", new THREE.BufferAttribute(beamPos, 3));
    const beamMat = new THREE.LineBasicMaterial({ color: TURQ, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(beamGeo);
    mats.push(beamMat);
    twinGroup.add(new THREE.LineSegments(beamGeo, beamMat));

    const pktPos = new Float32Array(K * 3);
    const pktGeo = new THREE.BufferGeometry();
    pktGeo.setAttribute("position", new THREE.BufferAttribute(pktPos, 3));
    const pktMat = new THREE.PointsMaterial({ color: "#9ff0e8", size: 0.09, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    geos.push(pktGeo);
    mats.push(pktMat);
    twinGroup.add(new THREE.Points(pktGeo, pktMat));

    // ---- star dust
    const S = small ? 220 : 480;
    const starPos = new Float32Array(S * 3);
    for (let i = 0; i < S; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(5 + Math.random() * 9);
      starPos.set([v.x, v.y, v.z - 4], i * 3);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: "#9fb6d9", size: 0.03, transparent: true, opacity: 0.55, depthWrite: false });
    geos.push(starGeo);
    mats.push(starMat);
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // ---- label anchors (HTML labels follow these)
    const aTeacher = new THREE.Object3D();
    aTeacher.position.set(0, R_T + 0.3, 0);
    teacherGroup.add(aTeacher);
    const aTwin = new THREE.Object3D();
    aTwin.position.set(0, R_W + 0.3, 0);
    twinGroup.add(aTwin);
    const aStudent = new THREE.Object3D();
    aStudent.position.set(0, 0.36, 0);
    students[0].mesh.add(aStudent);
    const anchors: [THREE.Object3D, HTMLElement | null][] = [
      [aTeacher, lTeacher.current],
      [aTwin, lTwin.current],
      [aStudent, lStudent.current],
    ];

    // ---- layout: story sits on the "end" side on wide screens
    let W = 1;
    let H = 1;
    const resize = () => {
      W = el.clientWidth;
      H = el.clientHeight;
      if (!W || !H) return;
      renderer.setSize(W, H, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = W / H;
      camera.updateProjectionMatrix();
      const wide = W >= 768;
      rig.position.x = wide ? sx * Math.min(2.5, camera.aspect * 1.2) : 0;
      rig.position.y = wide ? 0 : -0.1;
      rig.scale.setScalar(wide ? 1 : 0.7);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    const target = { x: 0, y: 0 };
    const onMove = (e: PointerEvent) => {
      target.x = (e.clientX / window.innerWidth - 0.5) * 0.4;
      target.y = (e.clientY / window.innerHeight - 0.5) * 0.25;
    };
    if (!reduced) window.addEventListener("pointermove", onMove, { passive: true });

    const tmp = new THREE.Vector3();
    const tw = new THREE.Vector3();
    const draw = (t: number) => {
      time.value = t;
      const build = Math.min(t / BUILD_SECONDS, 1);
      const settled = THREE.MathUtils.smoothstep(t, BUILD_SECONDS * 0.7, BUILD_SECONDS + 1.2);

      twin.u.uBuild.value = build;
      // the figure faces the viewer and only sways, so it reads as a person
      const sway = Math.sin(t * 0.3) * 0.35;
      twin.u.uSpin.value = sway;
      twin.u.uScan.value = Math.sin(t * 0.55) * (R_W + 0.05);
      synapses.rotation.y = sway;
      synMat.opacity = 0.2 * settled;
      coreMat.opacity = (0.3 + 0.15 * Math.sin(t * 2.1)) * settled;
      core.rotation.x = t * 0.18;
      core.rotation.y = t * 0.27;

      teacher.u.uSpin.value = Math.sin(t * 0.25 + 1) * 0.3;
      halo.rotation.z = t * 0.4;

      rig.rotation.y += (target.x - rig.rotation.y) * 0.04;
      rig.rotation.x += (target.y - rig.rotation.x) * 0.04;
      stars.rotation.y = t * 0.01;

      // knowledge stream: denser while the twin is being built
      arcMat.opacity = 0.18 + 0.25 * (1 - settled);
      for (let i = 0; i < M; i++) {
        const u = (t * (0.22 + 0.25 * (1 - settled)) + i / M) % 1;
        curve.getPoint(u, tmp).add(streamJit[i]);
        streamPos.set([tmp.x, tmp.y, tmp.z], i * 3);
      }
      streamGeo.attributes.position.needsUpdate = true;

      // students practising: beam + packet ping-pong between twin and student
      beamMat.opacity = 0.22 * settled;
      pktMat.opacity = 0.95 * settled;
      students.forEach((st, i) => {
        const a = st.a0 + t * st.speed;
        tw.set(Math.cos(a) * ORBIT, Math.sin(a) * ORBIT, 0).applyEuler(orbitTilt);
        st.mesh.position.copy(tw);
        st.mesh.rotation.y = Math.atan2(-tw.x, -tw.z); // face the twin
        beamPos.set([0, 0, 0, tw.x, tw.y, tw.z], i * 6);
        const ph = (t * 0.45 + i * 0.37) % 2;
        const u = ph < 1 ? ph : 2 - ph;
        tmp.copy(tw).multiplyScalar(0.25 + 0.75 * u);
        pktPos.set([tmp.x, tmp.y, tmp.z], i * 3);
      });
      beamGeo.attributes.position.needsUpdate = true;
      pktGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);

      // HTML labels follow their anchors
      for (const [obj, label] of anchors) {
        if (!label) continue;
        obj.getWorldPosition(tmp).project(camera);
        const x = (tmp.x * 0.5 + 0.5) * W;
        const y = (-tmp.y * 0.5 + 0.5) * H;
        label.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) translate(-50%, -100%)`;
      }
      lTwin.current?.classList.toggle("is-on", settled > 0.6);
      lStudent.current?.classList.toggle("is-on", settled > 0.9);
    };

    const clock = new THREE.Clock();
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
      draw(BUILD_SECONDS + 3); // one calm, fully built frame
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
    requestAnimationFrame(() => el.parentElement?.classList.add("is-ready"));

    return () => {
      stop();
      io?.disconnect();
      ro.disconnect();
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("visibilitychange", onVis);
      geos.forEach((g) => g.dispose());
      mats.forEach((m) => m.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [rtl]);

  return (
    <div aria-hidden="true" className="twin-canvas absolute inset-0">
      <div ref={holder} className="absolute inset-0" />
      <span ref={lTeacher} className="scene-label scene-label-teacher is-on">
        {labels.teacher}
      </span>
      <span ref={lTwin} className="scene-label scene-label-twin" dir="ltr">
        {labels.twin}
      </span>
      <span ref={lStudent} className="scene-label scene-label-student">
        {labels.student}
      </span>
    </div>
  );
}
