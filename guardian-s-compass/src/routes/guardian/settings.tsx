import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, localSession } from "@/lib/api";
import { toast } from "sonner";
import { X, Plus } from "lucide-react";

export const Route = createFileRoute("/guardian/settings")({
  head: () => ({ meta: [{ title: "Settings — YTG" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const nav = useNavigate();
  const [strictness, setStrictness] = useState("normal");
  const [newConnection, setNewConnection] = useState<number | "">(0);
  const [connections, setConnections] = useState<any[]>([]);
  const [isPersonalAccount, setIsPersonalAccount] = useState(false);

  const [warning, setWarning] = useState("Please skip this one for me, okay?");
  const [applause, setApplause] = useState("Proud of you for moving past that ❤️");
  const [pointsLoss, setPointsLoss] = useState(false);
  const [penalty, setPenalty] = useState(50);
  const [restrictions, setRestrictions] = useState<string[]>([]);
  const [newRestriction, setNewRestriction] = useState("");
  const session = typeof window !== "undefined" ? localSession.get() : null;

  useEffect(() => {
    if (!session) {
      nav({ to: "/auth" });
      return;
    }
    if (!session.guardian_id) return;
    (async () => {
      try {
        const u: any = await api.getGuardian(session.guardian_id!);
        const s: any = await api.getSettings(session.guardian_id!);
        setIsPersonalAccount(u.guardian_type === "personal");
        setStrictness(s.strictness || "normal");
        setWarning(s?.custom_warning_messages?.warning || warning);
        setApplause(s?.custom_warning_messages?.applause || applause);
        setPointsLoss(!!s.points_loss_enabled);
        setPenalty(s.base_points_lost ?? 50);
      } catch {}
      try {
        const r: any = await api.fetchRestrictions(session.guardian_id!);
        const c: any = await api.connections(session.guardian_id!);
        console.log("RAW CONNECTIONS RESPONSE:", c);

        // Fallback in case the API wraps the array in an object property (adjust key if needed, e.g., c.data or c.connections)
        //const connectionList = Array.isArray(c) ? c : (c?.connections || c?.data || []);

        console.log(`GUARDIAN CONNECTS: ${c.length}`);
        setRestrictions(r || []);
        setConnections(c || []);
      } catch {}
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addConnections() {
  if (!newConnection || !session?.guardian_id) return;
  const u: any = await api.getUserByNumberId(Number(newConnection));
  if (!u) return;
  
  setConnections((prev) => {
    // Check if user is already in the array by user_id
    if (prev.some((item) => item.user_id === u.user_id)) return prev;
    // Store the whole object instead of just the name string
    return [...prev, u];
  });
  
  setNewConnection(0);
  
  try {
    await api.addConnection(session.guardian_id, { 
      user_number_id: u.number_id, 
      relationship: "offspring" 
    });
  } catch (e) {
    console.log(`ERROR ADDING CONNECTION: ${e}`);
  }
}

  async function removeConnection(numberId: number|string) {
    if (!numberId) return;
    
    setConnections((prev) => prev.filter((user) => user.user_id !== numberId));
    
    if (!session?.guardian_id) return;
    try {
      await api.removeConnection(session.guardian_id, numberId);
    } catch {}
  }

  async function addRestriction() {
    if (!newRestriction || !session?.guardian_id) return;
    const r = newRestriction.trim();
    setRestrictions((prev) => [...new Set([...prev, r])]);
    setNewRestriction("");
    try {
      await api.addRestriction(session.guardian_id, r);
    } catch (e) {
      console.log(`ERROR ADDING RESTRICTION: ${e}`);
    }
  }

  async function removeRestriction(r: string) {
    setRestrictions((prev) => prev.filter((x) => x !== r));
    if (!session?.guardian_id) return;
    try {
      await api.removeRestriction(session.guardian_id, r);
    } catch {}
  }

  async function save() {
    if (!session?.guardian_id) return;
    try {
      console.log(`WARNING: ${warning} -- APPLAUSE: ${applause}`);
      await api.updateSettings(session.guardian_id, {
        strictness,
        warning_message: warning,
        applause_message: applause,
        points_loss_enabled: pointsLoss,
        base_points_lost: penalty,
      });
      toast.success("Settings saved");
    } catch {
      toast.warning("Backend unreachable — settings kept locally");
    }
  }

  return (
    <AppShell variant="guardian">
      <h1 className="font-display text-3xl font-semibold">Guardian settings</h1>

      {!isPersonalAccount && (
        <section className="mt-6 rounded-2xl border border-border bg-card p-6 lg:col-span-2">
          <p className="text-sm font-medium text-muted-foreground mb-2">
            Connections
          </p>

          <h2 className="text-lg font-semibold">Connections</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Add connections to your guardian.
          </p>

          <div className="mt-4 flex gap-2">
            <Input 
              id="dep" 
              type="text" 
              value={newConnection === 0 ? '' : newConnection} 
              onChange={(e) => {
                const val = e.target.value;
                if (/^\d*$/.test(val)) {
                  setNewConnection(val === '' ? 0 : Number(val)); 
                }
              }} 
              placeholder="user number id" 
            />
            <Button type="button" onClick={addConnections}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {connections.length === 0 ? (
  <span className="text-sm text-muted-foreground">No connections yet.</span>
) : (
  connections.map((user, index) => (
    <span
      key={user.user_id ?? index}
      className="inline-flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-sm text-secondary-foreground"
    >
      {user.user_name}
      <button 
        type="button"
        onClick={() => removeConnection(user.user_id)} 
        className="hover:text-destructive"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  ))
)}
          </div>
        </section>
      )}

      <p className="mt-1 text-sm text-muted-foreground">
        Tune how YTG responds — the tone, the strictness, the rewards.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card p-6">
          <h2 className="text-lg font-semibold">Strictness</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            How aggressively should content be flagged?
          </p>
          <div className="mt-4">
            <Select value={strictness} onValueChange={setStrictness}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="weak">Weak — obvious only</SelectItem>
                <SelectItem value="normal">Normal — balanced</SelectItem>
                <SelectItem value="harsh">Harsh — cautious flagging</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-6">
          <h2 className="text-lg font-semibold">Point penalty</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Optional: lose points if a warning is ignored.
          </p>
          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm">Enable</span>
            <Switch checked={pointsLoss} onCheckedChange={setPointsLoss} />
          </div>
          <div className="mt-4">
            <Label htmlFor="pen">Points at stake</Label>
            <Input
              id="pen"
              type="number"
              disabled={!pointsLoss}
              value={penalty}
              onChange={(e) => setPenalty(Number(e.target.value))}
            />
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold">Restricted content</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Add categories YTG should look out for.
          </p>
          <div className="mt-4 flex gap-2">
            <Input
              placeholder="e.g. extremist content"
              value={newRestriction}
              onChange={(e) => setNewRestriction(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addRestriction())}
            />
            
            <Button type="button" onClick={addRestriction}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {restrictions.length === 0 ? (
              <span className="text-sm text-muted-foreground">No restrictions yet.</span>
            ) : (
              restrictions.map((r) => (
                <span
                  key={r}
                  className="inline-flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-sm text-secondary-foreground"
                >
                  {r}
                  <button type="button" onClick={() => removeRestriction(r)} className="hover:text-destructive">
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold">Your voice</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The messages shown to your dependent. Make them sound like you.
          </p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="warn">Warning message</Label>
              <Textarea
                id="warn"
                rows={3}
                value={warning}
                onChange={(e) => setWarning(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="app">Applause message</Label>
              <Textarea
                id="app"
                rows={3}
                value={applause}
                onChange={(e) => setApplause(e.target.value)}
              />
            </div>
          </div>
        </section>
      </div>

      <div className="mt-6 flex justify-end">
        <Button onClick={save}>Save settings</Button>
      </div>
    </AppShell>
  );
}