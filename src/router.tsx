import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { ApiError } from "@/lib/api";
import { routeTree } from "./routeTree.gen";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: true,
      // Retrying won't fix auth or validation errors
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

export const router = createRouter({
  routeTree,
  context: { queryClient },
  scrollRestoration: true,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
