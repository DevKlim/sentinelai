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
import { Group, SpotLight } from "three";

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
    rotation: [0, 0, 0] as [number, number, number],
    color: "#ffc107", // Honey Yellow for Dashboard
    path: "/dashboard/",
    label: "Dashboard",
    modelUrl: "/models-dashboard/dashboard.glb",
    action: undefined as string | undefined,
  },
  {
    position: new THREE.Vector3(0, 0, 0),
    rotation: [0, (240 * Math.PI) / 180, 0] as [number, number, number], // Rotated 120 deg to face front
    color: "#6c757d", // A muted grey from a common palette
    path: undefined as string | undefined,
    label: "Request Demo",
    modelUrl: "/models-contact/contact.glb",
    action: "requestDemo" as string | undefined,
  },
  {
    position: new THREE.Vector3(0, 0, 0),
    rotation: [0, (120 * Math.PI) / 180, 0] as [number, number, number], // Rotated 240 deg to face front
    color: "#f0ad4e", // A warmer orange/yellow
    path: undefined as string | undefined,
    label: "Info",
    modelUrl: "/models-info/info.glb",
    action: "info" as string | undefined,
  },
];

const CarouselContent = ({ selectedIndex }: { selectedIndex: number }) => {
  const groupRef = useRef<Group>(null);
  const spotLightRef = useRef<SpotLight>(null!);
  const radius = 5; // Distance of items from the center

  // A helper object to act as the spotlight's target
  const spotLightTarget = new THREE.Object3D();

  useFrame((state) => {
    if (groupRef.current) {
      // Calculate the target rotation based on the selected index
      const targetRotation = -selectedIndex * ((Math.PI * 2) / items.length);

      // Smoothly interpolate the rotation of the whole carousel
      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        targetRotation,
        0.1
      );

      // Get the world position of the currently selected item
      const selectedItem = groupRef.current.children[selectedIndex];
      if (selectedItem) {
        const worldPosition = new THREE.Vector3();
        selectedItem.getWorldPosition(worldPosition);

        // Update spotlight target to point at the item
        spotLightTarget.position.copy(worldPosition);
        spotLightRef.current.target = spotLightTarget;

        // Smoothly move the spotlight to be above the item
        spotLightRef.current.position.lerp(
          new THREE.Vector3(worldPosition.x, 5, worldPosition.z),
          0.1
        );
      }
    }
    // Smoothly move camera
    state.camera.position.lerp(new THREE.Vector3(0, 0.75, 10), 0.05);
    state.camera.lookAt(0, 0, 0);
  });

  return (
    <>
      {/* Add the spotlight target to the scene so its matrix gets updated */}
      <primitive object={spotLightTarget} />
      <spotLight
        ref={spotLightRef}
        position={[0, 5, radius]} // Initial position
        angle={Math.PI / 4}
        penumbra={0.25}
        intensity={15} // Bright to make colors pop
        castShadow
        color="#fff5d6" // Light honey yellow, from palette
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

const LoadingScreen = () => {
  return (
    <div className="absolute inset-0 bg-background z-50 flex items-center justify-center transition-opacity duration-1000">
      <div className="text-center">
        <div className="w-24 h-24 border-4 border-primary border-t-transparent rounded-full animate-spin-slow mx-auto mb-4"></div>
        <p className="text-foreground text-2xl font-unna">
          Initializing SentinelAI Interface...
        </p>
      </div>
    </div>
  );
};

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
  selectedIndex,
  setSelectedIndex,
}: {
  selectedIndex: number;
  setSelectedIndex: Dispatch<SetStateAction<number>>;
}) => {
  const [loading, setLoading] = useState(true);

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
            <ModelFallback />
          </Suspense>
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            enableRotate={false}
          />
          <Preload all />
        </Canvas>
        <ScrollingText />
      </div>
    </div>
  );
};

export default Carousel;
