from demo.event import Event, Item, Order


def test_event():
    order = Order()
    item = Item("item", quantity=1)
    item_added = order.add_item(item)
