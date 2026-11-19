w3lib.html.get_base_url() can be slow due to quadratic regex complexity

`get_base_url("<base "*30000)` takes several second here, due to `<base\s[^>]*` in `w3lib.html._baseurl_re`. Changing `[^>]` to `[^<>]` fixes this case, not sure if there are still problematic ones after that.

Note that Scrapy only passes the first 4Kb of the page to this function so it's not a problem there.
