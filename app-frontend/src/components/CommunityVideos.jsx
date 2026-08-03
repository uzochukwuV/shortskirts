import React, { useState } from "react";
import VideoCard from "./VideoCard";

const categories = {
  "AI Film": [
    { title: "Upgrade Service", author: "Yibo", image_url: "https://res.papir.cc/buzzy-assets/G5o9gnSKGhY_Vn8XXsk3m_1782121168629_i1.avif", description: "UPGRADE SERVICE" },
    { title: "Backroom", author: "Neo", image_url: "https://res.creatiai.ai/web/creatiai/tag1-backroom_poster.avif", description: "BACKROOM ESCAPE" },
    { title: "The Last Key", author: "Roman", image_url: "https://res.creatiai.ai/web/creatiai/tag1-the-last-key.avif", description: "THE LAST KEY" },
    { title: "Before Rome Sunset", author: "El", image_url: "https://res.papir.cc/buzzy-assets/9buzS7r3tWU_SKNWBKq8K_1782121170648_i0.avif", description: "Before Rome Sunset" },
    { title: "Odyssey World Cup", author: "Ava", image_url: "https://res-prod.buzzy.now/file-service/3764d199-feb1-49a7-8c25-a43a32b336a2.jpg", description: "ODYSSEY WORLD CUP" },
    { title: "The Subtitle Murders", author: "Liam", image_url: "https://res-prod.buzzy.now/file-service/16a0f377-4856-4928-9d4d-960406602d3e.avif", description: "THE SUBTITLE MURDERS" },
    { title: "The Final Showdown", author: "Noah", image_url: "https://res-prod.buzzy.now/file-service/e6bb7a67-464d-4a43-a2a8-950cac2a6253.avif", description: "THE FINAL SHOWDOWN" },
    { title: "The Perfect Frame", author: "Mia", image_url: "https://res-prod.buzzy.now/file-service/50c9579a-f505-4f63-ae6d-a39fd60e1e94.jpg", description: "THE PERFECT FRAME" },
  ],
  "Branding Ads": [
    { title: "Pink Lemon", author: "Y1-B0", image_url: "https://res.papir.cc/buzzy-assets/fNaUhVpqbxFWOmhevBr6h_1781774410105_YiB0.avif", description: "Pink Lemon" },
    { title: "Beyond the Moment", author: "Lucas", image_url: "https://res.papir.cc/buzzy-assets/WmyTuAdlQu1EX8WswAvpg_1781774410105_Lucas.avif", description: "Beyond the Moment" },
    { title: "Nature's Essence", author: "Ember House", image_url: "https://res.papir.cc/buzzy-assets/N-x9NVnKn4Auq7pRsliHD_1781774410105_Ember%20House.avif", description: "Nature's Essence" },
    { title: "The Essence of Chairs", author: "Kani Studio", image_url: "https://res.papir.cc/buzzy-assets/oX2xQyKWJPuX1EwO1WGGv_1781774410105_Kani%20Studio.avif", description: "The Essence of Chairs" },
    { title: "Omno Fashion TVC", author: "Kani Studio", image_url: "https://res.papir.cc/buzzy-assets/oX2xQyKWJPuX1EwO1WGGv_1781774410105_Kani%20Studio.avif", description: "Omno Fashion TVC" },
    { title: "Noise cancelling headphones", author: "Ember House", image_url: "https://res.papir.cc/buzzy-assets/N-x9NVnKn4Auq7pRsliHD_1781774410105_Ember%20House.avif", description: "Noise cancelling headphones" },
    { title: "Sunglasses set", author: "Ember House", image_url: "https://res.papir.cc/buzzy-assets/N-x9NVnKn4Auq7pRsliHD_1781774410105_Ember%20House.avif", description: "Sunglasses set" },
    { title: "Pearl the Only", author: "Y1-B0", image_url: "https://res.papir.cc/buzzy-assets/0q_jW-wLaKz1sBvSA5-pE_1782121178717_i1.avif", description: "Pearl the Only" },
  ],
  "Animations": [
    { title: "The Fridge Guardian", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "The Fridge Guardian" },
    { title: "Mbappé Showdown", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Mbappé Showdown" },
    { title: "Forever Home", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Forever Home" },
    { title: "Golden Buddy", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Golden Buddy" },
  ],
  "MV & Explainer": [
    { title: "Rap", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Rap" },
    { title: "Dance", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Dance" },
    { title: "Blueberry Facts", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Blueberry Facts" },
    { title: "Geosmin Facts", author: "Neomorph", image_url: "https://res.papir.cc/buzzy-assets/FbeFR8u8kHTqV6ySEJYKJ_1782121186792_i2.avif", description: "Geosmin Facts" },
  ],
};

const tabs = ["AI Film", "Branding Ads", "Animations", "MV & Explainer"];

export default function CommunityVideos() {
  const [activeTab, setActiveTab] = useState("AI Film");
  const videos = categories[activeTab];

  return (
    <section className="px-4 sm:px-6 lg:px-10 py-12 sm:py-20 max-w-[1400px] mx-auto">
      <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight mb-6 sm:mb-8">
        Community Pro Videos
      </h2>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 sm:mb-8 overflow-x-auto pb-1">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 sm:px-5 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap transition-all ${
              activeTab === tab
                ? "bg-[#e0ff4c] text-black"
                : "bg-white/5 text-white/60 hover:text-white hover:bg-white/10"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Video grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {videos.map((video, i) => (
          <VideoCard key={`${activeTab}-${i}`} {...video} />
        ))}
      </div>

      {/* View all */}
      <div className="flex justify-center mt-12">
        <button className="text-sm text-white/60 hover:text-white border border-white/10 hover:border-white/30 px-6 py-2.5 rounded-full transition-all">
          View all videos
        </button>
      </div>
    </section>
  );
}