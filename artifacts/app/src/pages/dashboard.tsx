import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import { api } from "@/lib/api";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Plus, Film, Clock, AlertTriangle, ArrowRight, Loader2 } from "lucide-react";
import { format } from "date-fns";

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  
  const [formData, setFormData] = useState({
    title: "",
    prompt: "",
    genre: "action",
    style: "anime",
    num_episodes: 1,
    num_scenes: 5
  });

  const { data: stories, isLoading } = useQuery({
    queryKey: ["stories"],
    queryFn: api.getStories
  });

  const createMutation = useMutation({
    mutationFn: api.createStory,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["stories"] });
      setIsDialogOpen(false);
      setLocation(`/stories/${data.id}`);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "draft": return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
      case "generating": return "bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse";
      case "completed": return "bg-green-500/10 text-green-400 border-green-500/20";
      case "failed": return "bg-red-500/10 text-red-400 border-red-500/20";
      default: return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
    }
  };

  return (
    <Layout>
      <div className="container py-8 max-w-7xl mx-auto px-4 md:px-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-display font-bold uppercase tracking-tight">Productions</h1>
            <p className="text-zinc-400 mt-1">Manage your active series and episodic content.</p>
          </div>
          
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="font-display font-bold uppercase tracking-wider">
                <Plus className="mr-2 h-4 w-4" /> New Production
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] border-zinc-800 bg-zinc-950">
              <form onSubmit={handleSubmit}>
                <DialogHeader>
                  <DialogTitle className="font-display uppercase tracking-wide">Initialize Story Pipeline</DialogTitle>
                  <DialogDescription>
                    Provide the foundational parameters. The AI will extrapolate a full world and episode plan.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-6 py-6">
                  <div className="grid gap-2">
                    <Label htmlFor="title" className="text-xs uppercase tracking-wider text-zinc-400">Working Title</Label>
                    <Input 
                      id="title" 
                      value={formData.title}
                      onChange={e => setFormData({...formData, title: e.target.value})}
                      placeholder="e.g. Neon Genesis: Fall of Eden" 
                      className="bg-zinc-900 border-zinc-800"
                      required
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="prompt" className="text-xs uppercase tracking-wider text-zinc-400">Core Concept / Premise</Label>
                    <Textarea 
                      id="prompt" 
                      value={formData.prompt}
                      onChange={e => setFormData({...formData, prompt: e.target.value})}
                      placeholder="A group of rogue mecha pilots discover an ancient civilization living beneath the megacity..." 
                      className="bg-zinc-900 border-zinc-800 h-24 resize-none"
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label className="text-xs uppercase tracking-wider text-zinc-400">Genre</Label>
                      <Select value={formData.genre} onValueChange={v => setFormData({...formData, genre: v})}>
                        <SelectTrigger className="bg-zinc-900 border-zinc-800">
                          <SelectValue placeholder="Select genre" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="action">Action / Shonen</SelectItem>
                          <SelectItem value="sci-fi">Sci-Fi / Mecha</SelectItem>
                          <SelectItem value="fantasy">Dark Fantasy</SelectItem>
                          <SelectItem value="slice-of-life">Slice of Life</SelectItem>
                          <SelectItem value="horror">Psychological Horror</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-2">
                      <Label className="text-xs uppercase tracking-wider text-zinc-400">Visual Style</Label>
                      <Select value={formData.style} onValueChange={v => setFormData({...formData, style: v})}>
                        <SelectTrigger className="bg-zinc-900 border-zinc-800">
                          <SelectValue placeholder="Select style" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="anime">Classic Anime (90s Cel)</SelectItem>
                          <SelectItem value="modern-anime">Modern Anime (Ufotable style)</SelectItem>
                          <SelectItem value="manga">Manga (Black & White)</SelectItem>
                          <SelectItem value="realistic">Cinematic Realistic</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label htmlFor="episodes" className="text-xs uppercase tracking-wider text-zinc-400">Episodes to Plan</Label>
                      <Input 
                        id="episodes" 
                        type="number" 
                        min={1} max={12}
                        value={formData.num_episodes}
                        onChange={e => setFormData({...formData, num_episodes: parseInt(e.target.value) || 1})}
                        className="bg-zinc-900 border-zinc-800"
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="scenes" className="text-xs uppercase tracking-wider text-zinc-400">Scenes per Ep</Label>
                      <Input 
                        id="scenes" 
                        type="number" 
                        min={1} max={20}
                        value={formData.num_scenes}
                        onChange={e => setFormData({...formData, num_scenes: parseInt(e.target.value) || 5})}
                        className="bg-zinc-900 border-zinc-800"
                      />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" disabled={createMutation.isPending} className="font-display font-bold uppercase tracking-wider">
                    {createMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Initialize
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="border border-zinc-800 bg-zinc-950 rounded-lg p-5">
            <p className="text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1">Total Series</p>
            <p className="text-3xl font-display font-bold">{stories?.length || 0}</p>
          </div>
          <div className="border border-zinc-800 bg-zinc-950 rounded-lg p-5">
            <p className="text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1">In Production</p>
            <p className="text-3xl font-display font-bold text-blue-400">
              {stories?.filter(s => s.status === 'generating').length || 0}
            </p>
          </div>
          <div className="border border-zinc-800 bg-zinc-950 rounded-lg p-5">
            <p className="text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1">Completed</p>
            <p className="text-3xl font-display font-bold text-green-400">
              {stories?.filter(s => s.status === 'completed').length || 0}
            </p>
          </div>
          <div className="border border-zinc-800 bg-zinc-950 rounded-lg p-5">
            <p className="text-xs font-mono uppercase tracking-widest text-zinc-500 mb-1">Failed Runs</p>
            <p className="text-3xl font-display font-bold text-red-400">
              {stories?.filter(s => s.status === 'failed').length || 0}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : stories?.length === 0 ? (
          <div className="text-center py-24 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/50">
            <Film className="mx-auto h-12 w-12 text-zinc-600 mb-4" />
            <h3 className="text-xl font-display font-bold uppercase mb-2">No Active Productions</h3>
            <p className="text-zinc-500 max-w-md mx-auto mb-6">Initialize a new story pipeline to begin generating characters, scripts, and video scenes.</p>
            <Button onClick={() => setIsDialogOpen(true)} variant="outline" className="border-zinc-700">
              <Plus className="mr-2 h-4 w-4" /> Create First Story
            </Button>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {stories?.map((story) => (
              <Link key={story.id} href={`/stories/${story.id}`}>
                <Card className="h-full border-zinc-800 bg-zinc-950 hover:border-primary/50 transition-colors cursor-pointer flex flex-col group overflow-hidden relative">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  
                  <CardHeader className="pb-4">
                    <div className="flex justify-between items-start mb-2">
                      <Badge variant="outline" className={`font-mono text-[10px] uppercase tracking-widest ${getStatusColor(story.status)}`}>
                        {story.status}
                      </Badge>
                      <span className="text-xs text-zinc-500 font-mono">
                        {story.created_at ? format(new Date(story.created_at), 'MMM d, yyyy') : ''}
                      </span>
                    </div>
                    <CardTitle className="font-display text-xl uppercase tracking-tight line-clamp-1 group-hover:text-primary transition-colors">{story.title}</CardTitle>
                    <CardDescription className="text-zinc-500 flex gap-2 text-xs font-mono uppercase tracking-wider mt-2">
                      <span>{story.genre}</span> • <span>{story.style}</span>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 pb-4">
                    <p className="text-sm text-zinc-400 line-clamp-3">
                      {story.prompt}
                    </p>
                  </CardContent>
                  <CardFooter className="pt-0 flex justify-between items-center text-zinc-500 border-t border-zinc-900 mt-4">
                    <div className="flex items-center text-xs font-mono py-3">
                      <Clock className="mr-1 h-3 w-3" />
                      Updated recently
                    </div>
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0 text-primary" />
                  </CardFooter>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
