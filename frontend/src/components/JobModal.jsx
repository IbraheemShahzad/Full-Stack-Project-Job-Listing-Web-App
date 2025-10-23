// src/components/JobModal.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULTS = {
  title: "",
  company: "",
  city: "",
  country: "",
  location: "",
  job_type: "",
  posting_date: "",
  tags: [],
  job_url: "",
};

function sanitizeUrl(url) {
  if (!url) return "";
  const t = url.trim();
  if (!t) return "";
  return /^https?:\/\//i.test(t) ? t : `https://${t}`;
}

export default function JobModal({
  open,
  editing = false,
  initial = {},
  submitting = false,
  onClose,
  onSubmit,
}) {
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    ...DEFAULTS,
    ...initial,
    tags: Array.isArray(initial.tags) ? initial.tags : [],
  });

  const firstInputRef = useRef(null);
  const overlayRef = useRef(null);

  useEffect(() => {
    setForm({
      ...DEFAULTS,
      ...initial,
      tags: Array.isArray(initial.tags) ? initial.tags : [],
    });
    setError("");
  }, [initial, open]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => (document.body.style.overflow = prev);
  }, [open]);

  useEffect(() => {
    if (open) firstInputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const setField = (key, value) => setForm((p) => ({ ...p, [key]: value }));

  const tagsDisplay = useMemo(() => (form.tags ?? []).join(", "), [form.tags]);

  const handleTagsChange = (raw) => {
    const arr = raw.split(",").map((s) => s.trim()).filter(Boolean);
    setField("tags", Array.from(new Set(arr)));
  };

  const validate = (data) => {
    if (!data.title.trim()) return "Title is required.";
    if (!data.company.trim()) return "Company is required.";
    if (!data.posting_date) return "Posting date is required (YYYY-MM-DD).";
    if (!data.job_url) return "Job URL is required.";
    return null;
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");

    const payload = {
      ...form,
      title: form.title.trim(),
      company: form.company.trim(),
      city: form.city?.trim() || "",
      country: form.country?.trim() || "",
      location: form.location?.trim() || "",
      job_type: form.job_type || "",
      posting_date: form.posting_date || "",
      tags: (form.tags ?? []).map((t) => t.trim()).filter(Boolean),
      job_url: sanitizeUrl(form.job_url),
    };

    const err = validate(payload);
    if (err) return setError(err);

    await onSubmit(payload);
  };

  const onBackdrop = (e) => {
    if (e.target === overlayRef.current) onClose();
  };

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      onMouseDown={onBackdrop}
      className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
      aria-modal="true"
      role="dialog"
      aria-labelledby="job-modal-title"
    >
      <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="job-modal-title" className="text-lg font-semibold">
            {editing ? "Edit job" : "Add new job"}
          </h2>
          <button type="button" onClick={onClose} className="text-gray-500 rounded px-1" aria-label="Close modal">
            ✕
          </button>
        </div>

        {error ? <div className="bg-red-50 text-red-700 text-sm p-2 rounded border border-red-200">{error}</div> : null}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-sm">Title
            <input ref={firstInputRef} className="mt-1 w-full border rounded px-3 py-2" value={form.title}
              onChange={(e) => setField("title", e.target.value)} required />
          </label>

          <label className="text-sm">Company
            <input className="mt-1 w-full border rounded px-3 py-2" value={form.company}
              onChange={(e) => setField("company", e.target.value)} required />
          </label>

          <label className="text-sm">City
            <input className="mt-1 w-full border rounded px-3 py-2" value={form.city || ""}
              onChange={(e) => setField("city", e.target.value)} />
          </label>

          <label className="text-sm">Country
            <input className="mt-1 w-full border rounded px-3 py-2" value={form.country || ""}
              onChange={(e) => setField("country", e.target.value)} />
          </label>

          <label className="text-sm">Location (optional)
            <input className="mt-1 w-full border rounded px-3 py-2" value={form.location || ""}
              onChange={(e) => setField("location", e.target.value)} placeholder="e.g., London, UK" />
          </label>

          <label className="text-sm">Job Type
            <select className="mt-1 w-full border rounded px-3 py-2" value={form.job_type || ""}
              onChange={(e) => setField("job_type", e.target.value)}>
              <option value="">Select type</option>
              <option>Full-time</option><option>Part-time</option>
              <option>Contract</option><option>Internship</option>
            </select>
          </label>

          <label className="text-sm">Posting Date
            <input type="date" className="mt-1 w-full border rounded px-3 py-2"
              value={form.posting_date || ""} onChange={(e) => setField("posting_date", e.target.value)} />
          </label>

          <label className="text-sm">Tags (comma separated)
            <input className="mt-1 w-full border rounded px-3 py-2" value={tagsDisplay}
              onChange={(e) => handleTagsChange(e.target.value)} placeholder="Life, Pricing" />
          </label>

          <label className="text-sm md:col-span-2">Job URL
            <input className="mt-1 w-full border rounded px-3 py-2" value={form.job_url || ""}
              onChange={(e) => setField("job_url", e.target.value)} placeholder="https://example.com/job" inputMode="url" />
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded border">Cancel</button>
          <button disabled={submitting} className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-60">
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
