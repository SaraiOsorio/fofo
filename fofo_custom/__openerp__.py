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
    'name' : 'Ecosoft Custom - Fofo',
    'version': '1.0',
    'author': 'Ecosoft',
    'website' : 'http://www.ecosoft.co.th',
    'category': 'Ecosoft Custom',
    'description':"""
- Container Order Management.
    """,
    'data':[
            'security/ir.model.access.csv',
            'views/partner_view.xml',
            'views/product_view.xml',
            'views/picking_view.xml',
            'views/invoice_view.xml',
            'views/container_order_view.xml',
            'views/container_order_sequence.xml',
            'views/container_order_workflow.xml',
            'views/purchase_view.xml',
            'views/stock_picking_report.xml',
            'container_report.xml',
            'data/container_order_email_template.xml',
            'data/product_data.xml',
            'report/report_container_order.xml'
            ],
    'depends':['sale','purchase','account', 'stock',
               'order_invoice_line_percentage'],
    'installable':True,
    'auto_install':False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
