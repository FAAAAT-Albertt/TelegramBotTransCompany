"""The File Contains Common Classes For Integration"""

class Contact:
    """Contacts Phone"""

    def __init__(self, phone: str, name: str, address: str, city: str) -> None:
        self.phone = phone
        self.name = name
        self.address = address
        self.city = city

class Order:
    """Order Class"""

    def __init__(self, contact: Contact, delivery_type, order_id, order_type='Самовывоз') -> None:
        self.contact = contact
        self.delivery_type = delivery_type
        self.order_id = order_id
        self.order_type = order_type
