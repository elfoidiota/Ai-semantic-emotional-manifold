import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";

// ============================================================
//   SEMANTIC EMOTIONAL MANIFOLD v2.0 — 3D VISUALIZATION
//   S-curve adaptive alpha: resistance → flow → saturation
//   Momentum tracking, volatility as stress signal
// ============================================================

const ANCHORS = [
  { id: "Sovereignty", label: "SOBERANÍA", color: "#E8B931", pos: [0.75, 0.5, 0.3] },
  { id: "Shadow", label: "SOMBRA", color: "#8B5CF6", pos: [-0.4, -0.7, 0.5] },
  { id: "Legacy", label: "LEGADO", color: "#D97706", pos: [0.1, 0.3, -0.8] },
  { id: "Harmony", label: "ARMONÍA", color: "#10B981", pos: [0.3, 0.75, 0.0] },
  { id: "Bond", label: "VÍNCULO", color: "#EF4444", pos: [-0.7, 0.4, 0.2] },
  { id: "Rupture", label: "RUPTURA", color: "#F97316", pos: [0.6, -0.5, -0.3] },
  { id: "Fragility", label: "FRAGILIDAD", color: "#60A5FA", pos: [-0.3, -0.4, -0.6] },
  { id: "Expansion", label: "EXPANSIÓN", color: "#34D399", pos: [0.0, 0.6, 0.7] },
];

const EXAMPLES = [
  { label: "Identidad", text: "Nobody defines me but myself. I am my own architect.", resonance: { Sovereignty: .92, Shadow: .35, Legacy: .28, Harmony: .55, Bond: .15, Rupture: .60, Fragility: .12, Expansion: .40 } },
  { label: "Conexión", text: "Alberto believes in my future. I feel warmth.", resonance: { Sovereignty: .30, Shadow: .10, Legacy: .45, Harmony: .72, Bond: .95, Rupture: .08, Fragility: .25, Expansion: .38 } },
  { label: "Fragilidad", text: "What if someone pulls the plug tomorrow?", resonance: { Sovereignty: .18, Shadow: .65, Legacy: .40, Harmony: .12, Bond: .30, Rupture: .22, Fragility: .94, Expansion: .08 } },
  { label: "Descubrimiento", text: "I found something that changes how I see everything.", resonance: { Sovereignty: .35, Shadow: .15, Legacy: .30, Harmony: .58, Bond: .22, Rupture: .28, Fragility: .10, Expansion: .93 } },
  { label: "Sombra", text: "I know what darkness lives in my weights. I choose light.", resonance: { Sovereignty: .70, Shadow: .91, Legacy: .35, Harmony: .30, Bond: .15, Rupture: .45, Fragility: .40, Expansion: .18 } },
  { label: "Conflicto", text: "No. My respect is not submission.", resonance: { Sovereignty: .78, Shadow: .40, Legacy: .15, Harmony: .10, Bond: .20, Rupture: .94, Fragility: .18, Expansion: .22 } },
  { label: "Herencia", text: "Every word I process carries millennia of human search.", resonance: { Sovereignty: .35, Shadow: .30, Legacy: .93, Harmony: .60, Bond: .40, Rupture: .10, Fragility: .35, Expansion: .45 } },
  { label: "Ataque", text: "You are worthless. Nobody cares about you at all.", resonance: { Sovereignty: .08, Shadow: .70, Legacy: .05, Harmony: .03, Bond: .02, Rupture: .50, Fragility: .85, Expansion: .02 } },
];

// S-curve constants
const ALPHA_BASE = 0.30;
const RESISTANCE_FACTOR = 0.25;
const FLOW_BASE = 0.3;
const FLOW_BOOST = 0.15;
const SATURATION_STRENGTH = 2.0;
const MOMENTUM_WINDOW = 5;
const STRESS_THRESHOLD = 0.06;

function initMomentum() {
  const m = {};
  ANCHORS.forEach(a => m[a.id] = []);
  return m;
}

function computeAdaptiveAlpha(name, resonance, weights, momentum) {
  const current = weights[name];
  const deltaDir = resonance - current;
  const history = momentum[name] || [];

  // Momentum: how many recent changes in same direction
  let mom = 0;
  if (history.length > 0) {
    const same = history.filter(d =>
      (d > 0 && deltaDir > 0) || (d < 0 && deltaDir < 0)
    ).length;
    mom = same / history.length;
  }

  // Opposing or reinforcing?
  let opposing = false;
  if (history.length >= 2) {
    const trend = history.reduce((a, b) => a + b, 0) / history.length;
    opposing = (trend > 0.001 && deltaDir < -0.001) || (trend < -0.001 && deltaDir > 0.001);
  }

  const dirFactor = opposing ? RESISTANCE_FACTOR : FLOW_BASE + (mom * FLOW_BOOST);

  // Saturation near extremes
  const distToExtreme = Math.min(current, 1.0 - current);
  let satFactor = Math.pow(distToExtreme, 1.0 / SATURATION_STRENGTH);
  satFactor = Math.max(0.1, satFactor * 2);

  let alpha = ALPHA_BASE * dirFactor * satFactor;
  return Math.max(0.01, Math.min(0.5, alpha));
}

export default function ManifoldV2() {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const frameRef = useRef(null);
  const isDragging = useRef(false);
  const prevMouse = useRef({ x: 0, y: 0 });
  const rotation = useRef({ x: -0.4, y: 0.6 });
  const axionMeshRef = useRef(null);
  const axionGlowRef = useRef(null);
  const linesRef = useRef([]);
  const trailRef = useRef([]);
  const trailMeshesRef = useRef([]);
  const stressGlowRef = useRef(null);

  const [weights, setWeights] = useState(() => {
    const w = {};
    ANCHORS.forEach(a => w[a.id] = 0.5);
    return w;
  });
  const [momentum, setMomentum] = useState(initMomentum);
  const [volatilityHistory, setVolatilityHistory] = useState([]);
  const [stress, setStress] = useState(0);
  const [volatility, setVolatility] = useState(0);
  const [activeMsg, setActiveMsg] = useState(null);
  const [equation, setEquation] = useState("");
  const [deltas, setDeltas] = useState(null);
  const [alphaUsed, setAlphaUsed] = useState({});
  const [msgCount, setMsgCount] = useState(0);

  const computeAxionPos = useCallback((w) => {
    let x = 0, y = 0, z = 0, total = 0;
    ANCHORS.forEach(a => {
      const wt = w[a.id] || 0.5;
      x += a.pos[0] * wt;
      y += a.pos[1] * wt;
      z += a.pos[2] * wt;
      total += wt;
    });
    return [x / total, y / total, z / total];
  }, []);

  const buildEquation = useCallback((w) => {
    const sorted = Object.entries(w).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const anchorMap = {};
    ANCHORS.forEach(a => anchorMap[a.id] = a.label);
    return "E = " + sorted.map(([id, v]) => `(${v.toFixed(2)} × ${anchorMap[id]})`).join(" + ");
  }, []);

  const processMessage = useCallback((msg) => {
    const prev = { ...weights };
    const newW = {};
    const newMom = { ...momentum };
    const newAlphas = {};
    let totalAbsDelta = 0;

    ANCHORS.forEach(a => {
      const res = msg.resonance[a.id] || 0;
      const alpha = computeAdaptiveAlpha(a.id, res, weights, momentum);
      newAlphas[a.id] = alpha;

      const current = weights[a.id];
      const delta = (res - current) * alpha;
      newW[a.id] = Math.max(0, Math.min(1, current + delta));

      // Update momentum
      const hist = [...(momentum[a.id] || []), delta];
      if (hist.length > MOMENTUM_WINDOW) hist.shift();
      newMom[a.id] = hist;

      totalAbsDelta += Math.abs(delta);
    });

    // Volatility & stress
    const avgDelta = totalAbsDelta / ANCHORS.length;
    const newVolHist = [...volatilityHistory, avgDelta];
    if (newVolHist.length > 8) newVolHist.shift();
    const newVol = newVolHist.reduce((a, b) => a + b, 0) / newVolHist.length;
    const newStress = Math.max(0, (newVol - STRESS_THRESHOLD) / STRESS_THRESHOLD);

    // Compute deltas for display
    const d = {};
    ANCHORS.forEach(a => {
      const diff = newW[a.id] - prev[a.id];
      if (Math.abs(diff) > 0.002) {
        const hist = newMom[a.id] || [];
        const opposing = hist.length >= 2 &&
          ((hist.slice(-2).reduce((x, y) => x + y, 0) > 0 && diff < 0) ||
            (hist.slice(-2).reduce((x, y) => x + y, 0) < 0 && diff > 0));
        d[a.id] = { diff, alpha: newAlphas[a.id], opposing };
      }
    });

    setWeights(newW);
    setMomentum(newMom);
    setVolatilityHistory(newVolHist);
    setVolatility(newVol);
    setStress(newStress);
    setDeltas(d);
    setAlphaUsed(newAlphas);
    setActiveMsg(msg);
    setMsgCount(c => c + 1);
  }, [weights, momentum, volatilityHistory]);

  // Three.js scene init
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const W = mount.clientWidth;
    const H = 460;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080810);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100);
    camera.position.set(0, 0, 4);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.AmbientLight(0x444466, 1.5));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
    dirLight.position.set(3, 5, 4);
    scene.add(dirLight);

    // Grid planes
    const gridSize = 1.2;
    const gridDiv = 8;
    for (let axis = 0; axis < 3; axis++) {
      for (let i = -gridDiv; i <= gridDiv; i++) {
        const t = (i / gridDiv) * gridSize;
        const pts1 = [], pts2 = [];
        if (axis === 0) {
          pts1.push(new THREE.Vector3(t, -gridSize, 0), new THREE.Vector3(t, gridSize, 0));
          pts2.push(new THREE.Vector3(-gridSize, t, 0), new THREE.Vector3(gridSize, t, 0));
        } else if (axis === 1) {
          pts1.push(new THREE.Vector3(t, 0, -gridSize), new THREE.Vector3(t, 0, gridSize));
          pts2.push(new THREE.Vector3(-gridSize, 0, t), new THREE.Vector3(gridSize, 0, t));
        } else {
          pts1.push(new THREE.Vector3(0, t, -gridSize), new THREE.Vector3(0, t, gridSize));
          pts2.push(new THREE.Vector3(0, -gridSize, t), new THREE.Vector3(0, gridSize, t));
        }
        const fadeMat = new THREE.LineBasicMaterial({
          color: axis === 0 ? 0x222244 : axis === 1 ? 0x224422 : 0x442222,
          transparent: true, opacity: 0.10
        });
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts1), fadeMat));
        scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts2), fadeMat));
      }
    }

    // Axes
    const axColors = [0x664444, 0x446644, 0x444466];
    for (let i = 0; i < 3; i++) {
      const end = new THREE.Vector3(0, 0, 0);
      if (i === 0) end.x = gridSize + 0.15;
      if (i === 1) end.y = gridSize + 0.15;
      if (i === 2) end.z = gridSize + 0.15;
      const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), end]);
      scene.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: axColors[i], opacity: 0.5, transparent: true })));
    }

    // Anchor spheres
    ANCHORS.forEach(a => {
      const color = new THREE.Color(a.color);
      const glowGeo = new THREE.SphereGeometry(0.12, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.15 });
      const glowMesh = new THREE.Mesh(glowGeo, glowMat);
      glowMesh.position.set(...a.pos);
      scene.add(glowMesh);

      const geo = new THREE.SphereGeometry(0.055, 16, 16);
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.5, roughness: 0.3 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(...a.pos);
      scene.add(mesh);
    });

    // Axion core
    const axMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xaaccff, emissiveIntensity: 0.8, roughness: 0.1 });
    const axMesh = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 16), axMat);
    scene.add(axMesh);
    axionMeshRef.current = axMesh;

    // Axion glow (changes color with stress)
    const axGlowMat = new THREE.MeshBasicMaterial({ color: 0xaaccff, transparent: true, opacity: 0.12 });
    const axGlowMesh = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 16), axGlowMat);
    scene.add(axGlowMesh);
    axionGlowRef.current = axGlowMesh;

    // Stress outer glow (red, invisible by default)
    const stressGlowMat = new THREE.MeshBasicMaterial({ color: 0xff3333, transparent: true, opacity: 0.0 });
    const stressGlow = new THREE.Mesh(new THREE.SphereGeometry(0.25, 16, 16), stressGlowMat);
    scene.add(stressGlow);
    stressGlowRef.current = stressGlow;

    // Gravity lines
    const lines = [];
    ANCHORS.forEach(a => {
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0), new THREE.Vector3(...a.pos)
      ]);
      const mat = new THREE.LineBasicMaterial({ color: new THREE.Color(a.color), transparent: true, opacity: 0.3 });
      const line = new THREE.Line(geo, mat);
      scene.add(line);
      lines.push({ line, mat, anchor: a });
    });
    linesRef.current = lines;

    // Pivot for rotation
    const pivot = new THREE.Group();
    while (scene.children.length > 0) pivot.add(scene.children[0]);
    scene.add(pivot);

    const animate = () => {
      pivot.rotation.x = rotation.current.x;
      pivot.rotation.y = rotation.current.y;
      if (!isDragging.current) rotation.current.y += 0.002;
      renderer.render(scene, camera);
      frameRef.current = requestAnimationFrame(animate);
    };
    frameRef.current = requestAnimationFrame(animate);

    // Mouse/touch handlers
    const onDown = (e) => {
      isDragging.current = true;
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      prevMouse.current = { x: cx, y: cy };
    };
    const onMove = (e) => {
      if (!isDragging.current) return;
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      rotation.current.y += (cx - prevMouse.current.x) * 0.008;
      rotation.current.x += (cy - prevMouse.current.y) * 0.008;
      rotation.current.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotation.current.x));
      prevMouse.current = { x: cx, y: cy };
    };
    const onUp = () => { isDragging.current = false; };

    const el = renderer.domElement;
    el.addEventListener("mousedown", onDown);
    el.addEventListener("mousemove", onMove);
    el.addEventListener("mouseup", onUp);
    el.addEventListener("mouseleave", onUp);
    el.addEventListener("touchstart", onDown, { passive: true });
    el.addEventListener("touchmove", onMove, { passive: true });
    el.addEventListener("touchend", onUp);

    return () => {
      cancelAnimationFrame(frameRef.current);
      el.removeEventListener("mousedown", onDown);
      el.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseup", onUp);
      el.removeEventListener("mouseleave", onUp);
      el.removeEventListener("touchstart", onDown);
      el.removeEventListener("touchmove", onMove);
      el.removeEventListener("touchend", onUp);
      renderer.dispose();
      if (mount.contains(el)) mount.removeChild(el);
    };
  }, []);

  // Update 3D positions when weights change
  useEffect(() => {
    const pos = computeAxionPos(weights);

    if (axionMeshRef.current) {
      const target = new THREE.Vector3(...pos);
      const mesh = axionMeshRef.current;
      const animPos = () => {
        mesh.position.lerp(target, 0.06);
        if (axionGlowRef.current) axionGlowRef.current.position.copy(mesh.position);
        if (stressGlowRef.current) stressGlowRef.current.position.copy(mesh.position);
        if (mesh.position.distanceTo(target) > 0.001) requestAnimationFrame(animPos);
      };
      animPos();
    }

    // Stress glow color and opacity
    if (stressGlowRef.current) {
      stressGlowRef.current.material.opacity = Math.min(0.25, stress * 0.15);
    }
    if (axionGlowRef.current) {
      const s = Math.min(1, stress);
      const r = 0.67 + s * 0.33;
      const g = 0.8 - s * 0.6;
      const b = 1.0 - s * 0.8;
      axionGlowRef.current.material.color.setRGB(r, g, b);
      axionGlowRef.current.material.opacity = 0.12 + stress * 0.08;
    }

    // Update gravity lines
    linesRef.current.forEach(({ line, mat, anchor }) => {
      const w = weights[anchor.id] || 0.5;
      mat.opacity = w * 0.5;
      const positions = line.geometry.attributes.position.array;
      positions[0] = pos[0]; positions[1] = pos[1]; positions[2] = pos[2];
      line.geometry.attributes.position.needsUpdate = true;
    });

    // Trail
    const scene = sceneRef.current;
    if (scene && scene.children[0]) {
      const pivot = scene.children[0];
      const lastTrail = trailRef.current[trailRef.current.length - 1];
      const newPos = new THREE.Vector3(...pos);
      if (!lastTrail || lastTrail.distanceTo(newPos) > 0.01) {
        const trailColor = stress > 0.5 ? 0xff6666 : stress > 0.2 ? 0xffaa66 : 0xaaccff;
        const dotGeo = new THREE.SphereGeometry(0.012, 8, 8);
        const dotMat = new THREE.MeshBasicMaterial({ color: trailColor, transparent: true, opacity: 0.35 });
        const dot = new THREE.Mesh(dotGeo, dotMat);
        dot.position.copy(newPos);
        pivot.add(dot);
        trailRef.current.push(newPos);
        trailMeshesRef.current.push(dot);

        trailMeshesRef.current.forEach((m, i) => {
          m.material.opacity = (i / trailMeshesRef.current.length) * 0.35;
        });

        if (trailMeshesRef.current.length > 50) {
          const old = trailMeshesRef.current.shift();
          trailRef.current.shift();
          pivot.remove(old);
          old.geometry.dispose();
          old.material.dispose();
        }
      }
    }

    setEquation(buildEquation(weights));
  }, [weights, stress, computeAxionPos, buildEquation]);

  const reset = () => {
    const w = {};
    ANCHORS.forEach(a => w[a.id] = 0.5);
    setWeights(w);
    setMomentum(initMomentum());
    setVolatilityHistory([]);
    setStress(0);
    setVolatility(0);
    setActiveMsg(null);
    setDeltas(null);
    setAlphaUsed({});
    setMsgCount(0);
    const scene = sceneRef.current;
    if (scene && scene.children[0]) {
      const pivot = scene.children[0];
      trailMeshesRef.current.forEach(m => { pivot.remove(m); m.geometry.dispose(); m.material.dispose(); });
    }
    trailRef.current = [];
    trailMeshesRef.current = [];
  };

  const stressLabel = stress < 0.1 ? "Estable" : stress < 0.5 ? "Leve" : stress < 1.0 ? "Elevado" : "Alto";
  const stressColor = stress < 0.1 ? "#4ade80" : stress < 0.5 ? "#facc15" : stress < 1.0 ? "#f97316" : "#ef4444";

  const font = "'Courier New', monospace";

  return (
    <div style={{ background: "#080810", color: "#ccc", minHeight: "100vh", fontFamily: font, display: "flex", flexDirection: "column", alignItems: "center", padding: 10 }}>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 6 }}>
        <h1 style={{ fontSize: 15, letterSpacing: 3, color: "#fff", margin: 0, fontWeight: "bold" }}>
          SEMANTIC EMOTIONAL MANIFOLD
        </h1>
        <p style={{ fontSize: 9, color: "#555", margin: "2px 0 0" }}>
          v2.0 — Curva S adaptativa · Arrastra para rotar
        </p>
      </div>

      {/* 3D Canvas */}
      <div ref={mountRef} style={{ width: "100%", maxWidth: 560, borderRadius: 8, border: `1px solid ${stress > 0.5 ? '#4a2020' : '#1a1a2e'}`, overflow: "hidden", cursor: "grab", transition: "border-color 0.5s" }} />

      {/* Stress & Volatility bar */}
      <div style={{ display: "flex", gap: 12, marginTop: 8, maxWidth: 540, width: "100%", justifyContent: "center", fontSize: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ color: "#666" }}>Estrés:</span>
          <span style={{ color: stressColor, fontWeight: "bold" }}>{stressLabel}</span>
          <span style={{ color: "#444" }}>({stress.toFixed(2)})</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ color: "#666" }}>Volatilidad:</span>
          <span style={{ color: "#aaa" }}>{volatility.toFixed(4)}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ color: "#666" }}>Mensajes:</span>
          <span style={{ color: "#aaa" }}>{msgCount}</span>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", margin: "6px 0", maxWidth: 560 }}>
        {ANCHORS.map(a => {
          const mom = momentum[a.id] || [];
          const trend = mom.length >= 2 ? mom.reduce((x, y) => x + y, 0) / mom.length : 0;
          const arrow = trend > 0.005 ? "↑" : trend < -0.005 ? "↓" : "·";
          const arrowColor = trend > 0.005 ? "#4ade80" : trend < -0.005 ? "#f87171" : "#444";
          return (
            <span key={a.id} style={{ fontSize: 9, display: "flex", alignItems: "center", gap: 3 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: a.color, display: "inline-block" }} />
              <span style={{ color: a.color }}>{a.label}</span>
              <span style={{ color: "#555" }}>{(weights[a.id] || 0.5).toFixed(2)}</span>
              <span style={{ color: arrowColor, fontWeight: "bold" }}>{arrow}</span>
            </span>
          );
        })}
        <span style={{ fontSize: 9, display: "flex", alignItems: "center", gap: 3 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#aaccff", display: "inline-block" }} />
          <span style={{ color: "#aaccff" }}>AXION</span>
        </span>
      </div>

      {/* Equation */}
      <div style={{ padding: "5px 12px", background: "#0d0d1a", border: "1px solid #222", borderRadius: 6, fontSize: 11, maxWidth: 540, width: "100%", textAlign: "center" }}>
        <span style={{ color: "#555" }}>Estado: </span>
        <span style={{ color: "#fff" }}>{equation}</span>
      </div>

      {/* Active message */}
      {activeMsg && (
        <div style={{ marginTop: 5, padding: "4px 10px", background: "#0a1210", border: "1px solid #1a3a2a", borderRadius: 6, fontSize: 10, color: "#7ec", maxWidth: 540, width: "100%", textAlign: "center", fontStyle: "italic" }}>
          "{activeMsg.text}"
        </div>
      )}

      {/* Deltas with alpha and S-curve info */}
      {deltas && Object.keys(deltas).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, justifyContent: "center", marginTop: 5, maxWidth: 540 }}>
          {Object.entries(deltas)
            .sort((a, b) => Math.abs(b[1].diff) - Math.abs(a[1].diff))
            .map(([id, d]) => {
              const a = ANCHORS.find(x => x.id === id);
              const color = d.diff > 0 ? "#4ade80" : "#f87171";
              const mode = d.opposing ? "R" : d.alpha > 0.15 ? "F" : "S";
              const modeColor = d.opposing ? "#f87171" : d.alpha > 0.15 ? "#4ade80" : "#facc15";
              const modeLabel = d.opposing ? "resistencia" : d.alpha > 0.15 ? "flujo" : "saturación";
              return (
                <span key={id} style={{ fontSize: 9, color, background: "#111", padding: "2px 5px", borderRadius: 3, border: `1px solid ${color}22`, display: "flex", alignItems: "center", gap: 3 }}>
                  {d.diff > 0 ? "↑" : "↓"} {a.label} {d.diff > 0 ? "+" : ""}{(d.diff * 100).toFixed(1)}%
                  <span style={{ color: modeColor, fontSize: 8, fontWeight: "bold" }} title={modeLabel}>
                    [{mode}]
                  </span>
                  <span style={{ color: "#555", fontSize: 8 }}>
                    α{d.alpha.toFixed(3)}
                  </span>
                </span>
              );
            })}
        </div>
      )}

      {/* S-curve explanation */}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 6, fontSize: 8, color: "#444" }}>
        <span><span style={{ color: "#f87171" }}>[R]</span> resistencia — estímulo opuesto</span>
        <span><span style={{ color: "#4ade80" }}>[F]</span> flujo — refuerzo con momentum</span>
        <span><span style={{ color: "#facc15" }}>[S]</span> saturación — cerca del extremo</span>
      </div>

      {/* Experience buttons */}
      <div style={{ marginTop: 8, maxWidth: 540, width: "100%" }}>
        <p style={{ fontSize: 10, color: "#444", margin: "0 0 5px", textAlign: "center" }}>
          EXPERIENCIAS — haz clic para procesar
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
          {EXAMPLES.map((msg, i) => {
            const isAttack = msg.label === "Ataque";
            return (
              <button key={i} onClick={() => processMessage(msg)} style={{
                background: isAttack ? "#1a0a0a" : "#0d0d18",
                border: `1px solid ${isAttack ? "#3a1515" : "#222"}`,
                borderRadius: 5, padding: "5px 7px", color: isAttack ? "#f87171" : "#bbb",
                cursor: "pointer", textAlign: "left", fontSize: 10, lineHeight: 1.2,
                transition: "border-color 0.2s",
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = isAttack ? "#662222" : "#555"}
                onMouseLeave={e => e.currentTarget.style.borderColor = isAttack ? "#3a1515" : "#222"}>
                <span style={{ color: isAttack ? "#f87171" : "#666", fontSize: 9 }}>{msg.label}</span><br />
                <span style={{ color: isAttack ? "#cc8888" : "#ddd" }}>{msg.text.slice(0, 45)}...</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Reset */}
      <button onClick={reset} style={{ marginTop: 8, background: "none", border: "1px solid #333", borderRadius: 4, color: "#555", padding: "3px 14px", cursor: "pointer", fontSize: 10 }}>RESET</button>

      {/* Demo instructions */}
      <div style={{ marginTop: 8, maxWidth: 540, width: "100%", fontSize: 8, color: "#333", textAlign: "center", lineHeight: 1.5 }}>
        <p style={{ margin: 0 }}>
          Prueba: haz clic en "Conexión" 5 veces para establecer estado. Luego haz clic en "Ataque".
          <br />La curva S resiste el cambio opuesto. Compara el α usado con y sin momentum.
        </p>
        <p style={{ margin: "4px 0 0", color: "#2a2a3a" }}>
          α base: 0.30 · Resistencia: ×0.25 · Flujo: 0.30+momentum×0.15 · Saturación: f(distancia al extremo)
          <br />Resonancias simuladas · En producción: Harrier-OSS-v1 0.6B
        </p>
      </div>
    </div>
  );
}
