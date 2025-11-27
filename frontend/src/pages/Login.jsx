import React from "react";

export default function Login() {
  return (
    <div className="w-full min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-gray-900 text-white font-sans p-6">
      <div className="w-full max-w-md bg-gray-800/40 backdrop-blur-md p-8 rounded-2xl shadow-xl border border-gray-700 animate-fadeIn">
        <h1 className="text-3xl font-bold text-center mb-6 bg-gradient-to-r from-blue-300 via-purple-400 to-pink-400 bg-clip-text text-transparent">
          Login
        </h1>

        {/* Email Input */}
        <label className="block mb-2 text-blue-300">Email</label>
        <input
          type="email"
          placeholder="Enter your email"
          className="w-full p-3 mb-4 rounded-xl bg-gray-900 border border-gray-700 focus:border-blue-500 focus:outline-none text-white shadow-inner"
        />

        {/* Password Input */}
        <label className="block mb-2 text-blue-300">Password</label>
        <input
          type="password"
          placeholder="Enter your password"
          className="w-full p-3 mb-4 rounded-xl bg-gray-900 border border-gray-700 focus:border-blue-500 focus:outline-none text-white shadow-inner"
        />

        {/* Login Button */}
        <button className="w-full py-3 mt-2 bg-blue-700 hover:bg-blue-600 active:scale-95 transition-all rounded-xl text-white text-lg font-semibold shadow-md">
          Login
        </button>

        {/* Extra Links */}
        <p className="text-center mt-4 text-gray-300 text-sm">
          Don't have an account? <span className="text-blue-400 hover:underline cursor-pointer">Register</span>
        </p>
      </div>
    </div>
  );
}