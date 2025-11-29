import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import AnimatedBackground from "../components/AnimatedBackground";

export default function Home() {
  const navigate = useNavigate();

  // ---------------- SIDEBAR + CHAT HISTORY ----------------
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem("chatHistory");
    return saved ? JSON.parse(saved) : [];
  });

  const [currentChatId, setCurrentChatId] = useState(null);

  // ---------------- CHAT STATES ----------------
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const chatEndRef = useRef(null);

  const handleLoginClick = () => navigate("/login");

  const scrollToBottom = () => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  // ---------------- BACKEND SANITIZE API ----------------
  const BACKEND =
    import.meta.env.VITE_REACT_APP_API_URL || "http://localhost:5000";
  const api = axios.create({
    baseURL: BACKEND,
    timeout: 10000,
    headers: { "Content-Type": "application/json" },
  });

  function makeCorrelationId() {
    try {
      if (crypto?.randomUUID) return crypto.randomUUID();
    } catch {}
    return "cid-" + Math.random().toString(36).slice(2, 10);
  }

  async function sendToBackend(promptText) {
    const correlationId = makeCorrelationId();

    try {
      const resp = await api.post(
        "/api/sanitize",
        { prompt: promptText },
        {
          headers: {
            "X-Correlation-ID": correlationId,
          },
        }
      );

      return resp.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.response)
          return {
            error: `Server returned ${err.response.status}: ${
              typeof err.response.data === "string"
                ? err.response.data
                : JSON.stringify(err.response.data)
            }`,
          };
        else if (err.request)
          return { error: "No response from server. Check backend." };
        return { error: err.message };
      }
      return { error: String(err) };
    }
  }

  // ---------------- SEND CHAT MESSAGE ----------------
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    const updatedUserMessages = [...messages, userMsg];

    setMessages(updatedUserMessages);

    const promptText = input;
    setInput("");
    scrollToBottom();

    // 🔥 SEND TO BACKEND INSTEAD OF MOCK API
    const response = await sendToBackend(promptText);

    const botMsg =
      response.error
        ? { sender: "bot", text: `❌ ${response.error}` }
        : {
            sender: "bot",
            text: `Decision: ${response.decision}\nScore: ${
              response.score
            }\nSanitized: ${response.sanitizedPrompt || "None"}`,
          };

    const finalMessages = [...updatedUserMessages, botMsg];
    setMessages(finalMessages);
    scrollToBottom();

    // ------------ Save Chat History ------------
    let history = [...chatHistory];
    const idx = history.findIndex((c) => c.id === currentChatId);

    if (idx === -1) {
      const newChat = {
        id: Date.now(),
        title: userMsg.text.slice(0, 20) || "New Chat",
        messages: finalMessages,
      };
      history.push(newChat);
      setCurrentChatId(newChat.id);
    } else {
      history[idx].messages = finalMessages;
    }

    setChatHistory(history);
    localStorage.setItem("chatHistory", JSON.stringify(history));
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full min-h-screen text-white overflow-x-hidden font-sans relative"
      style={{ backgroundColor: "transparent" }}>

      {/* Background */}
      <AnimatedBackground />

      {/* =================== SIDEBAR =================== */}
      <div
        className={`fixed top-0 left-0 h-full w-64 bg-black/90 backdrop-blur-md border-r border-teal-500/40
        transform ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        transition-transform duration-300 z-50 flex flex-col`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-teal-300 text-xl font-semibold">Chats</h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="text-gray-400 hover:text-white"
          >
            ✖
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={() => {
            const id = Date.now();
            const newChat = { id, messages: [], title: "New Chat" };
            const updatedHistory = [...chatHistory, newChat];

            setChatHistory(updatedHistory);
            setCurrentChatId(id);
            localStorage.setItem("chatHistory", JSON.stringify(updatedHistory));

            setMessages([]);
            setSidebarOpen(false);
          }}
          className="m-4 py-2 bg-teal-600 rounded-lg text-white hover:bg-teal-500"
        >
          + New Chat
        </button>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto px-4 space-y-2">
          {chatHistory.map((chat) => (
            <div
              key={chat.id}
              onClick={() => {
                setCurrentChatId(chat.id);
                setMessages(chat.messages);
                setSidebarOpen(false);
              }}
              className={`p-3 rounded-xl cursor-pointer border border-gray-700 
              hover:bg-gray-800 ${
                currentChatId === chat.id ? "bg-gray-800" : ""
              }`}
            >
              {chat.title}
            </div>
          ))}
        </div>
      </div>
      {/* =============== END SIDEBAR =============== */}

      {/* ================= NAVBAR ================= */}
      <header className="relative z-10 w-full h-[10vh] flex items-center justify-between px-10 border-b border-teal-500/60">

        {/* LEFT: SYMBOL + TITLE */}
        <div className="flex items-center space-x-4">

          {/* Sidebar Toggle Icon */}
          <div onClick={() => setSidebarOpen(true)}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-9 w-9 text-teal-400 cursor-pointer hover:scale-110 transition"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M12 2l7 4v6c0 5-3 9-7 10-4-1-7-5-7-10V6l7-4z"
              />
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.5 12l2 2 4-4"
              />
            </svg>
          </div>

          <h1 className="text-3xl font-extrabold text-teal-300">
            LLM Safety Gateway
          </h1>
        </div>

        {/* RIGHT: LOGIN BUTTON */}
        <button
          onClick={handleLoginClick}
          className="px-6 py-2 bg-gray-900 border border-gray-700 rounded-full hover:bg-gray-800 transition"
        >
          Login
        </button>
      </header>

      {/* ================= HERO SECTION ================= */}
      <div className="relative z-10 w-full flex flex-col items-center mt-8">
        <h1 className="text-5xl font-extrabold text-center">
          <span className="text-teal-300">Check.</span>
          <span className="text-blue-400 ml-2">Clean.</span>
          <span className="text-green-400 ml-2">Create.</span>
        </h1>

        <p className="text-gray-400 mt-2">
          Secure your prompts through AI-powered safety validation
        </p>

        <div className="overflow-hidden w-full mt-5">
          <p className="whitespace-nowrap animate-marquee text-teal-300 font-semibold text-lg">
            Check your prompt here • Check your prompt here • Check your prompt here •
          </p>
        </div>

        <div className="w-3/4 mt-6 border-t border-teal-500"></div>
      </div>

      {/* ================= CHAT BOX ================= */}
      <div className="relative z-10 flex justify-center mt-10 px-4 w-full">
        <div className="w-full max-w-5xl rounded-3xl p-[3px] bg-gradient-to-r from-teal-400 via-cyan-500 to-teal-400 animate-glowShadow">

          {/* Chat Area */}
          <div className="bg-black rounded-3xl p-6 flex flex-col h-[60vh]">

            <div className="flex items-center justify-between mb-3">
              <h2 className="text-2xl font-semibold text-teal-300">Prompt Safety Check</h2>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`w-full flex ${
                    msg.sender === "user"
                      ? "justify-start"
                      : "justify-end"
                  }`}
                >
                  <div
                    className={`p-3 rounded-xl max-w-[70%] ${
                      msg.sender === "user"
                        ? "bg-blue-700"
                        : "bg-gray-800"
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}

              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="mt-4 flex items-center space-x-3">
              <input
                type="text"
                value={input}
                onKeyDown={handleKeyDown}
                onChange={(e) => setInput(e.target.value)}
                className="flex-1 p-4 rounded-xl bg-gray-900 border border-gray-700 
                focus:border-teal-400 outline-none text-white"
                placeholder="Type your message..."
              />

              <button
                onClick={handleSend}
                className="px-6 py-3 bg-teal-600 rounded-xl hover:bg-teal-500 transition-all"
              >
                Send
              </button>
            </div>

          </div>
        </div>
      </div>

    </div>
  );
}
