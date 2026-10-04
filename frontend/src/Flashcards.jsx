import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight, RotateCcw, Shuffle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

export default function Flashcards({ cards: initial }) {
  const reduce = useReducedMotion();
  const [cards, setCards] = useState(initial);
  const [idx, setIdx] = useState(0);
  const [dir, setDir] = useState(1);
  const [flipped, setFlipped] = useState(false);

  useEffect(() => { setCards(initial); setIdx(0); setFlipped(false); }, [JSON.stringify(initial)]);

  const go = useCallback((step) => {
    setDir(step); setFlipped(false);
    setIdx((i) => (i + step + cards.length) % cards.length);
  }, [cards.length]);
  const shuffle = () => { setCards([...cards].sort(() => Math.random() - 0.5)); setIdx(0); setFlipped(false); };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === " " || e.key === "Enter") { e.preventDefault(); setFlipped((f) => !f); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  if (!cards.length) return null;
  const card = cards[idx];
  const slide = reduce ? {} : { initial: { opacity: 0, x: 60 * dir }, animate: { opacity: 1, x: 0 }, exit: { opacity: 0, x: -60 * dir } };

  return (
    <div className="px-0.5 pb-2 pt-1">
      <AnimatePresence mode="wait" custom={dir}>
        <motion.div key={idx + card.front} {...slide} transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          drag={reduce ? false : "x"} dragConstraints={{ left: 0, right: 0 }} dragElastic={0.4}
          onDragEnd={(_, info) => { if (info.offset.x < -80) go(1); else if (info.offset.x > 80) go(-1); }}>
          <div className="h-[260px] cursor-pointer [perspective:1400px] focus-visible:outline-3 focus-visible:outline-blue-500 rounded-3xl" role="button" tabIndex={0} aria-label={flipped ? `Answer: ${card.back}` : `Question: ${card.front}. Press to flip.`} onClick={() => setFlipped(!flipped)}>
            <motion.div className="relative h-full w-full [transform-style:preserve-3d]" animate={{ rotateY: flipped ? 180 : 0 }} transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 24 }}>
              <div className="face border border-zinc-200 bg-white text-slate-900 shadow-[0_20px_60px_-25px_rgba(0,0,0,0.15)]"><small>Question · {idx + 1} / {cards.length}</small><div className="text-xl font-semibold leading-snug tracking-tight">{card.front}</div></div>
              <div className="face bg-neutral-900 text-white [transform:rotateY(180deg)]"><small>Answer</small><div className="text-xl font-semibold leading-snug tracking-tight">{card.back}</div></div>
            </motion.div>
          </div>
        </motion.div>
      </AnimatePresence>
      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="flex gap-2">
          <button className="iconbtn" onClick={() => go(-1)} aria-label="Previous card"><ChevronLeft size={20} /></button>
          <button className="iconbtn" onClick={() => go(1)} aria-label="Next card"><ChevronRight size={20} /></button>
        </div>
        <div className="flex flex-wrap justify-center gap-1.5" aria-hidden="true">{cards.map((_, i) => <motion.i key={i} layout className={`block h-2 rounded-full ${i === idx ? "w-6 bg-neutral-900" : "w-2 bg-zinc-300"}`} />)}</div>
        <div className="flex gap-2">
          <button className="iconbtn" onClick={() => setFlipped(!flipped)} aria-label="Flip card"><RotateCcw size={18} /></button>
          <button className="iconbtn" onClick={shuffle} aria-label="Shuffle cards"><Shuffle size={18} /></button>
        </div>
      </div>
      <div className="mt-2.5 text-center text-xs text-neutral-400">Click the card or press Space to flip · arrow keys or swipe to move</div>
    </div>
  );
}
