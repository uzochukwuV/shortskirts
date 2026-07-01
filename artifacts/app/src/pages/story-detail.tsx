import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { api, Story, Character, Episode, Scene, GenerationJob } from "@/lib/api";
import { Layout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ChevronLeft, Play, Download, User, Film, BookOpen, AlertCircle, Loader2, PlayCircle } from "lucide-react";
import { Link } from "wouter";

export default function StoryDetail() {
  const [, params] = useRoute("/stories/:id");
  const id = params?.id || "";
  const queryClient = useQueryClient();
  const [activeEpisode, setActiveEpisode] = useState<string>("");

  const { data: story, isLoading: isLoadingStory } = useQuery({
    queryKey: ["story", id],
    queryFn: () => api.getStory(id),
    enabled: !!id
  });

  const { data: characters, isLoading: isLoadingChars } = useQuery({
    queryKey: ["characters", id],
    queryFn: () => api.getCharacters(id),
    enabled: !!id
  });

  const { data: episodes, isLoading: isLoadingEps } = useQuery({
    queryKey: ["episodes", id],
    queryFn: () => api.getEpisodes(id),
    enabled: !!id
  });

  // Fetch active job if story is generating
  const { data: jobs } = useQuery({
    queryKey: ["jobs", "story", id],
    queryFn: () => api.getEntityJobs("story", id),
    enabled: !!id && (story?.status === "generating" || story?.status === "draft")
  });

  const activeJob = jobs?.find(j => j.status === "running" || j.status === "pending");

  // Poll job if active
  useQuery({
    queryKey: ["job", activeJob?.id],
    queryFn: () => api.getJob(activeJob!.id),
    refetchInterval: 3000,
    enabled: !!activeJob?.id && (activeJob.status === "running" || activeJob.status === "pending"),
    onSuccess: (data) => {
      if (data.status === "completed" || data.status === "failed") {
        queryClient.invalidateQueries({ queryKey: ["story", id] });
        queryClient.invalidateQueries({ queryKey: ["characters", id] });
        queryClient.invalidateQueries({ queryKey: ["episodes", id] });
        queryClient.invalidateQueries({ queryKey: ["jobs", "story", id] });
      }
    }
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateStory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["story", id] });
      queryClient.invalidateQueries({ queryKey: ["jobs", "story", id] });
    }
  });

  useEffect(() => {
    if (episodes && episodes.length > 0 && !activeEpisode) {
      setActiveEpisode(episodes[0].id);
    }
  }, [episodes, activeEpisode]);

  if (isLoadingStory) {
    return (
      <Layout>
        <div className="container p-6 animate-pulse">
          <Skeleton className="h-8 w-64 mb-4 bg-zinc-900" />
          <Skeleton className="h-4 w-96 mb-8 bg-zinc-900" />
          <Skeleton className="h-[400px] w-full bg-zinc-900" />
        </div>
      </Layout>
    );
  }

  if (!story) return <Layout><div className="p-6">Story not found.</div></Layout>;

  return (
    <Layout>
      <div className="border-b border-zinc-800 bg-zinc-950">
        <div className="container px-4 md:px-6 py-6">
          <div className="flex items-center gap-2 text-zinc-500 mb-4 text-sm font-mono uppercase tracking-wider">
            <Link href="/dashboard" className="hover:text-primary transition-colors flex items-center">
              <ChevronLeft className="h-4 w-4 mr-1" /> Dashboard
            </Link>
            <span>/</span>
            <span className="text-zinc-300">Production Workspace</span>
          </div>
          
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-4xl font-display font-bold uppercase tracking-tight">{story.title}</h1>
                <Badge variant="outline" className={`font-mono uppercase tracking-widest text-[10px] ${
                  story.status === 'completed' ? 'text-green-400 border-green-500/30 bg-green-500/10' :
                  story.status === 'generating' ? 'text-blue-400 border-blue-500/30 bg-blue-500/10 animate-pulse' :
                  story.status === 'failed' ? 'text-red-400 border-red-500/30 bg-red-500/10' :
                  'text-zinc-400 border-zinc-700 bg-zinc-800/50'
                }`}>
                  {story.status}
                </Badge>
              </div>
              <p className="text-zinc-400 max-w-2xl">{story.prompt}</p>
            </div>
            
            <div className="flex items-center gap-3 w-full md:w-auto">
              <Button 
                onClick={() => generateMutation.mutate()} 
                disabled={story.status === 'generating' || generateMutation.isPending}
                className="font-display uppercase tracking-widest font-bold w-full md:w-auto"
              >
                {story.status === 'generating' || generateMutation.isPending ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating</>
                ) : (
                  <><Play className="mr-2 h-4 w-4" /> Start Pipeline</>
                )}
              </Button>
            </div>
          </div>

          {activeJob && (
            <div className="mt-6 p-4 rounded-lg border border-blue-500/20 bg-blue-500/5">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                  <span className="text-sm font-mono uppercase tracking-wider text-blue-400">
                    Pipeline Active: {activeJob.current_step}
                  </span>
                </div>
                <span className="text-xs font-mono text-zinc-500">
                  {Math.round((activeJob.progress / activeJob.total_steps) * 100)}%
                </span>
              </div>
              <Progress value={(activeJob.progress / activeJob.total_steps) * 100} className="h-1 bg-zinc-800" />
            </div>
          )}
        </div>
      </div>

      <div className="container px-4 md:px-6 py-8">
        <Tabs defaultValue="episodes" className="w-full">
          <TabsList className="bg-zinc-900 border border-zinc-800 w-full justify-start p-1 h-auto rounded-lg mb-8">
            <TabsTrigger value="episodes" className="data-[state=active]:bg-zinc-800 font-mono uppercase tracking-wider text-xs py-2 px-4">
              <Film className="mr-2 h-4 w-4" /> Episodes & Scenes
            </TabsTrigger>
            <TabsTrigger value="characters" className="data-[state=active]:bg-zinc-800 font-mono uppercase tracking-wider text-xs py-2 px-4">
              <User className="mr-2 h-4 w-4" /> Cast & Characters
            </TabsTrigger>
            <TabsTrigger value="plan" className="data-[state=active]:bg-zinc-800 font-mono uppercase tracking-wider text-xs py-2 px-4">
              <BookOpen className="mr-2 h-4 w-4" /> Master Plan
            </TabsTrigger>
          </TabsList>

          <TabsContent value="episodes" className="m-0">
            {isLoadingEps ? (
              <div className="grid md:grid-cols-12 gap-8">
                <div className="md:col-span-3 space-y-2"><Skeleton className="h-12 w-full bg-zinc-900" /></div>
                <div className="md:col-span-9 space-y-4"><Skeleton className="h-64 w-full bg-zinc-900" /></div>
              </div>
            ) : episodes && episodes.length > 0 ? (
              <div className="grid md:grid-cols-12 gap-8">
                <div className="md:col-span-3">
                  <div className="font-mono text-xs uppercase tracking-widest text-zinc-500 mb-4 px-2">Episodes</div>
                  <div className="space-y-1">
                    {episodes.map(ep => (
                      <button
                        key={ep.id}
                        onClick={() => setActiveEpisode(ep.id)}
                        className={`w-full text-left px-4 py-3 rounded-md transition-colors ${
                          activeEpisode === ep.id 
                            ? 'bg-primary/10 text-primary border border-primary/20 font-medium' 
                            : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent'
                        }`}
                      >
                        <div className="text-xs font-mono uppercase opacity-70 mb-1">Episode {ep.episode_number}</div>
                        <div className="line-clamp-1 font-display tracking-wide">{ep.title}</div>
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="md:col-span-9">
                  {episodes.find(e => e.id === activeEpisode) && (
                    <div className="space-y-6">
                      <div className="border-b border-zinc-800 pb-6">
                        <h2 className="text-2xl font-display font-bold uppercase tracking-tight mb-2">
                          <span className="text-zinc-500 mr-2">EP {episodes.find(e => e.id === activeEpisode)?.episode_number}</span>
                          {episodes.find(e => e.id === activeEpisode)?.title}
                        </h2>
                        <p className="text-zinc-400 text-sm leading-relaxed">
                          {episodes.find(e => e.id === activeEpisode)?.summary}
                        </p>
                      </div>

                      <div className="space-y-8">
                        {episodes.find(e => e.id === activeEpisode)?.scenes?.map((scene: Scene) => (
                          <div key={scene.id} className="border border-zinc-800 rounded-xl bg-zinc-950 overflow-hidden">
                            <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50">
                              <div className="flex items-center gap-3">
                                <Badge variant="outline" className="font-mono bg-zinc-900 text-zinc-400">
                                  SCENE {String(scene.scene_number).padStart(3, '0')}
                                </Badge>
                                <span className="font-display font-medium">{scene.title}</span>
                              </div>
                              <Badge variant="outline" className="font-mono text-[10px] uppercase">
                                {scene.location} • {scene.mood}
                              </Badge>
                            </div>
                            
                            <div className="grid md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-zinc-800">
                              <div className="p-4 space-y-4">
                                <div>
                                  <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Action</div>
                                  <p className="text-sm text-zinc-300">{scene.description}</p>
                                </div>
                                <div>
                                  <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Visual Prompt</div>
                                  <p className="text-xs text-zinc-400 font-mono bg-zinc-900 p-2 rounded border border-zinc-800">
                                    {scene.visual_prompt}
                                  </p>
                                </div>
                              </div>
                              
                              <div className="p-4 bg-black flex flex-col justify-center items-center relative group min-h-[250px]">
                                {scene.video_url ? (
                                  <>
                                    <video 
                                      src={scene.video_url} 
                                      controls 
                                      className="w-full h-full object-contain rounded-md"
                                      poster="/hero-anime.png" // placeholder if needed
                                    />
                                    <a 
                                      href={scene.video_url} 
                                      download 
                                      className="absolute top-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity bg-black/60 hover:bg-black p-2 rounded backdrop-blur border border-white/10 text-white"
                                      title="Download Render"
                                    >
                                      <Download className="h-4 w-4" />
                                    </a>
                                  </>
                                ) : (
                                  <div className="text-center text-zinc-600 flex flex-col items-center">
                                    {story.status === 'generating' ? (
                                      <>
                                        <Loader2 className="h-8 w-8 mb-2 animate-spin text-zinc-500" />
                                        <span className="text-xs font-mono uppercase tracking-widest">Awaiting Render</span>
                                      </>
                                    ) : (
                                      <>
                                        <PlayCircle className="h-10 w-10 mb-2 opacity-20" />
                                        <span className="text-xs font-mono uppercase tracking-widest opacity-50">No Render Available</span>
                                      </>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                        {(!episodes.find(e => e.id === activeEpisode)?.scenes || episodes.find(e => e.id === activeEpisode)!.scenes.length === 0) && (
                          <div className="text-center p-12 border border-dashed border-zinc-800 rounded-xl text-zinc-500">
                            No scenes generated yet.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center p-12 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/50">
                <AlertCircle className="mx-auto h-8 w-8 text-zinc-600 mb-3" />
                <p className="text-zinc-400 font-mono text-sm uppercase tracking-wider">No episodes generated yet.</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="characters" className="m-0">
            {isLoadingChars ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1,2,3].map(i => <Skeleton key={i} className="h-[300px] w-full bg-zinc-900" />)}
              </div>
            ) : characters && characters.length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {characters.map(char => (
                  <Card key={char.id} className="border-zinc-800 bg-zinc-950 overflow-hidden">
                    {char.ref_image_urls && char.ref_image_urls.length > 0 ? (
                      <div className="aspect-[4/3] bg-zinc-900 border-b border-zinc-800 relative">
                        <img 
                          src={char.ref_image_urls[0]} 
                          alt={char.name} 
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 to-transparent" />
                      </div>
                    ) : (
                      <div className="aspect-[4/3] bg-zinc-900 border-b border-zinc-800 flex items-center justify-center relative">
                        <User className="h-12 w-12 text-zinc-800" />
                        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 to-transparent" />
                      </div>
                    )}
                    <CardHeader className="pt-4 pb-2 relative z-10 -mt-10">
                      <div className="flex justify-between items-start">
                        <CardTitle className="font-display text-2xl uppercase tracking-tight">{char.name}</CardTitle>
                      </div>
                      <Badge variant="outline" className="w-fit font-mono text-[10px] uppercase bg-zinc-900 text-primary border-primary/20">
                        {char.role}
                      </Badge>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <p className="text-sm text-zinc-400 line-clamp-3 leading-relaxed">{char.description}</p>
                      </div>
                      <div className="space-y-2 pt-2 border-t border-zinc-900">
                        <div>
                          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Appearance</div>
                          <p className="text-xs text-zinc-300 line-clamp-2">{char.appearance}</p>
                        </div>
                        <div>
                          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1">Personality</div>
                          <p className="text-xs text-zinc-300 line-clamp-2">{char.personality}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center p-12 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/50">
                <p className="text-zinc-400 font-mono text-sm uppercase tracking-wider">No characters generated yet.</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="plan" className="m-0">
            {story.episode_plan ? (
              <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 md:p-8">
                <div className="max-w-3xl mx-auto space-y-10">
                  <section>
                    <h3 className="text-lg font-display font-bold uppercase tracking-widest text-primary mb-3">Synopsis</h3>
                    <p className="text-zinc-300 leading-relaxed text-lg font-light">{story.episode_plan.synopsis}</p>
                  </section>
                  
                  <Separator className="bg-zinc-800" />
                  
                  <section>
                    <h3 className="text-lg font-display font-bold uppercase tracking-widest text-primary mb-3">Setting</h3>
                    <p className="text-zinc-300 leading-relaxed">{story.episode_plan.setting}</p>
                  </section>
                  
                  <Separator className="bg-zinc-800" />
                  
                  <section>
                    <h3 className="text-lg font-display font-bold uppercase tracking-widest text-primary mb-3">Core Themes</h3>
                    <div className="flex flex-wrap gap-2">
                      {story.episode_plan.themes?.map((theme, i) => (
                        <Badge key={i} variant="secondary" className="bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-zinc-800">
                          {theme}
                        </Badge>
                      ))}
                    </div>
                  </section>
                </div>
              </div>
            ) : (
               <div className="text-center p-12 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/50">
                <p className="text-zinc-400 font-mono text-sm uppercase tracking-wider">Master plan not yet extrapolated.</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
