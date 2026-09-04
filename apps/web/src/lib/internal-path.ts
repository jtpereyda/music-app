const INTERNAL_PATH_ORIGIN = "https://internal-path.invalid";

export function normalizeInternalPath(value: unknown): string | null {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.length > 2048 ||
    value.includes("?") ||
    value.includes("#")
  ) {
    return null;
  }

  try {
    const parsed = new URL(value, INTERNAL_PATH_ORIGIN);
    const pathname = parsed.pathname;

    return parsed.origin === INTERNAL_PATH_ORIGIN &&
      pathname.startsWith("/") &&
      !pathname.startsWith("//")
      ? pathname
      : null;
  } catch {
    return null;
  }
}
