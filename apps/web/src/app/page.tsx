"use client";

import { useState } from "react";
import { checkBackendHealth } from "@/lib/api";

export default function Home() {
  const [status, setStatus] = useState("Not checked");
  const [loading, setLoading] = useState(false);

  async function handleCheckBackend() {
    try {
      setLoading(true);
      setStatus("Checking...");

      const result = await checkBackendHealth();

      setStatus(`Backend status: ${result.status}`);
    } catch (error) {
      setStatus("Could not connect to the backend");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-bold">RepoLens AI</h1>

      <p>Frontend - Backend integration test</p>

      <button
        onClick={handleCheckBackend}
        disabled={loading}
        className="rounded-lg bg-black px-5 py-3 text-white disabled:opacity-50"
      >
        {loading ? "Checking..." : "Check backend connection"}
      </button>

      <p>{status}</p>
    </main>
  );
}
