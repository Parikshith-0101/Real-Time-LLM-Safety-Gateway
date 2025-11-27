import React, { useRef } from "react";
import { useNavigate } from "react-router-dom"; 
// Using the AnimatedBackground component as per your request
import AnimatedBackground from '../components/AnimatedBackground'; 

export default function Home() {
  const navigate = useNavigate();
  // Create a ref to target the main content area for scrolling
  const mainContentRef = useRef(null); 

  const handleLoginClick = () => {
    navigate('/login'); 
  };

  // Function to handle smooth scrolling to the main content
  const handleRecentClick = () => {
    if (mainContentRef.current) {
      mainContentRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'start', 
      });
    }
  };

  return (
    <div className="w-full min-h-screen relative text-white font-sans">
      
      {/* Background Component */}
      <AnimatedBackground /> 

      {/* Header Section (Seamless look) */}
      <header className="relative z-10 w-full h-[10vh] flex items-center justify-between px-10 shadow-xl animate-fadeIn
        bg-gray-800/40 backdrop-blur-md">
        
        <h1 className="text-4xl font-extrabold tracking-wide text-blue-300 drop-shadow-lg animate-slideDown">
          <span className="bg-gradient-to-r from-blue-300 via-purple-400 to-pink-400 bg-clip-text text-transparent">LLM Safety Gateway</span>
        </h1>
        
        {/* Buttons/Links Container */}
        <div className="flex items-center space-x-6"> 
            
            {/* The Recent Scroll Link: small font, no button styling */}
            <span
              className="text-sm font-medium text-gray-300 hover:text-blue-400 transition duration-200 cursor-pointer animate-slideDown"
              onClick={handleRecentClick} // Triggers the smooth scroll
            >
              Recent
            </span>
            
            {/* The Login / Sign up Button */}
            <button
              className="p-3 rounded-xl bg-blue-700 hover:bg-blue-600 active:scale-95 transition-all duration-300 text-white text-lg font-semibold shadow-md animate-slideDown"
              onClick={handleLoginClick} // Navigates to the login page
            >
              Login / Sign up
            </button>

        </div>
      </header>
      
      {/* Body Section - Target for the scroll action */}
      <main ref={mainContentRef} className="relative z-10 w-full h-3/4 p-6 flex justify-center items-start">
        <div className="w-full max-w-2xl bg-gray-800/40 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-gray-700 mt-10 animate-fadeIn">
          <h2 className="text-2xl font-semibold mb-4 text-blue-300">Enter your prompt</h2>

          <textarea
            placeholder="Type your prompt here..."
            className="w-full h-40 p-4 rounded-xl bg-gray-900 border border-gray-700 focus:border-blue-500 focus:outline-none text-white resize-none shadow-inner"></textarea>

          <button className="w-full mt-4 py-3 bg-blue-700 hover:bg-blue-600 active:scale-95 transition-all rounded-xl text-white text-lg font-semibold shadow-md">
            Sanitize Prompt
          </button>
        </div>
      </main>
    </div>
  );
}