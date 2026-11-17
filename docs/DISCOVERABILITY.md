# Project discoverability

## Initial audit · 17 November 2026

The public GitHub repository returned HTTP 200 and its initial HTML included
the README tagline. No `X-Robots-Tag`, robots meta element, or Googlebot meta
element was observed. GitHub Pages was unset, and the expected project URL
returned HTTP 404.

Sampled public searches for the exact project name, owner, tagline, and
repository scope did not surface a matching result. A Google-specific check
did not yield usable result listings. The Google index state remains unverified.
[Google's guidance on search operators](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site)

The repository description now names TRAJYN as an experimental experience
layer for agents. The repository topics describe agent memory, AI
infrastructure, experience learning, open source, and Python.

## Site and Search Console

The [project website](https://akaadiarun.github.io/trajyn/) returned HTTP 200
without authentication. Its canonical URL matched the repository homepage.
The [sitemap](https://akaadiarun.github.io/trajyn/sitemap.xml), social image,
and evidence downloads also returned HTTP 200. The homepage sent no
observed `noindex` directive.

The Pages workflow builds static HTML from `site/` and uses the Pages-provided
base URL for canonical, Open Graph, JSON-LD, and sitemap URLs. The source
trace and capsule are served at project-relative paths. Hosting operates
under `/trajyn/`. Crawlers read `robots.txt` on the hostname root.
[Google's robots specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)

Search Console verified the URL-prefix property through its HTML tag and
confirmed the sitemap submission on 17 November 2026.
[Open the submitted sitemap in Search Console](https://search.google.com/search-console/sitemaps?resource_id=https%3A%2F%2Fakaadiarun.github.io%2Ftrajyn%2F)

### Verification maintenance

1. In [Google Search Console](https://search.google.com/search-console/welcome),
   add the URL-prefix property `https://akaadiarun.github.io/trajyn/`.
2. Choose **HTML tag**. Copy the value of the `content` attribute from the tag.
   In TRAJYN's GitHub **Settings → Secrets and variables → Actions → Variables**,
   create the repository variable `GOOGLE_SITE_VERIFICATION` with that value.
3. Run the [Project website workflow](https://github.com/akaAdiArun/trajyn/actions/workflows/pages.yml)
   on `main`. View the live homepage source and confirm the tag appears.
4. Click **Verify** in Search Console. In **Sitemaps**, submit `sitemap.xml`
   once. Keep the verification variable in place for future checks.

The variable takes the account-specific value from Search Console. Search
engines control indexing and ranking, and reporting can lag deployment.
[Verification instructions](https://support.google.com/webmasters/answer/9008080) ·
[Sitemap instructions](https://support.google.com/webmasters/answer/7451001)

The website uses its own original [Open Graph image](../site/assets/social-preview.png).
GitHub's repository card uses the same image, configured separately under
**Settings → Social preview**.
[GitHub preview instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
