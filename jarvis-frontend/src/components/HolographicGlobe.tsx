import { useEffect, useRef } from "react";
import * as THREE from "three";
import { aiVisualController, AIVisualState } from "../services/aiVisualController";

type HolographicGlobeProps = {
  className?: string;
  size?: number;
};

export function HolographicGlobe({ className = "", size = 320 }: HolographicGlobeProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const latestVisualState = useRef<AIVisualState | null>(null);

  useEffect(() => {
    // 1. Subscribe to central single source of truth for audio DSP & visual state
    const unsubscribe = aiVisualController.subscribe((state) => {
      latestVisualState.current = state;
    });

    const container = containerRef.current;
    if (!container) return () => unsubscribe();

    // 2. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    const width = container.clientWidth || size;
    const height = container.clientHeight || size;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // Root Holographic Group
    const holoRoot = new THREE.Group();
    scene.add(holoRoot);

    // 3. Color Palette Definitions (Cinematic Holographic Tones)
    const colors = {
      cyan: new THREE.Color(0x00f0ff),
      electricBlue: new THREE.Color(0x1a75ff),
      deepCyan: new THREE.Color(0x0a6b82),
      cyberTeal: new THREE.Color(0x00e5c0),
      pureWhite: new THREE.Color(0xffffff),
      neonMagenta: new THREE.Color(0xff2d87),
      alertGold: new THREE.Color(0xffd152),
      alertCrimson: new THREE.Color(0xff3860),
    };

    // 4. Inner Luminous Singularity Core Sphere (Fresnel Glow Shader)
    const coreGeometry = new THREE.IcosahedronGeometry(38, 4);
    const coreMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uIntensity: { value: 0.6 },
        uColor: { value: colors.cyan.clone() },
        uCoreColor: { value: colors.pureWhite.clone() },
        uFresnelPower: { value: 2.2 },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vPosition = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform float uIntensity;
        uniform vec3 uColor;
        uniform vec3 uCoreColor;
        uniform float uFresnelPower;
        varying vec3 vNormal;
        varying vec3 vPosition;

        void main() {
          vec3 viewDir = vec3(0.0, 0.0, 1.0);
          float fresnel = pow(1.0 - abs(dot(vNormal, viewDir)), uFresnelPower);
          float coreGlow = smoothstep(0.75, 0.0, length(vPosition) / 38.0);
          vec3 finalColor = mix(uColor, uCoreColor, coreGlow * (0.6 + uIntensity * 0.4));
          float alpha = clamp(fresnel * 0.85 + coreGlow * 0.6 * uIntensity, 0.0, 0.96);
          gl_FragColor = vec4(finalColor * (1.2 + uIntensity * 0.5), alpha);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    holoRoot.add(coreMesh);

    // 5. Geodesic Wireframe Shell (Audio-Reactive Vertex Displacement)
    const wireGeo = new THREE.IcosahedronGeometry(50, 3);
    const wireMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uAmp: { value: 0.0 },
        uBass: { value: 0.0 },
        uMid: { value: 0.0 },
        uHigh: { value: 0.0 },
        uPitch: { value: 0.25 },
        uColor: { value: colors.cyan.clone() },
      },
      vertexShader: `
        uniform float uTime;
        uniform float uAmp;
        uniform float uBass;
        uniform float uMid;
        uniform float uHigh;
        uniform float uPitch;
        varying vec3 vPos;
        varying float vDisplacement;

        void main() {
          vPos = position;
          float theta = atan(position.y, position.x);
          float phi = acos(position.z / 50.0);
          
          float waveLow = sin(phi * 4.0 + uTime * 2.8) * uBass * 4.8;
          float waveMid = cos(theta * 6.0 + uTime * (4.0 + uPitch * 6.0)) * uMid * 3.8;
          float waveHigh = sin(position.y * 0.45 + uTime * 14.0) * uHigh * 2.4;
          
          float disp = waveLow + waveMid + waveHigh;
          vDisplacement = disp;
          vec3 displaced = position + normal * (disp + uAmp * 9.0);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform float uAmp;
        varying float vDisplacement;

        void main() {
          float glow = 0.55 + clamp(vDisplacement * 0.16 + uAmp * 0.45, 0.0, 0.85);
          gl_FragColor = vec4(uColor * (1.1 + glow), 0.75 + glow * 0.25);
        }
      `,
      wireframe: true,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    holoRoot.add(wireMesh);

    // 6. Concentric 3-Axis Orbital Gimbal Rings
    const createGimbalRing = (radius: number, tubeRadius: number, tiltX: number, tiltY: number) => {
      const ringGeo = new THREE.TorusGeometry(radius, tubeRadius, 16, 120);
      const ringMat = new THREE.MeshBasicMaterial({
        color: colors.cyan.clone(),
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        wireframe: true,
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = tiltX;
      ringMesh.rotation.y = tiltY;
      holoRoot.add(ringMesh);
      return { mesh: ringMesh, mat: ringMat, baseRadius: radius };
    };

    const ring1 = createGimbalRing(64, 0.45, Math.PI / 4, Math.PI / 6);
    const ring2 = createGimbalRing(74, 0.4, -Math.PI / 3, Math.PI / 5);
    const ring3 = createGimbalRing(84, 0.35, Math.PI / 6, -Math.PI / 4);

    // 7. Equatorial Segmented Audio Spectrum Waveform Ring
    const spectrumSegments = 32;
    const spectrumRadius = 92;
    const spectrumPoints: THREE.Vector3[] = [];
    for (let i = 0; i <= spectrumSegments; i++) {
      const angle = (i / spectrumSegments) * Math.PI * 2;
      spectrumPoints.push(new THREE.Vector3(Math.cos(angle) * spectrumRadius, Math.sin(angle) * spectrumRadius, 0));
    }
    const spectrumGeo = new THREE.BufferGeometry().setFromPoints(spectrumPoints);
    const spectrumMat = new THREE.LineBasicMaterial({
      color: colors.cyan.clone(),
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
    });
    const spectrumLine = new THREE.Line(spectrumGeo, spectrumMat);
    holoRoot.add(spectrumLine);

    // 8. Holographic Particle Cloud & Vortex
    const particleCount = 850;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleBasePositions = new Float32Array(particleCount * 3);
    const particleSpeeds = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const radius = 56 + (Math.random() - 0.5) * 32;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta);
      const z = radius * Math.cos(phi);

      particlePositions[i * 3] = x;
      particlePositions[i * 3 + 1] = y;
      particlePositions[i * 3 + 2] = z;

      particleBasePositions[i * 3] = x;
      particleBasePositions[i * 3 + 1] = y;
      particleBasePositions[i * 3 + 2] = z;

      particleSpeeds[i] = 0.6 + Math.random() * 1.6;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));

    const particleMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: colors.cyan.clone() },
        uIntensity: { value: 0.65 },
        uAmp: { value: 0.0 },
      },
      vertexShader: `
        uniform float uAmp;
        uniform float uIntensity;
        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = (2.4 + uAmp * 3.2) * (240.0 / -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform float uIntensity;
        void main() {
          vec2 coord = gl_PointCoord - vec2(0.5);
          float dist = length(coord);
          if (dist > 0.5) discard;
          float alpha = smoothstep(0.5, 0.0, dist) * uIntensity;
          gl_FragColor = vec4(uColor * 1.5, alpha);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const particlePoints = new THREE.Points(particleGeometry, particleMaterial);
    holoRoot.add(particlePoints);

    // 9. Volumetric Halo Backplate
    const haloGeo = new THREE.PlaneGeometry(190, 190);
    const haloMat = new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: colors.deepCyan.clone() },
        uIntensity: { value: 0.35 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform float uIntensity;
        varying vec2 vUv;
        void main() {
          float dist = distance(vUv, vec2(0.5));
          float alpha = smoothstep(0.5, 0.0, dist) * uIntensity;
          gl_FragColor = vec4(uColor * 1.3, alpha * 0.7);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const haloMesh = new THREE.Mesh(haloGeo, haloMat);
    haloMesh.position.z = -25;
    scene.add(haloMesh);

    const spokeCount = 18;
    const spokePositions = new Float32Array(spokeCount * 6);
    for (let i = 0; i < spokeCount; i++) {
      const angle = (i / spokeCount) * Math.PI * 2;
      spokePositions[i * 6] = Math.cos(angle) * 42;
      spokePositions[i * 6 + 1] = Math.sin(angle) * 42;
      spokePositions[i * 6 + 2] = 0;
      spokePositions[i * 6 + 3] = Math.cos(angle) * 96;
      spokePositions[i * 6 + 4] = Math.sin(angle) * 96;
      spokePositions[i * 6 + 5] = 0;
    }
    const spokeGeo = new THREE.BufferGeometry();
    spokeGeo.setAttribute("position", new THREE.BufferAttribute(spokePositions, 3));
    const spokeMat = new THREE.LineBasicMaterial({
      color: colors.electricBlue.clone(),
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending,
    });
    const spokeLines = new THREE.LineSegments(spokeGeo, spokeMat);
    holoRoot.add(spokeLines);

    // 10. Synchronized 60+ FPS Render Loop
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);

      const state = latestVisualState.current;
      const now = performance.now();
      const elapsedTime = now / 1000;

      // Determine palette target based on operational state
      let activeColor = colors.cyan;
      if (state?.state === "listening") {
        activeColor = colors.electricBlue;
      } else if (state?.state === "speaking") {
        activeColor = colors.cyberTeal;
      } else if (state?.state === "error") {
        activeColor = colors.alertCrimson;
      } else if (state?.state === "thinking" || state?.state === "searching" || state?.state === "executing") {
        activeColor = colors.pureWhite;
      }

      // Smooth color transitions across all shader uniforms & materials
      coreMaterial.uniforms.uColor.value.lerp(activeColor, 0.08);
      wireMat.uniforms.uColor.value.lerp(activeColor, 0.08);
      particleMaterial.uniforms.uColor.value.lerp(activeColor, 0.08);
      ring1.mat.color.lerp(activeColor, 0.08);
      ring2.mat.color.lerp(activeColor, 0.08);
      ring3.mat.color.lerp(activeColor, 0.08);
      spectrumMat.color.lerp(activeColor, 0.08);
      haloMat.uniforms.uColor.value.lerp(activeColor, 0.08);
      spokeMat.color.lerp(activeColor, 0.08);

      const amp = state?.amplitude ?? 0;
      const bass = state?.bass ?? 0;
      const mid = state?.mid ?? 0;
      const high = state?.high ?? 0;
      const pitch = state?.pitch ?? 0.25;
      const scale = state?.scale ?? 1.0;
      const glow = state?.glow ?? 0.5;
      const rotSpeed = state?.rotationSpeed ?? 0.5;
      const bands = state?.frequencyBands ?? [];
      spokeLines.rotation.z += 0.002 * rotSpeed;
      spokeMat.opacity = 0.16 + amp * 0.35;

      // Update shader uniforms
      coreMaterial.uniforms.uTime.value = elapsedTime;
      coreMaterial.uniforms.uIntensity.value = glow;

      wireMat.uniforms.uTime.value = elapsedTime;
      wireMat.uniforms.uAmp.value = amp;
      wireMat.uniforms.uBass.value = bass;
      wireMat.uniforms.uMid.value = mid;
      wireMat.uniforms.uHigh.value = high;
      wireMat.uniforms.uPitch.value = pitch;

      particleMaterial.uniforms.uAmp.value = amp;
      particleMaterial.uniforms.uIntensity.value = 0.55 + amp * 0.5;

      haloMat.uniforms.uIntensity.value = 0.25 + glow * 0.4;

      // Holographic root scaling
      holoRoot.scale.set(scale, scale, scale);

      // Ring rotations driven by pitch and voice energy
      const speedMultiplier = state?.state === "thinking" ? 2.5 : 1.0;
      ring1.mesh.rotation.z += 0.01 * rotSpeed * speedMultiplier;
      ring2.mesh.rotation.z -= 0.008 * rotSpeed * speedMultiplier;
      ring3.mesh.rotation.y += 0.007 * rotSpeed * speedMultiplier;

      const ringPulse = 1.0 + amp * 0.24 + (state?.emphasis ?? 0) * 0.18;
      ring1.mesh.scale.set(ringPulse, ringPulse, ringPulse);
      ring2.mesh.scale.set(ringPulse * 1.04, ringPulse * 1.04, ringPulse * 1.04);
      ring3.mesh.scale.set(ringPulse * 1.08, ringPulse * 1.08, ringPulse * 1.08);

      ring1.mat.opacity = 0.45 + amp * 0.55;
      ring2.mat.opacity = 0.4 + amp * 0.52;
      ring3.mat.opacity = 0.35 + amp * 0.48;

      // Update equatorial audio waveform ring points
      const spectrumPosAttr = spectrumGeo.getAttribute("position") as THREE.BufferAttribute;
      const specArr = spectrumPosAttr.array as Float32Array;
      for (let i = 0; i <= spectrumSegments; i++) {
        const bandIndex = i % (bands.length || 16);
        const energy = bands[bandIndex] || 0;
        const dynamicRadius = spectrumRadius + energy * 18 * (1.0 + amp * 0.5);
        const angle = (i / spectrumSegments) * Math.PI * 2 + elapsedTime * 0.5;
        specArr[i * 3] = Math.cos(angle) * dynamicRadius;
        specArr[i * 3 + 1] = Math.sin(angle) * dynamicRadius;
        specArr[i * 3 + 2] = Math.sin(elapsedTime * 2.0 + i) * (2.0 + amp * 6.0);
      }
      spectrumPosAttr.needsUpdate = true;
      spectrumMat.opacity = 0.4 + amp * 0.6;

      // Particle cloud expansion & high-frequency excitation
      const posAttr = particleGeometry.getAttribute("position") as THREE.BufferAttribute;
      const positionsArr = posAttr.array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        const bx = particleBasePositions[i3];
        const by = particleBasePositions[i3 + 1];
        const bz = particleBasePositions[i3 + 2];

        const speed = particleSpeeds[i] * speedMultiplier;
        const angle = elapsedTime * 0.28 * speed;
        const cosA = Math.cos(angle);
        const sinA = Math.sin(angle);

        const rx = bx * cosA - bz * sinA;
        const rz = bx * sinA + bz * cosA;
        const ry = by;

        const particleExpansion =
          1.0 + amp * 0.42 + high * 0.2 * Math.sin(elapsedTime * 8.0 + i);

        positionsArr[i3] = rx * particleExpansion;
        positionsArr[i3 + 1] = ry * particleExpansion;
        positionsArr[i3 + 2] = rz * particleExpansion;
      }
      posAttr.needsUpdate = true;

      // Core & wireframe rotation
      wireMesh.rotation.y += 0.007 * rotSpeed * speedMultiplier;
      wireMesh.rotation.x = Math.sin(elapsedTime * 0.6) * 0.16;
      coreMesh.rotation.y -= 0.005 * rotSpeed * speedMultiplier;

      haloMesh.lookAt(camera.position);

      renderer.render(scene, camera);
    };

    animate();

    // 11. Resize Observer & window resize handler
    const updateSize = () => {
      if (!container) return;
      const w = container.clientWidth || size;
      const h = container.clientHeight || size;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    };

    const resizeObserver = new ResizeObserver(() => updateSize());
    resizeObserver.observe(container);
    window.addEventListener("resize", updateSize);

    return () => {
      unsubscribe();
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateSize);
      renderer.dispose();
      coreGeometry.dispose();
      coreMaterial.dispose();
      wireGeo.dispose();
      wireMat.dispose();
      particleGeometry.dispose();
      particleMaterial.dispose();
      haloGeo.dispose();
      haloMat.dispose();
      spectrumGeo.dispose();
      spectrumMat.dispose();
      ring1.mesh.geometry.dispose();
      ring1.mat.dispose();
      ring2.mesh.geometry.dispose();
      ring2.mat.dispose();
      ring3.mesh.geometry.dispose();
      ring3.mat.dispose();
      spokeGeo.dispose();
      spokeMat.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [size]);

  return <div ref={containerRef} className={`holographic-globe-container ${className}`} />;
}
