import { useState } from "react";
import { format, startOfDay } from "date-fns";
import { Pencil } from "lucide-react";
import { toast } from "sonner";
import { trips as tripsApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
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
import type { Trip } from "@/types";

interface EditTripDialogProps {
  trip: Trip;
  onUpdated: () => void;
}

export function EditTripDialog({ trip, onUpdated }: EditTripDialogProps) {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState(trip.title);
  const [destination, setDestination] = useState(trip.destination ?? "");
  const [startDate, setStartDate] = useState<Date | undefined>(
    trip.proposed_start_date ? new Date(trip.proposed_start_date) : undefined
  );
  const [endDate, setEndDate] = useState<Date | undefined>(
    trip.proposed_end_date ? new Date(trip.proposed_end_date) : undefined
  );
  const [numOptions, setNumOptions] = useState(String(trip.num_options));
  const [notes, setNotes] = useState(trip.notes ?? "");

  const resetToTrip = () => {
    setTitle(trip.title);
    setDestination(trip.destination ?? "");
    setStartDate(trip.proposed_start_date ? new Date(trip.proposed_start_date) : undefined);
    setEndDate(trip.proposed_end_date ? new Date(trip.proposed_end_date) : undefined);
    setNumOptions(String(trip.num_options));
    setNotes(trip.notes ?? "");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await tripsApi.update(trip.id, {
        title: title.trim() || undefined,
        destination: destination.trim() || undefined,
        proposed_start_date: startDate ? format(startDate, "yyyy-MM-dd") : undefined,
        proposed_end_date: endDate ? format(endDate, "yyyy-MM-dd") : undefined,
        num_options: parseInt(numOptions, 10),
        notes: notes.trim() || undefined,
      });
      toast.success("Trip updated.");
      setOpen(false);
      onUpdated();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to update trip. Please try again.");
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
        if (!v) resetToTrip();
      }}
    >
      <DialogTrigger
        render={
          <button className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-black/70 hover:bg-muted/20 hover:text-black transition-colors" />
        }
      >
        <Pencil className="w-3.5 h-3.5" />
        Edit Trip
      </DialogTrigger>

      <DialogContent className="bg-card border-border text-black max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-black">Edit trip</DialogTitle>
        </DialogHeader>

        <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4 mt-2">
          <div className="space-y-1.5">
            <Label htmlFor="et-title" className="text-black/80">
              Trip title <span className="text-brand">*</span>
            </Label>
            <Input
              id="et-title"
              required
              value={title}
              onChange={(e) => { setTitle(e.target.value); }}
              className="bg-card border-border text-black placeholder:text-black/30"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="et-dest" className="text-black/80">
              Destination{" "}
              <span className="text-black/40 text-xs">(leave blank for AI surprise)</span>
            </Label>
            <Input
              id="et-dest"
              placeholder="e.g. Barcelona, Spain"
              value={destination}
              onChange={(e) => { setDestination(e.target.value); }}
              className="bg-card border-border text-black placeholder:text-black/30"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-black/80">Start date</Label>
              <DatePicker
                value={startDate}
                onChange={setStartDate}
                placeholder="Start date"
                disabled={(date) => date < startOfDay(new Date())}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-black/80">End date</Label>
              <DatePicker
                value={endDate}
                onChange={setEndDate}
                placeholder="End date"
                defaultMonth={startDate}
                disabled={startDate ? (date) => date < startDate : (date) => date < startOfDay(new Date())}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-black/80">Itinerary options to generate</Label>
            <Select value={numOptions} onValueChange={(v) => { if (v !== null) setNumOptions(v); }}>
              <SelectTrigger className="bg-white border-border text-black w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-white border-border text-black">
                {[2, 3, 4, 5].map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="et-notes" className="text-black/80">
              Notes <span className="text-black/40 text-xs">(optional)</span>
            </Label>
            <Textarea
              id="et-notes"
              placeholder="Any special requirements or context for the group…"
              value={notes}
              onChange={(e) => { setNotes(e.target.value); }}
              rows={3}
              className="bg-white border-border text-black placeholder:text-black/30 resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={() => { setOpen(false); }}
              className="text-black/60 hover:text-black hover:bg-transparent"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-brand hover:bg-brand-hover text-white font-semibold"
            >
              {isSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
