from scrapy.exporters import BaseItemExporter
from scrapy.utils.python import to_bytes

from Digikala_crawl.items import Review

class TxtReviewExporter(BaseItemExporter):
    def __init__(self, file, **kwargs):
        super().__init__(dont_fail=True, **kwargs)
        self.file = file

    def export_item(self, item: Review):
        self.file.write(to_bytes(item['text'] + '\n', self.encoding))