// Hero adapted from 21st.dev "Hero AI Value Proposition" (uilayout.contact), rebuilt around AskMyDocs.
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Brain, FileText, GitCompare, Languages, MessagesSquare, MousePointer2, Network, PenLine, Quote, ShieldCheck, Sparkles,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { setValue } from "./streamlit";
import { TimelineAnimation } from "./ui/timeline-animation";

const DEMO = [
  { q: "What is the refund window in the contract?", a: "Customers can request a full refund within 30 days of purchase.", cite: "acme-services-agreement.md · section 4" },
  { q: "Summarise the Q3 risks in one line.", a: "Supplier delays and a 12% rise in cloud costs are the two main risks.", cite: "northwind-q3-2026-report.md · section 5" },
];

const TOOLS = [
  { icon: FileText, label: "Summary", active: true },
  { icon: Brain, label: "Quiz & flashcards" },
  { icon: Network, label: "Mind map" },
  { icon: GitCompare, label: "Compare" },
];

const FEATURES = [
  { icon: MessagesSquare, title: "Chat with citations", text: "Every answer names the file and page it came from, or says it can't find it." },
  { icon: FileText, title: "Summaries & insights", text: "TL;DR, key numbers, dates, action items and risks pulled out for you." },
  { icon: Brain, title: "Quizzes & flashcards", text: "Turn a report or chapter into a scored quiz or a study deck." },
  { icon: Network, title: "Mind maps", text: "See how a long document is structured before you read it." },
  { icon: GitCompare, title: "Compare documents", text: "Two contracts or proposals, side by side: what differs." },
  { icon: PenLine, title: "Writer", text: "Emails, reports and posts grounded in your files." },
];

function ChatDemo() {
  const reduce = useReducedMotion();
  const [turn, setTurn] = useState(0);
  const [stage, setStage] = useState(reduce ? 2 : 0); // 0 question, 1 typing, 2 answer

  useEffect(() => {
    if (reduce) return;
    const id = setTimeout(() => {
      if (stage < 2) setStage(stage + 1);
      else { setTurn((turn + 1) % DEMO.length); setStage(0); }
    }, [900, 1300, 4200][stage]);
    return () => clearTimeout(id);
  }, [stage, turn, reduce]);

  const item = DEMO[turn];
  return (
    <div className="flex min-h-[220px] flex-col gap-3" aria-label="Example conversation">
      <AnimatePresence mode="popLayout">
        <motion.div key={`q${turn}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          className="max-w-[85%] self-end rounded-2xl rounded-br-md bg-neutral-900 px-4 py-2.5 text-sm text-white">
          {item.q}
        </motion.div>
        {stage === 1 && (
          <motion.div key={`t${turn}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex gap-1 self-start rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3.5" aria-label="Answer loading">
            {[0, 1, 2].map((i) => (
              <motion.i key={i} className="block h-1.5 w-1.5 rounded-full bg-neutral-400"
                animate={{ y: [0, -4, 0] }} transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.12 }} />
            ))}
          </motion.div>
        )}
        {stage === 2 && (
          <motion.div key={`a${turn}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="max-w-[90%] self-start rounded-2xl rounded-bl-md border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm leading-relaxed text-neutral-800">
            {item.a}
            <motion.span initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.25 }}
              className="mt-2 flex w-fit items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
              <Quote size={11} aria-hidden="true" />{item.cite}
            </motion.span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Landing() {
  const timelineRef = useRef(null);
  const T = (props) => <TimelineAnimation once timelineRef={timelineRef} {...props} />;

  return (
    <section ref={timelineRef} className="relative overflow-hidden bg-[#f9f9f9] text-[#111]">
      <article className="border-y border-zinc-200">
        <div className="mx-auto flex max-w-6xl flex-col items-center space-y-4 border-x border-zinc-200 px-6 py-10 text-center">
          <T as="span" animationNum={1}
            className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-500 shadow-sm">
            <ShieldCheck size={14} className="text-emerald-600" aria-hidden="true" />Private by default · Gemini & OpenAI
          </T>
          <T as="h1" animationNum={2} className="text-4xl font-semibold leading-[1.05] tracking-tight text-slate-900 md:text-6xl">
            Ask your documents. <br className="hidden md:block" />Get answers with sources.
          </T>
          <T as="p" animationNum={3} className="max-w-3xl text-base font-medium leading-relaxed text-neutral-400 md:text-lg">
            Upload PDFs or paste links, then chat with them, summarise them, quiz yourself and draft content.
            Every answer is grounded in your files and cites the page.
          </T>
        </div>
      </article>

      <div className="border-b border-zinc-200">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 border-x border-zinc-200 p-8">
          <T as="button" animationNum={4} onClick={() => setValue({ event: "sample", t: Date.now() })}
            whileTap={{ scale: 0.97 }}
            className="flex cursor-pointer items-center gap-2 rounded-full border-4 border-white/80 bg-neutral-900 px-8 py-3.5 text-base font-bold text-white shadow-2xl transition-colors hover:bg-black focus-visible:outline-3 focus-visible:outline-blue-500">
            <Sparkles size={18} aria-hidden="true" />Try with sample documents
          </T>
          <T as="p" animationNum={5} className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400">
            Or upload PDFs and links in the sidebar
          </T>
          <div className="flex flex-wrap justify-center gap-2">
            {[[FileText, "PDF & web pages"], [Languages, "10 answer languages"], [Quote, "Page-level citations"]].map(([Icon, label], i) => (
              <T key={label} animationNum={6 + i * 0.3}
                className="flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
                <Icon size={13} aria-hidden="true" />{label}
              </T>
            ))}
          </div>
        </div>
      </div>

      {/* Product mockup */}
      <div className="border-b border-zinc-200">
        <div className="mx-auto max-w-6xl border-x border-zinc-200 p-3">
          <T animationNum={7} className="relative rounded-4xl border border-zinc-200 bg-white p-2 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.08)]">
            <div className="relative overflow-hidden rounded-4xl bg-linear-to-b from-neutral-200 from-50% to-blue-400/80 px-4 pt-16 md:px-10">
              <T animationNum={8} className="relative z-10 mx-auto max-w-5xl">
                <T animationNum={10} className="absolute -top-8 left-16 -z-10 h-full w-[85%] rounded-t-4xl border border-neutral-100/50 bg-neutral-100" />
                <T animationNum={11} className="absolute -top-4 left-5 -z-10 h-full w-[95%] rounded-t-4xl border border-neutral-100/50 bg-neutral-50" />
                <T animationNum={9} className="flex flex-col gap-8 rounded-t-4xl border border-neutral-100/50 bg-white p-6 md:p-10">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 text-sm">
                      <span className="h-3 w-3 rounded-full bg-emerald-500" />
                      <span className="font-medium text-neutral-400">My documents /</span>
                      <span className="font-bold text-slate-800">acme-services-agreement.md</span>
                    </div>
                    <span className="hidden rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-500 sm:block">2 documents</span>
                  </div>
                  <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
                    <div className="lg:col-span-7">
                      <p className="mb-4 text-xs font-bold uppercase tracking-widest text-slate-400">Chat</p>
                      <ChatDemo />
                    </div>
                    <div className="lg:col-span-5">
                      <T animationNum={12} className="rounded-4xl border border-neutral-100 bg-[#fcfcfc] p-6 shadow-sm">
                        <p className="mb-6 text-[11px] font-bold uppercase tracking-widest text-slate-900">What do you want to make?</p>
                        <div className="grid grid-cols-2 gap-2">
                          {TOOLS.map(({ icon: Icon, label, active }, i) => (
                            <T key={label} animationNum={13 + i}
                              className={active
                                ? "relative flex flex-col gap-3 rounded-2xl border-2 border-blue-500 bg-white p-4 shadow-2xl"
                                : "flex flex-col gap-3 rounded-2xl border border-neutral-100 bg-white/80 p-4 opacity-80 grayscale"}>
                              <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${active ? "bg-blue-50 text-blue-500" : "bg-neutral-100 text-neutral-400"}`}>
                                <Icon size={18} aria-hidden="true" />
                              </div>
                              <p className="text-[11px] font-bold text-slate-900">{label}</p>
                              {active && <MousePointer2 className="absolute right-3 top-3 fill-slate-900 text-slate-900" size={18} aria-hidden="true" />}
                            </T>
                          ))}
                        </div>
                      </T>
                    </div>
                  </div>
                </T>
              </T>
            </div>
          </T>
        </div>
      </div>

      {/* Features, in the same ruled grid */}
      <div className="border-b border-zinc-200">
        <div className="mx-auto max-w-6xl border-x border-zinc-200">
          <div className="border-b border-zinc-200 px-6 py-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400">Studio</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">One upload, eight ways to use it</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }, i) => (
              <motion.div key={title} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }} transition={{ delay: (i % 3) * 0.06, duration: 0.4 }}
                className="group border-zinc-200 p-6 transition-colors hover:bg-white max-lg:border-b lg:[&:nth-child(-n+3)]:border-b lg:[&:not(:nth-child(3n))]:border-r sm:max-lg:[&:nth-child(odd)]:border-r">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100 text-neutral-500 transition-colors group-hover:bg-blue-50 group-hover:text-blue-600">
                  <Icon size={19} aria-hidden="true" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">{title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-neutral-500">{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
