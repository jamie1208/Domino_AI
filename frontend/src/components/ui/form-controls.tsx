import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const control = "min-h-12 w-full rounded-md border-2 border-foreground bg-white px-4 py-3 text-sm font-medium placeholder:text-muted-foreground/70 focus-visible:ring-4 focus-visible:ring-accent/30";
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) { return <input className={cn(control, className)} {...props} />; }
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) { return <select className={cn(control, className)} {...props} />; }
export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea className={cn(control, "min-h-36 resize-y", className)} {...props} />; }
