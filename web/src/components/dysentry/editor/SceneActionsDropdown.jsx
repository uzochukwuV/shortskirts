import React from "react";
import { MoreHorizontal, Lock, Unlock, Trash2, Copy } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function SceneActionsDropdown({ scene, onDelete, onLock, onUnlock, onDuplicate, children }) {
  const isLocked = scene?.locked;
  const isApproved = scene?.approval_status === "approved";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {children || (
          <button className="rounded-lg p-1.5 text-steel hover:bg-muted hover:text-ink transition-colors">
            <MoreHorizontal className="h-4 w-4" />
          </button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {onDuplicate && (
          <DropdownMenuItem onClick={onDuplicate} className="cursor-pointer">
            <Copy className="mr-2 h-4 w-4" />
            Duplicate scene
          </DropdownMenuItem>
        )}
        
        {onLock && !isLocked && (
          <DropdownMenuItem onClick={onLock} className="cursor-pointer">
            <Lock className="mr-2 h-4 w-4" />
            Lock scene
          </DropdownMenuItem>
        )}
        
        {onUnlock && isLocked && (
          <DropdownMenuItem onClick={onUnlock} className="cursor-pointer">
            <Unlock className="mr-2 h-4 w-4" />
            Unlock scene
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        {onDelete && (
          <DropdownMenuItem 
            onClick={onDelete} 
            className="cursor-pointer text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete scene
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
