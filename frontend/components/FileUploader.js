"use client";

import { useRef, useState } from "react";
import { api } from "@/services/api";
import { inr } from "@/lib/format";

const PAYMENT_METHODS = ["UPI", "Cash", "Card", "Bank transfer", "Other"];

export default function FileUploader({
  defaultType = "expense",
  availableCategories = [],
  onSuccess,
  onClose,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [parsedData, setParsedData] = useState(null); // { filename, total, items: [...] }
  const [selectedIds, setSelectedIds] = useState(new Set());
  const fileInputRef = useRef(null);

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  }

  function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  }

  async function uploadFile(file) {
    setError("");
    setSuccessMsg("");
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["csv", "xlsx", "xls", "pdf"].includes(ext)) {
      return setError(`Unsupported file format '.${ext}'. Please upload a CSV, Excel (.xlsx), or PDF file.`);
    }

    setParsing(true);
    try {
      const res = await api.uploadTransactions(file);
      // Attach temporary UI id to each parsed item for tracking and editing
      const itemsWithIds = res.items.map((item, index) => ({
        ...item,
        _id: `${Date.now()}-${index}`,
      }));
      setParsedData({
        filename: res.filename,
        items: itemsWithIds,
      });
      // By default select all parsed rows
      setSelectedIds(new Set(itemsWithIds.map((item) => item._id)));
    } catch (err) {
      setError(err.message || "Failed to parse file.");
    } finally {
      setParsing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function updateItem(id, field, value) {
    setParsedData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.map((item) => {
          if (item._id !== id) return item;
          return { ...item, [field]: value };
        }),
      };
    });
  }

  function removeItem(id) {
    setParsedData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.filter((item) => item._id !== id),
      };
    });
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!parsedData) return;
    if (selectedIds.size === parsedData.items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(parsedData.items.map((it) => it._id)));
    }
  }

  async function handleConfirmImport() {
    if (!parsedData) return;
    const itemsToCommit = parsedData.items.filter((item) => selectedIds.has(item._id));

    if (itemsToCommit.length === 0) {
      return setError("Please select at least one transaction to import.");
    }

    // Validate each row
    for (const [idx, item] of itemsToCommit.entries()) {
      const amt = Number(item.amount);
      if (!(amt > 0)) {
        return setError(`Row ${idx + 1} (${item.description || "Untitled"}): Amount must be greater than zero.`);
      }
      if (!item.category || !item.category.trim()) {
        return setError(`Row ${idx + 1} (${item.description || "Untitled"}): Category cannot be empty.`);
      }
      if (!item.transaction_date) {
        return setError(`Row ${idx + 1}: Transaction date is missing.`);
      }
    }

    setCommitting(true);
    setError("");

    // Prepare payload matching TransactionIn schema
    const payload = itemsToCommit.map((it) => ({
      type: it.type,
      amount: Number(it.amount),
      category: it.category.trim(),
      description: (it.description || "").trim(),
      transaction_date: it.transaction_date,
      payment_method: it.payment_method || "Bank transfer",
    }));

    try {
      const result = await api.bulkCreateTransactions(payload);
      setSuccessMsg(`Successfully imported ${result.length} transactions from ${parsedData.filename}!`);
      setParsedData(null);
      setSelectedIds(new Set());
      if (onSuccess) {
        onSuccess(result.length);
      }
    } catch (err) {
      setError(err.message || "Failed to save transactions.");
    } finally {
      setCommitting(false);
    }
  }

  function handleReset() {
    setParsedData(null);
    setSelectedIds(new Set());
    setError("");
    setSuccessMsg("");
  }

  const selectedCount = selectedIds.size;
  const totalCount = parsedData ? parsedData.items.length : 0;
  const selectedSum = parsedData
    ? parsedData.items
        .filter((it) => selectedIds.has(it._id))
        .reduce((sum, it) => sum + (Number(it.amount) || 0), 0)
    : 0;

  return (
    <div className="card space-y-4 border-dashed border-slate-300 bg-slate-50/50">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <h3 className="font-semibold text-slate-900">Universal Ingestion: Bulk Import</h3>
          <p className="text-xs text-slate-500">
            Import transactions from CSV, Excel (.xlsx), or PDF bank statements with auto column mapping and smart category inference.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-slate-600"
          >
            Close ✕
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          <p className="font-medium">Import Error</p>
          <p>{error}</p>
        </div>
      )}

      {successMsg && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          <p className="font-medium">Success</p>
          <p>{successMsg}</p>
        </div>
      )}

      {!parsedData ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
            isDragging
              ? "border-brand-500 bg-brand-50/50"
              : "border-slate-300 bg-white hover:border-slate-400"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv, .xlsx, .xls, .pdf"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload-input"
          />

          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          <p className="text-sm font-medium text-slate-800">
            {parsing
              ? "Parsing transactions with FinSight AI engine…"
              : "Drag and drop your bank statement or export file here"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Supports CSV, Excel (.xlsx), and standard PDF bank statements (up to 15 MB)
          </p>

          <label
            htmlFor="file-upload-input"
            className={`btn mt-4 cursor-pointer text-xs ${parsing ? "opacity-50 pointer-events-none" : ""}`}
          >
            {parsing ? "Parsing file…" : "Browse Files"}
          </label>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-3 border border-slate-200">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
                {parsedData.filename}
              </span>
              <span className="text-xs text-slate-600">
                {selectedCount} of {totalCount} selected · Total: <strong className="text-slate-900">{inr(selectedSum)}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={toggleSelectAll}
                className="text-xs text-brand-600 hover:underline"
              >
                {selectedCount === totalCount ? "Deselect All" : "Select All"}
              </button>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={handleReset}
                className="text-xs text-slate-500 hover:text-slate-700"
              >
                Upload different file
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-500">
            Review and adjust inferred categories or details before saving to your business database:
          </p>

          <div className="max-h-96 overflow-y-auto overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 pl-3 pr-2 w-8">
                    <input
                      type="checkbox"
                      checked={selectedCount > 0 && selectedCount === totalCount}
                      onChange={toggleSelectAll}
                      className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                  </th>
                  <th className="py-2.5 pr-2">Date</th>
                  <th className="py-2.5 pr-2">Type</th>
                  <th className="py-2.5 pr-2">Category / Source</th>
                  <th className="py-2.5 pr-2">Description</th>
                  <th className="py-2.5 pr-2">Method</th>
                  <th className="py-2.5 pr-3 text-right">Amount (₹)</th>
                  <th className="py-2.5 pr-3 text-center w-8">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {parsedData.items.map((item) => {
                  const isSelected = selectedIds.has(item._id);
                  return (
                    <tr
                      key={item._id}
                      className={`transition ${isSelected ? "bg-white hover:bg-slate-50/80" : "bg-slate-50/50 opacity-60"}`}
                    >
                      <td className="py-2 pl-3 pr-2">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(item._id)}
                          className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                        />
                      </td>
                      <td className="py-2 pr-2 whitespace-nowrap">
                        <input
                          type="date"
                          value={item.transaction_date}
                          onChange={(e) => updateItem(item._id, "transaction_date", e.target.value)}
                          className="input py-1 px-1.5 text-xs w-32"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <select
                          value={item.type}
                          onChange={(e) => updateItem(item._id, "type", e.target.value)}
                          className="input py-1 px-1.5 text-xs w-24"
                        >
                          <option value="expense">Expense</option>
                          <option value="revenue">Revenue</option>
                        </select>
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          list="ingest-categories"
                          value={item.category}
                          onChange={(e) => updateItem(item._id, "category", e.target.value)}
                          className="input py-1 px-2 text-xs min-w-[130px]"
                          placeholder="Category"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => updateItem(item._id, "description", e.target.value)}
                          className="input py-1 px-2 text-xs min-w-[180px]"
                          placeholder="Description"
                        />
                      </td>
                      <td className="py-2 pr-2">
                        <select
                          value={item.payment_method || "Bank transfer"}
                          onChange={(e) => updateItem(item._id, "payment_method", e.target.value)}
                          className="input py-1 px-1.5 text-xs w-28"
                        >
                          {PAYMENT_METHODS.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 pr-3 text-right">
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={item.amount}
                          onChange={(e) => updateItem(item._id, "amount", e.target.value)}
                          className="input py-1 px-2 text-xs w-24 text-right tabular-nums font-medium"
                        />
                      </td>
                      <td className="py-2 pr-3 text-center">
                        <button
                          type="button"
                          onClick={() => removeItem(item._id)}
                          title="Remove from import"
                          className="text-slate-400 hover:text-rose-600 transition"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <datalist id="ingest-categories">
            {availableCategories.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="btn-ghost text-xs"
              disabled={committing}
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleConfirmImport}
              disabled={committing || selectedCount === 0}
              className="btn text-xs"
            >
              {committing
                ? "Saving to database…"
                : `Confirm and Import ${selectedCount} Transaction${selectedCount === 1 ? "" : "s"}`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
