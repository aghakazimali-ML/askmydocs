import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { BookOpen, Brain, FileText, GitCompare, Languages, MessagesSquare, Network, PenLine, Quote, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { setValue } from "./streamlit";

const EASE_OUT = [0.22, 1, 0.36, 1];

const FEATURES = [
  { icon: MessagesSquare, title: "Chat with citations", text: "Every answer names the file and page it came from, or says it can't find it." },
  { icon: FileText, title: "Summaries & insights", text: "TL;DR, key numbers, dates, action items and risks pulled out for you." },
  { icon: Brain, title: "Quizzes & flashcards", text: "Turn a report or textbook chapter into a scored quiz or a study deck." },
  { icon: Network, title: "Mind maps", text: "See how a long document is structured before you read it." },
  { icon: GitCompare, title: "Compare documents", text: "Two contracts, two proposals: a side-by-side table of what differs." },
  { icon: PenLine, title: "Writer", text: "Draft emails, reports and LinkedIn posts grounded in your files." },
];

const STEPS = [
  { title: "Add documents", text: "Upload PDFs or paste links in the sidebar." },
  { title: "Process", text: "Text is split, embedded and indexed in seconds." },
  { title: "Ask and create", text: "Chat, or open Studio for summaries, quizzes and more." },
];

// Scripted demo conversation for the product preview.
const DEMO = [
  { q: "What is the refund window in the contract?", a: "Customers can request a full refund within 30 days of purchase.", cites: ["acme-services-agreement.md · section 4"] },
  { q: "Summarise the Q3 risks in one line.", a: "Supplier delays and a 12% rise in cloud costs are the two main risks.", cites: ["northwind-q3-2026-report.md · section 5"] },
];

function DemoWindow() {
  const reduce = useReducedMotion();
  const [turn, setTurn] = useState(0);
  const [stage, setStage] = useState(reduce ? 2 : 0); // 0 question, 1 typing, 2 answer

  useEffect(() => {
    if (reduce) return;
    const timings = [900, 1300, 4200];
    const id = setTimeout(() => {
      if (stage < 2) setStage(stage + 1);
      else { setTurn((turn + 1) % DEMO.length); setStage(0); }
    }, timings[stage]);
    return () => clearTimeout(id);
  }, [stage, turn, reduce]);

  const item = DEMO[turn];
  return (
    <motion.div className="window" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.25 }} aria-label="Example conversation">
      <div className="window-bar"><span className="lights"><i /><i /><i /></span>AskMyDocs</div>
      <div className="window-body">
        <div className="file"><FileText size={16} aria-hidden="true" />acme-services-agreement.md, northwind-q3-report.md<small>2 documents</small></div>
        <AnimatePresence mode="popLayout">
          <motion.div key={`q${turn}`} className="bubble user" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3, ease: EASE_OUT }}>
            {item.q}
          </motion.div>
          {stage === 1 && (
            <motion.div key={`t${turn}`} className="bubble bot typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} aria-label="Answer loading">
              {[0, 1, 2].map((i) => (
                <motion.i key={i} animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.12, ease: "easeInOut" }} />
              ))}
            </motion.div>
          )}
          {stage === 2 && (
            <motion.div key={`a${turn}`} className="bubble bot" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.35, ease: EASE_OUT }}>
              {item.a}
              <div>
                {item.cites.map((c, i) => (
                  <motion.span key={c} className="cite" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.25 + i * 0.12, type: "spring", stiffness: 420, damping: 26 }}>
                    <Quote size={11} aria-hidden="true" />{c}
                  </motion.span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

const reveal = {
  hidden: { opacity: 0, y: 18 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT, delay: i * 0.06 } }),
};

export default function Landing() {
  const words = ["Ask", "your", "documents."];
  return (
    <div>
      <section className="hero">
        <div>
          <motion.span className="eyebrow" initial="hidden" animate="show" variants={reveal}>
            <span className="dot" aria-hidden="true" />Retrieval-augmented AI · Gemini & OpenAI
          </motion.span>
          <h1 className="title">
            {words.map((w, i) => (
              <motion.span key={w} style={{ display: "inline-block", marginRight: "0.25em" }} initial="hidden" animate="show" variants={reveal} custom={i + 1}>{w}</motion.span>
            ))}
            <br />
            <motion.span className="hl" style={{ display: "inline-block" }} initial="hidden" animate="show" variants={reveal} custom={4}>Get answers with sources.</motion.span>
          </h1>
          <motion.p className="lead" initial="hidden" animate="show" variants={reveal} custom={5}>
            Upload PDFs or paste links, then chat with them, summarise them, quiz yourself and draft content. Nothing is made up: every answer is grounded in your files.
          </motion.p>
          <motion.div className="ctas" initial="hidden" animate="show" variants={reveal} custom={6}>
            <motion.button className="btn primary" whileTap={{ scale: 0.97 }} onClick={() => setValue({ event: "sample", t: Date.now() })}>
              <Sparkles size={18} aria-hidden="true" />Try with sample documents
            </motion.button>
            <span className="hint">Loads a sample contract and Q3 report. <Upload size={14} aria-hidden="true" style={{ verticalAlign: "-2px" }} /> Or upload PDFs in the sidebar.</span>
          </motion.div>
          <motion.div className="trust" initial="hidden" animate="show" variants={reveal} custom={7}>
            <span><ShieldCheck size={15} aria-hidden="true" />Answers only from your files</span>
            <span><Languages size={15} aria-hidden="true" />10 answer languages</span>
            <span><BookOpen size={15} aria-hidden="true" />Page-level citations</span>
          </motion.div>
        </div>
        <DemoWindow />
      </section>

      <div className="section-label">Features</div>
      <h2 className="section-title">One upload, eight ways to use it</h2>
      <div className="grid">
        {FEATURES.map(({ icon: Icon, title, text }, i) => (
          <motion.div key={title} className="feature" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }} variants={reveal} custom={i} whileHover={{ y: -3 }}>
            <div className="icon"><Icon size={20} aria-hidden="true" /></div>
            <h3>{title}</h3>
            <p>{text}</p>
          </motion.div>
        ))}
      </div>

      <div className="section-label">How it works</div>
      <div className="steps">
        {STEPS.map((s, i) => (
          <motion.div key={s.title} className="step" initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.4 }} variants={reveal} custom={i}>
            <div className="n">0{i + 1}</div>
            <h4>{s.title}</h4>
            <p>{s.text}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
