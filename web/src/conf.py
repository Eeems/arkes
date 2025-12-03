import datetime
from datetime import timezone

year = datetime.datetime.today().year

project = "Arkēs"
copyright = f"2024-{year}, Eeems"
author = "Nathaniel 'Eeems' van Diepen"

html_theme_path = ["_themes"]
html_static_path = ["_static"]
templates_path = ["_templates"]
html_js_files = [
    "https://peek.eeems.website/peek.js",
    (
        "https://browser.sentry-cdn.com/6.16.1/bundle.tracing.min.js",
        {
            "integrity": "sha384-hySah00SvKME+98UjlzyfP852AXjPPTh2vgJu26gFcwTlZ02/zm82SINaKTKwIX2",
            "crossorigin": "anonymous",
        },
    ),
    "oxide.js",
]

html_title = "Arkēs"
html_theme = "oxide"
master_doc = "sitemap"
html_sidebars = {"**": ["nav.html", "sidefooter.html"]}
html_permalinks_icon = "#"
html_baseurl = "https://arkes.eeems.codes"
html_use_opensearch = "https://arkes.eeems.codes"

ogp_site_url = html_baseurl
ogp_description_length = 200
ogp_site_name = project
ogp_image = "/_images/favicon.svg"
ogp_use_first_image = True
ogp_type = "article"
ogp_enable_meta_description = True
ogp_custom_meta_tags = [
    f'<meta property="og:article:modified_time" content="{datetime.datetime.now(timezone.utc).isoformat()}" />',
]
extensions = [
    "sphinxext.opengraph",
]
