# site-map

Extract all internal URLs from a documentation site by fetching its sitemap.xml.

## Usage

```
/site-map <site_base_url> [output_file]
```

If `output_file` is not specified, defaults to `scrape_translate/urls.txt` relative to project root.

## Steps

1. **Fetch the sitemap.xml**. Most docs sites (Mintlify, Docusaurus, etc.) serve it at `<base>/docs/sitemap.xml`:

```bash
curl -s "<base_url>/docs/sitemap.xml"
# Alternatives to try if 404:
# curl -s "<base_url>/sitemap.xml"
# curl -s "<base_url>/sitemap_index.xml"  (may reference sub-sitemaps)
```

2. **Extract URLs** matching the target path. Use grep to filter and sed to clean:

```bash
# Extract all <loc> values, filter by desired prefix, sort unique
curl -s "<base_url>/docs/sitemap.xml" \
  | grep -oE '<loc>https?://[^<]+</loc>' \
  | sed 's/<loc>//;s/<\/loc>//' \
  | grep '<path_prefix>' \
  | sort -u
```

Replace `<path_prefix>` with the path segment to filter by, e.g. `/zh-CN` for Chinese pages.

3. **Count and save**:

```bash
# Preview count first
... | wc -l

# Save to file
... > <output_file>
```

4. **Fallback: HTML scraping** if no sitemap.xml exists. Extract hrefs from the main page:

```bash
curl -s -L "<base_url>/<path>" \
  | grep -oE 'href="[^"]*"' \
  | sed 's/href="//;s/"//' \
  | grep '<path_prefix>' \
  | sort -u
```

This is less complete (only finds links on one page) but works as a fallback.

## Notes

- Sitemaps are the most reliable source — they list every page the site owner wants indexed
- The `grep -oE` pattern works in Git Bash / Unix shells; on Windows CMD use PowerShell equivalents
- For large sitemaps, pipe through `wc -l` first to verify the count before saving
