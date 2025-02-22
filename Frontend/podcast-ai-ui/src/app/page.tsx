"use client";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      <h1 className="text-4xl font-bold mb-6">Welcome to Podcast.ai</h1>
      <p className="mb-6">Your AI-powered podcasting experience starts here!</p>
      <div className="space-x-4">
        <button
          onClick={() => router.push("/login")}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Login
        </button>
        <button
          onClick={() => router.push("/signup")}
          className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
        >
          Signup
        </button>
      </div>
    </div>
  );
}
