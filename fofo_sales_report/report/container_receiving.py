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

from openerp.osv import osv
from openerp.report import report_sxw

class container_receiving_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context={}):
        super(container_receiving_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                                  'get_container_order': self._get_container_order,
                                  'get_order_lines' : self._get_order_lines
        })
        
    def _get_container_order(self, data):
        start_date = data['form']['start_date']
        end_date = data['form']['end_date']
        company_id = data['form']['company_id'][0]
        container_ids = data['form']['container_ids']
        domain = [('state', '=', 'confirm'),
                  ('arrive_date', '>=', start_date),
                  ('arrive_date', '<=', end_date),
                  ('company_id', '=', company_id)]
        if container_ids:
            shipper_containers = self.pool.get('container.shipper.number').browse(self.cr, self.uid, container_ids)
            numbers = [x.name for x in shipper_containers]
            domain.append(('container_shipper_number', 'in', numbers))
        order_list = []
        order_ids = self.pool.get('container.order').search(self.cr, self.uid, domain)
        order_data = self.pool.get('container.order').browse(self.cr, self.uid, order_ids)
        for o in order_data:
            order_list.append(o)
        return order_list

    def _get_order_lines(self, order):
        self.cr.execute("""SELECT 
                                co_line.id,
                                product.default_code as product,
                                tmpl.name as product_description, 
                                co_line.number_packages as qty_boxes,
                                tmpl.description_purchase as supplier_description,
                                co.arrive_date as arrive_date
                            FROM 
                                container_order_line co_line 
                            LEFT JOIN container_order co 
                                ON (co_line.container_order_id = co.id) 
                            LEFT JOIN purchase_order_line as pol
                                ON (co_line.po_line_id = pol.id)
                            LEFT JOIN product_product product 
                                ON (co_line.product_id = product.id) 
                            LEFT JOIN product_template tmpl 
                                ON (product.product_tmpl_id = tmpl.id) 
                            WHERE
                                 co.id = %s
                            """, (order.id, ))
        query_data = self.cr.dictfetchall()
        return query_data
        
class report_test(osv.AbstractModel):
    _name = "report.fofo_sales_report.container_receiving_report"
    _inherit = "report.abstract_report"
    _template = "fofo_sales_report.container_receiving_report"
    _wrapped_report_class = container_receiving_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
