import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { BookOpen, Clock, Files, Type } from "lucide-react";
import { useEffect } from "react";

function Counter({ value, suffix = "" }) {
  const reduce = useReducedMotion();
  const count = useMotionValue(reduce ? value : 0);
  const text = useTransform(count, (v) => Math.round(v).toLocaleString() + suffix);
  useEffect(() => {
    if (reduce) { count.set(value); return; }
    const controls = animate(count, value, { duration: 0.9, ease: [0.22, 1, 0.36, 1] });
    return () => controls.stop();
  }, [value, reduce]);
  return <motion.span>{text}</motion.span>;
}

export default function Stats({ stats }) {
  const items = [
    { icon: Files, label: "Documents", value: stats.documents },
    { icon: BookOpen, label: "Pages", value: stats.pages },
    { icon: Type, label: "Words", value: stats.words },
    { icon: Clock, label: "Reading time", value: stats.minutes, suffix: " min" },
  ];
  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-2xl border border-zinc-200 bg-white md:grid-cols-4">
      {items.map(({ icon: Icon, label, value, suffix }, i) => (
        <motion.div key={label} initial={{ opacity: 0, filter: "blur(6px)" }} animate={{ opacity: 1, filter: "blur(0px)" }}
          transition={{ delay: i * 0.08, duration: 0.4 }}
          className="flex flex-col gap-1 border-zinc-200 px-5 py-4 [&:not(:last-child)]:border-r max-md:[&:nth-child(2)]:border-r-0 max-md:[&:nth-child(-n+2)]:border-b">
          <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-400">
            <Icon size={12} aria-hidden="true" />{label}
          </span>
          <span className="text-2xl font-semibold tabular-nums tracking-tight text-slate-900"><Counter value={value} suffix={suffix} /></span>
        </motion.div>
      ))}
    </div>
  );
}
