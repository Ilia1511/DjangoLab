from importlib import reload

from django.test import SimpleTestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve

import WebApp.urls as project_urls


class DocsRoutingTests(SimpleTestCase):
    def reload_urls(self):
        clear_url_caches()
        reload(project_urls)

    @override_settings(DOCS_ENABLED=True)
    def test_docs_route_is_available_in_development(self):
        self.reload_urls()
        match = resolve("/api/docs/")
        self.assertEqual(match.url_name, "swagger-ui")

    @override_settings(DOCS_ENABLED=False)
    def test_docs_route_is_hidden_in_production(self):
        self.reload_urls()
        with self.assertRaises(Resolver404):
            resolve("/api/docs/")
