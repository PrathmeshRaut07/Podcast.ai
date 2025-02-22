"use client";
import { useRouter } from "next/navigation";

export default function Signup() {
  const router = useRouter();

  const handleSignup = () => {
    // Dummy auth, replace with actual signup logic
    router.push("/podcast");
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      <h2 className="text-3xl font-bold mb-4">Signup</h2>
      <input
        type="text"
        placeholder="Full Name"
        className="mb-2 p-2 border border-gray-700 rounded bg-gray-800"
      />
      <input
        type="email"
        placeholder="Email"
        className="mb-2 p-2 border border-gray-700 rounded bg-gray-800"
      />
      <input
        type="password"
        placeholder="Password"
        className="mb-4 p-2 border border-gray-700 rounded bg-gray-800"
      />
      <button onClick={handleSignup} className="px-6 py-2 bg-green-500 text-white rounded-lg">
        Signup
      </button>
    </div>
  );
}
