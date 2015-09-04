# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://ecosoft.co.th).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Lazada Import',
    'version': '1.0',
    'author': 'Ecosoft',
    'website' : 'http://www.ecosoft.co.th',
    'category': 'Ecosoft Custom',
    'description':"""
- Lazada Import Orders.
    """,
    'data':[
            'data/lazada_order_sequence.xml',
            'data/history_sequence.xml',
            'data/partner_data.xml',
            'views/import_history_view.xml',
            'wizard/import_wizard_view.xml',
            'views/sale_view.xml',
            'views/invoice_view.xml',
            'views/stock_view.xml',
            'views/account_move_view.xml',
            ],
    'depends':['fofo_custom'],
    'installable':True,
    'auto_install':False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
