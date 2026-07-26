import React, { useState, useEffect } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import Button from "@/components/dysentry/Button";

const ROLE_OPTIONS = [
  { value: "protagonist", label: "Protagonist" },
  { value: "deuteragonist", label: "Deuteragonist" },
  { value: "antagonist", label: "Antagonist" },
  { value: "supporting", label: "Supporting" },
  { value: "minor", label: "Minor" },
];

export default function CharacterSheet({ 
  open, 
  onOpenChange, 
  characters, 
  onAddCharacter,
  onUpdateCharacter,
  onDeleteCharacter,
  loading 
}) {
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({
    name: "",
    role: "supporting",
    description: "",
    appearance: "",
    personality: "",
  });

  // Reset when sheet closes
  useEffect(() => {
    if (!open) {
      setEditingId(null);
      setEditForm({});
      setShowAddForm(false);
      setAddForm({
        name: "",
        role: "supporting",
        description: "",
        appearance: "",
        personality: "",
      });
    }
  }, [open]);

  const handleEdit = (character) => {
    setEditingId(character.id);
    setEditForm({
      name: character.name || "",
      role: character.role || "supporting",
      description: character.description || "",
      appearance: character.appearance || "",
      personality: character.personality || "",
      ref_image_urls: character.ref_image_urls || [],
    });
  };

  const handleSaveEdit = async () => {
    if (editForm.name?.trim()) {
      await onUpdateCharacter(editingId, editForm);
      setEditingId(null);
      setEditForm({});
    }
  };

  const handleAdd = async () => {
    if (addForm.name?.trim()) {
      await onAddCharacter(addForm);
      setAddForm({
        name: "",
        role: "supporting",
        description: "",
        appearance: "",
        personality: "",
      });
      setShowAddForm(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Delete this character?")) {
      await onDeleteCharacter(id);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Characters</SheetTitle>
          <SheetDescription>
            Manage your story's cast. Characters are shared across all episodes.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* Add Character Button/Form */}
          {!showAddForm ? (
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={() => setShowAddForm(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Character
            </Button>
          ) : (
            <div className="rounded-lg border border-fog p-4 space-y-4">
              <h4 className="font-medium text-ink">New Character</h4>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2 space-y-1">
                  <label className="text-xs text-steel">Name *</label>
                  <input
                    type="text"
                    value={addForm.name}
                    onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                    placeholder="Character name"
                    className="w-full h-9 px-3 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                
                <div className="col-span-2 space-y-1">
                  <label className="text-xs text-steel">Role</label>
                  <select
                    value={addForm.role}
                    onChange={(e) => setAddForm({ ...addForm, role: e.target.value })}
                    className="w-full h-9 px-3 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    {ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setShowAddForm(false)}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button 
                  size="sm"
                  onClick={handleAdd}
                  disabled={loading || !addForm.name?.trim()}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
                </Button>
              </div>
            </div>
          )}

          {/* Character List */}
          <div className="space-y-3">
            {characters?.map((character) => (
              <div 
                key={character.id} 
                className={`rounded-lg border p-4 transition-colors ${
                  editingId === character.id ? "border-primary bg-primary/5" : "border-fog"
                }`}
              >
                {editingId === character.id ? (
                  // Edit Mode
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-xs text-steel">Name</label>
                      <input
                        type="text"
                        value={editForm.name || ""}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        className="w-full h-9 px-3 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-steel">Role</label>
                      <select
                        value={editForm.role || "supporting"}
                        onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                        className="w-full h-9 px-3 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      >
                        {ROLE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-steel">Description</label>
                      <textarea
                        value={editForm.description || ""}
                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                        rows={2}
                        className="w-full px-3 py-2 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                        placeholder="Character description..."
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-steel">Appearance</label>
                      <textarea
                        value={editForm.appearance || ""}
                        onChange={(e) => setEditForm({ ...editForm, appearance: e.target.value })}
                        rows={2}
                        className="w-full px-3 py-2 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                        placeholder="Visual appearance..."
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-steel">Personality</label>
                      <textarea
                        value={editForm.personality || ""}
                        onChange={(e) => setEditForm({ ...editForm, personality: e.target.value })}
                        rows={2}
                        className="w-full px-3 py-2 rounded-md border border-fog bg-paper text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                        placeholder="Personality traits..."
                      />
                    </div>

                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </Button>
                      <Button 
                        size="sm"
                        onClick={handleSaveEdit}
                        disabled={loading}
                      >
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                      </Button>
                    </div>
                  </div>
                ) : (
                  // View Mode
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-white font-medium">
                        {character.name?.[0]?.toUpperCase() || "?"}
                      </div>
                      <div>
                        <p className="font-medium text-ink">{character.name}</p>
                        <p className="text-xs text-steel capitalize">{character.role?.replace("_", " ")}</p>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleEdit(character)}
                        className="px-2 py-1 text-xs text-steel hover:text-ink rounded hover:bg-muted transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(character.id)}
                        className="px-2 py-1 text-xs text-destructive hover:text-destructive rounded hover:bg-destructive/10 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {!editingId || editingId !== character.id ? (
                  <>
                    {character.description && (
                      <p className="mt-2 text-sm text-steel line-clamp-2">
                        {character.description}
                      </p>
                    )}
                    {character.ref_image_urls?.length > 0 && (
                      <div className="mt-2 flex gap-1">
                        {character.ref_image_urls.slice(0, 3).map((url, i) => (
                          <img
                            key={i}
                            src={url}
                            alt=""
                            className="h-8 w-8 rounded object-cover"
                          />
                        ))}
                        {character.ref_image_urls.length > 3 && (
                          <div className="h-8 w-8 rounded bg-muted flex items-center justify-center text-xs text-steel">
                            +{character.ref_image_urls.length - 3}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            ))}

            {(!characters || characters.length === 0) && (
              <p className="text-sm text-steel text-center py-8">
                No characters yet. Add your first character to get started.
              </p>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
