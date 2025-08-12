"use client";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Preload } from "@react-three/drei";
import { Model } from "./Model";

export default function Scene({ children = null, ...props }) {
  return (
    <Canvas {...props}>
      <directionalLight intensity={0.75} />
      <ambientLight intensity={0.75} />
      <Model />
      {children}
      <Preload all />
      <OrbitControls />
    </Canvas>
  );
}