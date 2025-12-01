// src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';


import PromptDiff from './pages/PromptDiff';

function App() {
  return (
    // If you used BrowserRouter in main.jsx, you only need Routes here.
    // If you haven't, wrap this entire return in <BrowserRouter>
    <Routes>
      <Route path="/" element={<PromptDiff />} />      {/* 👈 Home uses useNavigate() */}
     
   
    </Routes>
  );
}

export default App;