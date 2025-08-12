"use client";

import * as THREE from "three";
import React, {
  useRef,
  useState,
  useEffect,
  Suspense,
  Dispatch,
  SetStateAction,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  OrbitControls,
  Preload,
  useProgress,
  useGLTF,
} from "@react-three/drei";
import { Group } from "three";
import RequestDemoModal from "../RequestDemoModal";
import InfoModal from "../InfoModal";

const Model = ({ url, ...props }: { url: string; [key: string]: any }) => {
  const { scene } = useGLTF(url);
  return <primitive object={scene} {...props} />;
};

// Fallback component for when GLTF fails to load
const ModelFallback = (props: any) => {
  return (
    <mesh {...props}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="orange" />
    </mesh>
  );
};

const items = [
  {
    position: new THREE.Vector3(0, 0, 0),
    path: "/dashboard/",
    label: "Dashboard",
    modelUrl: "/ai_brain.glb",
    action: undefined as string | undefined,
  },
];

const CarouselContent = ({ selectedIndex }: { selectedIndex: number }) => {
  const groupRef = useRef<Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      const targetRotation = -selectedIndex * ((Math.PI * 2) / items.length);
      let currentRotation = groupRef.current.rotation.y;

      const twoPi = Math.PI * 2;
      let diff = (targetRotation - currentRotation) % twoPi;
      if (diff > Math.PI) {
        diff -= twoPi;
      } else if (diff < -Math.PI) {
        diff += twoPi;
      }

      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        groupRef.current.rotation.y + diff,
        0.1
      );
    }
    state.camera.position.lerp(new THREE.Vector3(0, 2, 8), 0.1);
    state.camera.lookAt(0, 0, 0);
  });

  return (
    <group ref={groupRef}>
      {items.map((item, index) => (
        <group key={index} position={item.position}>
          <Suspense fallback={<ModelFallback scale={1.5} />}>
            <Model url={item.modelUrl} scale={1.5} />
          </Suspense>
        </group>
      ))}
    </group>
  );
};

const Loader = ({ onLoaded }: { onLoaded: () => void }) => {
  const { progress } = useProgress();
  useEffect(() => {
    if (progress === 100) {
      setTimeout(() => onLoaded(), 500);
    }
  }, [progress, onLoaded]);
  return null;
};

const LoadingScreen = () => {
  return (
    <div className="absolute inset-0 bg-background z-50 flex items-center justify-center transition-opacity duration-1000">
      <div className="text-center">
        <div className="w-24 h-24 border-4 border-primary border-t-transparent rounded-full animate-spin-slow mx-auto mb-4"></div>
        <p className="text-white text-2xl font-unna">
          Initializing SentinelAI Interface...
        </p>
      </div>
    </div>
  );
};

// This is now the ONLY scrolling text component.
// Its font size is doubled using Tailwind's arbitrary values (`text-[8rem]`).
const ScrollingText = () => {
  const textContent =
    "SENTINEL AI: TRANSFORMING CHAOS INTO CLARITY ◆ REAL-TIME INTELLIGENCE FOR FIRST RESPONDERS ◆ SAVING LIVES WITH DATA-DRIVEN INSIGHTS ◆";
  return (
    <div className="absolute bottom-10 left-0 w-full overflow-hidden pointer-events-none">
      <div className="text-white/80 font-unna text-[8rem] leading-none animate-marquee whitespace-nowrap text-glow">
        <span>{textContent}</span>
        <span>{textContent}</span>
      </div>
    </div>
  );
};

const Carousel = ({
  selectedIndex,
  setSelectedIndex,
}: {
  selectedIndex: number;
  setSelectedIndex: Dispatch<SetStateAction<number>>;
}) => {
  const [loading, setLoading] = useState(true);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [showInfoModal, setShowInfoModal] = useState(false);
  const actionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (actionTimeoutRef.current) {
      clearTimeout(actionTimeoutRef.current);
    }
    actionTimeoutRef.current = setTimeout(() => {
      const item = items[selectedIndex];
      if (item.path) {
        window.location.href = item.path;
      } else if (item.action === "requestDemo") {
        setShowDemoModal(true);
      } else if (item.action === "info") {
        setShowInfoModal(true);
      }
    }, 800);

    return () => {
      if (actionTimeoutRef.current) {
        clearTimeout(actionTimeoutRef.current);
      }
    };
  }, [selectedIndex]);

  const handleNext = () => {
    setSelectedIndex((prev) => (prev + 1) % items.length);
  };

  const handlePrev = () => {
    setSelectedIndex((prev) => (prev - 1 + items.length) % items.length);
  };

  const handleCanvasClick = (
    event: React.MouseEvent<HTMLDivElement, MouseEvent>
  ) => {
    const { clientX, currentTarget } = event;
    const { left, width } = currentTarget.getBoundingClientRect();
    const clickPosition = clientX - left;

    if (clickPosition < width / 2) {
      handlePrev();
    } else {
      handleNext();
    }
  };

  useEffect(() => {
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const direction = event.deltaY > 0 ? 1 : -1;
      setSelectedIndex(
        (prev) => (prev + direction + items.length) % items.length
      );
    };
    const target = window;
    target.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      target.removeEventListener("wheel", handleWheel);
    };
  }, [setSelectedIndex]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100vh" }}>
      {loading && <LoadingScreen />}
      <div
        style={{
          position: "relative",
          width: "100%",
          height: "100vh",
          opacity: loading ? 0 : 1,
          transition: "opacity 1s ease-in-out",
          cursor: "pointer",
        }}
        onClick={handleCanvasClick}
      >
        <Canvas
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
          }}
        >
          <ambientLight intensity={1.5} />
          <directionalLight position={[0, 10, 5]} intensity={1.5} />
          <Suspense fallback={<Loader onLoaded={() => setLoading(false)} />}>
            <CarouselContent selectedIndex={selectedIndex} />
          </Suspense>
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            enableRotate={false}
          />
          <Preload all />
        </Canvas>
        <ScrollingText />
        {showDemoModal && (
          <RequestDemoModal onClose={() => setShowDemoModal(false)} />
        )}
        {showInfoModal && <InfoModal onClose={() => setShowInfoModal(false)} />}
      </div>
    </div>
  );
};

export default Carousel;
