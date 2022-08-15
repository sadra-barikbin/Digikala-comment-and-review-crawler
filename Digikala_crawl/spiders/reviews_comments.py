from matplotlib.pyplot import title
import scrapy
from scrapy.http.response.text import TextResponse
from scrapy.exceptions import CloseSpider
from typing import Dict, Any, Iterable, Optional, Union

from Digikala_crawl.items import Comment, Review

DIGIKALA_API = "http://api.digikala.com/v1"

class ReviewsAndCommentsSpider(scrapy.Spider):
    name = 'reviews_comments'
    allowed_domains = ['api.digikala.com']

    def __init__(self, limit_in_gb: int=0.001, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.limit_in_mb = limit_in_gb * 1024

    def start_requests(self) -> Iterable[scrapy.Request]:
        return [scrapy.Request(
            f'{DIGIKALA_API}/',
            callback=self.parse_initial_response
        )]

    def parse_initial_response(self, response: TextResponse) -> Iterable[scrapy.Request]:
        data: Dict[str, Any] = response.json()['data']
        for main_category_dict in data['main_categories']['categories']:
            main_category_code: str = main_category_dict['code']

            yield scrapy.Request(
                f'{DIGIKALA_API}/categories/{main_category_code}/',
                callback=self.parse_main_categories_response
            )

    def parse_main_categories_response(self, response: TextResponse) -> Iterable[scrapy.Request]:
        data: Dict[str, Any] = response.json()['data']
        for category_dict in data['sub_categories']:
            category_code: str = category_dict['code']

            yield scrapy.Request(
                f"{DIGIKALA_API}/categories/{category_code}/search/",
                callback=self.parse_category_response
            )
    
    def parse_category_response(self, response: TextResponse) -> Iterable[scrapy.Request]:
        data: Dict[str, Any] = response.json()['data']

        if 'categories' in data['filters']:
            for subcategory_dict in data['filters']['categories']['options']:
                subcategory_code: str = subcategory_dict['code']

                yield scrapy.Request(
                    f"{DIGIKALA_API}/categories/{subcategory_code}/search/",
                    callback=self.parse_subcategory_response,
                )
        else:
            for product_dict in data['products']:
                product_id: int = product_dict['id']

                yield scrapy.Request(
                    f"{DIGIKALA_API}/product/{product_id}/",
                    callback=self.parse_product_response
                )
            
            current_page: int = data['pager']['current_page']
            total_pages: int = data['pager']['total_pages']
            category_code: str = data['category']['code']
            if current_page < total_pages:
                yield scrapy.Request(
                    f"{DIGIKALA_API}/categories/{category_code}/search/?page={current_page + 1}",
                    callback=self.parse_subcategory_response,
                )

    def parse_subcategory_response(self, response: TextResponse) -> Iterable[scrapy.Request]:
        data: Dict[str, Any] = response.json()['data']
        subcategory_code: str = data["category"]["code"]

        if "brands" in data["filters"]:
            for brand_dict in data["filters"]["brands"]["options"]:
                brand_code: str = brand_dict['code']

                yield scrapy.Request(
                    f"{DIGIKALA_API}/categories/{subcategory_code}/brands/{brand_code}/search/",
                    callback=self.parse_brand_response
                )
        else:
            for product_dict in data['products']:
                product_id: int = product_dict['id']

                yield scrapy.Request(
                    f"{DIGIKALA_API}/product/{product_id}/",
                    callback=self.parse_product_response
                )
            
            current_page: int = data['pager']['current_page']
            total_pages: int = data['pager']['total_pages']
            if current_page < total_pages:
                yield scrapy.Request(
                    f"{DIGIKALA_API}/categories/{subcategory_code}/search/?page={current_page + 1}",
                    callback=self.parse_subcategory_response,
                )

    def parse_brand_response(self, response: TextResponse) -> Optional[Iterable[scrapy.Request]]:
        data: Dict[str, Any] = response.json()['data']
        subcategory_code: str = data["category"]["code"]
        for product_dict in data['products']:
            product_id: int = product_dict['id']

            yield scrapy.Request(
                f"{DIGIKALA_API}/product/{product_id}/",
                callback=self.parse_product_response
            )

        current_page: int = data['pager']['current_page']
        total_pages: int = data['pager']['total_pages']
        brand_code: str = data["brand"]["code"]

        # Second clause is due to api limitations, but since we have broken
        # products into main_categories, categories, subcategories and brands,
        # this is not much likely to reach this limitation here, except for
        # some categories when brand is `miscellaneous`.
        if current_page < total_pages and current_page < 100:
            yield scrapy.Request(
                f"{DIGIKALA_API}/categories/{subcategory_code}/brands/{brand_code}/search/?page={current_page + 1}",
                callback=self.parse_brand_response
            )

    def parse_product_response(self, response: TextResponse) -> Iterable[Union[scrapy.Request, scrapy.Item]]:
        product: Dict[str, Any] = response.json()['data']['product']

        if "description" in product["review"]:
            yield Review(text=product["review"]["description"])
        
        for expert_review_section in product['expert_reviews']["review_sections"]:
            for subsection in expert_review_section['sections']:
                if subsection['template'] == 'text':
                    yield Review(text=subsection['text'])

        product_id: int = product['id']
        yield scrapy.Request(
            f"{DIGIKALA_API}/product/{product_id}/comments/",
            callback=self.parse_product_comments_response,
            cb_kwargs={'product_id': product_id}
        )

    def parse_product_comments_response(
        self,
        response: TextResponse,
        product_id: int
    ) -> Optional[Iterable[Union[scrapy.Request, scrapy.Item]]]:
        data: Dict[str, Any] = response.json()['data']

        if 'comments' in data:
            for comment_dict in data['comments']:
                yield Comment(
                    text="" if comment_dict['body'] is None else comment_dict['body'],
                    title="" if comment_dict['title'] is None else comment_dict['title'],
                    date=comment_dict['created_at']
                )
        
        for comment_dict in data['media_comments']:
            yield Comment(
                text="" if comment_dict['body'] is None else comment_dict['body'],
                title="" if comment_dict['title'] is None else comment_dict['title'],
                date=comment_dict['created_at']
            )

        current_page: int = data['pager']['current_page']
        total_pages: int = data['pager']['total_pages']

        # Second clause is due to api limitations, but since we have broken
        # products into main_categories, categories, subcategories and brands,
        # this is not likely to face with this limitation here.
        if current_page < total_pages and current_page < 100:
            yield scrapy.Request(
                f"{DIGIKALA_API}/product/{product_id}/comments/?page={current_page + 1}",
                callback=self.parse_product_comments_response,
                cb_kwargs={'product_id': product_id}
            )
