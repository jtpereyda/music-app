"use client";

import { useId, useState } from "react";
import type { Hymn } from "@/lib/catalog";

interface HymnSearchProps {
  catalog: readonly Hymn[];
  selectedHymn: Hymn;
  onSelect: (hymn: Hymn) => void;
}

export function HymnSearch({
  catalog,
  selectedHymn,
  onSelect,
}: HymnSearchProps) {
  const listId = useId();
  const [query, setQuery] = useState(selectedHymn.title);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const matches = catalog
    .filter((hymn) => {
      if (!normalizedQuery) {
        return true;
      }

      return [hymn.title, hymn.textAuthor, hymn.tuneName].some((value) =>
        value.toLocaleLowerCase().includes(normalizedQuery),
      );
    })
    .slice(0, 6);

  function chooseHymn(hymn: Hymn) {
    setQuery(hymn.title);
    setIsOpen(false);
    onSelect(hymn);
  }

  return (
    <div
      className="relative"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setIsOpen(false);
        }
      }}
    >
      <label
        htmlFor={`${listId}-search`}
        className="mb-2 block text-xs font-medium uppercase tracking-[0.12em] text-ink/55"
      >
        Hymn
      </label>
      <div className="relative">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-ink/40"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
          <path d="m16 16 4 4" stroke="currentColor" strokeWidth="1.8" />
        </svg>
        <input
          id={`${listId}-search`}
          type="search"
          value={query}
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            isOpen && matches[activeIndex]
              ? `${listId}-option-${activeIndex}`
              : undefined
          }
          autoComplete="off"
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
            setIsOpen(true);
          }}
          onFocus={(event) => {
            event.currentTarget.select();
            setActiveIndex(0);
            setIsOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setQuery(selectedHymn.title);
              setIsOpen(false);
            }

            if (event.key === "ArrowDown" && matches.length > 0) {
              event.preventDefault();
              setIsOpen(true);
              setActiveIndex((index) => (index + 1) % matches.length);
            }

            if (event.key === "ArrowUp" && matches.length > 0) {
              event.preventDefault();
              setIsOpen(true);
              setActiveIndex(
                (index) => (index - 1 + matches.length) % matches.length,
              );
            }

            if (event.key === "Enter" && matches[activeIndex]) {
              event.preventDefault();
              chooseHymn(matches[activeIndex]);
            }
          }}
          className="h-12 w-full rounded-xl border border-ink/15 bg-white px-10 pr-4 text-sm text-ink shadow-sm outline-none transition placeholder:text-ink/35 focus:border-blue/60 focus:ring-4 focus:ring-blue/10"
          placeholder="Search title, author, or tune"
        />
      </div>

      {isOpen ? (
        <div
          id={listId}
          role="listbox"
          className="absolute z-30 mt-2 max-h-80 w-full overflow-auto rounded-xl border border-ink/10 bg-white p-1.5 shadow-[0_18px_50px_rgba(29,39,50,0.18)]"
        >
          {matches.length > 0 ? (
            matches.map((hymn, index) => (
              <button
                key={hymn.id}
                id={`${listId}-option-${index}`}
                type="button"
                role="option"
                aria-selected={hymn.id === selectedHymn.id}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => chooseHymn(hymn)}
                className={`flex w-full items-start justify-between gap-4 rounded-lg px-3 py-2.5 text-left outline-none transition hover:bg-cream focus-visible:bg-cream ${
                  index === activeIndex ? "bg-cream" : ""
                }`}
              >
                <span>
                  <span className="block text-sm font-medium leading-5 text-ink">
                    {hymn.title}
                  </span>
                  <span className="mt-0.5 block text-xs text-ink/50">
                    {hymn.textAuthor} · {hymn.tuneName}
                  </span>
                </span>
                <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-ink/35">
                  {hymn.meter}
                </span>
              </button>
            ))
          ) : (
            <p className="px-3 py-6 text-center text-sm text-ink/50">
              No hymns match “{query}”.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
