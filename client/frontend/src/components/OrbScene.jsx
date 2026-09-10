/**
 * OrbScene.jsx — JARVIS Holographic Orb v3.0
 * 
 * A Three.js R3F scene with:
 *  - Custom GLSL shader sphere (Fresnel edge glow + simplex noise surface)
 *  - Orbital particle rings
 *  - State-reactive animations: sleep / awake / listening
 */
import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// ─── GLSL Snippets ──────────────────────────────────────────────────────────

// Simplex 3D noise (Ashima / Stefan Gustavson - public domain)
const SIMPLEX_GLSL = /* glsl */`
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
`;

// ─── Vertex Shader ───────────────────────────────────────────────────────────
const vertexShader = /* glsl */`
${SIMPLEX_GLSL}

uniform float uTime;
uniform float uNoiseMag;

varying vec3 vNormal;
varying vec3 vViewDir;
varying float vNoise;
varying vec3 vPosition;

void main() {
  vPosition = position;
  
  float n = snoise(normal * 2.5 + uTime * 0.4);
  vec3 displaced = position + normal * n * uNoiseMag;
  
  vNoise = n;
  vNormal = normalize(normalMatrix * normal);
  
  vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
  vViewDir = normalize(-mvPosition.xyz);
  
  gl_Position = projectionMatrix * mvPosition;
}
`;

// ─── Fragment Shader ──────────────────────────────────────────────────────────
const fragmentShader = /* glsl */`
uniform vec3  uColorCore;
uniform vec3  uColorRim;
uniform float uFresnelPower;
uniform float uTime;
uniform float uPulse;
uniform float uOpacity;

varying vec3  vNormal;
varying vec3  vViewDir;
varying float vNoise;
varying vec3  vPosition;

void main() {
  // Fresnel edge
  float fresnel = pow(1.0 - abs(dot(vNormal, vViewDir)), uFresnelPower);
  
  // Animated surface color
  float pulse = sin(uTime * 3.0) * 0.5 + 0.5;
  
  // Mix core color with rim based on fresnel
  vec3 color = mix(uColorCore, uColorRim, fresnel);
  
  // Add noise-based shimmer
  color += (vNoise * 0.15) * uColorRim;
  
  // Inner glow pulse
  color += pulse * 0.1 * uColorRim * uPulse;
  
  // Alpha: core semi-transparent, rim opaque
  float alpha = mix(0.55, 1.0, fresnel) * uOpacity;
  
  gl_FragColor = vec4(color, alpha);
}
`;

// ─── Holographic Sphere Mesh ──────────────────────────────────────────────────
function HoloSphere({ stateRef }) {
  const meshRef = useRef();
  const matRef = useRef();

  const uniforms = useMemo(() => ({
    uTime:         { value: 0 },
    uNoiseMag:     { value: 0.06 },
    uColorCore:    { value: new THREE.Color('#00e5ff') },
    uColorRim:     { value: new THREE.Color('#a855f7') },
    uFresnelPower: { value: 2.5 },
    uPulse:        { value: 0.0 },
    uOpacity:      { value: 1.0 },
  }), []);

  useFrame((_, delta) => {
    const mat = matRef.current;
    const mesh = meshRef.current;
    if (!mat || !mesh) return;

    const state = stateRef.current;
    const t = mat.uniforms.uTime.value + delta;
    mat.uniforms.uTime.value = t;

    // State-specific targets
    if (state === 'listening') {
      // Fast, bright magenta
      mat.uniforms.uColorCore.value.lerp(new THREE.Color('#ff00ff'), 0.05);
      mat.uniforms.uColorRim.value.lerp(new THREE.Color('#00e5ff'), 0.05);
      mat.uniforms.uNoiseMag.value += (0.14 - mat.uniforms.uNoiseMag.value) * 0.05;
      mat.uniforms.uPulse.value += (1.5 - mat.uniforms.uPulse.value) * 0.08;
      mat.uniforms.uFresnelPower.value += (1.5 - mat.uniforms.uFresnelPower.value) * 0.05;
      mesh.rotation.y += delta * 1.2;
      mesh.rotation.x += delta * 0.4;
    } else if (state === 'awake') {
      // Calm cyan + purple
      mat.uniforms.uColorCore.value.lerp(new THREE.Color('#0ff0fc'), 0.03);
      mat.uniforms.uColorRim.value.lerp(new THREE.Color('#a855f7'), 0.03);
      mat.uniforms.uNoiseMag.value += (0.07 - mat.uniforms.uNoiseMag.value) * 0.03;
      mat.uniforms.uPulse.value += (0.5 - mat.uniforms.uPulse.value) * 0.04;
      mat.uniforms.uFresnelPower.value += (2.5 - mat.uniforms.uFresnelPower.value) * 0.03;
      mesh.rotation.y += delta * 0.3;
      mesh.rotation.x += delta * 0.1;
    } else {
      // sleep — dim, very slow
      mat.uniforms.uColorCore.value.lerp(new THREE.Color('#003344'), 0.02);
      mat.uniforms.uColorRim.value.lerp(new THREE.Color('#220033'), 0.02);
      mat.uniforms.uNoiseMag.value += (0.03 - mat.uniforms.uNoiseMag.value) * 0.02;
      mat.uniforms.uPulse.value += (0.0 - mat.uniforms.uPulse.value) * 0.03;
      mat.uniforms.uFresnelPower.value += (3.5 - mat.uniforms.uFresnelPower.value) * 0.02;
      mesh.rotation.y += delta * 0.05;
    }
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 128, 128]} />
      <shaderMaterial
        ref={matRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        side={THREE.FrontSide}
      />
    </mesh>
  );
}

// ─── Orbital Particle Ring ────────────────────────────────────────────────────
function ParticleRing({ radius = 1.5, count = 80, tilt = 0, speed = 0.4, stateRef }) {
  const ref = useRef();
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      // Spread particles slightly around the ring
      const spread = (Math.random() - 0.5) * 0.06;
      arr[i * 3 + 0] = Math.cos(angle) * (radius + spread);
      arr[i * 3 + 1] = (Math.random() - 0.5) * 0.08;
      arr[i * 3 + 2] = Math.sin(angle) * (radius + spread);
    }
    return arr;
  }, [count, radius]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const state = stateRef.current;
    const actualSpeed = state === 'listening' ? speed * 3 : state === 'sleep' ? speed * 0.1 : speed;
    ref.current.rotation.y += delta * actualSpeed;
  });

  return (
    <group ref={ref} rotation={[tilt, 0, 0]}>
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.025}
          color="#00e5ff"
          transparent
          opacity={0.7}
          depthWrite={false}
          sizeAttenuation
        />
      </points>
    </group>
  );
}

// ─── Inner Core Glow ─────────────────────────────────────────────────────────
function CoreGlow({ stateRef }) {
  const ref = useRef();
  const matRef = useRef();

  useFrame((_, delta) => {
    if (!ref.current || !matRef.current) return;
    const state = stateRef.current;
    const t = (matRef.current.uniforms?.uTime?.value ?? 0) + delta;
    
    let targetScale = state === 'listening' ? 0.55 + Math.sin(t * 8) * 0.1
                    : state === 'awake'     ? 0.45 + Math.sin(t * 2) * 0.05
                    :                         0.25;
    
    ref.current.scale.setScalar(
      ref.current.scale.x + (targetScale - ref.current.scale.x) * 0.08
    );
  });

  return (
    <mesh ref={ref} scale={0.45}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial
        color="#80ffff"
        transparent
        opacity={0.15}
        depthWrite={false}
        side={THREE.BackSide}
      />
    </mesh>
  );
}

// ─── Scene Root ───────────────────────────────────────────────────────────────
function OrbSceneInner({ stateRef }) {
  return (
    <>
      <ambientLight intensity={0.1} />
      <pointLight position={[0, 0, 2]} intensity={2} color="#00e5ff" />
      <pointLight position={[0, 2, -1]} intensity={1} color="#a855f7" />

      <HoloSphere stateRef={stateRef} />
      <CoreGlow stateRef={stateRef} />

      {/* Three concentric particle rings at different tilts */}
      <ParticleRing radius={1.38} count={100} tilt={Math.PI * 0.1}  speed={0.35} stateRef={stateRef} />
      <ParticleRing radius={1.48} count={60}  tilt={Math.PI * 0.45} speed={-0.25} stateRef={stateRef} />
      <ParticleRing radius={1.55} count={40}  tilt={Math.PI * 0.3}  speed={0.5}  stateRef={stateRef} />
    </>
  );
}

// ─── Exported Component ───────────────────────────────────────────────────────
/**
 * Drop-in replacement for the old Aurora component.
 * Accepts the same `state` and `style` props.
 */
const OrbScene = ({ state = 'awake', style }) => {
  // Use a ref so the animation loop always reads the latest state
  // without re-mounting the Canvas on every state change.
  const stateRef = useRef(state);
  stateRef.current = state;

  const containerStyle = {
    position: 'absolute',
    width: '100%',
    height: '100%',
    top: 0,
    left: 0,
    // NO overflow:hidden ni borderRadius aquí — dejar que el shader maneje
    // la transparencia a través de la ventana frameless de pywebview.
    transition: 'opacity 0.6s ease, filter 0.6s ease',
    opacity: state === 'sleep' ? 0.25 : 1,
    filter: state === 'listening'
      ? 'drop-shadow(0 0 24px #ff00ff) drop-shadow(0 0 48px #ff00ff88)'
      : state === 'awake'
      ? 'drop-shadow(0 0 16px #00e5ff) drop-shadow(0 0 32px #00e5ff66)'
      : 'none',
    ...style,
  };

  return (
    <div style={containerStyle}>
      <Canvas
        camera={{ position: [0, 0, 2.8], fov: 45 }}
        gl={{
          antialias: true,
          alpha: true,
          // premultipliedAlpha: false es CRÍTICO para que pywebview + Edge WebView2
          // propague correctamente el canal alpha del WebGL al compositor de Windows.
          premultipliedAlpha: false,
        }}
        onCreated={({ gl, scene }) => {
          // Forzar fondo completamente transparente.
          gl.setClearColor(0x000000, 0);
          gl.setClearAlpha(0);
          // R3F puede poner un fondo de escena por defecto — lo anulamos.
          scene.background = null;
        }}
      >
        <OrbSceneInner stateRef={stateRef} />
      </Canvas>
    </div>
  );
};

export default OrbScene;
