"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Podcast {
  id: string;
  user_email: string;
  title: string;
  description: string;
  topic: string;
  audio_base64?: string;
  created_at: string;
  duration_seconds: number;
}

export default function PodcastDashboard() {
  const router = useRouter();
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form states for creating a podcast
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [topic, setTopic] = useState<string>("");
  const [isCreating, setIsCreating] = useState<boolean>(false);

  // State for audio playback
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playingPodcastId, setPlayingPodcastId] = useState<string | null>(null);

  // Retrieve token from localStorage
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Redirect to login if token is missing
  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  // Fetch user podcasts from FastAPI
  const fetchPodcasts = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/podcasts/", {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error("Failed to fetch podcasts");
      }
      const data = await res.json();
      setPodcasts(data);
    } catch (err: any) {
      setError(err.message || "Error fetching podcasts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchPodcasts();
    }
  }, [token]);

  // Create a new podcast with loader indicator
  const handleCreatePodcast = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/podcasts/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ title, description, topic }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      // Refresh podcast list after creation
      fetchPodcasts();
      // Reset form
      setTitle("");
      setDescription("");
      setTopic("");
    } catch (err: any) {
      setError(err.message || "Failed to create podcast");
    } finally {
      setIsCreating(false);
    }
  };

  // Delete a podcast
  const handleDeletePodcast = async (podcastId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/podcasts/${podcastId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      fetchPodcasts();
    } catch (err: any) {
      setError(err.message || "Failed to delete podcast");
    }
  };

  // Play podcast audio: fetch audio as blob and create an Object URL
  const handlePlayPodcast = async (podcastId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/podcasts/${podcastId}/audio`, {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to fetch podcast audio");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setPlayingPodcastId(podcastId);
    } catch (err: any) {
      setError(err.message || "Failed to play podcast");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Navigation/Header */}
      <header className="bg-gray-800 shadow-md py-4 px-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold">Podcast Hub</h1>
        <button
          onClick={() => {
            localStorage.removeItem("token");
            router.push("/login");
          }}
          className="px-4 py-2 bg-red-500 hover:bg-red-600 transition duration-200 rounded"
        >
          Logout
        </button>
      </header>

      <main className="flex-grow container mx-auto p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-600 rounded shadow text-center">
            {error}
          </div>
        )}

        {/* Create Podcast Form */}
        <section className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-2xl font-semibold mb-4 border-b pb-2">Create New Podcast</h2>
          <form onSubmit={handleCreatePodcast} className="space-y-4">
            <div>
              <input
                type="text"
                placeholder="Title"
                className="w-full p-3 rounded bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div>
              <input
                type="text"
                placeholder="Topic"
                className="w-full p-3 rounded bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>
            <div>
              <textarea
                placeholder="Description"
                className="w-full p-3 rounded bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              ></textarea>
            </div>
            <button
              type="submit"
              disabled={isCreating}
              className="w-full py-3 bg-blue-500 hover:bg-blue-600 transition rounded font-semibold flex items-center justify-center"
            >
              {isCreating ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5 mr-3 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    ></path>
                  </svg>
                  Creating...
                </>
              ) : (
                "Create Podcast"
              )}
            </button>
          </form>
        </section>

        {/* Podcasts List */}
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4 border-b pb-2">Your Podcasts</h2>
          {loading ? (
            <p className="text-center">Loading podcasts...</p>
          ) : podcasts.length === 0 ? (
            <p className="text-center">No podcasts found. Create one to get started!</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {podcasts.map((podcast) => (
                <div
                  key={podcast.id}
                  className="bg-gray-800 rounded-lg shadow-md p-4 flex flex-col justify-between transition transform hover:scale-105"
                >
                  <div>
                    <h3 className="text-xl font-bold mb-1">{podcast.title}</h3>
                    <p className="text-gray-300 mb-2">{podcast.description}</p>
                    <p className="text-sm text-gray-400">
                      Topic: <span className="text-gray-200">{podcast.topic}</span>
                    </p>
                    <p className="text-sm text-gray-400">
                      Created: {new Date(podcast.created_at).toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-400">
                      Duration: {podcast.duration_seconds}s
                    </p>
                  </div>
                  <div className="mt-4 flex justify-between">
                    <button
                      onClick={() => handlePlayPodcast(podcast.id)}
                      className="px-4 py-2 bg-green-500 hover:bg-green-600 transition rounded text-sm"
                    >
                      Play
                    </button>
                    <button
                      onClick={() => handleDeletePodcast(podcast.id)}
                      className="px-4 py-2 bg-red-500 hover:bg-red-600 transition rounded text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Audio Player */}
        {audioUrl && playingPodcastId && (
          <section className="bg-gray-800 p-6 rounded-lg shadow-lg flex flex-col items-center">
            <h2 className="text-2xl font-semibold mb-4">Now Playing</h2>
            <audio controls src={audioUrl} className="w-full max-w-md mb-4" />
            <button
              onClick={() => {
                setAudioUrl(null);
                setPlayingPodcastId(null);
              }}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 transition rounded"
            >
              Stop
            </button>
          </section>
        )}
      </main>

      <footer className="bg-gray-800 py-4 text-center text-gray-500">
        &copy; {new Date().getFullYear()} Podcast Hub. All rights reserved.
      </footer>
    </div>
  );
}
