import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CasePage } from "@/features/case/CasePage";
import { QueuePage } from "@/features/queue/QueuePage";
import { ResultsPage } from "@/features/results/ResultsPage";
import { StreamPage } from "@/features/stream/StreamPage";
import { AppShell } from "./AppShell";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/stream" replace /> },
      { path: "stream", element: <StreamPage /> },
      { path: "queue", element: <QueuePage /> },
      { path: "cases/:caseId", element: <CasePage /> },
      { path: "results", element: <ResultsPage /> },
      { path: "*", element: <Navigate to="/stream" replace /> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <RouterProvider router={router} />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
