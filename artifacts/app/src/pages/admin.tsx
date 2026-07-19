import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ChartPie,
  ChevronRight,
  Clock3,
  Database,
  LogOut,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { api, clearAdminAuthToken, getAdminAuthToken, setAdminAuthToken, type AdminOverview, type AdminUserDetail, type AdminUserSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/page-header";

const PIE_COLORS = ["#0c0a09", "#96ff1a", "#71737a", "#d4d4d8", "#f2f1f0", "#083300", "#4d4d51"];

function shortDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function metricCard({ label, value, hint, icon: Icon }: { label: string; value: string | number; hint?: string; icon: any }) {
  return (
    <div className="rounded-[20px] border border-[#e6e6e7] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wide text-[#71737a]">{label}</div>
          <div className="mt-2 text-3xl font-extrabold text-[#0c0a09]">{value}</div>
          {hint && <div className="mt-1 text-[12px] text-[#71737a]">{hint}</div>}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#f2f1f0] text-[#083300]">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api.adminLogin({ email, password }),
    onSuccess: (res) => {
      setAdminAuthToken(res.token);
      window.location.reload();
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f2f1f0] p-6 text-[#0c0a09]">
      <div className="w-full max-w-[440px] rounded-[24px] border border-[#e6e6e7] bg-white p-6 shadow-[0_20px_60px_rgba(0,0,0,0.08)]">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-[#96ff1a] text-[#083300]">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase text-[#71737a]">Admin access</div>
            <div className="text-xl font-extrabold">Operations dashboard</div>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="admin-email">Email</Label>
            <Input id="admin-email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@example.com" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="admin-password">Password</Label>
            <Input id="admin-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>
          <Button className="w-full" variant="lime" onClick={() => login.mutate()} disabled={login.isPending}>
            {login.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Sign in
          </Button>
          {login.isError && <div className="text-sm text-red-600">{(login.error as Error).message}</div>}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === "completed" || status === "approved"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : status === "failed"
        ? "bg-red-50 text-red-700 border-red-200"
        : status === "generating" || status === "running"
          ? "bg-[#f5ffd8] text-[#083300] border-[#96ff1a]"
          : "bg-[#f2f1f0] text-[#323232] border-[#e6e6e7]";
  return <Badge className={`border px-2.5 py-1 ${tone}`}>{status}</Badge>;
}

function UserDetailDialog({
  user,
  open,
  onOpenChange,
}: {
  user: AdminUserSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const detail = useQuery({
    queryKey: ["admin-user", user?.id],
    queryFn: () => api.adminUserDetail(user!.id),
    enabled: !!user?.id && open,
  });

  const data = detail.data;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] max-w-[1100px] overflow-hidden rounded-[24px] border border-[#e6e6e7] bg-white">
        <DialogHeader>
          <DialogTitle className="text-2xl font-extrabold text-[#0c0a09]">{user?.email || "User detail"}</DialogTitle>
          <DialogDescription>Production history, failures, and recent requests.</DialogDescription>
        </DialogHeader>

        {!data ? (
          <div className="py-10 text-sm text-[#71737a]">Loading user detail...</div>
        ) : (
          <Tabs defaultValue="overview" className="min-h-0">
            <TabsList className="grid w-full grid-cols-3 bg-[#f2f1f0]">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="jobs">Jobs</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
            </TabsList>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {metricCard({ label: "Stories", value: data.user.story_count, hint: "All productions", icon: Database })}
              {metricCard({ label: "Completed", value: data.user.completed_story_count, hint: "Completed stories", icon: CheckIcon })}
              {metricCard({ label: "Failures", value: data.user.failed_story_count, hint: "Failed stories", icon: AlertTriangle })}
            </div>

            <TabsContent value="overview" className="mt-4 max-h-[60vh] overflow-hidden">
              <div className="rounded-[20px] border border-[#e6e6e7] bg-white">
                <div className="border-b border-[#e6e6e7] px-4 py-3 text-[11px] font-bold uppercase text-[#71737a]">Recent productions</div>
                <ScrollArea className="h-[44vh]">
                  <div className="divide-y divide-[#e6e6e7]">
                    {data.stories.map((story) => (
                      <div key={story.id} className="px-4 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-bold text-[#0c0a09]">{story.title}</div>
                            <div className="mt-1 text-[12px] text-[#71737a]">
                              {story.workflow_type} - {story.episode_count} episodes - {story.job_count} jobs
                            </div>
                          </div>
                          <StatusPill status={story.status} />
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-[#71737a]">
                          <span className="rounded-full border border-[#e6e6e7] px-2 py-1">approval {story.approval_status}</span>
                          <span className="rounded-full border border-[#e6e6e7] px-2 py-1">updated {shortDate(story.updated_at)}</span>
                        </div>
                      </div>
                    ))}
                    {!data.stories.length && <div className="px-4 py-6 text-sm text-[#71737a]">No stories found.</div>}
                  </div>
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="jobs" className="mt-4">
              <div className="rounded-[20px] border border-[#e6e6e7] bg-white">
                <div className="border-b border-[#e6e6e7] px-4 py-3 text-[11px] font-bold uppercase text-[#71737a]">Recent jobs</div>
                <ScrollArea className="h-[50vh]">
                  <div className="divide-y divide-[#e6e6e7]">
                    {data.recent_jobs.map((job) => (
                      <div key={job.id} className="px-4 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-bold text-[#0c0a09]">{job.story_title || job.job_type || job.entity_type}</div>
                            <div className="mt-1 text-[12px] text-[#71737a]">
                              {job.current_step || job.job_type} - {job.progress}/{job.total_steps}
                            </div>
                          </div>
                          <StatusPill status={job.status} />
                        </div>
                        {job.error && <div className="mt-2 text-xs text-red-600">{job.error}</div>}
                      </div>
                    ))}
                    {!data.recent_jobs.length && <div className="px-4 py-6 text-sm text-[#71737a]">No jobs found.</div>}
                  </div>
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="activity" className="mt-4">
              <div className="rounded-[20px] border border-[#e6e6e7] bg-white">
                <div className="border-b border-[#e6e6e7] px-4 py-3 text-[11px] font-bold uppercase text-[#71737a]">Recent activity</div>
                <ScrollArea className="h-[50vh]">
                  <div className="divide-y divide-[#e6e6e7]">
                    {data.recent_activity.map((item) => (
                      <div key={`${item.kind}-${item.id}`} className="px-4 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-bold text-[#0c0a09]">{item.title || item.kind}</div>
                            <div className="mt-1 text-[12px] text-[#71737a]">{item.kind} - {shortDate(item.updated_at || item.created_at)}</div>
                          </div>
                          <StatusPill status={item.status} />
                        </div>
                      </div>
                    ))}
                    {!data.recent_activity.length && <div className="px-4 py-6 text-sm text-[#71737a]">No recent activity.</div>}
                  </div>
                </ScrollArea>
              </div>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

export default function AdminPage() {
  const qc = useQueryClient();
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedUser, setSelectedUser] = useState<AdminUserSummary | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  const me = useQuery({
    queryKey: ["admin-me"],
    queryFn: () => api.adminMe(),
    enabled: ready && !!getAdminAuthToken(),
    retry: false,
  });

  useEffect(() => {
    if (me.isError) {
      clearAdminAuthToken();
      qc.invalidateQueries({ queryKey: ["admin-me"] });
    }
  }, [me.isError, qc]);

  const overview = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => api.adminOverview(),
    enabled: !!me.data,
    refetchInterval: 15000,
  });
  const users = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api.adminUsers(),
    enabled: !!me.data,
    refetchInterval: 15000,
  });

  const logout = useMutation({
    mutationFn: () => api.adminLogout(),
    onSettled: () => {
      clearAdminAuthToken();
      qc.clear();
      window.location.reload();
    },
  });

  const filteredUsers = useMemo(() => {
    const list = users.data || [];
    const needle = query.trim().toLowerCase();
    if (!needle) return list;
    return list.filter((user) =>
      [user.email, user.last_story_title, user.last_story_status].some((value) => value?.toLowerCase().includes(needle)),
    );
  }, [users.data, query]);

  const storyChartData = overview.data?.story_status_breakdown || [];
  const jobChartData = overview.data?.job_status_breakdown || [];
  const dailyData = overview.data?.daily_activity || [];

  if (!ready) return null;
  if (!me.data) return <LoginScreen />;

  const storyPieConfig = {
    completed: { label: "Completed", color: "var(--chart-1)" },
    failed: { label: "Failed", color: "var(--chart-2)" },
    generating: { label: "Generating", color: "var(--chart-3)" },
    approved: { label: "Approved", color: "var(--chart-4)" },
    draft: { label: "Draft", color: "var(--chart-5)" },
    checkpoint_review: { label: "Review", color: "var(--chart-6)" },
    ready: { label: "Ready", color: "var(--chart-7)" },
  };

  const jobPieConfig = {
    completed: { label: "Completed", color: "var(--chart-1)" },
    failed: { label: "Failed", color: "var(--chart-2)" },
    running: { label: "Running", color: "var(--chart-3)" },
    pending: { label: "Pending", color: "var(--chart-4)" },
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="mx-auto max-w-[1400px] space-y-6 px-4 py-6 md:px-6">
        <PageHeader
          eyebrow="Admin console"
          title="System health, users, request flow, and failures."
          description="Operational view for tracking users, stories, jobs, and provider behavior across the workspace."
          actions={
            <>
              <Badge className="border-border bg-muted text-foreground">{me.data.email}</Badge>
              <Button variant="outline" size="sm" onClick={() => overview.refetch()}>
                <RefreshCw className={`h-4 w-4 ${overview.isFetching ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <Button variant="ghost" size="sm" onClick={() => logout.mutate()}>
                <LogOut className="h-4 w-4" />
                Sign out
              </Button>
            </>
          }
          stats={[
            { label: "Users", value: String(overview.data?.totals.total_users ?? 0), hint: "Registered accounts" },
            { label: "Stories", value: String(overview.data?.totals.total_stories ?? 0), hint: "All productions" },
            { label: "Completed", value: String(overview.data?.totals.completed_stories ?? 0), hint: "Finished productions" },
            { label: "Failures", value: String(overview.data?.totals.failed_stories ?? 0), hint: "Completed or failed jobs" },
          ]}
        />

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {metricCard({ label: "Users", value: overview.data?.totals.total_users ?? 0, hint: "Registered accounts", icon: Users })}
          {metricCard({ label: "Stories", value: overview.data?.totals.total_stories ?? 0, hint: "All productions", icon: Database })}
          {metricCard({ label: "Completed", value: overview.data?.totals.completed_stories ?? 0, hint: "Finished productions", icon: CheckIcon })}
          {metricCard({ label: "Failures", value: overview.data?.totals.failed_stories ?? 0, hint: "Completed or failed jobs", icon: AlertTriangle })}
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr_0.9fr]">
          <div className="rounded-[24px] border border-[#e6e6e7] bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-bold uppercase text-[#71737a]">Activity</div>
                <div className="text-lg font-extrabold">Daily production volume</div>
              </div>
              <Activity className="h-4 w-4 text-[#71737a]" />
            </div>
            <div className="mt-4 h-[300px]">
              <ChartContainer
                config={{
                  count: { label: "Stories", color: "var(--chart-1)" },
                }}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyData}>
                    <CartesianGrid vertical={false} stroke="#e6e6e7" />
                    <XAxis dataKey="day" tickLine={false} axisLine={false} tickMargin={8} />
                    <YAxis tickLine={false} axisLine={false} tickMargin={8} allowDecimals={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line type="monotone" dataKey="count" stroke="#0c0a09" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          </div>

          <div className="rounded-[24px] border border-[#e6e6e7] bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-bold uppercase text-[#71737a]">Stories</div>
                <div className="text-lg font-extrabold">Story status mix</div>
              </div>
              <ChartPie className="h-4 w-4 text-[#71737a]" />
            </div>
            <div className="mt-4 h-[300px]">
              <ChartContainer config={storyPieConfig}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={storyChartData} dataKey="count" nameKey="status" innerRadius={70} outerRadius={110} paddingAngle={3}>
                      {storyChartData.map((entry, index) => (
                        <Cell key={entry.status} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          </div>

          <div className="rounded-[24px] border border-[#e6e6e7] bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-bold uppercase text-[#71737a]">Jobs</div>
                <div className="text-lg font-extrabold">Job status mix</div>
              </div>
              <ChevronRight className="h-4 w-4 text-[#71737a]" />
            </div>
            <div className="mt-4 h-[300px]">
              <ChartContainer config={jobPieConfig}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={jobChartData} dataKey="count" nameKey="status" innerRadius={70} outerRadius={110} paddingAngle={3}>
                      {jobChartData.map((entry, index) => (
                        <Cell key={entry.status} fill={PIE_COLORS[(index + 2) % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[24px] border border-[#e6e6e7] bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-bold uppercase text-[#71737a]">Provider metrics</div>
                <div className="text-lg font-extrabold">Latency and cost</div>
              </div>
              <Clock3 className="h-4 w-4 text-[#71737a]" />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {metricCard({ label: "Avg latency", value: `${overview.data?.provider_latency.avg_latency_ms ?? 0} ms`, icon: Clock3 })}
              {metricCard({ label: "P95 latency", value: `${overview.data?.provider_latency.p95_latency_ms ?? 0} ms`, icon: Clock3 })}
              {metricCard({ label: "Cost", value: `$${(overview.data?.provider_costs.total_cost ?? 0).toFixed(2)}`, icon: Sparkles })}
            </div>
            <div className="mt-4 h-[260px]">
              <ChartContainer
                config={{
                  failures: { label: "Failures", color: "var(--chart-1)" },
                }}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overview.data?.top_failure_steps || []}>
                    <CartesianGrid vertical={false} stroke="#e6e6e7" />
                    <XAxis dataKey="step_name" tickLine={false} axisLine={false} tickMargin={8} />
                    <YAxis tickLine={false} axisLine={false} tickMargin={8} allowDecimals={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="failures" fill="#0c0a09" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          </div>

          <div className="rounded-[24px] border border-[#e6e6e7] bg-white">
            <div className="border-b border-[#e6e6e7] p-4">
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Users</div>
              <div className="mt-1 text-lg font-extrabold">Accounts and request volume</div>
              <div className="mt-3 flex items-center gap-2 rounded-[14px] border border-[#e6e6e7] bg-[#f8f8f8] px-3 py-2">
                <Search className="h-4 w-4 text-[#71737a]" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search email, latest story, or status"
                  className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
                />
              </div>
            </div>
            <ScrollArea className="h-[520px]">
              <div className="divide-y divide-[#e6e6e7]">
                {filteredUsers.map((user) => (
                  <button
                    key={user.id}
                    type="button"
                    onClick={() => {
                      setSelectedUser(user);
                      setDialogOpen(true);
                    }}
                    className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition hover:bg-[#f8f8f8]"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-[#0c0a09]">{user.email}</div>
                      <div className="mt-1 text-[12px] text-[#71737a]">
                        {user.story_count} stories - {user.total_job_count} jobs - last {shortDate(user.last_activity_at)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusPill status={user.last_story_status || "unknown"} />
                      <ArrowRight className="h-4 w-4 text-[#71737a]" />
                    </div>
                  </button>
                ))}
                {!filteredUsers.length && <div className="px-4 py-8 text-sm text-[#71737a]">No users match the current filter.</div>}
              </div>
            </ScrollArea>
          </div>
        </section>

        <section className="rounded-[24px] border border-[#e6e6e7] bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Failures</div>
              <div className="text-lg font-extrabold">Recent provider errors</div>
            </div>
            <Separator orientation="vertical" className="h-6" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(overview.data?.recent_failures || []).slice(0, 6).map((item, index) => (
              <div key={`${item.metric_kind}-${index}`} className="rounded-[18px] border border-[#e6e6e7] bg-[#f8f8f8] p-4">
                <div className="text-[11px] font-bold uppercase text-[#71737a]">{item.metric_kind}</div>
                <div className="mt-2 text-sm font-bold text-[#0c0a09]">{item.step_name || "step"}</div>
                <div className="mt-1 text-[12px] text-[#71737a]">{item.provider || "provider"} - {shortDate(item.created_at)}</div>
                {item.error && <div className="mt-3 line-clamp-3 text-xs leading-5 text-red-600">{item.error}</div>}
              </div>
            ))}
            {!overview.data?.recent_failures?.length && <div className="text-sm text-[#71737a]">No failures recorded.</div>}
          </div>
        </section>
      </main>

      <UserDetailDialog user={selectedUser} open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}
