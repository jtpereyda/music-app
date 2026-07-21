"use client";

import { useEffect, useId, useRef, useState } from "react";
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
  const listRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState(selectedHymn.title);
  const [isOpen, setIsOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const matches = showAll
    ? catalog
    : catalog.filter((hymn) => {
        if (!normalizedQuery) {
          return true;
        }

        return [hymn.title, hymn.textAuthor, hymn.tuneName].some((value) =>
          value.toLocaleLowerCase().includes(normalizedQuery),
        );
      });

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const activeOption = listRef.current?.querySelector(
      `[data-option-index="${activeIndex}"]`,
    );
    activeOption?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, isOpen]);

  function openCatalog() {
    const selectedIndex = catalog.findIndex(
      (hymn) => hymn.id === selectedHymn.id,
    );
    setActiveIndex(Math.max(selectedIndex, 0));
    setShowAll(true);
    setIsOpen(true);
  }

  function chooseHymn(hymn: Hymn) {
    setQuery(hymn.title);
    setIsOpen(false);
    setShowAll(false);
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
            setShowAll(false);
            setIsOpen(true);
          }}
          onFocus={(event) => {
            event.currentTarget.select();
            openCatalog();
          }}
          onClick={(event) => {
            if (!isOpen) {
              event.currentTarget.select();
              openCatalog();
            }
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setQuery(selectedHymn.title);
              setIsOpen(false);
              setShowAll(false);
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
          className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-ink/10 bg-white shadow-[0_18px_50px_rgba(29,39,50,0.18)]"
        >
          <div className="flex items-center justify-between border-b border-ink/8 px-3.5 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-ink/40">
            <span>
              {showAll || !normalizedQuery
                ? `${catalog.length} hymns`
                : `${matches.length} ${matches.length === 1 ? "match" : "matches"}`}
            </span>
            {matches.length > 6 ? <span>Scroll to browse</span> : null}
          </div>
          <div
            id={listId}
            ref={listRef}
            role="listbox"
            className="max-h-[min(28rem,60vh)] overflow-y-auto p-1.5 overscroll-contain"
          >
            {matches.length > 0 ? (
              matches.map((hymn, index) => (
                <button
                  key={hymn.id}
                  id={`${listId}-option-${index}`}
                  data-option-index={index}
                  type="button"
                  role="option"
                  tabIndex={-1}
                  aria-selected={hymn.id === selectedHymn.id}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveIndex(index)}
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
        </div>
      ) : null}
    </div>
  );
}
