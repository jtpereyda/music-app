import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import {
  AUTHORIZED_ADMIN_EMAIL,
  isAuthorizedAdmin,
} from "@/lib/admin-auth";

type GoogleProfile = {
  email?: string;
  email_verified?: boolean;
};

export const { auth, handlers, signIn, signOut } = NextAuth({
  providers: [
    Google({
      authorization: {
        params: {
          login_hint: AUTHORIZED_ADMIN_EMAIL,
          prompt: "select_account",
        },
      },
    }),
  ],
  pages: {
    error: "/admin/sign-in",
    signIn: "/admin/sign-in",
  },
  callbacks: {
    signIn({ account, profile }) {
      if (account?.provider !== "google") return false;

      const googleProfile = profile as GoogleProfile | undefined;
      return (
        googleProfile?.email_verified === true &&
        isAuthorizedAdmin(googleProfile.email)
      );
    },
  },
});
