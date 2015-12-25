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
    'name' : 'Master Data for FOFO',
    'version': '1.0',
    'author': 'Ecosoft',
    'website' : 'http://www.ecosoft.co.th',
    'category': 'Master Data for FOFO',
    'description':"""

* Payment Term [Commented]
* Partner Tag [Commented]
* Product Category [Commented]
* Product 
    """,
    'data':[
#         'res.partner.category.csv',
#         'account.payment.term.csv',
#         'product.category.csv',
#         'product.ul.csv',
        'product_data.xml',  # Price List
#         'res.partner.csv',
#         'product.product.csv',
#         'product.supplierinfo.csv', # Please delete product_supplierinfo, pricelist_partnerinfo
    ],
    'depends':['sale','purchase','account', 'stock'],
    'installable':True,
    'auto_install':False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
