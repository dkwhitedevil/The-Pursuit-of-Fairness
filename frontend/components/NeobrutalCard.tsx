"use client";
import React from "react";

type Props = {
  title?: string;
  subtitle?: string;
  accent?: string;
  children?: React.ReactNode;
  className?: string;
};

export default function NeobrutalCard({ title, subtitle, accent = "#ff7a18", children, className }: Props) {
  return (
    <div
      className={`neo-card relative p-6 rounded-md bg-white border-4 border-black ${className || ""}`}
      style={{
        boxShadow: `8px 8px 0 0 ${accent}55`,
      }}
    >
      {title && <h3 className="neo-title text-3xl font-extrabold mb-2">{title}</h3>}
      {subtitle && <div className="neo-sub text-sm mb-4 opacity-90">{subtitle}</div>}
      <div className="neo-body">{children}</div>
    </div>
  );
}
