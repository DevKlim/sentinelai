"use client";

import * as THREE from "three";
import React, {
  useRef,
  useEffect,
  Suspense,
  Dispatch,
  SetStateAction,
  useState,
  useCallback,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import {
  OrbitControls,
  Preload,
  useProgress,
  useGLTF,
} from "@react-three/drei";
import { Group, SpotLight } from "three";
import { ChevronLeft, ChevronRight } from "lucide-react";

// Type definition for a carousel item
interface CarouselItem {
  position: THREE.Vector3;
  rotation: [number, number, number];
  color: string;
  path?: string;
  label: string;
  modelUrl: string;
  action?: string;
}

const Model = ({
  url,
  color,
  ...props
}: {
  url: string;
  color: string;
  [key: string]: any;
}) => {
  const { scene } = useGLTF(url);
  useEffect(() => {
    const material = new THREE.MeshStandardMaterial({
      color: color,
      roughness: 0.4,
      metalness: 0.5,
    });
    if (scene) {
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.material = material;
        }
      });
    }
  }, [scene, color]);
  return <primitive object={scene} {...props} />;
};

const CarouselContent = ({
  items,
  rotationCounter,
}: {
  items: CarouselItem[];
  rotationCounter: React.MutableRefObject<number>;
}) => {
  const groupRef = useRef<Group>(null);
  const spotLightRef = useRef<SpotLight>(null!);
  const radius = 5;

  const spotLightTarget = React.useMemo(() => new THREE.Object3D(), []);

  useFrame((state) => {
    if (groupRef.current) {
      const targetRotation =
        -rotationCounter.current * ((Math.PI * 2) / items.length);

      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        targetRotation,
        0.1
      );

      const selectedIndex =
        ((rotationCounter.current % items.length) + items.length) %
        items.length;
      const selectedItem = groupRef.current.children[selectedIndex];

      if (selectedItem) {
        const worldPosition = new THREE.Vector3();
        selectedItem.getWorldPosition(worldPosition);

        spotLightTarget.position.copy(worldPosition);
        if (spotLightRef.current.target !== spotLightTarget) {
          spotLightRef.current.target = spotLightTarget;
        }

        spotLightRef.current.position.lerp(
          new THREE.Vector3(worldPosition.x, 5, worldPosition.z),
          0.1
        );
      }
    }
    state.camera.position.lerp(new THREE.Vector3(0, 0.75, 10), 0.05);
    state.camera.lookAt(0, 0, 0);
  });

  return (
    <>
      <primitive object={spotLightTarget} />
      <spotLight
        ref={spotLightRef}
        position={[0, 5, radius]}
        angle={Math.PI / 4}
        penumbra={0.25}
        intensity={15}
        castShadow
        color="#fff5d6"
      />
      <group ref={groupRef}>
        {items.map((item, index) => {
          const angle = index * ((Math.PI * 2) / items.length);
          const x = Math.sin(angle) * radius;
          const z = Math.cos(angle) * radius;

          return (
            <group key={index} position={[x, 0, z]} rotation={[0, -angle, 0]}>
              <Model
                url={item.modelUrl}
                color={item.color}
                scale={1.5}
                rotation={item.rotation}
              />
            </group>
          );
        })}
      </group>
    </>
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

const LoadingScreen = () => (
  <div className="absolute inset-0 bg-background z-50 flex items-center justify-center">
    <div className="text-center">
      <div className="w-24 h-24 border-4 border-primary border-t-transparent rounded-full animate-spin-slow mx-auto mb-4"></div>
      <p className="text-foreground text-2xl font-unna">
        Initializing SentinelAI Interface...
      </p>
    </div>
  </div>
);

const ScrollingText = () => {
  const textContent =
    "SENTINEL AI: TRANSFORMING CHAOS INTO CLARITY ◆ REAL-TIME INTELLIGENCE FOR FIRST RESPONDERS ◆ SAVING LIVES WITH DATA-DRIVEN INSIGHTS ◆";
  return (
    <div className="absolute bottom-10 left-0 w-full overflow-hidden pointer-events-none">
      <div className="text-black/80 font-unna text-[8rem] leading-none animate-marquee whitespace-nowrap">
        <span>{textContent}</span>
        <span>{textContent}</span>
      </div>
    </div>
  );
};

const Carousel = ({
  items,
  selectedIndex,
  setSelectedIndex,
  onCenterClick,
}: {
  items: CarouselItem[];
  selectedIndex: number;
  setSelectedIndex: Dispatch<SetStateAction<number>>;
  onCenterClick: () => void;
}) => {
  const [loading, setLoading] = useState(true);
  const rotationCounterRef = useRef(selectedIndex);
  const prevIndexRef = useRef(selectedIndex);

  useEffect(() => {
    const numItems = items.length;
    const current = selectedIndex;
    const prev = prevIndexRef.current;
    if (current === prev) return;

    let diff = current - prev;
    if (diff > numItems / 2) diff -= numItems;
    if (diff < -numItems / 2) diff += numItems;

    rotationCounterRef.current += diff;
    prevIndexRef.current = current;
  }, [selectedIndex, items.length]);

  const handleNext = useCallback(() => {
    rotationCounterRef.current++;
    const newIndex =
      ((rotationCounterRef.current % items.length) + items.length) %
      items.length;
    setSelectedIndex(newIndex);
  }, [items.length, setSelectedIndex]);

  const handlePrev = useCallback(() => {
    rotationCounterRef.current--;
    const newIndex =
      ((rotationCounterRef.current % items.length) + items.length) %
      items.length;
    setSelectedIndex(newIndex);
  }, [items.length, setSelectedIndex]);

  useEffect(() => {
    let scrollTimeout: NodeJS.Timeout;

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      clearTimeout(scrollTimeout);

      scrollTimeout = setTimeout(() => {
        if (event.deltaY > 0) {
          handleNext();
        } else {
          handlePrev();
        }
      }, 50); // Debounce scroll events
    };

    const target = window;
    target.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      target.removeEventListener("wheel", handleWheel);
      clearTimeout(scrollTimeout);
    };
  }, [handleNext, handlePrev]);

  return (
    <div className="relative w-full h-full">
      {loading && <LoadingScreen />}
      <div
        className="relative w-full h-full transition-opacity duration-1000"
        style={{ opacity: loading ? 0 : 1 }}
      >
        <Canvas
          style={{ position: "absolute", top: 0, left: 0, zIndex: 0 }}
          shadows
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[0, 10, 5]} intensity={1} castShadow />
          <Suspense fallback={<Loader onLoaded={() => setLoading(false)} />}>
            <CarouselContent
              items={items}
              rotationCounter={rotationCounterRef}
            />
          </Suspense>
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            enableRotate={false}
          />
          <Preload all />
        </Canvas>
        <ScrollingText />

        {/* Click Overlays */}
        <div
          className="group absolute left-0 top-0 h-full w-[30%] z-10 cursor-pointer flex items-center justify-start p-8 bg-gradient-to-r from-black/40 to-transparent"
          onClick={handlePrev}
        >
          <ChevronLeft className="w-16 h-16 text-white opacity-0 group-hover:opacity-70 transition-opacity duration-300" />
        </div>
        <div
          className="absolute left-[30%] top-0 h-full w-[40%] z-10 cursor-pointer"
          onClick={onCenterClick}
        />
        <div
          className="group absolute right-0 top-0 h-full w-[30%] z-10 cursor-pointer flex items-center justify-end p-8 bg-gradient-to-l from-black/40 to-transparent"
          onClick={handleNext}
        >
          <ChevronRight className="w-16 h-16 text-white opacity-0 group-hover:opacity-70 transition-opacity duration-300" />
        </div>
      </div>
    </div>
  );
};

export default Carousel;
