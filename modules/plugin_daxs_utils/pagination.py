

class Pagination:
    """
    Utility class for building pagination
    """

    def __init__(self, db, query, limit=10, current_page=1, order_by=None):
        """
        Utility class for building pagination constructor
        :param db: Database object
        :param query: Query
        :param limit: Number of elements on page
        :param current_page: Current page
        :param orderby: Ordering param for query
        """
        self.db = db
        self.query = query
        self.limit = limit
        self.current_page = current_page
        self.order_by = order_by
        self._update_pagination()

    def _update_pagination(self):
        """
        Set count and total pages
        """
        self.count = self.count()
        self.pages = self.pages()

    def count(self):
        """
        Count total elements
        :return: Total query elements
        """
        return self.db(self.query).count()

    def pages(self):
        """
        Calculate total pages
        :return: Total pages
        """
        if self.count % self.limit > 0:
            pages = (self.count // self.limit) + 1
        else:
            pages = self.count // self.limit
        return pages

    def set_page(self, page):
        """
        Set current page
        """
        self.current_page = page

    def set_next_page(self):
        """
        Jump to next page
        """
        self.current_page += 1

    def is_last_page(self):
        return self.current_page >= self.pages

    def select_next_page(self, *fields, **params):
        """
        Jump to next page and select query, same signature of select()
        :return: Rows object
        """
        self.set_next_page()
        return self.select_current_page(*fields, **params)

    def select_current_page(self, *fields, **params):
        """
        Select query for current page elements, same signature of select()
        :return: Rows object
        """
        start = (self.current_page - 1) * self.limit
        end = self.current_page * self.limit
        return self.db(self.query).select(*fields, orderby=self.order_by, limitby=(start, end), **params)