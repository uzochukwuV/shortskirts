import React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function CharacterDialog({ character, open, onOpenChange }) {
  if (!character) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-ink text-[16px] font-medium text-white">
              {character.name?.[0]}
            </div>
            <div>
              <p className="font-display text-[18px] font-medium tracking-tight-bold text-ink">{character.name}</p>
              {character.role && <p className="text-[12px] text-steel">{character.role}</p>}
            </div>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          {character.description && <Detail label="Description" text={character.description} />}
          {character.appearance && <Detail label="Appearance" text={character.appearance} />}
          {character.personality && <Detail label="Personality" text={character.personality} />}
          {character.voice && <Detail label="Voice" text={character.voice} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Detail({ label, text }) {
  return (
    <div>
      <p className="mb-1 text-[11px] font-medium tracking-tight-bold text-steel uppercase">{label}</p>
      <p className="text-[14px] text-ink" style={{ lineHeight: 1.5 }}>{text}</p>
    </div>
  );
}