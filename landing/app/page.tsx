"use client";
import React, { useState } from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";
import * as THREE from "three";
import Carousel from "@/components/canvas/Carousel";
import RequestDemoModal from "@/components/RequestDemoModal";
import InfoModal from "@/components/InfoModal";

// Consolidated items array, this is now the single source of truth.
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
    rotation: [0, (120 * Math.PI) / 180, 0] as [number, number, number],
    color: "#6c757d", // Muted grey
    path: undefined as string | undefined,
    label: "Request Demo",
    modelUrl: "/models-contact/contact.glb",
    action: "requestDemo" as string | undefined,
  },
  {
    position: new THREE.Vector3(0, 0, 0),
    rotation: [0, (240 * Math.PI) / 180, 0] as [number, number, number],
    color: "#f0ad4e", // Warmer orange/yellow
    path: undefined as string | undefined,
    label: "Info",
    modelUrl: "/models-info/info.glb",
    action: "info" as string | undefined,
  },
];

const LandingPage = () => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [showInfoModal, setShowInfoModal] = useState(false);

  const handleCenterClick = () => {
    const item = items[selectedIndex];
    if (item.path) {
      window.location.href = item.path;
    } else if (item.action === "requestDemo") {
      setShowDemoModal(true);
    } else if (item.action === "info") {
      setShowInfoModal(true);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex flex-col overflow-hidden">
      {/* Modals are rendered here at the top level */}
      {showDemoModal && (
        <RequestDemoModal onClose={() => setShowDemoModal(false)} />
      )}
      {showInfoModal && <InfoModal onClose={() => setShowInfoModal(false)} />}

      <div className="relative z-10 flex-grow">
        {/* Header Area */}
        <div className="fixed top-0 left-0 right-0 z-20 p-4 pointer-events-none">
          {/* Logo */}
          <motion.a
            href="#"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="absolute top-4 left-6 flex items-center space-x-3 pointer-events-auto"
          >
            <Shield className="w-8 h-8 text-primary" />
            <h1 className="text-xl font-bold tracking-wider">SentinelAI</h1>
          </motion.a>

          {/* Centered navigation */}
          <div className="flex items-center justify-center">
            <div className="flex items-center justify-center bg-black/20 backdrop-blur-md rounded-full p-1 space-x-1 glass pointer-events-auto">
              {items.map((item, index) => (
                <button
                  key={index}
                  onClick={() => {
                    // Clicking top nav button just selects the item in the carousel
                    setSelectedIndex(index);
                  }}
                  className={`px-6 py-2 text-base rounded-full transition-all duration-300 focus:outline-none ${
                    selectedIndex === index
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-white/70 hover:text-white"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main 3D Scene */}
        <main className="absolute inset-0 z-0">
          <Carousel
            items={items}
            selectedIndex={selectedIndex}
            setSelectedIndex={setSelectedIndex}
            onCenterClick={handleCenterClick}
          />
        </main>
      </div>
    </div>
  );
};

export default LandingPage;
