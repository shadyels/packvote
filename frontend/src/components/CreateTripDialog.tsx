import { useState } from "react";
import { Plus, X } from "lucide-react";
import { trips as tripsApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";

interface CreateTripDialogProps {
  onCreated: () => void;
}

export function CreateTripDialog({ onCreated }: CreateTripDialogProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [numOptions, setNumOptions] = useState("3");
  const [notes, setNotes] = useState("");
  const [emails, setEmails] = useState<string[]>([""]);

  const resetForm = () => {
    setTitle("");
    setDestination("");
    setStartDate("");
    setEndDate("");
    setNumOptions("3");
    setNotes("");
    setEmails([""]);
    setError(null);
  };

  const addEmail = () => { setEmails((prev) => [...prev, ""]); };

  const removeEmail = (idx: number) =>
    { setEmails((prev) => prev.filter((_, i) => i !== idx)); };

  const updateEmail = (idx: number, val: string) =>
    { setEmails((prev) => prev.map((e, i) => (i === idx ? val : e))); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validEmails = emails.map((e) => e.trim()).filter(Boolean);
    if (validEmails.length === 0) {
      setError("Add at least one participant email.");
      return;
    }

    setIsSubmitting(true);
    try {
      await tripsApi.create({
        title: title.trim(),
        destination: destination.trim() || undefined,
        proposed_start_date: startDate || undefined,
        proposed_end_date: endDate || undefined,
        num_options: parseInt(numOptions, 10),
        participant_emails: validEmails,
        notes: notes.trim() || undefined,
      });
      resetForm();
      setOpen(false);
      onCreated();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to create trip. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) resetForm();
      }}
    >
      <DialogTrigger
        render={
          <Button className="bg-accent hover:bg-accent-hover text-white font-semibold">
            <Plus className="w-4 h-4 mr-1" />
            New Trip
          </Button>
        }
      />

      <DialogContent className="bg-card border-border text-cream max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-cream">Create a new trip</DialogTitle>
        </DialogHeader>

        <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4 mt-2">
          {/* Title */}
          <div className="space-y-1.5">
            <Label htmlFor="ct-title" className="text-cream/80">
              Trip title <span className="text-accent">*</span>
            </Label>
            <Input
              id="ct-title"
              required
              placeholder="Summer adventure 2025"
              value={title}
              onChange={(e) => { setTitle(e.target.value); }}
              className="bg-background border-border text-cream placeholder:text-cream/30"
            />
          </div>

          {/* Destination */}
          <div className="space-y-1.5">
            <Label htmlFor="ct-dest" className="text-cream/80">
              Destination{" "}
              <span className="text-cream/40 text-xs">(leave blank for AI surprise)</span>
            </Label>
            <Input
              id="ct-dest"
              placeholder="e.g. Barcelona, Spain"
              value={destination}
              onChange={(e) => { setDestination(e.target.value); }}
              className="bg-background border-border text-cream placeholder:text-cream/30"
            />
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="ct-start" className="text-cream/80">
                Start date
              </Label>
              <Input
                id="ct-start"
                type="date"
                value={startDate}
                onChange={(e) => { setStartDate(e.target.value); }}
                className="bg-background border-border text-cream"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ct-end" className="text-cream/80">
                End date
              </Label>
              <Input
                id="ct-end"
                type="date"
                value={endDate}
                onChange={(e) => { setEndDate(e.target.value); }}
                className="bg-background border-border text-cream"
              />
            </div>
          </div>

          {/* Num options */}
          <div className="space-y-1.5">
            <Label className="text-cream/80">Itinerary options to generate</Label>
            <Select value={numOptions} onValueChange={(v) => { if (v !== null) setNumOptions(v); }}>
              <SelectTrigger className="bg-background border-border text-cream w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-card border-border text-cream">
                {[2, 3, 4, 5].map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Separator className="bg-border" />

          {/* Participant emails */}
          <div className="space-y-2">
            <Label className="text-cream/80">
              Participant emails <span className="text-accent">*</span>
            </Label>
            {emails.map((email, idx) => (
              <div key={idx} className="flex gap-2">
                <Input
                  type="email"
                  placeholder={`participant${(idx + 1).toString()}@example.com`}
                  value={email}
                  onChange={(e) => { updateEmail(idx, e.target.value); }}
                  className="bg-background border-border text-cream placeholder:text-cream/30"
                />
                {emails.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => { removeEmail(idx); }}
                    className="shrink-0 text-cream/40 hover:text-red-400 hover:bg-transparent"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={addEmail}
              className="text-accent hover:text-accent hover:bg-transparent px-0"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add participant
            </Button>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="ct-notes" className="text-cream/80">
              Notes <span className="text-cream/40 text-xs">(optional)</span>
            </Label>
            <Textarea
              id="ct-notes"
              placeholder="Any special requirements or context for the group…"
              value={notes}
              onChange={(e) => { setNotes(e.target.value); }}
              rows={3}
              className="bg-background border-border text-cream placeholder:text-cream/30 resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={() => { setOpen(false); }}
              className="text-cream/60 hover:text-cream hover:bg-transparent"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-accent hover:bg-accent-hover text-white font-semibold"
            >
              {isSubmitting ? "Creating…" : "Create trip"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
