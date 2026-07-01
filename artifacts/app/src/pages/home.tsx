import { motion } from "framer-motion";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Layout } from "@/components/layout";
import { PlayCircle, Cpu, Film, Sparkles, MoveRight, Layers, Workflow, Activity } from "lucide-react";

export default function Home() {
  return (
    <Layout>
      <div className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-24 pb-32 lg:pt-36 lg:pb-40 border-b border-border/40">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/20 via-background to-background -z-10" />
          
          <div className="container px-4 md:px-6">
            <div className="grid gap-12 lg:grid-cols-2 lg:gap-8 items-center">
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="flex flex-col justify-center space-y-8"
              >
                <div className="space-y-4">
                  <div className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
                    <Sparkles className="mr-2 h-4 w-4" />
                    Next-Gen Anime Production
                  </div>
                  <h1 className="text-5xl font-display font-bold tracking-tighter sm:text-6xl xl:text-7xl/none text-foreground uppercase">
                    Direct Your <br/>
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-rose-400">Masterpiece</span>
                  </h1>
                  <p className="max-w-[600px] text-zinc-400 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed font-light">
                    The creative director's cockpit for AI-generated anime. Command state-of-the-art models to write, cast, and render cinematic episodes from a single prompt.
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link href="/dashboard">
                    <Button size="lg" className="h-12 px-8 font-display uppercase tracking-widest font-bold w-full sm:w-auto">
                      Start Production
                      <MoveRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                  <Button size="lg" variant="outline" className="h-12 px-8 font-display uppercase tracking-widest font-bold w-full sm:w-auto bg-transparent border-zinc-800 hover:bg-zinc-900">
                    View Showcase
                  </Button>
                </div>
                
                <div className="grid grid-cols-3 gap-4 pt-8 border-t border-border/50">
                  <div>
                    <h4 className="text-3xl font-display font-bold text-primary">Qwen</h4>
                    <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Story Engine</p>
                  </div>
                  <div>
                    <h4 className="text-3xl font-display font-bold text-primary">Wan</h4>
                    <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Video Render</p>
                  </div>
                  <div>
                    <h4 className="text-3xl font-display font-bold text-primary">4K</h4>
                    <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">Resolution</p>
                  </div>
                </div>
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.7, delay: 0.2 }}
                className="mx-auto w-full max-w-[600px] lg:max-w-none"
              >
                <div className="aspect-[4/3] overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50 shadow-2xl relative">
                  <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-10" />
                  <img 
                    src="/hero-anime.png" 
                    alt="Anime Studio Interface" 
                    className="object-cover w-full h-full opacity-80"
                  />
                  
                  {/* Decorative UI overlays */}
                  <div className="absolute top-4 left-4 z-20 flex gap-2">
                    <div className="h-3 w-3 rounded-full bg-rose-500 animate-pulse" />
                    <span className="text-[10px] font-mono uppercase tracking-widest text-rose-500 font-bold">Rendering Scene 04</span>
                  </div>
                  
                  <div className="absolute bottom-4 right-4 z-20 flex gap-2">
                    <div className="bg-black/80 backdrop-blur border border-white/10 px-3 py-1.5 rounded text-xs font-mono text-zinc-300">
                      FRAMES: 2450/4800
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Feature Section */}
        <section className="py-24 bg-zinc-950">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
              <h2 className="text-3xl font-display font-bold tracking-tighter uppercase sm:text-5xl">Professional <span className="text-primary">Pipeline</span></h2>
              <p className="max-w-[900px] text-zinc-400 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                A robust architecture designed for serious creators. From script generation to final render, every step is orchestrated with precision.
              </p>
            </div>
            
            <div className="grid gap-8 md:grid-cols-3">
              <div className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 hover:bg-zinc-900 transition-colors">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Cpu className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-xl font-display font-bold uppercase tracking-wide">LLM Screenwriting</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Powered by advanced language models to generate cohesive episode arcs, complex character backstories, and precise scene directions.
                </p>
              </div>
              
              <div className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 hover:bg-zinc-900 transition-colors">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Layers className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-xl font-display font-bold uppercase tracking-wide">Character Consistency</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Persistent character reference sheets ensure visual continuity across diverse scenes, outfits, and emotional states.
                </p>
              </div>
              
              <div className="group relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 hover:bg-zinc-900 transition-colors">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Film className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-xl font-display font-bold uppercase tracking-wide">Cinematic Render</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  High-fidelity video models translate text prompts into sweeping cinematic shots with complex camera movements and atmospheric lighting.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-32 relative overflow-hidden border-t border-border/40">
          <div className="absolute inset-0 bg-primary/5" />
          <div className="container relative z-10 px-4 md:px-6 text-center">
            <h2 className="text-4xl font-display font-bold tracking-tighter uppercase sm:text-6xl mb-6">
              Ready to Forge Your Story?
            </h2>
            <p className="mx-auto max-w-[600px] text-zinc-400 md:text-xl mb-10">
              Join the vanguard of AI-assisted anime production. Initialize your workspace and start directing.
            </p>
            <Link href="/dashboard">
              <Button size="lg" className="h-14 px-10 text-lg font-display uppercase tracking-widest font-bold">
                Enter Dashboard
              </Button>
            </Link>
          </div>
        </section>
      </div>
    </Layout>
  );
}
