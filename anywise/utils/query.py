"""
NOTE: unpack might be great for query

"""

import typing as ty


class SQLQuery[Q]: ...


class ProductSalesByWeek:
    """
    SELECT
        sku, quantity, price
    FROM
        products
    WHERE
        sku = :sku
    """

    sku: str


class SalesReport:  # BaseModel
    sku: str
    total_sales: int
    total_prices: int
    avg_sales_daily: float

    # @computed_field
    # def avg_price(self):
    #     return self.total_prices / self.total_sales


class Connection: ...


def query(t: type) -> ty.Callable[..., ty.Any]: ...


async def get_sales_report(
    conn: Connection, query: SQLQuery[ProductSalesByWeek]
) -> SalesReport:
    """
    This function could be auto generated, e.g.

    query_func = generate_query(conn=inject(get_conn), query=SQLQuery[SalesReport])
    """
    ...
    # return await conn.execute(query)
