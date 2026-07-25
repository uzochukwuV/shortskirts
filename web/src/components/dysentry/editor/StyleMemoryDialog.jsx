import React, { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Button from "../Button";

export default function StyleMemoryDialog({ open, onOpenChange, value, onSave }) {
  const [text, setText] = useState(value || "");

  useEffect(() => {
    if (open) setText(value || "");
  }, [value, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display text-[16px] font-medium tracking-tight-bold text-ink">
            Style memory
          </DialogTitle>
        </DialogHeader>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Persistent tone, palette, pacing, formatting conventions…"
          rows={8}
          className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[14px] text-ink outline-none placeholder-steel focus:border-ash"
          style={{ lineHeight: 1.5 }}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" className="px-4 py-2 text-[13px]" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            className="px-4 py-2 text-[13px]"
            onClick={() => {
              onSave(text);
              onOpenChange(false);
            }}
          >
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}