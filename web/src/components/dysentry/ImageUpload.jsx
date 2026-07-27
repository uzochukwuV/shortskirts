import React, { useCallback, useState, useRef } from "react";
import { Upload, X, Image as ImageIcon, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Reusable image upload component with drag & drop support.
 * 
 * @param {string[]} value - Array of image URLs
 * @param {function} onChange - Callback with new URLs array
 * @param {string} label - Label for the upload area
 * @param {string} hint - Optional hint text
 * @param {number} maxImages - Maximum number of images (default: 5)
 * @param {string} className - Additional classes
 */
export default function ImageUpload({
  value = [],
  onChange,
  label,
  hint,
  maxImages = 5,
  className,
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleUpload = useCallback(
    async (files) => {
      if (!files || files.length === 0) return;
      const remainingSlots = maxImages - value.length;
      const filesToUpload = Array.from(files).slice(0, remainingSlots);
      
      if (filesToUpload.length === 0) return;
      
      setUploading(true);
      try {
        const newUrls = [];
        for (const file of filesToUpload) {
          const formData = new FormData();
          formData.append("file", file);
          
          const response = await fetch("/api/pipeline/uploads/image", {
            method: "POST",
            body: formData,
          });
          
          if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: "Upload failed" }));
            throw new Error(error.detail || "Upload failed");
          }
          
          const data = await response.json();
          newUrls.push(data.url);
        }
        
        onChange([...value, ...newUrls]);
      } catch (error) {
        console.error("Upload error:", error);
        alert(error.message || "Failed to upload image");
      } finally {
        setUploading(false);
      }
    },
    [value, onChange, maxImages]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const files = e.dataTransfer?.files;
      if (files) handleUpload(files);
    },
    [handleUpload]
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleFileInput = useCallback(
    (e) => {
      const files = e.target.files;
      if (files) handleUpload(files);
      e.target.value = "";
    },
    [handleUpload]
  );

  const handleRemove = useCallback(
    (index) => {
      const newUrls = value.filter((_, i) => i !== index);
      onChange(newUrls);
    },
    [value, onChange]
  );

  const canAddMore = value.length < maxImages;

  return (
    <div className={cn("space-y-3", className)}>
      {label && (
        <div className="flex items-baseline justify-between gap-3">
          <label className="block text-[11px] font-medium uppercase tracking-tight-bold text-steel">
            {label}
          </label>
          {hint && <span className="text-[11px] text-ash">{hint}</span>}
        </div>
      )}

      {/* Image Grid */}
      {value.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          {value.map((url, index) => (
            <div
              key={`${url}-${index}`}
              className="group relative aspect-square overflow-hidden rounded-lg border border-fog bg-muted"
            >
              <img
                src={url}
                alt={`Upload ${index + 1}`}
                className="h-full w-full object-cover"
                onError={(e) => {
                  e.target.src = "/placeholder-image.png";
                }}
              />
              <button
                type="button"
                onClick={() => handleRemove(index)}
                className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity hover:bg-red-500 group-hover:opacity-100"
              >
                <X className="h-3 w-3" />
              </button>
              {index === 0 && (
                <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 py-0.5 text-[9px] text-white">
                  Cover
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload Area */}
      {canAddMore && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => !uploading && inputRef.current?.click()}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors",
            dragOver
              ? "border-signal bg-signal/5"
              : "border-fog hover:border-ash",
            uploading && "cursor-wait opacity-60"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileInput}
            className="hidden"
          />
          {uploading ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-steel" />
              <span className="text-[13px] text-steel">Uploading...</span>
            </>
          ) : (
            <>
              <Upload className="h-6 w-6 text-ash" />
              <div className="text-center">
                <span className="text-[13px] text-ink">
                  Drop images here or{" "}
                  <span className="text-signal">browse</span>
                </span>
                <p className="mt-1 text-[11px] text-steel">
                  {value.length}/{maxImages} images · JPG, PNG, WebP up to 10MB
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
