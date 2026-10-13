import { useState } from "react";

export function SideMenu({ children, side = "left" }) {
  const [shown, setShown] = useState(true);
  const isLeft = side === "left";

  const panelWidth = 500; // px
  const tabWidth = 48; // px visible when hidden
  const hiddenOffset = panelWidth - tabWidth; // how much to move off-screen

  const transform = isLeft
    ? shown
      ? "translateX(0)"
      : `translateX(-${hiddenOffset}px)`
    : shown
    ? "translateX(0)"
    : `translateX(${hiddenOffset}px)`;

  const containerStyle = {
    width: `${panelWidth}px`,
    top: "25%",
    transform,
    transitionProperty: "transform",
    transitionDuration: "600ms",
    transitionTimingFunction: "cubic-bezier(.34,1.56,.64,1)", // bouncy
  };

  const tabStyle = isLeft ? { right: -tabWidth / 2 } : { left: -tabWidth / 2 };

  return (
    <div
      style={containerStyle}
    className={`fixed z-20 ${isLeft ? "left-4" : "right-4"} transition-transform duration-600 flex 
      flex-col bg-white/20 border border-white backdrop-blur-sm rounded-2xl overflow-hidden 
      shadow-lg`}
    >
      <div className="min-h-[150px] max-h-[70vh] overflow-hidden p-4">{children}</div>

      <button
        aria-expanded={shown}
        onClick={() => setShown((s) => !s)}
        style={{ ...tabStyle }}
        className="absolute top-0 h-full w-12 flex items-center
         justify-center bg-white/80 blur-xl shadow-md text-black text-3xl"
      >
        <span className="text-xl select-none">{isLeft ? (shown ? "‹" : "›") : shown ? "›" : "‹"}</span>
      </button>
    </div>
  );
}
