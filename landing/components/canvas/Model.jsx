"use client";
import * as THREE from "three";
import React, { useRef, useEffect, useState } from "react";
import { useFrame, useLoader } from "@react-three/fiber";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

function IPad() {
  const gltf = useLoader(GLTFLoader, "/ipad.glb");
  const [video] = useState(() => {
    const vid = document.createElement("video");
    vid.src = "/sentinelai.mp4";
    vid.crossOrigin = "Anonymous";
    vid.loop = true;
    vid.muted = true;
    vid.playsInline = true;
    vid.play().catch((e) => console.error("Video play failed:", e));
    return vid;
  });

  useEffect(() => {
    if (gltf.scene) {
      // Find the screen mesh in the loaded model
      const screen = gltf.scene.getObjectByName("Screen");
      if (screen && screen.isMesh) {
        // Apply the video as a texture
        screen.material = new THREE.MeshBasicMaterial({
          map: new THREE.VideoTexture(video),
        });
      }
    }
  }, [gltf.scene, video]);

  return <primitive object={gltf.scene} />;
}

export function Model(props) {
  const groupRef = useRef();
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    // Trigger the flip animation after a 1-second delay
    const timer = setTimeout(() => setFlipped(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  useFrame(() => {
    if (groupRef.current) {
      // Animate the rotation from PI (back) to 0 (front)
      const targetRotation = flipped ? 0 : Math.PI;
      // Using Y-axis for a horizontal flip, which feels natural for a tablet
      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        targetRotation,
        0.05
      );
    }
  });

  return (
    // Start with the back of the tablet facing the camera (rotated 180 degrees on Y-axis)
    <group ref={groupRef} {...props} dispose={null} rotation-y={Math.PI}>
      <IPad />
    </group>
  );
}
