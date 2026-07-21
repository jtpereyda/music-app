export const AUTHORIZED_ADMIN_EMAIL = "joshua.t.pereyda@gmail.com";

export function isAuthorizedAdmin(email: string | null | undefined): boolean {
  return email?.trim().toLowerCase() === AUTHORIZED_ADMIN_EMAIL;
}
