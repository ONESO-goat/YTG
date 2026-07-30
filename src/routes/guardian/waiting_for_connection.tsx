import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router';
import { api, localSession } from '@/lib/api';
import { AppShell } from '@/components/AppShell';

const [numberId, setNumberId] = useState(0);
const nav = useNavigate();
export const Route = createFileRoute('/guardian/waiting_for_connection')({
  component: RouteComponent,
})

const [session, setSession] = useState<any>(null);

  // 2. Safely read localStorage ONLY on the client after mount
  useEffect(() => {
    const activeSession = localSession.get();
    if (!activeSession) {
      nav({ to: "/auth" });
      return;
    }
    setSession(activeSession);
  }, [nav]);

useEffect( () =>{
 
    (async () =>{
        const u: any = api.getUser(session?.user_id);
        const connection: any = await api.getConnectionIfUserHasOne(u?.id);
        if (connection !== null){
            nav({to: "/guardian/dashboard"});
            return;
        }
        setNumberId(u?.number_id);
    })
})


function RouteComponent() {
  return (
  <AppShell variant="guardian">
  <div>
    ID: {numberId}
    (Share this to trusted members)
    <br></br>
    Waiting for connection...
    
    </div>
    </AppShell>
    )
}
