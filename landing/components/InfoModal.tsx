
'use client';

import React from 'react';

const InfoModal = ({ onClose }: { onClose: () => void }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-gray-800 p-8 rounded-lg">
        <h2 className="text-white text-2xl mb-4">About SentinelAI</h2>
        <p className="text-white mb-4">
          SentinelAI ingests raw 911 incident reports and transforms them into structured, actionable EIDO data—powering the next generation of emergency response.
        </p>
        <div className="flex justify-end">
          <button type="button" onClick={onClose} className="text-white">Close</button>
        </div>
      </div>
    </div>
  );
};

export default InfoModal;
