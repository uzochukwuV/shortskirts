import React, { useState } from "react";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import CommunityVideos from "@/components/CommunityVideos";
import Footer from "@/components/Footer";
import AuthModal from "@/components/AuthModal";

export default function Home() {
  const [authOpen, setAuthOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Navbar onStartClick={() => setAuthOpen(true)} />
      <Hero onStartClick={() => setAuthOpen(true)} />
      <CommunityVideos />
      <Footer />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}