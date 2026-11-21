{
    "name": "MJO Connector — AI marketing manager for your store",
    "summary": "Connect Odoo to MJO: a read-only access group and a one-click link. MJO reads your invoices, products and stock to prepare offers, designs and WhatsApp campaigns you approve.",
    "version": "17.0.1.0.0",
    "category": "Marketing",
    "author": "1st Mall (MJO)",
    "website": "https://mjo.marketing",
    "license": "LGPL-3",
    "depends": ["account", "stock"],
    "data": [
        "security/mjo_security.xml",
        "security/ir.model.access.csv",
        "views/mjo_menu.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
}
