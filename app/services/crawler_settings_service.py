from app.config import (
    DETAIL_REFRESH_HOURS,
    MAX_DETAIL_FETCHES,
    MAX_SEARCH_PAGES_PER_KEYWORD,
    REQUEST_INTERVAL_SECONDS,
)
from app.models.crawler_keyword import (
    CrawlerKeyword,
)
from app.models.crawler_setting import (
    CrawlerSetting,
)
from app.repositories.crawler_settings_repository import (
    CrawlerSettingsRepository,
)


class CrawlerSettingsService:
    def __init__(self, session):
        self.session = session
        self.repository = (
            CrawlerSettingsRepository(
                session
            )
        )

    @staticmethod
    def _integer(value, name, minimum, maximum):
        try:
            normalized = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{name} 必須是整數"
            ) from error

        if not minimum <= normalized <= maximum:
            raise ValueError(
                f"{name} 必須介於 "
                f"{minimum} 到 {maximum}"
            )
        return normalized

    @staticmethod
    def _interval(value):
        try:
            normalized = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Request 間隔必須是數字"
            ) from error

        if normalized < 1:
            raise ValueError(
                "Request 間隔不可小於 1 秒"
            )
        return normalized

    @staticmethod
    def _keyword(value):
        normalized = " ".join(
            (value or "").split()
        )
        if not normalized:
            raise ValueError(
                "Keyword 不可為空"
            )
        if len(normalized) > 255:
            raise ValueError(
                "Keyword 不可超過 255 字元"
            )
        return normalized

    @staticmethod
    def _boolean(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no", ""}:
            return False
        raise ValueError("啟用狀態格式不正確")

    def get_settings(self):
        settings = (
            self.repository.get_settings()
        )
        if settings is None:
            settings = CrawlerSetting(
                id=1,
                max_detail_fetches=(
                    MAX_DETAIL_FETCHES
                ),
                max_search_pages_per_keyword=(
                    MAX_SEARCH_PAGES_PER_KEYWORD
                ),
                detail_refresh_hours=(
                    DETAIL_REFRESH_HOURS
                ),
                request_interval_seconds=(
                    REQUEST_INTERVAL_SECONDS
                ),
            )
            self.repository.add_settings(
                settings
            )
            self.session.flush()
        return settings

    def update_settings(
        self,
        *,
        max_detail_fetches,
        max_search_pages_per_keyword,
        detail_refresh_hours,
        request_interval_seconds,
    ):
        values = {
            "max_detail_fetches": self._integer(
                max_detail_fetches,
                "每次最多 Detail",
                1,
                500,
            ),
            "max_search_pages_per_keyword": (
                self._integer(
                    max_search_pages_per_keyword,
                    "每個關鍵字最多搜尋頁數",
                    1,
                    20,
                )
            ),
            "detail_refresh_hours": self._integer(
                detail_refresh_hours,
                "舊職缺重新檢查小時數",
                1,
                720,
            ),
            "request_interval_seconds": (
                self._interval(
                    request_interval_seconds
                )
            ),
        }
        settings = self.get_settings()
        for field, value in values.items():
            setattr(settings, field, value)
        return settings

    def get_keywords(self):
        return self.repository.get_keywords()

    def add_keyword(
        self,
        *,
        keyword,
        enabled=True,
        target_count,
        sort_order=0,
    ):
        keyword = self._keyword(keyword)
        if self.repository.find_keyword(keyword):
            raise ValueError(
                "Keyword 已存在"
            )

        model = CrawlerKeyword(
            keyword=keyword,
            enabled=self._boolean(enabled),
            target_count=self._integer(
                target_count,
                "Target Count",
                1,
                500,
            ),
            sort_order=self._integer(
                sort_order,
                "排序",
                -100000,
                100000,
            ),
        )
        return self.repository.add_keyword(
            model
        )

    def update_keyword(
        self,
        keyword_id,
        *,
        keyword,
        enabled,
        target_count,
        sort_order,
    ):
        model = self.repository.get_keyword(
            keyword_id
        )
        if model is None:
            raise LookupError(
                "找不到 Keyword"
            )

        keyword = self._keyword(keyword)
        duplicate = (
            self.repository.find_keyword(
                keyword
            )
        )
        if (
            duplicate is not None
            and duplicate.id != model.id
        ):
            raise ValueError(
                "Keyword 已存在"
            )

        model.keyword = keyword
        model.enabled = self._boolean(
            enabled
        )
        model.target_count = self._integer(
            target_count,
            "Target Count",
            1,
            500,
        )
        model.sort_order = self._integer(
            sort_order,
            "排序",
            -100000,
            100000,
        )
        return model

    def delete_keyword(self, keyword_id):
        model = self.repository.get_keyword(
            keyword_id
        )
        if model is None:
            raise LookupError(
                "找不到 Keyword"
            )
        self.repository.delete_keyword(model)

    def get_runtime_config(self):
        settings = self.get_settings()
        keywords = [
            {
                "keyword": item.keyword,
                "target_count": (
                    item.target_count
                ),
            }
            for item in self.get_keywords()
            if item.enabled
        ]
        return {
            "keywords": keywords,
            "max_detail_fetches": (
                settings.max_detail_fetches
            ),
            "max_search_pages_per_keyword": (
                settings
                .max_search_pages_per_keyword
            ),
            "detail_refresh_hours": (
                settings.detail_refresh_hours
            ),
            "request_interval_seconds": (
                settings
                .request_interval_seconds
            ),
        }
