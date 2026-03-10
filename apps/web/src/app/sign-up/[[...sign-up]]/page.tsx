import { SignUp } from "@clerk/nextjs";
import { Radar, Check } from "lucide-react";
import Link from "next/link";

const benefits = [
  "14-day free trial, no credit card required",
  "Monitor up to 3 competitors for free",
  "AI-powered weekly intelligence briefings",
  "Setup takes less than 2 minutes",
];

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-between bg-primary/5 p-12 lg:flex">
        <Link href="/" className="flex items-center gap-2">
          <Radar className="h-7 w-7 text-primary" />
          <span className="text-xl font-bold">Scout AI</span>
        </Link>
        <div className="space-y-6">
          <h2 className="text-3xl font-bold">
            Start monitoring your
            <br />
            competitors today.
          </h2>
          <ul className="space-y-3">
            {benefits.map((benefit) => (
              <li key={benefit} className="flex items-center gap-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10">
                  <Check className="h-3.5 w-3.5 text-primary" />
                </div>
                <span className="text-muted-foreground">{benefit}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Scout AI
        </p>
      </div>
      <div className="flex flex-1 items-center justify-center p-8">
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-none",
            },
          }}
        />
      </div>
    </div>
  );
}
