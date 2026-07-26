import React, { useEffect, useState } from "react";
import { useToast } from "@/components/ui/use-toast";
import AppChrome from "@/components/dysentry/AppChrome";
import Button from "@/components/dysentry/Button";
import { Check, Plug, Trash2 } from "lucide-react";
import db from "@/api/base44Client";
import { disconnectSocialAccount, listSocialAccounts, startSocialConnect } from "@/api/dysentryClient";

const platforms = [
  { id: "youtube", label: "YouTube", note: "Connect your YouTube channel for upload and scheduled publishing." },
  { id: "tiktok", label: "TikTok", note: "Connect TikTok to publish shorts from completed productions." },
];

export default function Settings() {
  const { toast } = useToast();
  const [me, setMe] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [currentUser, socialAccounts] = await Promise.all([
          db.auth.me(),
          listSocialAccounts(),
        ]);
        setMe(currentUser);
        setAccounts(socialAccounts);
      } catch (error) {
        toast({ title: "Could not load settings", description: error.message, variant: "destructive" });
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const handleConnect = async (platform) => {
    try {
      const response = await startSocialConnect(platform.id);
      window.location.href = response.authorization_url;
    } catch (error) {
      toast({
        title: `Could not start ${platform.label} connection`,
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleDisconnect = async (accountId) => {
    try {
      await disconnectSocialAccount(accountId);
      setAccounts((prev) => prev.filter((account) => account.id !== accountId));
      toast({ title: "Account disconnected" });
    } catch (error) {
      toast({ title: "Could not disconnect account", description: error.message, variant: "destructive" });
    }
  };

  return (
    <AppChrome breadcrumb={[{ label: "Studio", path: "/dashboard" }, { label: "Settings" }]}>
      <div className="mx-auto max-w-3xl px-8 py-10">
        <h1 className="font-display mb-1 text-[26px] font-medium text-ink">Settings</h1>
        <p className="mb-10 text-[14px] text-steel">Manage your connected channels and publishing access.</p>

        <section className="mb-12 rounded-lg border border-fog p-5">
          <h2 className="mb-4 text-[16px] font-medium text-ink">Account</h2>
          {loading ? (
            <p className="text-[13px] text-steel">Loading account…</p>
          ) : (
            <div className="space-y-2">
              <p className="text-[14px] text-ink">{me?.email || "Unknown user"}</p>
              <p className="text-[12px] text-steel">Authenticated through Dysentry backend sessions.</p>
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-4 text-[16px] font-medium text-ink">Connections</h2>
          <div className="space-y-3">
            {platforms.map((p) => (
              <div
                key={p.id}
                className="flex flex-col gap-3 rounded-lg border border-fog p-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-[15px] font-medium text-ink">{p.label}</p>
                  <p className="mt-0.5 text-[13px] text-steel" style={{ lineHeight: 1.45 }}>
                    {p.note}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {accounts.some((account) => account.platform === p.id && account.status === "connected") && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 px-2.5 py-1 text-[11px] text-emerald-700">
                      <Check className="h-3.5 w-3.5" /> Connected
                    </span>
                  )}
                  <Button
                    variant="outline"
                    className="px-4 py-2 text-[13px]"
                    onClick={() => handleConnect(p)}
                  >
                    <Plug className="h-4 w-4" /> Connect
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <h2 className="mb-4 text-[16px] font-medium text-ink">Connected accounts</h2>
          <div className="divide-y divide-mist rounded-lg border border-fog">
            {accounts.length === 0 ? (
              <div className="p-5 text-[13px] text-steel">No social accounts connected yet.</div>
            ) : (
              accounts.map((account) => (
                <div key={account.id} className="flex items-center justify-between p-5">
                  <div>
                    <p className="text-[15px] text-ink">{account.display_name || account.platform}</p>
                    <p className="mt-0.5 text-[13px] text-steel" style={{ lineHeight: 1.45 }}>
                      {account.platform} · {account.status}
                    </p>
                  </div>
                  <Button variant="outline" className="px-3 py-2 text-[12px]" onClick={() => handleDisconnect(account.id)}>
                    <Trash2 className="h-3.5 w-3.5" /> Disconnect
                  </Button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </AppChrome>
  );
}
