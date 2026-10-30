import type { QueryClient } from "@tanstack/react-query";
import { Link, Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { Toaster } from "@/components/ui/sonner";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: () => (
    <>
      <Outlet />
      <Toaster position="top-center" theme="dark" richColors />
    </>
  ),
  notFoundComponent: NotFound,
  errorComponent: ({ error, reset }) => (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold">This page didn't load</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <div className="mt-6 flex justify-center gap-2">
          <button className="btn" onClick={reset}>
            Try again
          </button>
          <Link to="/" className="btn btn-outline">
            Go home
          </Link>
        </div>
      </div>
    </div>
  ),
});

function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <p className="mt-4 text-muted-foreground">This page wandered off.</p>
        <Link to="/" className="btn mt-6">
          Go home
        </Link>
      </div>
    </div>
  );
}
