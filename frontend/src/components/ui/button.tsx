import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-full border-2 border-foreground px-5 py-2.5 text-sm font-bold transition-[transform,box-shadow,background-color] focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  { variants: { variant: {
    default: "bg-accent text-white shadow-hard hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-hard-hover active:translate-x-0.5 active:translate-y-0.5 active:shadow-none",
    secondary: "bg-white text-foreground shadow-hard hover:bg-muted",
    ghost: "border-transparent bg-transparent text-foreground hover:bg-muted",
  } }, defaultVariants: { variant: "default" } },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean };
export function Button({ className, variant, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant }), className)} {...props} />;
}
