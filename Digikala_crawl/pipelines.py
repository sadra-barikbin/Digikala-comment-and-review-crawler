# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


from typing import Union
import scrapy
from tokenizers import normalizers, Regex
from khayyam import JalaliDate

from Digikala_crawl.items import Review, Comment


class ReviewAndCommentNormalizerPipeline:

    normalizer = normalizers.Sequence([
        normalizers.Replace(Regex('[^‌0-9۰-۹ۀء-غ ف-ي ًھکگژپچۆۇێەی!.,?؟!،‌]'), ' '),
        normalizers.Replace(Regex('[0-9۰-۹]+'), '[NUM]'),
        normalizers.Replace(Regex('[ي­ێ]'), 'ی'),
        normalizers.Replace(Regex('[ۀة]'), 'ه'),
        normalizers.Replace(Regex('[ك]'), 'ک'),
        normalizers.Replace(Regex('[إ]'), 'ا'),
        normalizers.Replace(Regex('[ڒ]'), 'ر'),
        normalizers.Replace(Regex('[ۆ]'), 'و'),
        normalizers.Replace(Regex('  +'), ' '),
    ])

    def process_item(self, item: Union[Comment, Review], spider):

        item['text'] = self.normalizer.normalize_str(item['text'])

        if isinstance(item, Comment):

            item['title'] = self.normalizer.normalize_str(item['title'])
            item['date'] = JalaliDate.strptime(item['date'],'%d %B %Y').todate().isoformat()
        
        return item
