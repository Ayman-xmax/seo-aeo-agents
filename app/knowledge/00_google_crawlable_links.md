# Make Your Links Crawlable (Google Search Central)

Source: https://developers.google.com/search/docs/crawling-indexing/links-crawlable
Tier: official_google

## Crawlable link markup
Google can only follow links that are `<a>` HTML elements with an `href` attribute
resolving to a real URL. Acceptable forms:
- `<a href="https://example.com">`
- `<a href="/products/category/shoes">`
- `<a href="./products/category/shoes">`
- `<a href="/products/category/shoes" onclick="javascript:goTo('shoes')">` (has href)
- `<a href="/products/category/shoes" class="pretty">`

Links inserted dynamically with JavaScript are crawlable **as long as** they use the
same `<a href>` HTML markup. Verify with the URL Inspection Tool that the link is in
the rendered HTML.

## Markup Google CANNOT reliably follow
- `<a routerLink="products/category">` (framework attribute, no href)
- `<span href="https://example.com">` (not an anchor element)
- `<a onclick="goto('https://example.com')">` (script-only, no href)
- `<a href="javascript:goTo('products')">` (javascript: pseudo-URL)
- `<a href="javascript:window.location.href='/products'">` (javascript: pseudo-URL)

The href must resolve to an actual web address a crawler can request
(`/products`, `/products.php?id=123`, `https://example.com/stuff`).

## Anchor text best practices
- Put descriptive anchor text between the `<a>` tags; it tells people and Google what
  the linked page is about.
- Empty links: use the `title` attribute. Image links: use the image `alt` text.
- Avoid generic anchors: "click here", "read more", "here", "website".
- Test: read the anchor text out of context — is it specific enough to make sense alone?
- Do not keyword-stuff anchors (spam-policy violation); keep them natural and relevant.
- Balance length: not too short/generic, not an entire sentence.
- Don't chain links next to each other — readers can't distinguish them and you lose the
  surrounding descriptive context. Space links out.

## Internal links
Every page you care about should have a link from at least one other page on your site.
There is no magic ideal number of links; if it feels like too many, it probably is.

## External links & attributes
Link out when it adds value and cite sources. Use link attributes correctly:
- `rel="nofollow"` — only for sources you don't trust (don't apply to every external link).
- `rel="sponsored"` — required for paid/advertising links.
- `rel="ugc"` — required for user-generated content links (forums, comments, Q&A).
Use `sponsored` or `nofollow` for all paid links. If users can insert links on your site,
add `ugc` or `nofollow`.
