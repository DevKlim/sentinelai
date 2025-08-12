
'use client';

import React from 'react';

const RequestDemoModal = ({ onClose }: { onClose: () => void }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-gray-800 p-8 rounded-lg">
        <h2 className="text-white text-2xl mb-4">Request a Demo</h2>
        <form>
          <div className="mb-4">
            <label htmlFor="name" className="block text-white mb-2">Name</label>
            <input type="text" id="name" className="w-full p-2 rounded bg-gray-700 text-white" />
          </div>
          <div className="mb-4">
            <label htmlFor="email" className="block text-white mb-2">Email</label>
            <input type="email" id="email" className="w-full p-2 rounded bg-gray-700 text-white" />
          </div>
          <div className="flex justify-end">
            <button type="button" onClick={onClose} className="text-white mr-4">Cancel</button>
            <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded">Submit</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RequestDemoModal;
