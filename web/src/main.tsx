import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Shell } from "./app/Shell";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

createRoot(root).render(
  <StrictMode>
    <Shell />
  </StrictMode>,
);
