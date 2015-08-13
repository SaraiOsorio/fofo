# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://Ecosoft.co.th).
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
    'name': 'Fofo Accounting',
    'category': 'Accounting & Finance',
    'version': '1.0',
    'author': 'Ecosoft',
    'depends': ['base', 'account','account_chart'],
    'website': 'http://Ecosoft.co.th',
    'description': """ 
    """,
    'data': [
             'data/account.account.csv',
#              'data/account.account.type.csv',
             'data/account.tax.code.csv',
             'data/account.tax.csv',
             'fofo_import_wizard.xml'
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
