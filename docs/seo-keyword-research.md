# Transposify initial keyword and landing-page research

Research date: 2026-07-20  
Primary market: United States, English

## Executive summary

The most promising search pattern is not one giant keyword. It is a family of
small, high-intent clusters:

1. **`{hymn} sheet music`** — the largest immediately relevant opportunity.
2. **`{hymn} sheet music key of {key}`** — smaller, highly specific demand
   suitable for selected preset pages.
3. **`{hymn} {instrument} sheet music`** — especially cello and trombone.
4. **`{hymn} bass clef`** — real demand, but concentrated most visibly around
   “Amazing Grace.”
5. **`sheet music transposer`** — meaningful demand and a weak SERP, but the
   current fixed hymn catalog only partially satisfies the generic intent.

Google Autocomplete showed exact key demand for five of the six hymns already
in the catalog. Live-result spot checks often returned a piano arrangement,
chord chart, contemporary song sharing the hymn title, marketplace category,
or isolated PDF instead of a page that lets the searcher choose the exact key,
voice line, and clef. That mismatch is Transposify's opening.

Ahrefs Lite subsequently verified that the base hymn queries are substantially
larger than most exact key/clef phrases. The best initial strategy is therefore:

- Make every hymn page a substantial, indexable canonical page.
- Add only **curated, demand-validated preset pages** for key, clef, or
  instrument combinations. Use canonical query-string presets for unmeasured
  combinations instead of generating the full indexable matrix.
- Default each preset page to the promised edition and render a real preview;
  this makes it a functional result, not a thin doorway page.
- Expand the catalog next with hymns whose key-specific queries repeat in
  Autocomplete.

## Launch blocker before keyword work can pay off

The production HTML currently includes:

```html
<meta name="robots" content="noindex, nofollow">
```

That comes from `apps/web/src/app/layout.tsx`. There is also no sitemap route in
the current web source. Keep `noindex` only if this is still deliberately a
private technical preview. Otherwise, removing it, adding a sitemap, verifying
the domain in Google Search Console, and submitting the sitemap are the first
SEO launch tasks.

## Evidence and limitations

This pass used:

- The current six-hymn Transposify catalog and its page/metadata structure.
- Google Autocomplete with US/English parameters as a directional demand
  signal. Autocomplete presence is not a search-volume estimate.
- Live web-result spot checks for query-to-result fit.
- Ahrefs Keywords Explorer and SERP Overview after the account was upgraded to
  Lite. Search volumes are Ahrefs estimates for the US unless stated otherwise;
  KD is Ahrefs' backlink-based keyword-difficulty score, not a guarantee of
  ranking.

SERPs are personalized and change over time. “Gap” below means the sampled
results did not consistently provide the exact traditional hymn, requested
key/clef/instrument, a visible score preview, and a printable result on one
page.

## Ahrefs-verified demand

### Existing catalog

| Keyword | US volume/mo | Global volume/mo | KD | Traffic potential | Interpretation |
|---|---:|---:|---:|---:|---|
| `amazing grace sheet music` | 1,800 | 2,500 | 2 | 500 | Largest current-page opportunity, but also the strongest SERP |
| `it is well with my soul sheet music` | 450 | 600 | 0 | 450 | Best balance of demand, product fit, and weak ranking pages |
| `come thou fount sheet music` | 250 | 250 | 0 | 200 | Strong near-term target; the full-title variant has 150 US volume |
| `blessed assurance sheet music` | 200 | 300 | 0 | 50 | Strong near-term target with weak individual ranking pages |
| `o for a thousand tongues to sing sheet music` | 30 | 60 | 0 | 10 | Small but extremely relevant and commercially/transactionally classified |
| `beneath the cross of jesus sheet music` | 10 | 20 | n/a | n/a | Real but small; Ahrefs' available SERP snapshot is old |

### Specific formats and presets

| Keyword | US volume/mo | KD | Traffic potential | Decision |
|---|---:|---:|---:|---|
| `amazing grace cello sheet music` | 150 | 0 | 70 | Justifies a dedicated cello preset after instrument suitability is verified |
| `amazing grace trombone sheet music` | 70 | 0 | 30 | Justifies a dedicated trombone preset |
| `the old rugged cross sheet music key of c` | 50 | n/a | n/a | Strong expansion/preset candidate |
| `be thou my vision sheet music key of c` | 40 | 0 | 10 | Measurable exact-key opportunity |
| `it is well with my soul sheet music key of c` | 30 | n/a | n/a | Measurable exact-key opportunity |
| `it is well with my soul sheet music key of g` | 20 | n/a | n/a | Measurable exact-key opportunity |
| `amazing grace bass clef` | 20 | 0 | 10 | Measurable but smaller than instrument-language demand |
| `amazing grace sheet music key of c` | 20 | n/a | n/a | Measurable exact-key opportunity |
| `blessed assurance sheet music key of c` | 20 | n/a | n/a | Measurable exact-key opportunity |
| `it is well with my soul sheet music key of d` | 10 | n/a | n/a | Small but measurable |
| `come thou fount sheet music key of c` | 10 | n/a | n/a | Small but measurable |

Ahrefs found no measurable volume for the original full query, `o for a
thousand tongues to sing in d bass clef`, or for its close bass-clef variants.
The broader sheet-music query has 30 US searches/month. The D/bass-clef state
should therefore be a shareable preset on the main hymn page, not one of the
first separately indexed pages.

### Second-pass exact-key opportunities

A systematic Ahrefs check of 20 additional public-domain hymn titles across
six keys and bass, tenor, and alto clef phrases produced ten more measurable
exact-key queries. Most other title/key/clef combinations returned zero
measurable volume. Current live-result sampling was used where Ahrefs had no
stored SERP; `n/a` KD therefore means “not calculated,” not “zero difficulty.”

| Exact keyword | US volume/mo | KD | SERP targeting assessment | Decision |
|---|---:|---:|---|---|
| `the old rugged cross sheet music key of c` | 50 | n/a | Several pages explicitly promise the hymn in C, including interactive, transposable, and paid C-instrument editions | Skip as a first long-tail page despite the volume; the intent is already well served |
| `great is thy faithfulness sheet music key of c` | 40 | n/a | Results fragment across a seven-key lead-sheet page, contemporary arrangements, paid beginner piano, and individual marketplace products | **Build.** A traditional FAITHFULNESS SATB edition with selectable parts is more exact than most results |
| `be thou my vision sheet music key of c` | 40 | 0 | The top 10 contains one exact paid product, a harp page, MuseScore, a bare PDF, and general hymn pages; the ranking URLs are UR 0–4 with zero or one referring domain | **Build.** Targeting exists, but page-level competition is unusually weak |
| `doxology sheet music key of c` | 10 | n/a | Live results did not consistently return the traditional OLD 100TH tune in C; the clearest C result was a different modern choral work called “Doxology” | **Build.** Strong mismatch opportunity if the tune is named prominently |
| `great is thy faithfulness sheet music key of g` | 10 | n/a | A paid elementary-piano page and isolated PDFs mention G; most results are not a traditional, configurable hymn edition | **Build.** Smaller but less directly satisfied than the C query |
| `great is thy faithfulness sheet music key of d` | 10 | n/a | Results skew toward contemporary PraiseCharts products and a specific ensemble arrangement; one multi-key lead-sheet page includes D | **Build or combine with the C/G cluster.** Use one strong parent plus indexable key presets |
| `holy holy holy sheet music key of c` | 10 | n/a | Results mix NICAEA, modern songs with the same title, paid beginner-piano products, bare PDFs, and general pages; an older Ahrefs SERP included DR 2/UR 0 and several UR 0–4 pages | **Build.** Tune disambiguation plus SATB/clef controls directly addresses the mismatch |
| `be thou my vision sheet music key of d` | 10 | n/a | Live results are dominated by PraiseCharts arrangements and the modern “Lord You Are” extension rather than a simple traditional any-part edition | **Build after the C page.** It can share the same parent cluster and tool |
| `jesus loves me sheet music key of c` | 10 | n/a | Results mix the traditional hymn with a different Hillsong song; the clearest traditional result is a paid advanced-piano arrangement | **Build.** Traditional-title disambiguation and non-piano parts create a clear gap |
| `i surrender all sheet music key of c` | 10 | n/a | PraiseCharts offers the key directly and a current visual-piano page is explicitly in C | Secondary/watchlist; more directly targeted than the other 10-volume candidates |

The strongest eight-page expansion from this pass is therefore Great Is Thy
Faithfulness in C/G/D, Be Thou My Vision in C/D, Doxology in C, Holy Holy Holy
in C, and Jesus Loves Me in C. Those eight URLs collapse into five underlying
hymn pages, so the implementation cost should be much lower than eight
independent content pages.

### Tool and category queries

| Keyword | US volume/mo | KD | Traffic potential | Product-fit note |
|---|---:|---:|---:|---|
| `transpose sheet music` | 300 | 0 | 350 | Generic intent often expects arbitrary-file upload |
| `music transposer` | 300 | 0 | 900 | Broad and ambiguous; parent topic is Transposr |
| `sheet music transposer` | 250 | 0 | 400 | Weak SERP, but current catalog breadth limits satisfaction |
| `transpose sheet music online free` | 150 | 0 | 250 | Attractive future tool-page target |
| `hymn sheet music` | 150 | 2 | 3,300 | Supports a real `/hymns` catalog landing page |
| `free hymn sheet music` | 60 | 3 | 150 | Supports the same catalog page if the offer remains free |

The exact `hymn transposer` and `bass clef hymns` phrases showed no measurable
Ahrefs volume despite appearing in Google Autocomplete. They remain useful
supporting language, not primary volume targets.

## Ranking feasibility from Ahrefs SERPs

The SERP evidence is unusually favorable for a new functional product. High-DR
domains appear, but many of the ranking URLs themselves have almost no links.

| Query | Evidence of room in the current top 10 |
|---|---|
| `it is well with my soul sheet music` | The #1 bare PDF has UR 4 and one referring domain; a DR 17 page ranks #7 with UR 0 and two referring domains |
| `blessed assurance sheet music` | MuseScore ranks #4 with UR 0 and no backlinks; a DR 17 page ranks #5 with UR 0 and one referring domain |
| `come thou fount sheet music` | The #1 bare PDF has no backlinks; multiple top-10 commercial pages have zero backlinks, including a DR 8 result at #9 |
| `o for a thousand tongues to sing sheet music` | The #2 page is DR 17/UR 0 with two referring domains; several other top-10 pages have UR 0 and no backlinks |
| `be thou my vision sheet music` | The #1 result is a bare PDF on DR 31 with UR 0; #2 has no backlinks; a DR 17 page ranks #4 with one referring domain |
| `amazing grace cello sheet music` | A DR 4/UR 0 PDF ranks #2; DR 3 and DR 29 pages with no backlinks also rank in the top 10 |
| `sheet music transposer` | The SERP is mostly forum/help/blog content rather than a strong purpose-built tool, although Transposr at #7 has 547 referring domains |

This supports publishing pages before trying to acquire many links. Transposify
will still need internal links, crawlability, and some domain-level trust, but
the evidence does not suggest a large backlink threshold for most hymn pages.

## How the interactive landing pages should work

Yes: the landing page should contain the complete interactive tool, preloaded
to the state promised by the search result.

Recommended behavior:

1. The canonical hymn page, such as `/hymns/it-is-well-with-my-soul`, loads the
   chosen hymn immediately and targets the larger base query.
2. A measured preset page, such as
   `/hymns/it-is-well-with-my-soul/key-of-c`, server-renders the hymn in C and
   includes a self-canonical URL, unique title/H1/introduction, and exact score
   preview.
3. An instrument page such as `/hymns/amazing-grace/cello` preselects the
   melody voice, bass clef, and an appropriate octave/range. It must describe
   itself as a melody part unless it truly includes a composed accompaniment.
4. The visitor can change key, line, clef, octave, and page size without leaving
   the tool. Changing to an unvalidated combination creates a shareable query
   state but canonicals back to the main hymn page.
5. Search engines receive meaningful HTML before client JavaScript: tune name,
   selected key/clef, available parts, visible preset links, rights/source
   context, and a rendered preview/download action.

This architecture makes the landing promise true on first paint while avoiding
hundreds of near-duplicate indexable combinations.

## Recommended landing-page map

### Priority 0: launch and existing canonical pages

| Target page | Primary cluster | Demand signal | Sampled SERP gap | Recommendation |
|---|---|---|---|---|
| `/hymns/it-is-well-with-my-soul` | `it is well with my soul sheet music` | 450 US volume, KD 0, TP 450 | The #1 result is a bare PDF with one referring domain; several results are piano arrangements or different modern settings | Best current-catalog opportunity. Disambiguate VILLE DU HAVRE prominently. |
| `/hymns/come-thou-fount-of-every-blessing` | `come thou fount sheet music` | 250 US volume, KD 0, TP 200 | The #1 bare PDF has no backlinks; several lower top-10 pages also have none | High priority. Differentiate with SATB/voice extraction, clef choice, and instant preview. |
| `/hymns/blessed-assurance` | `blessed assurance sheet music` | 200 US volume, KD 0, TP 50 | MuseScore ranks #4 with no backlinks; a DR 17 page ranks #5 with one referring domain | High priority and realistic for a focused traditional-hymn page. |
| `/hymns/amazing-grace` | `amazing grace sheet music` | 1,800 US volume, KD 2, TP 500 | Stronger brands and more links than the other hymn SERPs, but DR 17/UR 0 and DR 35/UR 0 pages still rank | Highest upside, but likely slower than the three pages above. |
| `/hymns/o-for-a-thousand-tongues` | `o for a thousand tongues to sing sheet music` | 30 US volume, KD 0, TP 10 | Several top-10 pages have UR 0 and 0–2 referring domains; none offers the full Transposify interaction | Small, highly qualified, and an excellent product-story page. Keep D/bass-clef as a preset rather than a separate initial page. |
| `/hymns/beneath-the-cross-of-jesus` | `beneath the cross of jesus sheet music` | 10 US volume; no current KD/TP | Results mix the traditional ST. CHRISTOPHER hymn and modern Getty material | Keep a strong canonical page, but do not build variants yet. |
| `/hymns` | `hymn sheet music`, `free hymn sheet music` | 150 US volume/KD 2 and 60 US volume/KD 3 respectively | Current results tend to be static libraries rather than configurable editions | Ship as a generic canary with the initial catalog, then strengthen it as more rights-approved hymns go live. |
| `/uses/hymn-transposer` | `sheet music transposer`, `transpose sheet music` | 250–300 US volume, KD 0 | Results mix forums, help pages, Reddit, articles, and upload tools | Use the existing route as the generic tool canary, but state “for public-domain hymns” until arbitrary file upload is supported. |

### Generic canary pages

Use one URL per search intent, not a separate page for every close synonym:

| Canonical page | Primary keyword | Supporting keyword | Initial job |
|---|---|---|---|
| `/hymns` | `hymn sheet music` — 150 US, KD 2 | `free hymn sheet music` — 60 US, KD 3 | Searchable catalog with real hymn links, tune names, available parts, and preview thumbnails; measure when Google begins trusting the library |
| `/uses/hymn-transposer` | `sheet music transposer` — 250 US, KD 0 | `transpose sheet music` — 300 US, KD 0 | Full interactive tool plus an honest catalog-only explanation; measure when Transposify begins entering broader tool SERPs |

The broad title pages `/hymns/amazing-grace` (1,800 US, KD 2) and
`/hymns/it-is-well-with-my-soul` (450 US, KD 0) are also useful canaries, but
they already belong to the core hymn-page architecture and do not require
additional generic URLs.

### Priority 1: curated preset pages

These should be real server-rendered editions with a unique title, introduction,
score preview, selected control state, and download action. Each should link
back to its parent hymn and to nearby keys. If that cannot be done, keep the
variants as sections/presets on the canonical hymn page instead of indexing
separate URLs.

Suggested URL patterns:

- `/hymns/{hymn}/key-of-{key}`
- `/hymns/{hymn}/bass-clef`
- `/hymns/{hymn}/trombone`

First **indexable** key presets justified by measurable Ahrefs volume:

| Hymn | Curated key presets | Measured US demand |
|---|---|---:|
| It Is Well with My Soul | C, G, D | 30, 20, 10 |
| Amazing Grace | C | 20 |
| Blessed Assurance | C | 20 |
| Come, Thou Fount of Every Blessing | C | 10 |

Other Autocomplete keys should remain selectable/shareable presets on the main
hymn page until they earn impressions in Search Console or appear with
measurable third-party volume. O for a Thousand Tongues in D/bass clef belongs
in this non-indexed preset group.

First clef/instrument presets:

| Candidate page | Default score state | Why it is worth testing | Competition note |
|---|---|---|---|
| `/hymns/amazing-grace/cello` | Melody in G major, bass clef, shifted into a comfortable cello octave | 150 US volume, KD 0, TP 70 | Multiple exact competitors, but the top two are UR 0; a DR 4/UR 0 bare PDF ranks #2 and the remaining organic pages are UR 0–5 with no backlinks |
| `/hymns/amazing-grace/trombone` | Melody in concert B-flat major, bass clef, in a comfortable tenor-trombone octave | 70 US volume, KD 0, TP 30 | Exact competitors exist, including an all-keys page, but the ranking URLs are generally UR 0–4 with zero referring domains; editable key and range remain differentiators |
| `Amazing Grace` bass clef | Melody in G major, bass clef, comfortable lower octave | 20 US volume, KD 0, TP 10 | Smaller than instrument-language demand; use a strong section or alias linked from the instrument presets before adding another canonical page |
| Bass-clef hymn library page | Catalog filtered to hymns with useful bass-clef presets | Autocomplete signal but no measurable Ahrefs volume | Treat as internal navigation first, then promote if Search Console shows impressions |

The cello and trombone pages should say “melody part” rather than implying a
composed solo with piano accompaniment. Their defaults are musically routine,
not locked: the visitor can immediately choose a different key, clef, octave,
or hymn voice.

Use instrument language carefully. The current product can produce a concert-
pitch melody or hymn voice in bass clef; that is not the same thing as a
composed trombone-and-piano arrangement. A page should promise “melody part in
bass clef” unless it truly includes an accompaniment/arrangement.

### Priority 2: catalog expansion driven by search patterns

The Open Hymnal source contains 292 unique primary titles. An Ahrefs overview of
`{title} sheet music` found the following strongest evergreen expansion
candidates (rights review still required):

| Expansion candidate | US volume | KD | Traffic potential | Priority note |
|---|---:|---:|---:|---|
| Be Thou My Vision | 600 | 0 | 600 | Best evergreen addition; top SERP result is a bare UR 0 PDF |
| Jesus Loves Me | 300 | 0 | 350 | Strong evergreen demand |
| Nearer, My God, to Thee | 250 | 0 | 80 | Strong evergreen demand |
| Holy, Holy, Holy | 150 | 0 | 60 | Distinguish NICAEA from modern songs/settings |
| The Old Rugged Cross | 150 | 1 | 150 | Key-of-C variant alone has 50 US volume |
| What a Friend We Have in Jesus | 150 | 0 | 60 | Strong fit plus several key variants in Autocomplete |
| Be Still My Soul | 150 | 0 | 70 | Check FINLANDIA text/tune/setting rights carefully |
| Abide with Me | 100 | 0 | 50 | Solid evergreen addition |
| All Creatures of Our God and King | 100 | 0 | 40 | Solid evergreen addition |
| Crown Him with Many Crowns | 100 | 0 | 20 | Solid evergreen addition |
| How Firm a Foundation | 80 | 0 | 450 | Lower direct volume but unusually good traffic potential |

Christmas should be its own seasonal catalog batch: Silent Night (1,500 US),
Joy to the World (900), God Rest Ye Merry Gentlemen (700), Away in a Manger
(600), Angels We Have Heard on High (500), O Come O Come Emmanuel (500), The
First Noel (400), In the Bleak Midwinter (350), and O Come All Ye Faithful
(300) all showed KD 0. Publish these well before seasonal demand peaks.

The rights/provenance gate in the project plan still applies independently to
the text, tune, and harmonization before any candidate is published.

## On-page brief for a hymn landing page

The page should answer the query before explaining the product.

Suggested metadata and copy structure:

- **Title:** `{Hymn} Sheet Music in Any Key & Clef | Transposify`
- **H1:** `{Hymn} sheet music in the key and clef you need`
- **Opening sentence:** Name the traditional tune, say the score is printable,
  and state that the visitor can select a key, SATB or individual voice, and
  clef.
- **Visible preset links:** List the demand-validated keys in human-readable
  text: “Key of C,” “Key of D,” and so on.
- **Clef/part copy:** Explain full SATB versus soprano/alto/tenor/bass and name
  treble, bass, alto, and tenor clefs.
- **Score preview:** Render the promised preset without requiring an extra
  click.
- **Download wording:** Say exactly what is downloaded (print-ready PDF), page
  size, and whether it is free.
- **Tune disambiguation:** Include the tune name and authorship so searches for
  a modern song with the same title do not create a misleading landing page.
- **Internal links:** Link to the hymn transposer, bass-clef collection, nearby
  key presets, and related hymns.

Example for an exact preset:

- **Title:** `It Is Well with My Soul Sheet Music in C — SATB & Bass Clef`
- **H1:** `It Is Well with My Soul sheet music in C major`
- **Default state:** C major, full SATB, original clefs; offer bass line and
  bass-clef melody as immediate alternate presets.
- **Disambiguation:** “Traditional VILLE DU HAVRE tune by Philip P. Bliss,” not
  the Hillsong song/setting.

## Tracked keyword seed list

This is the seed set used for the Ahrefs pass. Keep zero-volume phrases in a
rank tracker when they have clear download intent; low-volume tools routinely
undercount long-tail queries.

### Tool and category seeds

- hymn transposer
- hymn key transposer
- hymn sheet music transposer
- bass clef hymns
- hymns in bass clef
- sheet music transposer
- sheet music transposer PDF
- transpose sheet music online
- transpose sheet music online free PDF
- SATB hymn sheet music

### Current catalog seeds

- amazing grace bass clef
- amazing grace bass clef sheet music
- amazing grace trombone sheet music
- amazing grace cello sheet music
- amazing grace sheet music key of C
- amazing grace sheet music key of D
- amazing grace sheet music key of F
- amazing grace sheet music key of G
- blessed assurance sheet music key of C
- blessed assurance sheet music key of D
- blessed assurance sheet music key of G
- blessed assurance trombone sheet music
- it is well with my soul sheet music key of C
- it is well with my soul sheet music key of D
- it is well with my soul sheet music key of G
- it is well with my soul sheet music key of A
- it is well with my soul SATB sheet music
- it is well with my soul trombone sheet music
- come thou fount sheet music key of C
- come thou fount sheet music key of D
- come thou fount sheet music key of G
- come thou fount SATB sheet music
- come thou fount trombone sheet music
- o for a thousand tongues to sing sheet music
- o for a thousand tongues to sing hymn sheet music
- o for a thousand tongues to sing key of C
- o for a thousand tongues to sing key of D
- o for a thousand tongues to sing key of F
- o for a thousand tongues to sing key of G
- o for a thousand tongues to sing bass clef
- beneath the cross of jesus hymn sheet music

### Expansion seeds

- be thou my vision sheet music key of C
- be thou my vision sheet music key of D
- be thou my vision sheet music key of E
- be thou my vision sheet music key of E flat
- be thou my vision sheet music key of F
- be thou my vision sheet music key of G
- what a friend we have in jesus sheet music key of C
- what a friend we have in jesus sheet music key of D
- what a friend we have in jesus sheet music key of F
- what a friend we have in jesus sheet music key of G
- holy holy holy sheet music key of C
- holy holy holy sheet music key of D
- holy holy holy sheet music key of G
- the old rugged cross sheet music key of C
- the old rugged cross sheet music key of G
- the old rugged cross sheet music key of A
- jesus loves me sheet music key of C
- jesus loves me sheet music key of D

## Tool recommendation

### Lowest-cost workable stack

1. Google Autocomplete for phrase discovery.
2. Google Ads Keyword Planner for directional monthly volume and related
   phrases. It requires a completed Google Ads account with billing information,
   but an ad campaign does not need to be the research goal.
3. Manual live-SERP review for intent match and result quality.
4. Google Search Console after indexation for real query/impression data.

Keyword Planner's “competition” field reflects ad competition, not organic
ranking difficulty, so it cannot replace the SERP review.

### Best automated stack in the current setup

The active Ahrefs Lite connection is sufficient. This pass retrieved:

- US and global volume
- keyword difficulty
- traffic potential and parent topic
- intent classification
- current top-10 URLs, domain rating, URL rating, and referring domains
- matching/search-suggestion terms for each cluster

Continue using that data to rank proposed pages, but do not discard good
zero-volume long tails automatically.

## Recommended next actions

1. Remove the intentional `noindex` when the catalog is ready for discovery;
   add sitemap/robots metadata and verify Search Console.
2. Improve the six existing canonical hymn pages, in the priority order above.
3. Add the measured It Is Well key presets plus Amazing Grace cello and
   trombone presets.
4. Ship the `/hymns` catalog canary with the initial rights-approved catalog and
   optimize the existing `/uses/hymn-transposer` route for the generic tool
   cluster without implying arbitrary-file upload.
5. Ingest and approve Be Thou My Vision next, followed by Jesus Loves Me,
   Nearer My God to Thee, Holy Holy Holy, The Old Rugged Cross, and What a
   Friend We Have in Jesus.
6. Prepare a separate Christmas batch early enough to index before November.
7. Track the base, key, clef, and instrument queries in Ahrefs Rank Tracker and
   record a 28-day Search Console baseline before the next content batch.

## Sample live-result sources

- [Hymnary FlexScores](https://www.hymnary.org/flexscores) — incumbent with
  transposition, clef/instrument parts, and print formats.
- [RiffSpot bass-clef hymn category](https://riffspot.com/music/beginner-bass-clef/category/hymns/)
  — exact competitor for the category query.
- [Jackman Music bass-clef hymn collection](https://jackmanmusic.com/products/hymns-for-instruments-bass-clef)
  — paid LDS-focused collection.
- [8notes Amazing Grace for trombone](https://www.8notes.com/scores/15697.asp)
  — a strong exact result with all 12 transpositions.
- [MuseScore O for a Thousand Tongues score](https://musescore.com/user/2504401/scores/10367629)
  — the result that inspired the initial query.
- [PraiseCharts It Is Well with My Soul](https://www.praisecharts.com/songs/details/23390/it-is-well-with-my-soul-sheet-music/lead-piano)
  — demonstrates title/setting ambiguity.
- [Ahrefs API v3 plan eligibility](https://help.ahrefs.com/en/articles/6559232-about-api-v3)
  — Lite and higher support API/MCP usage.
- [Google Keyword Planner documentation](https://support.google.com/google-ads/answer/7337243?hl=en)
  — keyword discovery and monthly-search estimates.
