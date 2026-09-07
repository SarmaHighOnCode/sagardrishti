import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "./app/Shell";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

// One client for the app's lifetime. Not per-render — TanStack Query's
// cache is what lets a refetch update the map without a full remount
// (see MapCanvas's setProps-based layer update).
const queryClient = new QueryClient();

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Shell />
    </QueryClientProvider>
  </StrictMode>,
);
