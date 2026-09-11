"use client";

import { FormEvent, useState } from "react";

const API_BASE = "http://127.0.0.1:8001";

const demoUsers = [
  { username: "dr.mehta", password: "doctor", role: "doctor" },
  { username: "nurse.priya", password: "nurse", role: "nurse" },
  { username: "billing.ravi", password: "billing_executive", role: "billing_executive" },
  { username: "tech.anand", password: "technician", role: "technician" },
  { username: "admin.sys", password: "admin", role: "admin" },
];

const roleCollections: Record<string, string[]> = {
  doctor: ["general", "clinical", "nursing"],
  nurse: ["general", "nursing"],
  billing_executive: ["general", "billing"],
  technician: ["general", "equipment"],
  admin: ["general", "clinical", "nursing", "billing", "equipment"],
};

export default function Home() {
  const [username, setUsername] = useState(demoUsers[0].username);
  const [password, setPassword] = useState(demoUsers[0].password);
  const [role, setRole] = useState<string>("doctor");
  const [token, setToken] = useState<string>("");
  const [question, setQuestion] = useState("What are the standard treatment protocols for sepsis?");
  const [answer, setAnswer] = useState<string>("");
  const [sources, setSources] = useState<any[]>([]);
  const [retrievalType, setRetrievalType] = useState<string>("");
  const [loginError, setLoginError] = useState<string>("");

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setLoginError(data.detail || "Invalid username or password.");
        return;
      }
      setLoginError("");
      setRole(data.role);
      setToken(data.token);
    } catch (error) {
      setLoginError("Unable to reach the backend server.");
    }
  }

  async function handleChat(e: FormEvent) {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, role }),
      });
      const data = await response.json();
      setAnswer(data.answer || "No answer");
      setSources(data.sources || []);
      setRetrievalType(data.retrieval_type || "hybrid_rag");
    } catch (error) {
      setAnswer("The backend is unavailable. Please check the server.");
      setSources([]);
      setRetrievalType("hybrid_rag");
    }
  }

  return (
    <main className="page-shell">
      <aside className="sidebar">
        <h1>MediBot</h1>
        <p className="subtitle">Role-based clinical assistant</p>

        <form onSubmit={handleLogin} className="form-box">
          <label>
            Username
            <select value={username} onChange={(e) => setUsername(e.target.value)}>
              {demoUsers.map((user) => (
                <option key={user.username} value={user.username}>{user.username}</option>
              ))}
            </select>
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button type="submit">Login</button>
          {loginError ? <small className="error">{loginError}</small> : null}
        </form>

        <div className="role-card">
          <span>Active role</span>
          <strong>{role}</strong>
          <div className="badge-row">
            {(roleCollections[role] || []).map((collection) => (
              <span key={collection} className="badge">{collection}</span>
            ))}
          </div>
        </div>
      </aside>

      <section className="chat-panel">
        <div className="response-header">
          <h2>Chat</h2>
          {retrievalType ? <span className="retrieval-type">{retrievalType}</span> : null}
        </div>

        <form onSubmit={handleChat} className="chat-form">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask MediBot about clinical, billing, or equipment policy"
          />
          <button type="submit">Ask MediBot</button>
        </form>

        <div className="answer-box">
          <h3>Answer</h3>
          <p>{answer || "Sign in and ask a question to see the response."}</p>
        </div>

        <div className="source-box">
          <h3>Sources</h3>
          {sources.length ? (
            <ul>
              {sources.map((source, index) => (
                <li key={`${source.source_document}-${index}`}>
                  {source.source_document} — {source.section_title} ({source.collection})
                </li>
              ))}
            </ul>
          ) : (
            <p>No sources yet.</p>
          )}
        </div>

        <div className="token-box">Token: {token || "Not logged in"}</div>
      </section>
    </main>
  );
}
