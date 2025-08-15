"use client";

import React from "react";
import { motion } from "framer-motion";

const RequestDemoModal = ({ onClose }: { onClose: () => void }) => {
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
        <h2 className="text-3xl font-bold font-unna text-yellow-400 mb-6 text-shadow-lg">
          Request a Demo
        </h2>
        <form>
          <div className="mb-4">
            <label htmlFor="name" className="block text-yellow-50/80 mb-2">
              Name
            </label>
            <input
              type="text"
              id="name"
              className="w-full p-2 rounded bg-black/30 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-yellow-400 transition-shadow"
            />
          </div>
          <div className="mb-4">
            <label htmlFor="email" className="block text-yellow-50/80 mb-2">
              Email
            </label>
            <input
              type="email"
              id="email"
              className="w-full p-2 rounded bg-black/30 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-yellow-400 transition-shadow"
            />
          </div>
          <div className="flex justify-end space-x-4 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-black/40 text-yellow-50/90 rounded-full transition-colors hover:bg-black/60"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-primary text-primary-foreground font-semibold rounded-full transition-all duration-300 hover:bg-yellow-500 hover:text-black focus:outline-none focus:ring-2 focus:ring-yellow-400"
            >
              Submit
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
};

export default RequestDemoModal;
