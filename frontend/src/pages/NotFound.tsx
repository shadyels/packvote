import { Link } from "react-router-dom";
import { FlapWord } from "@/components/ui/Flap";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <div className="flex justify-center">
        <FlapWord text="404" size="board" />
      </div>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        That page doesn&apos;t exist or the link has changed.
      </p>
      <Link
        to="/"
        className="mt-6 inline-block text-sm font-medium text-accent-ink hover:underline"
      >
        Back to home
      </Link>
    </div>
  );
}
