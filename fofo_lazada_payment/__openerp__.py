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
    'name' : 'Lazada Payment Import',
    'version': '1.0',
    'author': 'Ecosoft',
    'website' : 'http://www.ecosoft.co.th',
    'category': 'Ecosoft Custom',
    'description':"""
- This module allows to import payment from .xlsx file and it will create the account billing for the .xlsx file content.
- Import payment from Accounting/Customer/Lazada Payment Import.
- It also maintain the history of imported payment.
    """,
    'data':[
            'security/ir.model.access.csv',
            'data/history_sequence.xml',
            'views/lazada_payment_transaction_view.xml',
            'data/transaction_type_data.xml',
            'data/transaction_type_config_data.xml',
            'wizard/payment_view.xml',
            'views/account_voucher_view.xml',
            'views/account_billing_view.xml',
            'views/payment_history_view.xml'
            ],
    'depends':['fofo_lazada'],
    'installable':True,
    'auto_install':False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
