// src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Login from './pages/Login';

function App() {
  return (
    // If you used BrowserRouter in main.jsx, you only need Routes here.
    // If you haven't, wrap this entire return in <BrowserRouter>
    <Routes>
      <Route path="/" element={<Home />} />      {/* 👈 Home uses useNavigate() */}
      <Route path="/login" element={<Login />} />
    </Routes>
  );
}

export default App;