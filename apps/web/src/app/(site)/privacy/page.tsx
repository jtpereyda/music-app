import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
  description: "How Transposify handles information and third-party services.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <section className="bg-paper px-5 py-16 sm:px-8 sm:py-24">
      <article className="mx-auto max-w-3xl text-ink">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
          Privacy
        </p>
        <h1 className="mt-4 text-4xl font-medium tracking-[-0.045em] sm:text-5xl">
          How we handle your information.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-ink/65">
          Transposify uses a small number of services to operate the site,
          understand how it is used, and answer questions from visitors.
        </p>

        <div className="mt-12 space-y-10 text-sm leading-7 text-ink/70">
          <section>
            <h2 className="text-xl font-semibold tracking-[-0.025em] text-ink">
              Customer support chat
            </h2>
            <p className="mt-3">
              We use Crisp to provide customer support and collect feature
              requests through the chat widget. If you use it, Crisp processes
              your messages and any contact information you choose to provide,
              and may use cookies or similar browser storage to keep the
              conversation available. See{" "}
              <a
                className="font-medium text-blue underline decoration-blue/30 underline-offset-4 transition hover:decoration-blue"
                href="https://crisp.chat/en/privacy/"
                rel="noreferrer"
                target="_blank"
              >
                Crisp&apos;s privacy policy
              </a>{" "}
              for more information.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold tracking-[-0.025em] text-ink">
              Analytics
            </h2>
            <p className="mt-3">
              We may use Google Analytics and Microsoft Clarity to understand
              visits and improve the product. These services may use cookies or
              similar technologies. Analytics integrations remain disabled
              when their project identifiers are not configured.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold tracking-[-0.025em] text-ink">
              Information you provide
            </h2>
            <p className="mt-3">
              Please avoid sending sensitive personal information in support
              messages. We use the information you provide to respond to your
              question, evaluate your request, and improve Transposify.
            </p>
          </section>
        </div>
      </article>
    </section>
  );
}
