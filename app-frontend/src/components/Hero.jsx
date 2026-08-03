import React from "react";

const floatingCards = [
  {
    label: "PRODUCT",
    name: "Nano Pro",
    img: "https://res-prod.buzzy.now/file-service/b165e42c-165d-4624-afde-dd9c9fc9b924.avif",
    className: "top-8 left-0 w-[180px] h-[220px] hidden md:block",
    rotate: "-rotate-6",
  },
  {
    label: "SCENE",
    name: "GPT Image 2",
    img: "https://res-prod.buzzy.now/file-service/158ec6b7-1403-4f5c-bbda-d6ea0dd588c4.avif",
    className: "bottom-4 left-4 w-[170px] h-[200px] hidden md:block",
    rotate: "rotate-3",
  },
  {
    label: "VIDEO",
    name: "Seedance 2",
    img: "https://res-prod.buzzy.now/file-service/16a0f377-4856-4928-9d4d-960406602d3e.avif",
    className: "top-12 right-0 w-[240px] h-[300px] hidden lg:block",
    rotate: "rotate-6",
  },
];

export default function Hero({ onStartClick }) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Grid dot pattern background */}
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.12) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />
      {/* Radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(224,255,76,0.06)_0%,transparent_60%)]" />

      {/* Floating cards */}
      {floatingCards.map((card, i) => (
        <div
          key={i}
          className={`absolute z-10 ${card.className} ${card.rotate}`}
          style={{ animation: `float${i} ${6 + i}s ease-in-out infinite` }}
        >
          <div className="relative w-full h-full rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
            <img src={card.img} alt={card.name} className="w-full h-full object-cover" />
            <div className="absolute top-2 left-2">
              <span className="text-[9px] uppercase tracking-widest text-white/50 font-medium">{card.label}</span>
            </div>
            <div className="absolute bottom-2 right-2">
              <span className="text-[10px] text-white/70 font-medium bg-black/40 px-2 py-0.5 rounded">{card.name}</span>
            </div>
          </div>
        </div>
      ))}

      {/* Hero content */}
      <div className="relative z-20 text-center px-6">
        <h1 className="text-4xl sm:text-5xl lg:text-7xl xl:text-8xl font-bold text-white tracking-tighter leading-[1.05]">
          Pro Video,
          <br />
          Made Easy
        </h1>
        <button onClick={onStartClick} className="mt-8 sm:mt-10 bg-[#e0ff4c] text-black font-semibold px-7 sm:px-8 py-2.5 sm:py-3 rounded-full text-sm sm:text-base hover:bg-[#d4f53e] transition-all hover:scale-105 active:scale-95">
          Get started
        </button>
      </div>

      <style>{`
        @keyframes float0 { 0%,100% { transform: translateY(0px) rotate(-6deg); } 50% { transform: translateY(-14px) rotate(-6deg); } }
        @keyframes float1 { 0%,100% { transform: translateY(0px) rotate(3deg); } 50% { transform: translateY(-10px) rotate(3deg); } }
        @keyframes float2 { 0%,100% { transform: translateY(0px) rotate(6deg); } 50% { transform: translateY(-18px) rotate(6deg); } }
      `}</style>
    </section>
  );
}