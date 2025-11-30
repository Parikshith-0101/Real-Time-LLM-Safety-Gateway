// src/components/AnimatedBackground.jsx
import React, { useEffect } from 'react';
import './AnimatedBackground.css';

const AnimatedBackground = () => {

  useEffect(() => {
    const canvas = document.getElementById("network-canvas");
    if (!canvas) return; // Prevents null crash

    const ctx = canvas.getContext("2d");

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let particles = [];
    const particleCount = 90;

    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.6;
        this.vy = (Math.random() - 0.5) * 0.6;
        this.radius = 2;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;

        if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
        if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,0.35)";
        ctx.fill();
      }
    }

    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    function connectParticles() {
      for (let a = 0; a < particleCount; a++) {
        for (let b = a; b < particleCount; b++) {
          const dx = particles[a].x - particles[b].x;
          const dy = particles[a].y - particles[b].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 130) {
            ctx.strokeStyle = "rgba(255,255,255,0.08)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(particles[a].x, particles[a].y);
            ctx.lineTo(particles[b].x, particles[b].y);
            ctx.stroke();
          }
        }
      }
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        p.update();
        p.draw();
      });

      connectParticles();
      requestAnimationFrame(animate);
    }

    animate();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);

  }, []);

  return (
    <div className="animated-background-container">

      {/* Existing neon particles */}
      <div className="neuron-particle layer-1"></div>
      <div className="neuron-particle layer-2"></div>
      <div className="neuron-particle layer-3"></div>
      <div className="neuron-particle layer-4"></div>
      <div className="neuron-particle layer-5"></div>
      <div className="neuron-particle layer-6"></div>
      <div className="neuron-particle layer-7"></div>
      <div className="neuron-particle layer-8"></div>

      {/* NEW CONSTELLATION NETWORK */}
      <canvas id="network-canvas"></canvas>

    </div>
  );
};

export default AnimatedBackground;
