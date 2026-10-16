import type { ReactNode } from "react";

export function PageHeading({ eyebrow, title, description, aside }: { eyebrow: string; title: string; description: string; aside?: ReactNode }) {
  return <div className="flex flex-col justify-between gap-6 border-b-2 border-foreground pb-8 md:flex-row md:items-end"><div className="max-w-3xl"><span className="eyebrow mb-5">{eyebrow}</span><h1 className="text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl">{title}</h1><p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">{description}</p></div>{aside}</div>;
}
