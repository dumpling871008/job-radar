from sqlalchemy import func, select

from app.models.crawler_keyword import (
    CrawlerKeyword,
)
from app.models.crawler_setting import (
    CrawlerSetting,
)


class CrawlerSettingsRepository:
    def __init__(self, session):
        self.session = session

    def get_settings(self):
        return self.session.get(
            CrawlerSetting,
            1,
        )

    def add_settings(self, settings):
        self.session.add(settings)
        return settings

    def get_keywords(self):
        return self.session.scalars(
            select(CrawlerKeyword).order_by(
                CrawlerKeyword.sort_order,
                CrawlerKeyword.id,
            )
        ).all()

    def get_keyword(self, keyword_id):
        return self.session.get(
            CrawlerKeyword,
            keyword_id,
        )

    def find_keyword(self, keyword):
        return self.session.scalar(
            select(CrawlerKeyword).where(
                func.lower(
                    CrawlerKeyword.keyword
                )
                == keyword.lower()
            )
        )

    def add_keyword(self, keyword):
        self.session.add(keyword)
        return keyword

    def delete_keyword(self, keyword):
        self.session.delete(keyword)
