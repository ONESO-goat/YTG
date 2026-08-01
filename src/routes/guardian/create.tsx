import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Shield } from "lucide-react";
import { api, localSession, pickId } from "@/lib/api";
import { toast } from "sonner";

const searchSchema = z.object({
  type: z.enum(["family", "personal", "dependent"]).catch("personal"),
});

export const Route = createFileRoute("/guardian/create")({
  head: () => ({ meta: [{ title: "Create Guardian — YTG" }] }),
  validateSearch: searchSchema,
  component: CreateGuardian,
});

function CreateGuardian() {
  const nav = useNavigate();
  const { type } = Route.useSearch();
  const [name, setName] = useState("");
  const [depIdOrUsername, setDepIdOrUsername] = useState("");
  const [depNumberId, setDepNumberId] = useState(0);
  const [step, setStep] = useState<"create" | "connect">("create");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const s = localSession.get();
    if (!s) nav({ to: "/auth" });
  }, [nav]);

  async function create() {
    const s = localSession.get();
    if (!s) return;
    setBusy(true);
    try {
      const r: any = await api.createGuardian({
        owner_id: s.user_id,
        name: name || (type === "family" ? "Family Guardian" : "Personal Guardian"),
        guardian_type: type,
      });

      let gid = pickId(r, "guardian_id", "id");
   
      if (!gid) {
        gid = r.id;
        if (!gid){
          throw new Error("Backend did not return a guardian id");
        }
      }
      localSession.patch({ role: "guardian", guardian_id: gid });
      toast.success("Guardian created");
      if (type === "family") setStep("connect");
      else nav({ to: "/guardian/dashboard" });
    } catch (err: any) {
      toast.error(err?.message || "Could not create guardian");
    } finally {
      setBusy(false);
    }
  }

  async function connect() {
    const s = localSession.get();
    if (!s?.guardian_id) return;
    setBusy(true);
    try {
      await api.addConnection(s.guardian_id, { user_number_id: depNumberId, relationship: "offspring" });
      toast.success("Connected");
      nav({ to: "/guardian/dashboard" });
    } catch (err: any) {
      toast.error(err?.message || "Could not connect dependent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-xl">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2 font-display text-2xl font-extrabold">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-primary text-primary-foreground shadow-glow">
            <Shield className="h-5 w-5" />
          </span>
          <span className="bg-gradient-primary bg-clip-text text-transparent">YTG</span>
        </Link>
        <div className="duo-card p-8">
          {step === "create" && (
            <>
              <h1 className="font-display text-3xl font-extrabold">Name your Guardian</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                A label you'll see across your dashboards.
              </p>
              <div className="mt-6 space-y-4">
                <div>
                  <Label htmlFor="gname">Guardian name</Label>
                  <Input
                    id="gname"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={type === "family" ? "The Smith Household" : "My Guardian"}
                  />
                </div>
                <button className="duo-btn duo-btn-lg w-full" onClick={create} disabled={busy}>
                  {busy ? "Creating..." : "Create Guardian"}
                </button>
              </div>
            </>
          )}

          {step === "connect" && (
            <>
              <h1 className="font-display text-3xl font-extrabold">Connect a dependent</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Enter a user ID to connect them. You can add more later.
              </p>
              <div className="mt-6 space-y-4">
                <div>
                  <Label htmlFor="dep">Dependent user number ID</Label>
<Input 
  id="dep" 
  type="text" // Change to text
  value={depNumberId} 
  onChange={(e) => {
    const val = e.target.value;
    // Regex safely checks the exact string typed
    if (/^\d*$/.test(val)) {
      setDepNumberId(val === '' ? 0 : Number(val)); // Keeps your number state happy
    }
  }} 
  placeholder="user_..." 
/>
                </div>
                <div className="flex gap-2">
                  <button
                    className="duo-btn duo-btn-outline flex-1"
                    onClick={() => nav({ to: "/guardian/dashboard" })}
                  >
                    Skip
                  </button>
                  <button className="duo-btn flex-1" onClick={connect} disabled={busy || !depNumberId}>
                    Connect
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
