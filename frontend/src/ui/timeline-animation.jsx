// Port of 21st.dev's TimelineAnimation helper (uilayout): elements blur and rise into view in sequence.
import { motion, useInView } from "framer-motion";

const variants = {
  hidden: { opacity: 0, y: -20, filter: "blur(10px)" },
  visible: (i) => ({ opacity: 1, y: 0, filter: "blur(0px)", transition: { delay: i * 0.12, duration: 0.5 } }),
};

export function TimelineAnimation({ as = "div", animationNum = 0, timelineRef, once = true, className, children, ...props }) {
  const inView = useInView(timelineRef, { once });
  const Tag = motion[as] ?? motion.div;
  return (
    <Tag custom={animationNum} variants={variants} initial="hidden" animate={inView ? "visible" : "hidden"} className={className} {...props}>
      {children}
    </Tag>
  );
}
