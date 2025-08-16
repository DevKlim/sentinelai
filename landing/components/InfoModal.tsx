"use client";

import React from "react";
import { motion } from "framer-motion";

const InfoModal = ({ onClose }: { onClose: () => void }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="glass rounded-lg text-white p-8 max-w-md w-full border border-yellow-500/30"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
      >
        <h2 className="text-3xl font-bold font-unna text-yellow-400 mb-4 text-shadow-lg">
          About SentinelAI
        </h2>
        <p className="mb-6 text-yellow-50/90 leading-relaxed">
          SentinelAI ingests raw 911 incident reports and transforms them into
          structured, actionable EIDO data—powering the next generation of
          emergency response.
        </p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2 bg-primary text-primary-foreground font-semibold rounded-full transition-all duration-300 hover:bg-yellow-500 hover:text-black focus:outline-none focus:ring-2 focus:ring-yellow-400"
          >
            Close
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default InfoModal;
