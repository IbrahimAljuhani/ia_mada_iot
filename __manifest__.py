# -*- coding: utf-8 -*-
{
    'name': 'POS Mada Terminal (IoT)',
    'version': '18.0.1.1.0',
    'category': 'Point of Sale',
    'summary': 'Mada payment terminal integration for POS via IoT Box (NeoLeap)',
    'description': """
        Adds Mada payment terminal support to Odoo 18 POS via IoT Box.
        Works with NeoLeap Mada app running WebSocket on ws://localhost:7000.
        Requires Raspberry Pi running Odoo IoT Box on the same local network.

        Features:
        - CHECK_STATUS before payment (NeoLeap protocol compliant)
        - Full StatusCode handling (00 approved, 01 bank decline, 11 cancelled)
        - Manual payment fallback (approval code entry)
        - Arabic/English translations
        - Safe import guard (no crash on Odoo server)
    """,
    'author': 'Ibrahim Aljuhani',
    'email': 'info@ia.sa',
    'website': 'https://ia.sa',
    'depends': ['point_of_sale', 'iot', 'pos_iot'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'ia_mada_iot/static/src/app/payment_mada.js',
            'ia_mada_iot/static/src/app/model.js',
            'ia_mada_iot/static/src/app/payment_screen.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
