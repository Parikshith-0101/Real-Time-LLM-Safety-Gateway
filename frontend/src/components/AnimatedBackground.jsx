// src/components/AnimatedBackground.jsx
import React from 'react';
import './AnimatedBackground.css'; // Make sure this path is correct

const AnimatedBackground = () => {
  return (
    <div className="animated-background-container">
      {/* Update these class names from 'bg-layer' to 'neuron-particle' */}
      <div className="neuron-particle layer-1"></div>
      <div className="neuron-particle layer-2"></div>
      <div className="neuron-particle layer-3"></div>
      <div className="neuron-particle layer-4"></div>
      <div className="neuron-particle layer-5"></div>
      <div className="neuron-particle layer-6"></div>
      <div className="neuron-particle layer-7"></div>
      <div className="neuron-particle layer-8"></div>
    </div>
  );
};

export default AnimatedBackground;