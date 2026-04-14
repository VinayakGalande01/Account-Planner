'use client';

import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface WebGLGridProps {
  transitionActive?: boolean;
}

export default function WebGLGrid({ transitionActive = false }: WebGLGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const animatingTransition = useRef(false);

  useEffect(() => {
    if (transitionActive) {
      animatingTransition.current = true;
    }
  }, [transitionActive]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // SCENE SETUP
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x020202, 0.001);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
    camera.position.z = 400;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // DOT CLOUD SETUP
    const pointCount = 6000;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(pointCount * 3);
    const basePositions = new Float32Array(pointCount * 3);
    const velocities = new Float32Array(pointCount * 3);

    for (let i = 0; i < pointCount; i++) {
      const i3 = i * 3;
      // Distribute points in a wide grid-like or volume pattern
      const x = (Math.random() - 0.5) * 2000;
      const y = (Math.random() - 0.5) * 1000;
      const z = (Math.random() - 0.5) * 1000;
      
      positions[i3] = x;
      positions[i3 + 1] = y;
      positions[i3 + 2] = z;
      
      basePositions[i3] = x;
      basePositions[i3 + 1] = y;
      basePositions[i3 + 2] = z;
      
      velocities[i3] = 0;
      velocities[i3 + 1] = 0;
      velocities[i3 + 2] = 0;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('basePosition', new THREE.BufferAttribute(basePositions, 3));
    geometry.setAttribute('velocity', new THREE.BufferAttribute(velocities, 3));

    // Custom Shader for Points to handle nice glow
    const material = new THREE.PointsMaterial({
      size: 3,
      color: 0x2563eb, // Cobalt Blue
      transparent: true,
      opacity: 0.6,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // MOUSE REACTION VARIABLES
    const raycaster = new THREE.Raycaster();
    const mouseParams = new THREE.Vector2();
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);

    const handleMouseMove = (event: MouseEvent) => {
      mouseParams.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouseParams.y = -(event.clientY / window.innerHeight) * 2 + 1;
      
      raycaster.setFromCamera(mouseParams, camera);
      const target = new THREE.Vector3();
      raycaster.ray.intersectPlane(plane, target);
      
      mouseRef.current = { x: target.x, y: target.y };
    };

    window.addEventListener('mousemove', handleMouseMove);

    // ANIMATION LOOP
    const clock = new THREE.Clock();
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = clock.getDelta();

      const posAttr = particles.geometry.attributes.position as THREE.BufferAttribute;
      const baseAttr = particles.geometry.attributes.basePosition as THREE.BufferAttribute;
      const velAttr = particles.geometry.attributes.velocity as THREE.BufferAttribute;

      if (animatingTransition.current) {
        // STARFIELD EFFECT
        camera.position.z -= 1500 * delta; // Accelerate toward camera
        particles.material.opacity = Math.max(0, particles.material.opacity - 0.5 * delta);
        
        // Optional warp distortion
        for (let i = 0; i < pointCount; i++) {
          const z = posAttr.getZ(i);
          posAttr.setZ(i, z + 200 * delta);
        }
        posAttr.needsUpdate = true;
        
      } else {
        // MAGNETIC REPULSION & SPRING
        const mx = mouseRef.current.x;
        const my = mouseRef.current.y;
        
        const influenceRadius = 150;
        const spring = 0.05;
        const friction = 0.85;

        for (let i = 0; i < pointCount; i++) {
          const px = posAttr.getX(i);
          const py = posAttr.getY(i);
          const pz = posAttr.getZ(i);
          
          let vx = velAttr.getX(i);
          let vy = velAttr.getY(i);
          let vz = velAttr.getZ(i);
          
          const bx = baseAttr.getX(i);
          const by = baseAttr.getY(i);
          const bz = baseAttr.getZ(i);

          // Calculate distance to mouse (only on XY plane for simpler repulsion)
          const dx = px - mx;
          const dy = py - my;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Repulse
          if (dist < influenceRadius && dist > 0) {
            const force = (influenceRadius - dist) / influenceRadius; // 0 to 1
            const dirX = dx / dist;
            const dirY = dy / dist;
            
            vx += dirX * force * 5;
            vy += dirY * force * 5;
          }

          // Spring back to base
          vx += (bx - px) * spring;
          vy += (by - py) * spring;
          vz += (bz - pz) * spring; // Slowly drift back Z

          // Add some slow floating
          vx += (Math.random() - 0.5) * 0.2;
          vy += (Math.random() - 0.5) * 0.2;

          // Apply friction
          vx *= friction;
          vy *= friction;
          vz *= friction;

          // Move
          posAttr.setXYZ(i, px + vx, py + vy, pz + vz);
          velAttr.setXYZ(i, vx, vy, vz);
        }
        
        posAttr.needsUpdate = true;
        velAttr.needsUpdate = true;
      }

      // Rotate whole cloud slightly
      if (!animatingTransition.current) {
        particles.rotation.y = Math.sin(clock.elapsedTime * 0.1) * 0.1;
        particles.rotation.x = Math.cos(clock.elapsedTime * 0.1) * 0.05;
      }

      renderer.render(scene, camera);
    };

    animate();

    // RESIZE EVENT
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
      if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  return <div ref={containerRef} className="fixed inset-0 pointer-events-none z-0" />;
}
