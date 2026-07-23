import "server-only";

type ServiceAccount = {
  client_email: string;
  private_key: string;
  token_uri?: string;
};

const googleScopes = [
  "https://www.googleapis.com/auth/webmasters.readonly",
  "https://www.googleapis.com/auth/analytics.readonly",
];

function base64Url(value: string | Uint8Array): string {
  const encoded =
    typeof value === "string"
      ? Buffer.from(value).toString("base64")
      : Buffer.from(value).toString("base64");
  return encoded.replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function privateKeyBytes(pem: string): ArrayBuffer {
  const body = pem
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\s/g, "");
  return Uint8Array.from(Buffer.from(body, "base64")).buffer;
}

async function serviceAccountAccessToken(
  serviceAccountJson: string,
): Promise<string> {
  const account = JSON.parse(serviceAccountJson) as ServiceAccount;
  if (!account.client_email || !account.private_key) {
    throw new Error("Google service account JSON is missing required fields.");
  }
  const now = Math.floor(Date.now() / 1_000);
  const header = base64Url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claims = base64Url(
    JSON.stringify({
      aud: account.token_uri ?? "https://oauth2.googleapis.com/token",
      exp: now + 3_600,
      iat: now,
      iss: account.client_email,
      scope: googleScopes.join(" "),
    }),
  );
  const unsignedToken = `${header}.${claims}`;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    privateKeyBytes(account.private_key),
    { hash: "SHA-256", name: "RSASSA-PKCS1-v1_5" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    Buffer.from(unsignedToken),
  );
  const assertion = `${unsignedToken}.${base64Url(new Uint8Array(signature))}`;
  const response = await fetch(
    account.token_uri ?? "https://oauth2.googleapis.com/token",
    {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        assertion,
        grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      }),
      cache: "no-store",
    },
  );
  const payload = (await response.json()) as {
    access_token?: string;
    error_description?: string;
  };
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description ?? "Google token exchange failed.");
  }
  return payload.access_token;
}

async function refreshTokenAccessToken(refreshToken: string): Promise<string> {
  const clientId = process.env.AUTH_GOOGLE_ID;
  const clientSecret = process.env.AUTH_GOOGLE_SECRET;
  if (!clientId || !clientSecret) {
    throw new Error("Google OAuth client credentials are unavailable.");
  }
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    }),
    cache: "no-store",
  });
  const payload = (await response.json()) as {
    access_token?: string;
    error_description?: string;
  };
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description ?? "Google token refresh failed.");
  }
  return payload.access_token;
}

export function googleSeoConfigured(): boolean {
  return Boolean(
    process.env.GOOGLE_SEO_SERVICE_ACCOUNT_JSON ??
      process.env.GOOGLE_SEO_REFRESH_TOKEN,
  );
}

export async function getGoogleSeoAccessToken(): Promise<string | null> {
  const refreshToken = process.env.GOOGLE_SEO_REFRESH_TOKEN;
  if (refreshToken) return refreshTokenAccessToken(refreshToken);

  const serviceAccountJson = process.env.GOOGLE_SEO_SERVICE_ACCOUNT_JSON;
  if (serviceAccountJson) {
    return serviceAccountAccessToken(serviceAccountJson);
  }
  return null;
}
