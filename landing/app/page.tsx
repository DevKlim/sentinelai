"use client";
import React, { useState } from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";
import Carousel from "@/components/canvas/Carousel";
import RequestDemoModal from "@/components/RequestDemoModal";
import InfoModal from "@/components/InfoModal";

// These items correspond to the 3D models and their associated actions/links.
const items = [
  { path: "/dashboard/", label: "Dashboard" },
  { action: "requestDemo", label: "Request Demo" },
  { action: "info", label: "Info" },
];

const LandingPage = () => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [showInfoModal, setShowInfoModal] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex flex-col overflow-x-hidden">
      <div className="relative z-10">
        {/* This div acts as the new header area, positioned at the top. */}
        <div className="fixed top-0 left-0 right-0 z-50 p-4">
          {/* Logo and name remain in the top-left corner */}
          <motion.a
            href="#"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="absolute top-4 left-6 flex items-center space-x-3"
          >
            <Shield className="w-8 h-8 text-primary" />
            <h1 className="text-xl font-bold tracking-wider">SentinelAI</h1>
          </motion.a>

          {/* Centered navigation for 3D object selection, where the header used to be. */}
          <div className="flex items-center justify-center">
            <div className="flex items-center justify-center bg-black/20 backdrop-blur-md rounded-full p-1 space-x-1 glass">
              {items.map((item, index) => (
                <button
                  key={index}
                  onClick={() => {
                    if (item.path) {
                      window.location.href = item.path;
                    } else {
                      setSelectedIndex(index);
                      if (item.action === "requestDemo") {
                        setShowDemoModal(true);
                      } else if (item.action === "info") {
                        setShowInfoModal(true);
                      }
                    }
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

        <main className="flex-grow">
          <section className="relative w-full h-screen flex items-center justify-center text-center">
            <div className="absolute inset-0 z-0">
              {/* The Carousel component now receives the state to control which model is shown */}
              <Carousel
                selectedIndex={selectedIndex}
                setSelectedIndex={setSelectedIndex}
              />
            </div>
          </section>
        </main>
      </div>
      {showDemoModal && (
        <RequestDemoModal onClose={() => setShowDemoModal(false)} />
      )}
      {showInfoModal && <InfoModal onClose={() => setShowInfoModal(false)} />}
    </div>
  );
};

export default LandingPage;
