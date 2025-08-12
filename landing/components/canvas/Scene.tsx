'use client';

import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment } from '@react-three/drei';
import { useGLTF } from '@react-three/drei';
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Group } from 'three';

function Model() {
  const { scene } = useGLTF('https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/Box/glTF/Box.gltf');
  const ref = useRef<Group>(null);

  useFrame((state, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.1;
    }
  });

  return <primitive object={scene} ref={ref} scale={2} />;
}

export default function Scene() {
  return (
    <Canvas>
      <ambientLight intensity={0.5} />
      <directionalLight position={[0, 10, 5]} intensity={1} />
      <Environment preset="city" />
      <Model />
      <OrbitControls enableZoom={false} autoRotate />
    </Canvas>
  );
}
