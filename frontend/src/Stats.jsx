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
    <div className="stats">
      {items.map(({ icon: Icon, label, value, suffix }, i) => (
        <motion.div key={label} className="stat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.4 }}>
          <div className="icon" style={{ marginBottom: 0 }}><Icon size={19} aria-hidden="true" /></div>
          <div><div className="v"><Counter value={value} suffix={suffix} /></div><div className="l">{label}</div></div>
        </motion.div>
      ))}
    </div>
  );
}
