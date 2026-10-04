import { MotionConfig } from "framer-motion";
import { createRoot } from "react-dom/client";
import Flashcards from "./Flashcards";
import Landing from "./Landing";
import Stats from "./Stats";
import { useAutoHeight, useStreamlitArgs } from "./streamlit";
import "./styles.css";

function App() {
  const args = useStreamlitArgs();
  useAutoHeight();
  if (!args) return null;
  let view = null;
  if (args.view === "landing") view = <Landing />;
  else if (args.view === "stats") view = <Stats stats={args.stats} />;
  else if (args.view === "flashcards") view = <Flashcards cards={args.cards || []} />;
  return <MotionConfig reducedMotion="user">{view}</MotionConfig>;
}

createRoot(document.getElementById("root")).render(<App />);
